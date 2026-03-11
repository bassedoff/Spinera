# GLM BACKLOG — New Spinora

> Рабочий backlog-файл для coding-агента (GLM / GLM-5 / другой агентный LLM).
> Цель: не обсуждать проект абстрактно, а пошагово довести его до рабочего состояния без расползания архитектуры.

---

# 0. Как агент должен работать с этим файлом

## 0.1 Режим работы
Работай строго по фазам. Не перепрыгивай через критические зависимости.

Сначала:
1. изучи структуру репозитория;
2. найди все точки входа;
3. найди все legacy-слои;
4. только после этого начинай переписывание.

## 0.2 Обязательные правила

### Нельзя
- нельзя продолжать развивать dual-storage логику (`JSON + SQLite`) как production-решение;
- нельзя оставлять несовместимые связи между Node- и Python-слоями;
- нельзя определять исход вращения колеса на клиенте;
- нельзя доверять фронтенду в вопросах прав, идентичности пользователя, giveaway, канала, приза, статуса участия;
- нельзя внедрять новые экраны поверх сломанной архитектуры, не устранив базовые блокеры;
- нельзя оставлять production flow на моках и заглушках;
- нельзя сохранять критичную бизнес-логику только во frontend;
- нельзя менять продуктовую механику без явной необходимости;
- нельзя оставлять полурабочие TODO как якобы завершённую функцию.

### Нужно
- привести проект к единой архитектуре;
- сделать один источник истины для данных;
- разделить creator flow и participant flow;
- реализовать полноценный жизненный цикл giveaway;
- обеспечить планирование публикации и завершения;
- сделать безопасную Mini App auth;
- сделать серверную механику спина;
- логировать все критичные действия.

## 0.3 Принцип исполнения
Каждую фазу закрывай только после:
1. изменения кода;
2. локальной проверки;
3. фиксации результата в `STATUS.md`;
4. перечисления затронутых файлов;
5. перечисления оставшихся рисков.

## 0.4 Что создать в репозитории сразу
Если файлов нет — создай:
- `STATUS.md` — журнал выполнения;
- `docs/architecture.md` — краткая целевая архитектура;
- `docs/domain-model.md` — сущности и связи;
- `docs/api-contract.md` — API-контракты;
- `docs/runbook.md` — как запускать проект локально;
- `docs/migrations.md` — история и правила миграций.

---

# 1. Цель проекта

Нужно превратить текущий прототип в рабочий сервис Telegram-розыгрышей формата **Wheel of Fortune**.

Итоговый продукт должен уметь:
1. подключать Telegram-канал владельца;
2. создавать giveaway через Mini App-админку;
3. выбирать пост, призы, дату публикации и дату окончания;
4. отправлять превью в бота;
5. публиковать giveaway в канал сразу или по расписанию;
6. открывать конкретный giveaway для участника через Mini App;
7. давать пользователю один корректный серверный spin;
8. сохранять результаты, победителей и статус выдачи призов.

---

# 2. Зафиксированные продуктовые контуры

## 2.1 Creator Flow
Роль: владелец канала.

Должен уметь:
- подключить канал;
- создать/выбрать пост;
- создать giveaway;
- выбрать start/end datetime;
- выбрать канал публикации;
- настроить призы;
- получить preview;
- approve/reject;
- управлять своими giveaway;
- видеть победителей и ошибки публикации.

## 2.2 Participant Flow
Роль: участник giveaway.

Должен уметь:
- открыть конкретный giveaway;
- пройти eligibility check;
- крутить колесо;
- получить результат;
- повторно открыть giveaway и увидеть уже сохранённый статус.

---

# 3. Архитектурное направление

## 3.1 Источник истины
Оставить **одну базу данных**.

Предпочтительно:
- PostgreSQL

Допустимо для MVP:
- SQLite

Но:
- JSON storage не должен участвовать в production flow.

## 3.2 Слои системы
Нужны согласованные слои:
- Telegram Bot
- Backend API
- Admin Mini App
- Public Mini App
- Worker / Scheduler
- DB Layer

## 3.3 Обязательные сущности
Нужно реализовать и использовать единообразно:
- User
- Channel
- PostDraft
- Giveaway
- GiveawayChannel
- GiveawayPrize
- Participant
- Spin
- Winner
- Job
- AuditLog

---

# 4. Приоритет выполнения

## P0 — без этого проект нельзя считать рабочим
- единый data layer;
- запуск backend без несовместимых импортов;
- корректная Mini App auth;
- привязка канала;
- start_at / end_at / timezone;
- preview workflow;
- publish flow;
- public giveaway route;
- server-side spin;
- participants / winners / logs.

## P1 — обязательно после P0
- список giveaway;
- retry publication;
- winners UI;
- errors/logs UI;
- базовая аналитика.

## P2 — улучшения
- мультиязычность;
- экспорт победителей;
- дублирование giveaway;
- расширенная аналитика;
- дополнительные игровые механики.

---

# 5. Пошаговый backlog

---

# PHASE 0 — Inventory, audit, freeze legacy

## TASK-000 — Провести инвентаризацию проекта
### Цель
Понять реальную структуру проекта до переписывания.

### Что сделать
- перечислить все директории и точки входа;
- зафиксировать runtime-слои;
- определить, где живёт bot logic;
- определить, где живёт API logic;
- определить, где живёт frontend admin;
- определить, есть ли public frontend или он отсутствует;
- определить, где используется JSON storage;
- определить, где используется SQLite;
- определить, какие модули несовместимы между собой.

### Выход
Создать/обновить:
- `docs/architecture.md`
- `STATUS.md`

### Definition of Done
- есть карта проекта;
- есть список всех точек входа;
- есть список legacy-слоёв;
- есть список блокеров запуска.

---

## TASK-001 — Заморозить legacy-поведение
### Цель
Чтобы агент не продолжал дорабатывать сломанные ветки по инерции.

### Что сделать
- отметить JSON storage как legacy;
- отметить старые endpoint’ы как deprecated;
- выделить места, которые должны быть переписаны, а не патчены;
- пометить небезопасные auth-пути;
- зафиксировать несовместимые Node↔Python вызовы.

### Выход
- раздел `Legacy Freeze` в `docs/architecture.md`
- запись в `STATUS.md`

### Definition of Done
- legacy обозначен явно;
- агент понимает, что нельзя строить новый функционал поверх старой схемы.

---

# PHASE 1 — Stabilize architecture

## TASK-010 — Убрать несовместимые импорты и привести backend к рабочему запуску
### Цель
Сделать backend физически запускаемым.

### Что сделать
- найти все места, где один runtime пытается напрямую использовать несовместимые модули другого runtime;
- заменить их на корректный слой взаимодействия;
- если логика должна жить в backend — перенести её в backend-совместимый модуль;
- устранить точки, где Node ожидает Python-модуль как JS или наоборот;
- привести конфигурацию запуска к одному понятному сценарию.

### Скорее всего затронутые области
- `web/*`
- `bot/*`
- `data/*`
- entrypoint-скрипты запуска

### Выход
- backend стартует локально;
- бот стартует локально;
- нет явных incompatible import errors.

### Definition of Done
- проект можно поднять локально без падения на базовых импортах;
- запуск описан в `docs/runbook.md`.

---

## TASK-011 — Выбрать единый production storage
### Цель
Убрать разрыв между JSON и SQLite.

### Что сделать
- выбрать production storage;
- переподключить все бизнес-операции к одному data layer;
- исключить JSON storage из рабочего пути creator/participant flow;
- если нужен переходный период — сделать явный migration path, но не dual logic.

### Выход
- `docs/migrations.md`
- обновлённый `docs/domain-model.md`
- единый repository/service layer

### Definition of Done
- post drafts, channels, giveaways, prizes, participants, winners работают через один storage;
- JSON не участвует в production flow.

---

## TASK-012 — Собрать доменную модель
### Цель
Сделать проект не набором случайных объектов, а системой со связями.

### Что сделать
- описать сущности и поля;
- описать связи между сущностями;
- описать обязательные индексы и уникальные ограничения;
- описать статусы giveaway и allowed transitions.

### Обязательные сущности
- User
- Channel
- PostDraft
- Giveaway
- GiveawayChannel
- GiveawayPrize
- Participant
- Spin
- Winner
- Job
- AuditLog

### Выход
- `docs/domain-model.md`
- миграции / init schema

### Definition of Done
- schema соответствует продуктовой логике;
- нет “висящих” сущностей без понятной роли.

---

# PHASE 2 — Auth and trust boundaries

## TASK-020 — Реализовать безопасную Mini App auth на backend
### Цель
Перестать доверять клиентскому payload без серверной валидации.

### Что сделать
- валидировать Telegram Mini App init data на backend;
- извлекать пользователя только после верификации;
- ввести TTL / ограничение времени жизни auth context;
- унифицировать auth middleware для creator API и public API;
- логировать ошибки auth.

### Нельзя
- принимать user id из клиента без проверки;
- принимать init data “как есть” без подписи.

### Выход
- auth middleware
- unit/integration checks для auth flow
- описание в `docs/api-contract.md`

### Definition of Done
- backend не доверяет raw frontend user payload;
- auth используется единообразно.

---

## TASK-021 — Закрыть trust boundaries
### Цель
Чтобы фронтенд не мог подменять критичные сущности.

### Что сделать
- серверно проверять принадлежность канала пользователю;
- серверно проверять принадлежность post_draft пользователю;
- серверно проверять принадлежность giveaway пользователю;
- запретить “ручной” доступ к чужим giveaway через id;
- в participant flow не доверять prize id, result, eligibility status с клиента.

### Definition of Done
- все объектные права проверяются сервером;
- нет критичных операций, основанных только на клиентских данных.

---

# PHASE 3 — Channel binding

## TASK-030 — Реализовать production-flow подключения канала
### Цель
Сделать реальную привязку канала к владельцу.

### Что сделать
- реализовать сценарий подключения канала через бота;
- реализовать подтверждение после добавления бота в канал;
- проверить существование канала;
- проверить, что бот состоит в канале;
- проверить, что бот имеет права администратора;
- проверить, что бот может публиковать;
- сохранить канал как сущность Channel.

### Важно
Канал должен считаться доступным только после успешной проверки прав.

### Выход
- creator может видеть свои каналы;
- канал доступен в мастере giveaway.

### Definition of Done
- канал реально подтверждается через Telegram;
- канал появляется в списке creator channels;
- неподтверждённый канал не участвует в publish flow.

---

## TASK-031 — Сделать экран/раздел “Мои каналы”
### Цель
Дать создателю понятный доступ к управлению каналами.

### Что сделать
- показать список подключённых каналов;
- показать статус прав бота;
- показать, активен канал или нет;
- предусмотреть повторную проверку прав.

### Definition of Done
- creator видит свои каналы в админке;
- статусы каналов прозрачны.

---

# PHASE 4 — Post drafts

## TASK-040 — Нормализовать сущность PostDraft
### Цель
Убрать разрозненное хранение постов.

### Что сделать
- определить единую модель post draft;
- поддержать типы контента: text / photo / video / document (если продукт разрешает);
- связать draft с owner;
- реализовать create/list/read.

### Definition of Done
- post draft хранится в едином storage;
- используется в creator flow без JSON legacy.

---

## TASK-041 — Реализовать creator flow создания поста
### Цель
Сделать черновики постов реальной частью системы.

### Что сделать
- бот должен позволять создать черновик;
- backend должен сохранить post draft;
- admin mini app должен уметь читать post drafts;
- draft должен быть доступен для выбора в wizard.

### Definition of Done
- creator может создать post draft и использовать его в giveaway wizard.

---

# PHASE 5 — Giveaway creation wizard

## TASK-050 — Реализовать Giveaway CRUD как центральную сущность
### Цель
Сделать giveaway главным объектом системы, а не побочным результатом мастера.

### Что сделать
- создать Giveaway entity;
- реализовать create/read/update/list;
- обеспечить owner-based access;
- поддержать статусы и transitions.

### Обязательные поля
- type
- title
- description
- language
- post_draft_id
- start_at
- end_at
- timezone
- status
- public_slug / deeplink_token
- rules_json

### Definition of Done
- giveaway существует как полноценная сущность;
- giveaway не является эфемерным объектом только во frontend state.

---

## TASK-051 — Очистить wizard от неподдерживаемых режимов
### Цель
Не обещать пользователю то, чего backend не поддерживает.

### Что сделать
- оставить в production только `wheel`;
- `case` убрать из UI или скрыть фичефлагом;
- синхронизировать фронтенд и backend по allowed giveaway types.

### Definition of Done
- UI и backend не расходятся в supported modes.

---

## TASK-052 — Реализовать шаг выбора канала
### Цель
Привязать wizard к реальным каналам creator’а.

### Что сделать
- wizard должен получать список только подтверждённых каналов;
- нельзя вручную подсунуть произвольный канал;
- канал должен серверно проверяться как принадлежащий creator.

### Definition of Done
- giveaway нельзя создать на чужой или неподтверждённый канал.

---

## TASK-053 — Реализовать шаг призов
### Цель
Сделать prize configuration бизнес-значимой и валидной.

### Что сделать
- реализовать giveaway prizes;
- минимум поля: title, description, total_quantity, remaining_quantity, weight, sort_order;
- валидировать, что prizes не пустые;
- валидировать, что total_quantity > 0;
- валидировать, что weight > 0;
- предусмотреть проигрышный результат как часть конфигурации.

### Definition of Done
- призы сохраняются и читаются через backend;
- prize configuration валидируется до preview/publish.

---

## TASK-054 — Реализовать планирование
### Цель
Закрыть центральную продуктовую дыру.

### Что сделать
- добавить `start_at`;
- добавить `end_at`;
- добавить `timezone`;
- добавить publication mode: immediate / scheduled;
- валидировать, что `end_at > start_at`;
- валидировать, что публикация не уходит в прошлое.

### Definition of Done
- giveaway может быть запущен сразу или по расписанию;
- даты и время участвуют в state machine.

---

# PHASE 6 — Preview and approval

## TASK-060 — Реализовать preview workflow
### Цель
Сделать нормальную точку контроля перед публикацией.

### Что сделать
- после завершения wizard переводить giveaway в `pending_preview`;
- собрать preview payload;
- отправить preview в бота создателю;
- сохранить связку giveaway ↔ preview_message_id;
- перевести giveaway в `preview_sent`.

### Preview должно включать
- контент post draft;
- заголовок giveaway;
- даты старта/окончания;
- выбранные каналы;
- список призов;
- CTA / кнопку открытия giveaway;
- действия approve / reject / edit / cancel.

### Definition of Done
- preview приходит в бота;
- giveaway связан с preview message.

---

## TASK-061 — Реализовать approve/reject/edit/cancel
### Цель
Сделать из preview реальную точку принятия решения.

### Что сделать
- approve;
- reject / back to draft;
- cancel;
- редактирование после reject;
- перевод статусов по правилам.

### Definition of Done
- creator может управлять giveaway после preview;
- статус меняется предсказуемо и корректно.

---

# PHASE 7 — Scheduler and publishing

## TASK-070 — Реализовать jobs / scheduler
### Цель
Сделать публикацию и завершение управляемыми по времени.

### Что сделать
- ввести сущность Job;
- реализовать job types минимум:
  - publish
  - finish
  - recheck_channel_permissions
  - notify
- реализовать worker/scheduler;
- реализовать retry policy;
- логировать ошибки выполнения.

### Definition of Done
- scheduled giveaway реально переходит в publish job;
- end jobs реально завершают giveaway.

---

## TASK-071 — Реализовать publish flow
### Цель
Довести publish до реального постинга в канал.

### Что сделать
- перед публикацией повторно проверить права бота;
- проверить существование post draft;
- проверить валидность giveaway;
- опубликовать в Telegram-канал;
- сохранить `published_message_id`, `published_at`;
- перевести giveaway в `active`;
- при ошибке перевести публикацию или giveaway в `failed`;
- уведомить создателя о результате.

### Definition of Done
- giveaway реально публикуется;
- message_id сохраняется;
- ошибки обрабатываются явно.

---

## TASK-072 — Реализовать завершение giveaway
### Цель
Корректно закрывать окно участия.

### Что сделать
- по `end_at` переводить giveaway в `ended`;
- запрещать новые spins после завершения;
- фиксировать итоговый статус;
- инициировать post-end уведомления при необходимости.

### Definition of Done
- после `end_at` участие невозможно;
- giveaway переходит в корректный финальный статус.

---

# PHASE 8 — Public giveaway and participant flow

## TASK-080 — Реализовать public route конкретного giveaway
### Цель
Сделать так, чтобы участник попадал в конкретный giveaway, а не в общую админку.

### Что сделать
- выбрать механизм маршрутизации: `public_slug` и/или `deeplink_token` и/или `start_param`;
- реализовать backend route для публичного чтения giveaway;
- реализовать frontend route public giveaway;
- исключить доступ к creator dashboard из participant context.

### Definition of Done
- по ссылке/кнопке открывается конкретный giveaway;
- пользователь не попадает в админский интерфейс.

---

## TASK-081 — Реализовать public giveaway screen
### Цель
Сделать экран, на котором участник понимает, где он и что будет происходить.

### Что сделать
- показать title;
- показать description;
- показать призы;
- показать визуал колеса;
- показать таймер до окончания;
- показать CTA `Крутить колесо`.

### Definition of Done
- participant видит понятный landing конкретного giveaway.

---

## TASK-082 — Реализовать eligibility check
### Цель
Проверять допуск пользователя до спина.

### Что сделать
- проверить, что giveaway активен;
- проверить auth пользователя;
- проверить, что giveaway не ended;
- проверить, что пользователь ещё не играл;
- при необходимости проверить условия подписки/доступа;
- сохранить eligibility status.

### Definition of Done
- недопустимый пользователь не может перейти к spin;
- допустимый пользователь проходит дальше.

---

# PHASE 9 — Spin engine

## TASK-090 — Реализовать server-side spin engine
### Цель
Убрать фродовую клиентскую механику и сделать результат серверным.

### Что сделать
- создать endpoint spin;
- внутри транзакции:
  - получить/создать participant;
  - повторно проверить eligibility;
  - убедиться, что spin ещё не был выполнен;
  - рассчитать результат;
  - при выигрыше зарезервировать/списать приз;
  - сохранить Spin;
  - при выигрыше создать Winner;
- вернуть клиенту только уже вычисленный результат для анимации.

### Нельзя
- выбирать результат на клиенте;
- принимать prize/result с клиента;
- позволять race conditions раздать один и тот же приз дважды.

### Definition of Done
- один пользователь получает один серверно зафиксированный результат;
- призы списываются атомарно.

---

## TASK-091 — Реализовать participant result screens
### Цель
Показать сохранённый результат корректно.

### Что сделать
- экран win;
- экран lose;
- экран already participated;
- экран giveaway ended;
- повторный вход должен показывать ранее сохранённый результат.

### Definition of Done
- participant flow завершён и не ломается при повторном входе.

---

# PHASE 10 — Winners, logs, analytics

## TASK-100 — Реализовать winners management
### Цель
Дать создателю возможность работать с победителями.

### Что сделать
- сущность Winner;
- список победителей;
- фильтрация по giveaway;
- статусы `pending_issue / issued / cancelled`;
- комментарий менеджера;
- ручное изменение статуса выдачи.

### Definition of Done
- creator видит и управляет победителями.

---

## TASK-101 — Реализовать audit log
### Цель
Сделать поведение системы прозрачным.

### Что сделать
Логировать минимум:
- создание giveaway;
- редактирование giveaway;
- отправку на preview;
- approve/reject/cancel;
- публикацию;
- ошибки публикации;
- spin;
- win;
- изменение статуса winner.

### Definition of Done
- по критичным действиям есть audit trail.

---

## TASK-102 — Реализовать базовую аналитику
### Цель
Дать владельцу хотя бы минимальную полезную картину.

### Что сделать
Считать минимум:
- opens;
- unique opens;
- participants;
- spins;
- wins;
- remaining prizes;
- status giveaway.

### Definition of Done
- creator dashboard показывает базовые цифры по giveaway.

---

# 6. API backlog

## 6.1 Creator API
Реализовать/привести к единому контракту:
- `GET /api/me`
- `GET /api/channels`
- `POST /api/channels/connect/verify`
- `GET /api/post-drafts`
- `POST /api/post-drafts`
- `GET /api/giveaways`
- `GET /api/giveaways/:id`
- `POST /api/giveaways`
- `PATCH /api/giveaways/:id`
- `POST /api/giveaways/:id/preview`
- `POST /api/giveaways/:id/approve`
- `POST /api/giveaways/:id/reject`
- `POST /api/giveaways/:id/cancel`
- `GET /api/giveaways/:id/winners`

## 6.2 Public API
Реализовать:
- `GET /api/public/giveaways/:slug`
- `POST /api/public/giveaways/:id/eligibility-check`
- `POST /api/public/giveaways/:id/spin`
- `GET /api/public/giveaways/:id/result`

## 6.3 Internal jobs
Реализовать внутренние обработчики:
- publish
- finish
- retry
- recheck channel permissions
- notify

---

# 7. UI backlog

## 7.1 Admin Mini App
Нужные экраны:
- Dashboard
- Мои каналы
- Мои посты
- Создать giveaway
- Черновики
- Scheduled
- Active
- Ended
- Failed
- Winners
- Logs / Errors

## 7.2 Public Mini App
Нужные экраны:
- loading
- giveaway landing
- eligibility
- wheel spin
- result
- already participated
- giveaway ended
- error

---

# 8. Definition of Done по продукту

Проект считается завершённым только если:

## 8.1 Creator Flow готов
- пользователь подключает канал;
- создаёт post draft;
- создаёт giveaway;
- задаёт `start_at/end_at/timezone`;
- получает preview в боте;
- approve/reject работает;
- publish работает;
- scheduled publish работает.

## 8.2 Participant Flow готов
- участник попадает в конкретный giveaway;
- проходит eligibility;
- делает один корректный spin;
- получает результат;
- повторный вход показывает сохранённый статус.

## 8.3 Admin Management готов
- creator видит свои giveaway;
- creator видит статусы;
- creator видит winners;
- creator видит ошибки публикации;
- creator может отменять / редактировать / смотреть детали.

## 8.4 Техническая готовность достигнута
- нет production зависимости от legacy JSON;
- нет несовместимых импортов между runtime-слоями;
- auth Mini App валидируется сервером;
- spin логика серверная и атомарная;
- все критичные действия логируются;
- есть миграции и runbook.

---

# 9. Как агент должен отчитываться после каждой фазы

После каждой фазы агент обязан обновлять `STATUS.md` в формате:

```md
## PHASE X — <название>

### Что сделано
- ...

### Какие файлы изменены
- ...

### Что проверено
- ...

### Что осталось / риски
- ...