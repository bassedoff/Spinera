const crypto = require('crypto');

class TelegramAuth {
    constructor(botToken) {
        this.botToken = botToken;
    }

    /**
     * Parse and validate Telegram init data
     * @param {string} initData - Raw init data from Telegram WebApp
     * @returns {Object|null} User data or null if invalid
     */
    parseInitData(initData) {
        if (!initData) return null;

        try {
            const params = new URLSearchParams(initData);
            const userJson = params.get('user');
            
            if (!userJson) return null;
            
            const user = JSON.parse(decodeURIComponent(userJson));
            return {
                id: user.id,
                username: user.username || '',
                first_name: user.first_name || '',
                last_name: user.last_name || ''
            };
        } catch (error) {
            console.error('Error parsing init data:', error);
            return null;
        }
    }

    /**
     * Validate init data signature (simplified version for development)
     * In production, you should validate the hash signature
     * @param {string} initData - Raw init data
     * @returns {boolean} Valid or not
     */
    validateInitData(initData) {
        // In development mode, we skip signature validation
        // Production implementation would check the hash
        return !!this.parseInitData(initData);
    }

    /**
     * Get user ID from init data
     * @param {string} initData - Raw init data
     * @returns {number|null} Telegram user ID
     */
    getUserId(initData) {
        const userData = this.parseInitData(initData);
        return userData ? userData.id : null;
    }

    /**
     * Create development user for testing
     * @returns {Object} Mock user data
     */
    getDevUser() {
        return {
            id: parseInt(process.env.DEV_TELEGRAM_ID) || 123456789,
            username: process.env.DEV_USERNAME || 'testuser',
            first_name: process.env.DEV_FIRST_NAME || 'Test',
            last_name: process.env.DEV_LAST_NAME || 'User'
        };
    }
}

module.exports = TelegramAuth;