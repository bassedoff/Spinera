class SpinoraApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.wizardData = {
            type: '',
            title: '',
            language: 'en',  // Changed from 'ru' to 'en'
            postId: null,
            channels: [],  // Now stores real channel objects
            prizes: []
        };
        this.posts = [];
        this.selectedPost = null;
        this.resolvedChannels = [];  // Store resolved real channels
        
        this.init();
    }

    async init() {
        // Initialize Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        this.bindEvents();
        await this.loadUserData();
        await this.loadPosts();
        this.renderPosts();
    }

    bindEvents() {
        // Main screen events
        document.getElementById('refresh-posts').addEventListener('click', () => this.loadPosts());
        document.getElementById('create-giveaway-btn').addEventListener('click', () => this.showWizard());

        // Wizard navigation
        document.getElementById('wizard-back').addEventListener('click', () => this.hideWizard());
        document.getElementById('wizard-prev').addEventListener('click', () => this.previousStep());
        document.getElementById('wizard-next').addEventListener('click', () => this.nextStep());
        document.getElementById('wizard-finish').addEventListener('click', () => this.finishWizard());

        // Step 1 - Type selection
        document.querySelectorAll('.type-card').forEach(card => {
            card.addEventListener('click', (e) => {
                document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
                e.currentTarget.classList.add('selected');
                this.wizardData.type = e.currentTarget.dataset.type;
            });
        });

        // Step 2 - Settings
        document.getElementById('select-post-btn').addEventListener('click', () => this.showPostsModal());
        document.getElementById('change-post-btn').addEventListener('click', () => this.showPostsModal());

        // Step 3 - Channels
        document.getElementById('add-channel-btn').addEventListener('click', () => this.addChannel());
        document.getElementById('channel-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addChannel();
        });

        // Step 4 - Prizes
        document.getElementById('add-prize-btn').addEventListener('click', () => this.addPrize());

        // Modal events
        document.getElementById('close-posts-modal').addEventListener('click', () => this.hidePostsModal());
        document.getElementById('success-close').addEventListener('click', () => this.hideSuccessModal());

        // Close modals when clicking outside
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.add('hidden');
            });
        });
    }

    async loadUserData() {
        try {
            const response = await this.apiFetch('/api/me');
            if (response.ok) {
                this.user = await response.json();
            }
        } catch (error) {
            console.error('Error loading user data:', error);
        }
    }

    async loadPosts() {
        try {
            const response = await this.apiFetch('/api/posts?scope=drafts');
            if (response.ok) {
                this.posts = await response.json();
                this.renderPosts();
            }
        } catch (error) {
            console.error('Error loading posts:', error);
            this.showError('Не удалось загрузить посты');
        }
    }

    async resolveChannel(identifier) {
        try {
            const response = await this.apiFetch('/api/channels/resolve', {
                method: 'POST',
                body: JSON.stringify({ identifier })
            });
            
            if (response.ok) {
                const channel = await response.json();
                return channel;
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to resolve channel');
            }
        } catch (error) {
            console.error('Error resolving channel:', error);
            throw error;
        }
    }

    async loadResolvedChannels() {
        try {
            const response = await this.apiFetch('/api/channels');
            if (response.ok) {
                this.resolvedChannels = await response.json();
                this.updateStep3UI();
            }
        } catch (error) {
            console.error('Error loading channels:', error);
        }
    }

    renderPosts() {
        const postsList = document.getElementById('posts-list');
        
        if (this.posts.length === 0) {
            postsList.innerHTML = `
                <div class="empty-state">
                    <p>Нет сохраненных постов</p>
                    <p class="hint">Создайте пост через бота</p>
                </div>
            `;
            return;
        }

        postsList.innerHTML = this.posts.map(post => `
            <div class="post-item" data-id="${post.id}">
                <div class="post-type">${this.getPostTypeLabel(post.type)}</div>
                <div class="post-text">${post.text || 'Без текста'}</div>
                <div class="post-meta">ID: ${post.id} • ${new Date(post.created_at).toLocaleDateString()}</div>
            </div>
        `).join('');
    }

    getPostTypeLabel(type) {
        const labels = {
            'photo': '📷 Фото',
            'video': '🎥 Видео',
            'document': '📄 Документ',
            'text': '📝 Текст'
        };
        return labels[type] || type;
    }

    showWizard() {
        if (this.posts.length === 0) {
            this.showError('Сначала создайте пост через бота');
            return;
        }

        document.getElementById('main-screen').classList.remove('active');
        document.getElementById('wizard-screen').classList.add('active');
        this.currentStep = 1;
        this.updateWizardUI();
    }

    hideWizard() {
        document.getElementById('wizard-screen').classList.remove('active');
        document.getElementById('main-screen').classList.add('active');
    }

    updateWizardUI() {
        // Update step indicators
        document.getElementById('wizard-step').textContent = `Шаг ${this.currentStep}/${this.totalSteps}`;
        
        // Show/hide step content
        document.querySelectorAll('.wizard-step').forEach((step, index) => {
            step.classList.toggle('active', index === this.currentStep - 1);
        });

        // Update navigation buttons
        const prevBtn = document.getElementById('wizard-prev');
        const nextBtn = document.getElementById('wizard-next');
        const finishBtn = document.getElementById('wizard-finish');

        prevBtn.classList.toggle('hidden', this.currentStep === 1);
        nextBtn.classList.toggle('hidden', this.currentStep === this.totalSteps);
        finishBtn.classList.toggle('hidden', this.currentStep !== this.totalSteps);

        // Update specific step UI
        if (this.currentStep === 2) {
            this.updateStep2UI();
        } else if (this.currentStep === 3) {
            this.updateStep3UI();
        } else if (this.currentStep === 4) {
            this.updateStep4UI();
        }
    }

    updateStep2UI() {
        document.getElementById('giveaway-title').value = this.wizardData.title;
        document.getElementById('giveaway-language').value = this.wizardData.language;
        
        const preview = document.getElementById('selected-post-preview');
        const button = document.getElementById('select-post-btn');
        
        if (this.selectedPost) {
            button.classList.add('hidden');
            preview.classList.remove('hidden');
            document.querySelector('.post-preview-content').innerHTML = `
                <div class="post-type">${this.getPostTypeLabel(this.selectedPost.type)}</div>
                <div class="post-text">${this.selectedPost.text || 'Без текста'}</div>
            `;
        } else {
            button.classList.remove('hidden');
            preview.classList.add('hidden');
        }
    }

    updateStep3UI() {
        const channelsList = document.getElementById('channels-list');
        channelsList.innerHTML = this.wizardData.channels.map((channel, index) => `
            <div class="channel-item">
                <div class="channel-info">
                    <div class="channel-title">${channel.title}</div>
                    <div class="channel-username">@${channel.username}</div>
                    <div class="channel-status">
                        ${channel.bot_is_admin ? '✅ Админ' : '❌ Не админ'}
                        ${channel.bot_can_post ? ' ✅ Может постить' : ' ❌ Не может постить'}
                    </div>
                </div>
                <button class="remove-channel" onclick="app.removeChannel(${index})">×</button>
            </div>
        `).join('');
    }

    updateStep4UI() {
        const prizesList = document.getElementById('prizes-list');
        
        // Store current input values to preserve them during re-render
        const currentValues = [];
        prizesList.querySelectorAll('.prize-input, .prize-qty').forEach(input => {
            currentValues.push({
                index: parseInt(input.dataset.index),
                field: input.dataset.field,
                value: input.value
            });
        });
        
        prizesList.innerHTML = this.wizardData.prizes.map((prize, index) => {
            // Restore values if they existed
            const nameValue = currentValues.find(v => v.index === index && v.field === 'name')?.value || prize.name;
            const qtyValue = currentValues.find(v => v.index === index && v.field === 'qty')?.value || prize.qty;
            
            return `
            <div class="prize-item">
                <div class="prize-row">
                    <input type="text" class="prize-input" placeholder="Название приза" 
                           value="${nameValue}" data-index="${index}" data-field="name">
                    <input type="number" class="prize-qty" placeholder="Кол-во" min="1"
                           value="${qtyValue}" data-index="${index}" data-field="qty">
                    <button class="remove-prize" onclick="app.removePrize(${index})">×</button>
                </div>
            </div>
        `}).join('');
        
        // Add event listeners using event delegation
        prizesList.removeEventListener('input', this.handlePrizeInput);
        this.handlePrizeInput = (e) => {
            if (e.target.matches('.prize-input, .prize-qty')) {
                const index = parseInt(e.target.dataset.index);
                const field = e.target.dataset.field;
                const value = field === 'qty' ? parseInt(e.target.value) || 1 : e.target.value;
                this.updatePrize(index, field, value);
            }
        };
        prizesList.addEventListener('input', this.handlePrizeInput);

        // Add initial prize if none exist
        if (this.wizardData.prizes.length === 0) {
            this.addPrize();
        }
    }

    nextStep() {
        if (this.validateCurrentStep()) {
            if (this.currentStep < this.totalSteps) {
                this.currentStep++;
                this.updateWizardUI();
            }
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardUI();
        }
    }

    validateCurrentStep() {
        if (this.currentStep === 1) {
            if (!this.wizardData.type) {
                this.showError('Выберите тип розыгрыша');
                return false;
            }
        } else if (this.currentStep === 2) {
            const title = document.getElementById('giveaway-title').value.trim();
            if (!title) {
                this.showError('Введите название розыгрыша');
                return false;
            }
            if (!this.selectedPost) {
                this.showError('Выберите пост');
                return false;
            }
            this.wizardData.title = title;
            this.wizardData.language = document.getElementById('giveaway-language').value;
            this.wizardData.postId = this.selectedPost.id;
        } else if (this.currentStep === 3) {
            if (this.wizardData.channels.length === 0) {
                this.showError('Добавьте хотя бы один канал');
                return false;
            }
        } else if (this.currentStep === 4) {
            if (this.wizardData.prizes.length === 0 || 
                this.wizardData.prizes.some(p => !p.name.trim() || p.qty <= 0)) {
                this.showError('Заполните все призы корректно');
                return false;
            }
        }
        return true;
    }

    showPostsModal() {
        const modalList = document.getElementById('posts-modal-list');
        modalList.innerHTML = this.posts.map(post => `
            <div class="post-item" onclick="app.selectPost(${post.id})">
                <div class="post-type">${this.getPostTypeLabel(post.type)}</div>
                <div class="post-text">${post.text || 'Без текста'}</div>
                <div class="post-meta">ID: ${post.id}</div>
            </div>
        `).join('');
        
        document.getElementById('posts-overlay').classList.remove('hidden');
    }

    hidePostsModal() {
        document.getElementById('posts-overlay').classList.add('hidden');
    }

    selectPost(postId) {
        this.selectedPost = this.posts.find(p => p.id === postId);
        this.hidePostsModal();
        this.updateStep2UI();
    }

    async addChannel() {
        const input = document.getElementById('channel-input');
        const identifier = input.value.trim();
        
        if (!identifier) return;
        
        try {
            this.showLoading();
            
            // Resolve channel to get real data
            const channel = await this.resolveChannel(identifier);
            
            // Check if already added
            const exists = this.wizardData.channels.some(c => c.id === channel.id);
            if (!exists) {
                this.wizardData.channels.push(channel);
                input.value = '';
                this.updateStep3UI();
            }
            
        } catch (error) {
            this.showError(error.message || 'Ошибка при добавлении канала');
        } finally {
            this.hideLoading();
        }
    }

    removeChannel(index) {
        this.wizardData.channels.splice(index, 1);
        this.updateStep3UI();
    }

    addPrize() {
        this.wizardData.prizes.push({ name: '', qty: 1 });
        this.updateStep4UI();
    }

    updatePrize(index, field, value) {
        if (field === 'qty') {
            value = parseInt(value) || 1;
        }
        this.wizardData.prizes[index][field] = value;
    }

    removePrize(index) {
        this.wizardData.prizes.splice(index, 1);
        this.updateStep4UI();
    }

    async finishWizard() {
        if (!this.validateCurrentStep()) return;

        this.showLoading();

        try {
            // Prepare data for new API
            const giveawayData = {
                title: this.wizardData.title,
                language: this.wizardData.language,
                postId: this.wizardData.postId,
                channels: this.wizardData.channels.map(c => c.id), // Send channel IDs
                prizes: this.wizardData.prizes
            };

            // Create giveaway via new API endpoint
            const response = await this.apiFetch('/api/wizard/commit', {
                method: 'POST',
                body: JSON.stringify(giveawayData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка создания розыгрыша');
            }

            const result = await response.json();
            const giveawayId = result.giveaway_id;

            // Request preview via Telegram WebApp
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.sendData(JSON.stringify({
                    event: 'giveaway_preview_request',
                    giveaway_id: giveawayId
                }));
                
                this.showSuccess(`${giveawayId} (ожидайте превью в боте)`);
            } else {
                // Fallback - show success without preview
                this.showSuccess(`Розыгрыш создан. ID: ${giveawayId}`);
            }

            await this.loadPosts();
            
        } catch (error) {
            console.error('Error creating giveaway:', error);
            this.showError(error.message || 'Ошибка при создании розыгрыша');
        } finally {
            this.hideLoading();
        }
    }

    showSuccess(giveawayId) {
        document.getElementById('success-message').textContent = 
            `Розыгрыш "${this.wizardData.title}" успешно создан! ID: ${giveawayId}`;
        document.getElementById('success-modal').classList.remove('hidden');
    }

    hideSuccessModal() {
        document.getElementById('success-modal').classList.add('hidden');
        this.resetWizard();
        this.hideWizard();
    }

    resetWizard() {
        this.currentStep = 1;
        this.wizardData = {
            type: '',
            title: '',
            language: 'ru',
            postId: null,
            channels: [],
            prizes: []
        };
        this.selectedPost = null;
        document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
        document.getElementById('giveaway-title').value = '';
        document.getElementById('giveaway-language').value = 'ru';
    }

    showLoading() {
        document.getElementById('loading-modal').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-modal').classList.add('hidden');
    }

    showError(message) {
        // Simple alert for now, can be enhanced with proper toast notifications
        alert(message);
    }

    showModal(title, message) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('custom-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'custom-modal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="modal-title"></h3>
                        <button class="close-button" onclick="document.getElementById('custom-modal').classList.add('hidden')">×</button>
                    </div>
                    <div class="modal-body">
                        <p id="modal-message"></p>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-message').textContent = message;
        modal.classList.remove('hidden');
    }

    openModal(title, message) {
        this.showModal(title, message);
    }

    async apiFetch(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add Telegram init data if available
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
            headers['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData;
        }

        return fetch(endpoint, {
            ...options,
            headers
        });
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SpinoraApp();
});