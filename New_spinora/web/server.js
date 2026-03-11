const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const Storage = require('./storage');
const TelegramAuth = require('./telegram_auth');
const { db } = require('../data/db_manager');
const { validate_channel_identifier, validate_giveaway_data, validate_bot_permissions } = require('../data/validation');

const app = express();
const PORT = process.env.PORT || 3000;
const storage = new Storage(path.join(__dirname, '..', 'data', 'storage.json'));
const telegramAuth = new TelegramAuth(process.env.BOT_TOKEN);

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Authentication middleware
const authenticateUser = (req, res, next) => {
    try {
        // Development mode bypass
        if (process.env.DEV_AUTH_BYPASS === '1') {
            req.user = {
                id: process.env.DEV_TELEGRAM_ID || '123456789',
                username: process.env.DEV_USERNAME || 'testuser',
                first_name: process.env.DEV_FIRST_NAME || 'Test'
            };
            return next();
        }

        // Production mode - parse Telegram init data
        const initDataHeader = req.headers['x-telegram-init-data'];
        if (!initDataHeader) {
            return res.status(401).json({ error: 'Unauthorized', details: 'No init data provided' });
        }

        // Simple parsing without signature validation (will add later)
        const params = new URLSearchParams(initDataHeader);
        const userJson = params.get('user');
        
        if (!userJson) {
            return res.status(401).json({ error: 'Unauthorized', details: 'No user data in init data' });
        }

        const user = JSON.parse(decodeURIComponent(userJson));
        req.user = {
            id: user.id.toString(),
            username: user.username || '',
            first_name: user.first_name || '',
            last_name: user.last_name || ''
        };

        next();
    } catch (error) {
        console.error('Auth error:', error);
        res.status(401).json({ error: 'Authentication failed', details: error.message });
    }
};

// Helper function to ensure user exists in storage
const ensureUserExists = (userId, userData) => {
    const existingUser = storage.getUser(userId);
    if (!existingUser) {
        storage.saveUser({
            telegram_id: userId,
            username: userData.username,
            first_name: userData.first_name,
            last_name: userData.last_name,
            created_at: new Date().toISOString()
        });
    }
};

// Routes

// Health check
app.get('/api/health', (req, res) => {
    res.json({ ok: true });
});

// Get current user
app.get('/api/me', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    res.json(req.user);
});

// Get user posts
app.get('/api/posts', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const scope = req.query.scope || 'drafts';
    let posts = [];
    
    if (scope === 'drafts') {
        posts = storage.getUserPosts(req.user.id);
    }
    
    res.json(posts);
});

// Create post (placeholder for future use)
app.post('/api/posts', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const { type, file_id, text } = req.body;
    
    if (!type) {
        return res.status(400).json({ error: 'Missing post type' });
    }
    
    const postData = { type, file_id, text };
    const postId = storage.savePostDraft(req.user.id, postData);
    
    res.json({ id: postId });
});

// Get wizard draft
app.get('/api/wizard/draft', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const draft = storage.getGiveawayDraft(req.user.id);
    res.json(draft || {});
});

// Save wizard draft
app.post('/api/wizard/draft', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const { step, draft } = req.body;
    
    if (!step || !draft) {
        return res.status(400).json({ error: 'Missing step or draft data' });
    }
    
    storage.saveGiveawayDraft(req.user.id, step, draft);
    res.json({ success: true });
});

// Get user giveaways
app.get('/api/giveaways', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const scope = req.query.scope || 'created';
    let giveaways = [];
    
    if (scope === 'created') {
        giveaways = storage.getUserGiveaways(req.user.id);
    }
    
    res.json(giveaways);
});

// Resolve and save channel
app.post('/api/channels/resolve', authenticateUser, async (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const { identifier } = req.body;
    
    if (!identifier) {
        return res.status(400).json({ error: 'Channel identifier is required' });
    }
    
    // Validate identifier format
    const [isValid, errorMsg] = validate_channel_identifier(identifier);
    if (!isValid) {
        return res.status(400).json({ error: errorMsg });
    }
    
    try {
        // In development mode, simulate channel resolution
        if (process.env.DEV_AUTH_BYPASS === '1') {
            const mockChannel = {
                chat_id: -1001234567890, // Mock chat ID
                title: `Channel ${identifier}`,
                username: identifier.startsWith('@') ? identifier.substring(1) : `channel_${Math.abs(parseInt(identifier))}`,
                bot_is_admin: true,
                bot_can_post: true
            };
            
            const savedChannel = db.resolve_and_save_channel(
                parseInt(req.user.id), 
                identifier, 
                mockChannel
            );
            
            return res.json(savedChannel);
        }
        
        // TODO: Implement real Telegram API calls for production
        // This would involve calling getChat and getChatMember APIs
        
        res.status(501).json({ error: 'Channel resolution not implemented in production mode yet' });
        
    } catch (error) {
        console.error('Error resolving channel:', error);
        res.status(500).json({ error: 'Failed to resolve channel', details: error.message });
    }
});

// Get user channels
app.get('/api/channels', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    try {
        const channels = db.get_user_channels(parseInt(req.user.id));
        res.json(channels);
    } catch (error) {
        console.error('Error getting channels:', error);
        res.status(500).json({ error: 'Failed to get channels', details: error.message });
    }
});

// Create giveaway (new implementation with DB)
app.post('/api/wizard/commit', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const giveawayData = req.body;
    
    // Validate giveaway data
    const [isValid, errors] = validate_giveaway_data(giveawayData);
    if (!isValid) {
        return res.status(400).json({ error: 'Validation failed', details: errors });
    }
    
    try {
        // Create giveaway in database
        const giveawayId = db.create_giveaway(
            parseInt(req.user.id),
            giveawayData.title,
            giveawayData.language || 'en',
            giveawayData.postId, // post_draft_id
            giveawayData.channels, // array of channel IDs
            giveawayData.prizes
        );
        
        res.json({ giveaway_id: giveawayId });
    } catch (error) {
        console.error('Error creating giveaway:', error);
        res.status(500).json({ error: 'Failed to create giveaway', details: error.message });
    }
});

// Legacy endpoint for backward compatibility
app.post('/api/giveaways', authenticateUser, (req, res) => {
    ensureUserExists(req.user.id, req.user);
    
    const config = req.body;
    
    if (!config || Object.keys(config).length === 0) {
        return res.status(400).json({ error: 'Missing giveaway configuration' });
    }
    
    try {
        const giveawayId = storage.createGiveaway(req.user.id, config);
        res.json({ giveaway_id: giveawayId });
    } catch (error) {
        console.error('Error creating giveaway:', error);
        res.status(500).json({ error: 'Failed to create giveaway', details: error.message });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).json({ error: 'Internal server error', details: err.message });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`📁 Storage path: ${storage.storagePath}`);
    console.log(`🔧 Dev auth bypass: ${process.env.DEV_AUTH_BYPASS === '1' ? 'ENABLED' : 'DISABLED'}`);
    console.log(`📊 Database: ${process.env.DEV_AUTH_BYPASS === '1' ? 'SQLite (Development)' : 'SQLite'}`);
    console.log('📱 Endpoints available:');
    console.log('  POST /api/channels/resolve - Resolve and save channel');
    console.log('  GET /api/channels - Get user channels');
    console.log('  POST /api/wizard/commit - Create giveaway');
});