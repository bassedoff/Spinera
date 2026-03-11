import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
from datetime import datetime

from config import Config
from storage import Storage  # LEGACY - will be removed in future
from data.db_manager import db
import sqlite3

# Configure logging
# Configure logging with absolute paths
import os
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'bot.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
Config.validate()
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()
router = Router()
storage = Storage(Config.STORAGE_PATH)

class PostStates(StatesGroup):
    waiting_post = State()

def get_main_menu():
    """Create main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🧩 Запустить приложение",
        web_app=WebAppInfo(url=Config.WEB_APP_URL)
    )
    builder.button(text="📝 Создать пост", callback_data="create_post")
    builder.button(text="📣 Мои каналы", callback_data="my_channels")
    builder.adjust(1)
    return builder.as_markup()

def get_preview_buttons(giveaway_id: int):
    """Create preview confirmation buttons"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Все хорошо!", callback_data=f"giveaway_approve:{giveaway_id}")
    builder.button(text="❌ Отклонить", callback_data=f"giveaway_reject:{giveaway_id}")
    builder.adjust(1)
    return builder.as_markup()

async def send_giveaway_preview(bot, user_id: int, giveaway_id: int):
    """Send giveaway preview to user"""
    try:
        # Get giveaway data
        giveaway = db.get_giveaway(giveaway_id)
        if not giveaway:
            await bot.send_message(user_id, "❌ Розыгрыш не найден")
            return
        
        # Get post draft
        post_draft = db.get_post_draft(giveaway['post_draft_id'])
        if not post_draft:
            await bot.send_message(user_id, "❌ Пост не найден")
            return
        
        # Send post content
        if post_draft['type'] == 'photo' and post_draft['file_id']:
            await bot.send_photo(
                user_id,
                photo=post_draft['file_id'],
                caption=post_draft['text'] or ""
            )
        elif post_draft['type'] == 'video' and post_draft['file_id']:
            await bot.send_video(
                user_id,
                video=post_draft['file_id'],
                caption=post_draft['text'] or ""
            )
        elif post_draft['type'] == 'document' and post_draft['file_id']:
            await bot.send_document(
                user_id,
                document=post_draft['file_id'],
                caption=post_draft['text'] or ""
            )
        else:
            # Text post
            await bot.send_message(user_id, post_draft['text'] or "Пост без текста")
        
        # Send giveaway header with buttons
        header_text = (
            f"🎯 РОЗЫГРЫШ: {giveaway['title']}\n\n"
            f"📍 Каналы: {len(giveaway['channels'])}\n"
            f"🎁 Призы: {len(giveaway['prizes'])}\n\n"
            f"Все верно?"
        )
        
        await bot.send_message(
            user_id,
            header_text,
            reply_markup=get_preview_buttons(giveaway_id)
        )
        
        logger.info(f"Sent preview for giveaway {giveaway_id} to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending giveaway preview: {e}")
        await bot.send_message(user_id, "❌ Ошибка при отправке превью")

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    logger.info(f"User {message.from_user.id} started bot")
    
    # Save user data to SQLite (production)
    db.create_or_update_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or ""
    )
    
    # LEGACY: Also save to JSON for backward compatibility during transition
    # TODO: Remove this after full migration to SQLite
    user_data = {
        "telegram_id": str(message.from_user.id),
        "username": message.from_user.username or "",
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
        "created_at": datetime.now().isoformat()
    }
    storage.save_user(user_data)
    
    await message.answer(
        "🎯 Добро пожаловать в SpinoraBot!\n\n"
        "Создавайте розыгрыши \"Колесо фортуны\" для ваших Telegram каналов.",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "create_post")
async def create_post_callback(callback_query, state: FSMContext):
    """Handle create post button"""
    logger.info(f"User {callback_query.from_user.id} wants to create post")
    
    await callback_query.message.edit_text(
        "📝 Отправьте мне фото, видео, документ или просто текст для поста.\n\n"
        "Вы можете добавить описание в caption.",
        reply_markup=None
    )
    
    await callback_query.answer()
    # Set state to wait for post
    await state.set_state(PostStates.waiting_post)

@router.message(PostStates.waiting_post)
async def handle_post(message: Message, state: FSMContext):
    """Handle incoming post"""
    logger.info(f"Received post from user {message.from_user.id}")
    
    # Determine post type
    if message.photo:
        post_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        post_type = "video"
        file_id = message.video.file_id
    elif message.document:
        post_type = "document"
        file_id = message.document.file_id
    elif message.text:
        post_type = "text"
        file_id = None
    else:
        await message.reply("❌ Поддерживаются только фото, видео, документы и текст.")
        return
    
    # Save post draft to SQLite (production)
    try:
        post_id = db.create_post_draft(
            telegram_id=message.from_user.id,
            post_type=post_type,
            file_id=file_id,
            text=message.caption or message.text or ""
        )
        logger.info(f"Saved post draft {post_id} for user {message.from_user.id} to SQLite")
    except Exception as e:
        logger.error(f"Error saving post to SQLite: {e}")
        await message.reply("❌ Ошибка при сохранении поста. Попробуйте еще раз.")
        return
    
    # LEGACY: Also save to JSON for backward compatibility during transition
    # TODO: Remove this after full migration to SQLite
    post_data = {
        "type": post_type,
        "file_id": file_id,
        "text": message.caption or message.text or ""
    }
    storage.save_post_draft(str(message.from_user.id), post_data)
    
    await message.reply(
        f"✅ Пост сохранён. ID: {post_id}\n\n"
        f"Теперь вы можете создать розыгрыш в мини-приложении.",
        reply_markup=get_main_menu()
    )
    
    await state.clear()

@router.callback_query(F.data == "my_channels")
async def my_channels_callback(callback_query):
    """Handle my channels button"""
    logger.info(f"User {callback_query.from_user.id} requested channels")
    
    # Get user channels (placeholder for now)
    channels = storage.get_user_channels(str(callback_query.from_user.id))
    
    if channels:
        channels_text = "\n".join([f"• {ch['title']} (@{ch['username']})" for ch in channels])
        response = f"📺 Ваши каналы:\n\n{channels_text}"
    else:
        response = (
            "📺 У вас пока нет сохраненных каналов.\n\n"
            "Добавьте каналы в процессе создания розыгрыша."
        )
    
    await callback_query.message.edit_text(response, reply_markup=get_main_menu())
    await callback_query.answer()

@router.callback_query(F.data.startswith("giveaway_approve:"))
async def approve_giveaway_callback(callback_query):
    """Handle giveaway approval"""
    try:
        giveaway_id = int(callback_query.data.split(":")[1])
        user_id = callback_query.from_user.id
        
        logger.info(f"User {user_id} approved giveaway {giveaway_id}")
        
        # Update giveaway status
        db.update_giveaway_status(giveaway_id, 'approved')
        
        # TODO: Implement actual posting to channels
        # For now, just simulate success
        
        await callback_query.message.edit_text(
            f"✅ Розыгрыш одобрен!\n\n"
            f"ID: {giveaway_id}\n"
            f"Статус: Одобрено\n\n"
            f"Пост будет опубликован в выбранные каналы."
        )
        
        await callback_query.answer("Розыгрыш одобрен!")
        
    except Exception as e:
        logger.error(f"Error approving giveaway: {e}")
        await callback_query.answer("Ошибка при одобрении")
        await callback_query.message.reply("❌ Ошибка при одобрении розыгрыша")

@router.callback_query(F.data.startswith("giveaway_reject:"))
async def reject_giveaway_callback(callback_query):
    """Handle giveaway rejection"""
    try:
        giveaway_id = int(callback_query.data.split(":")[1])
        user_id = callback_query.from_user.id
        
        logger.info(f"User {user_id} rejected giveaway {giveaway_id}")
        
        # Update giveaway status
        db.update_giveaway_status(giveaway_id, 'rejected')
        
        await callback_query.message.edit_text(
            f"❌ Розыгрыш отклонен\n\n"
            f"ID: {giveaway_id}\n"
            f"Статус: Отклонено\n\n"
            f"Вернитесь в мини-приложение и создайте заново."
        )
        
        await callback_query.answer("Розыгрыш отклонен")
        
    except Exception as e:
        logger.error(f"Error rejecting giveaway: {e}")
        await callback_query.answer("Ошибка при отклонении")
        await callback_query.message.reply("❌ Ошибка при отклонении розыгрыша")

@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Handle data from web app"""
    logger.info(f"Received web app data from user {message.from_user.id}")
    logger.info(f"Web app data content: {message.web_app_data.data}")
    
    try:
        # Parse web app data
        data = json.loads(message.web_app_data.data)
        event = data.get("event")
        
        if event == "giveaway_preview_request":
            # Handle preview request
            giveaway_id = data.get("giveaway_id")
            if giveaway_id:
                await send_giveaway_preview(bot, message.from_user.id, giveaway_id)
            else:
                await message.reply("❌ Не указан ID розыгрыша для превью")
                
        # LEGACY: wizard_commit - kept for backward compatibility during transition
        # New flow uses direct API call to backend instead
        elif event == "wizard_commit":
            logger.warning("Received legacy wizard_commit event - should use direct API call instead")
            config = data.get("payload", {})
            
            # Create in SQLite (production)
            giveaway_id = db.create_giveaway(
                telegram_id=message.from_user.id,
                title=config.get('title', 'Без названия'),
                language=config.get('language', 'en'),
                post_draft_id=config.get('postId'),
                channels=config.get('channels', []),
                prizes=config.get('prizes', [])
            )
            logger.info(f"Created giveaway {giveaway_id} for user {message.from_user.id} in SQLite")
            
            # LEGACY: Also create in JSON for backward compatibility
            storage_giveaway_id = storage.create_giveaway(str(message.from_user.id), config)
            logger.info(f"Created legacy giveaway {storage_giveaway_id} in JSON")
            
            await message.reply(
                f"✅ Розыгрыш создан. ID: {giveaway_id}\n\n"
                f"Название: {config.get('title', 'Без названия')}",
                reply_markup=get_main_menu()
            )
        else:
            await message.reply("❌ Неизвестный тип события.")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in web app data")
        await message.reply("❌ Ошибка обработки данных.")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await message.reply("❌ Ошибка при обработке запроса.")

async def main():
    """Main function"""
    logger.info("Starting bot...")
    
    # Register router
    dp.include_router(router)
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())