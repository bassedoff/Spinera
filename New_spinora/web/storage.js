const fs = require('fs');
const path = require('path');

class Storage {
    constructor(storagePath) {
        this.storagePath = storagePath;
        this.lock = false;
        this.ensureStorageExists();
    }

    ensureStorageExists() {
        const dir = path.dirname(this.storagePath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        if (!fs.existsSync(this.storagePath)) {
            const initialData = {
                users: {},
                post_drafts: {},
                giveaway_drafts: {},
                giveaways: {},
                channels: {},
                counters: {
                    post_id: 0,
                    giveaway_id: 0
                }
            };
            this.atomicWrite(initialData);
        }
    }

    atomicWrite(data) {
        const tempPath = `${this.storagePath}.tmp`;
        try {
            fs.writeFileSync(tempPath, JSON.stringify(data, null, 2));
            fs.renameSync(tempPath, this.storagePath);
        } catch (error) {
            if (fs.existsSync(tempPath)) {
                fs.unlinkSync(tempPath);
            }
            throw error;
        }
    }

    readStorage() {
        // Simple mutex implementation
        while (this.lock) {
            // Wait for unlock
        }
        this.lock = true;
        
        try {
            const data = fs.readFileSync(this.storagePath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Error reading storage:', error);
            return {
                users: {},
                post_drafts: {},
                giveaway_drafts: {},
                giveaways: {},
                channels: {},
                counters: { post_id: 0, giveaway_id: 0 }
            };
        } finally {
            this.lock = false;
        }
    }

    writeStorage(data) {
        // Simple mutex implementation
        while (this.lock) {
            // Wait for unlock
        }
        this.lock = true;
        
        try {
            this.atomicWrite(data);
        } finally {
            this.lock = false;
        }
    }

    getUser(telegramId) {
        const storage = this.readStorage();
        return storage.users[telegramId] || null;
    }

    saveUser(userData) {
        const storage = this.readStorage();
        storage.users[userData.telegram_id] = userData;
        this.writeStorage(storage);
    }

    savePostDraft(telegramId, postData) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        
        // Increment counter
        storage.counters.post_id += 1;
        const postId = storage.counters.post_id;
        
        // Prepare post data
        const postEntry = {
            id: postId,
            type: postData.type,
            file_id: postData.file_id,
            text: postData.text || "",
            created_at: new Date().toISOString()
        };
        
        // Save to user's drafts
        if (!storage.post_drafts[userId]) {
            storage.post_drafts[userId] = [];
        }
        storage.post_drafts[userId].push(postEntry);
        
        this.writeStorage(storage);
        return postId;
    }

    getUserPosts(telegramId) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        return storage.post_drafts[userId] || [];
    }

    saveGiveawayDraft(telegramId, step, draftData) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        
        storage.giveaway_drafts[userId] = {
            step: step,
            draft: draftData,
            updated_at: new Date().toISOString()
        };
        
        this.writeStorage(storage);
    }

    getGiveawayDraft(telegramId) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        return storage.giveaway_drafts[userId] || null;
    }

    createGiveaway(telegramId, config) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        
        // Increment counter
        storage.counters.giveaway_id += 1;
        const giveawayId = `G-${storage.counters.giveaway_id.toString().padStart(4, '0')}`;
        
        // Prepare giveaway data
        const giveawayEntry = {
            id: giveawayId,
            status: "created",
            config: config,
            created_at: new Date().toISOString()
        };
        
        // Save to user's giveaways
        if (!storage.giveaways[userId]) {
            storage.giveaways[userId] = [];
        }
        storage.giveaways[userId].push(giveawayEntry);
        
        this.writeStorage(storage);
        return giveawayId;
    }

    getUserGiveaways(telegramId) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        return storage.giveaways[userId] || [];
    }

    saveChannels(telegramId, channels) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        storage.channels[userId] = channels;
        this.writeStorage(storage);
    }

    getUserChannels(telegramId) {
        const storage = this.readStorage();
        const userId = telegramId.toString();
        return storage.channels[userId] || [];
    }
}

module.exports = Storage;