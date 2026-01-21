class BrainrotClicker {
    constructor() {
        this.money = 0;
        this.clickPower = 1;
        this.totalClicks = 0;
        this.autoClickers = 0;
        this.upgrades = {};
        this.gameStartTime = Date.now();
        this.telegram = null;
        this.user = null;
        
        this.init();
    }
    
    init() {
        this.loadGame();
        this.initTelegram();
        this.bindEvents();
        this.startGameLoop();
        this.updateUI();
    }
    
    initTelegram() {
        if (window.Telegram && Telegram.WebApp) {
            this.telegram = Telegram.WebApp;
            this.telegram.ready();
            this.telegram.expand();
            
            this.user = this.telegram.initDataUnsafe?.user || {
                id: Math.floor(Math.random() * 1000000),
                first_name: 'Игрок',
                photo_url: 'https://cdn-icons-png.flaticon.com/512/149/149071.png'
            };
            
            document.getElementById('user-name').textContent = this.user.first_name;
            if (this.user.photo_url) {
                document.getElementById('user-avatar').src = this.user.photo_url;
            }
            
            this.generateReferralLink();
        }
    }
    
    generateReferralLink() {
        const refLink = `https://t.me/your_bot?start=${this.user.id}`;
        document.getElementById('ref-link').value = refLink;
    }
    
    bindEvents() {
        // Кнопка клика
        document.getElementById('click-button').addEventListener('click', () => {
            this.click();
            this.animateClick();
        });
        
        // Кнопки покупки
        document.querySelectorAll('.buy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const price = parseInt(e.target.dataset.price);
                const id = e.target.closest('.upgrade-item').dataset.id;
                this.buyUpgrade(id, price);
            });
        });
        
        // Премиум покупки
        document.querySelectorAll('.premium-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const feature = e.target.closest('.premium-btn').dataset.feature;
                this.showPaymentModal(feature);
            });
        });
        
        // Копирование реферальной ссылки
        document.getElementById('copy-ref').addEventListener('click', () => {
            const refInput = document.getElementById('ref-link');
            refInput.select();
            document.execCommand('copy');
            this.showNotification('Ссылка скопирована!');
        });
        
        // Модальные окна
        document.getElementById('leaderboard').addEventListener('click', () => {
            this.showLeaderboard();
        });
        
        document.getElementById('achievements').addEventListener('click', () => {
            this.showAchievements();
        });
        
        document.getElementById('settings').addEventListener('click', () => {
            // Настройки
        });
        
        // Закрытие модальных окон
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.modal').forEach(modal => {
                    modal.style.display = 'none';
                });
            });
        });
    }
    
    click() {
        this.money += this.clickPower;
        this.totalClicks++;
        this.updateUI();
        
        if (Math.random() > 0.95) {
            this.showNotification('CRITICAL HIT! +' + (this.clickPower * 2));
            this.money += this.clickPower;
        }
    }
    
    animateClick() {
        const btn = document.getElementById('click-button');
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            btn.style.transform = 'scale(1)';
        }, 100);
        
        // Эффект частиц
        this.createParticle();
    }
    
    createParticle() {
        const particles = ['💀', '🔥', '💥', '⚡', '💎', '👁️'];
        const particle = document.createElement('div');
        particle.textContent = particles[Math.floor(Math.random() * particles.length)];
        particle.style.position = 'absolute';
        particle.style.left = Math.random() * 300 + 'px';
        particle.style.top = Math.random() * 300 + 'px';
        particle.style.fontSize = '24px';
        particle.style.pointerEvents = 'none';
        particle.style.animation = 'particleAnim 1s forwards';
        
        document.querySelector('.brainrot-display').appendChild(particle);
        
        setTimeout(() => particle.remove(), 1000);
    }
    
    buyUpgrade(id, price) {
        if (this.money >= price) {
            this.money -= price;
            
            switch(id) {
                case '1':
                    this.clickPower += 1;
                    break;
                case '2':
                    this.autoClickers += 1;
                    break;
                case '3':
                    this.clickPower *= 2;
                    break;
                case '4':
                    this.clickPower += 5;
                    break;
            }
            
            this.upgrades[id] = (this.upgrades[id] || 0) + 1;
            this.showNotification('Улучшение куплено!');
            this.updateUI();
            this.saveGame();
        } else {
            this.showNotification('Недостаточно денег!', 'error');
        }
    }
    
    showPaymentModal(feature) {
        const prices = {
            booster: 99,
            backup: 199,
            unlimited: 299
        };
        
        const modal = document.getElementById('payment-modal');
        const info = document.getElementById('payment-info');
        
        info.innerHTML = `
            <p>Вы покупаете: <strong>${this.getFeatureName(feature)}</strong></p>
            <p>Стоимость: <strong>${prices[feature]}₽</strong></p>
            <button class="buy-btn" style="margin: 10px 0;" id="confirm-payment">
                Купить через Telegram
            </button>
        `;
        
        modal.style.display = 'flex';
        
        document.getElementById('confirm-payment').addEventListener('click', () => {
            this.processPayment(feature, prices[feature]);
        });
    }
    
    processPayment(feature, amount) {
        if (this.telegram) {
            // В реальном приложении здесь будет интеграция с платежами Telegram
            this.telegram.showPopup({
                title: 'Покупка',
                message: `Вы покупаете ${this.getFeatureName(feature)} за ${amount}₽`,
                buttons: [
                    {type: 'default', text: 'Отмена'},
                    {type: 'ok', text: 'Купить'}
                ]
            }, (buttonId) => {
                if (buttonId === 'ok') {
                    this.activatePremiumFeature(feature);
                    this.showNotification('Покупка успешна!');
                }
            });
        } else {
            // Для теста
            this.activatePremiumFeature(feature);
            this.showNotification('Покупка успешна! (тестовый режим)');
        }
    }
    
    activatePremiumFeature(feature) {
        switch(feature) {
            case 'booster':
                this.clickPower *= 2;
                setTimeout(() => {
                    this.clickPower /= 2;
                    this.showNotification('Бустер закончился!');
                }, 24 * 60 * 60 * 1000);
                break;
            case 'backup':
                this.backupGame();
                break;
            case 'unlimited':
                // Снимает ограничения
                this.showNotification('Неограниченная энергия активирована на 7 дней!');
                break;
        }
        
        document.getElementById('payment-modal').style.display = 'none';
        this.saveGame();
    }
    
    getFeatureName(feature) {
        const names = {
            booster: 'x2 Множитель на 24 часа',
            backup: 'Защита прогресса',
            unlimited: 'Неограниченная энергия'
        };
        return names[feature] || 'Фича';
    }
    
    showLeaderboard() {
        const modal = document.getElementById('leaderboard-modal');
        const list = document.getElementById('leaderboard-list');
        
        // Заглушка для теста
        list.innerHTML = `
            <div class="leaderboard-item">
                <span>1. 👑 Sigma Player</span>
                <span>1,234,567</span>
            </div>
            <div class="leaderboard-item">
                <span>2. 💀 Skibidi King</span>
                <span>987,654</span>
            </div>
            <div class="leaderboard-item">
                <span>3. 🚽 Toilet Pro</span>
                <span>654,321</span>
            </div>
        `;
        
        modal.style.display = 'flex';
    }
    
    showAchievements() {
        const modal = document.getElementById('achievements-modal');
        const list = document.getElementById('achievements-list');
        
        const achievements = [
            {name: 'Первый клик', desc: 'Сделать 1 клик', done: this.totalClicks >= 1},
            {name: 'Новичок', desc: 'Накопить 100 монет', done: this.money >= 100},
            {name: 'Профи', desc: 'Накопить 1000 монет', done: this.money >= 1000},
            {name: 'Кликер', desc: 'Сделать 100 кликов', done: this.totalClicks >= 100},
        ];
        
        list.innerHTML = achievements.map(ach => `
            <div class="achievement-item ${ach.done ? 'unlocked' : 'locked'}">
                <i class="fas fa-${ach.done ? 'check-circle' : 'lock'}"></i>
                <div>
                    <h4>${ach.name}</h4>
                    <p>${ach.desc}</p>
                </div>
            </div>
        `).join('');
        
        modal.style.display = 'flex';
    }
    
    showNotification(text, type = 'success') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = text;
        notification.style.background = type === 'error' ? 'rgba(255, 0, 0, 0.9)' : 'rgba(0, 255, 0, 0.9)';
        
        notifications.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    startGameLoop() {
        setInterval(() => {
            // Автокликеры
            if (this.autoClickers > 0) {
                this.money += this.clickPower * this.autoClickers;
                this.updateUI();
            }
            
            this.updatePlayTime();
            this.saveGame();
        }, 1000);
    }
    
    updatePlayTime() {
        const seconds = Math.floor((Date.now() - this.gameStartTime) / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        document.getElementById('play-time').textContent = 
            `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    updateUI() {
        document.getElementById('money').textContent = Math.floor(this.money);
        document.getElementById('click-power').textContent = this.clickPower;
        document.getElementById('total-clicks').textContent = this.totalClicks;
        document.getElementById('per-second').textContent = this.autoClickers * this.clickPower;
        document.getElementById('record-clicks').textContent = 
            Math.max(this.totalClicks, parseInt(document.getElementById('record-clicks').textContent) || 0);
        
        // Обновление уровня
        const level = Math.floor(Math.sqrt(this.totalClicks / 100)) + 1;
        document.getElementById('user-level').textContent = level;
    }
    
    saveGame() {
        const gameData = {
            money: this.money,
            clickPower: this.clickPower,
            totalClicks: this.totalClicks,
            autoClickers: this.autoClickers,
            upgrades: this.upgrades,
            gameStartTime: this.gameStartTime
        };
        
        localStorage.setItem('brainrot-clicker', JSON.stringify(gameData));
        
        // Резервное копирование в Telegram Cloud
        if (this.telegram && this.telegram.CloudStorage) {
            this.telegram.CloudStorage.setItem('game_data', JSON.stringify(gameData));
        }
    }
    
    loadGame() {
        const saved = localStorage.getItem('brainrot-clicker');
        if (saved) {
            const gameData = JSON.parse(saved);
            Object.assign(this, gameData);
        }
    }
    
    backupGame() {
        // В реальном приложении здесь будет синхронизация с сервером
        this.showNotification('Прогресс сохранен в облако!');
    }
}

// Инициализация игры при загрузке страницы
window.addEventListener('DOMContentLoaded', () => {
    window.game = new BrainrotClicker();
    
    // Добавление стилей для частиц
    const style = document.createElement('style');
    style.textContent = `
        @keyframes particleAnim {
            0% { transform: translateY(0) scale(1); opacity: 1; }
            100% { transform: translateY(-100px) scale(0.5); opacity: 0; }
        }
        
        .leaderboard-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
        
        .achievement-item {
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
        
        .achievement-item.unlocked {
            border-left: 4px solid var(--brainrot-green);
        }
        
        .achievement-item.locked {
            opacity: 0.5;
        }
    `;
    document.head.appendChild(style);
});