// Инициализация Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand(); // Разворачиваем на весь экран
tg.ready();

// Игровые переменные
let gameState = {
    score: 0,
    totalClicks: 0,
    clickPower: 1,
    level: 1,
    incomePerSecond: 0,
    
    // Улучшения клика
    upgrades: {
        upgrade1: { count: 0, price: 10, power: 1 },
        upgrade2: { count: 0, price: 100, power: 5 },
    },
    
    // Автоматические улучшения
    autoUpgrades: {
        auto1: { count: 0, price: 50, income: 1 },
        auto2: { count: 0, price: 500, income: 10 },
        auto3: { count: 0, price: 2500, income: 50 },
    },
    
    // Достижения
    achievements: {
        '100': false,
        '1000': false,
        '10000': false
    },
    
    // Статистика
    lastSave: Date.now(),
    version: '1.0'
};

// Инициализация пользователя
function initUser() {
    const user = tg.initDataUnsafe.user;
    if (user) {
        document.getElementById('user-name').textContent = 
            user.first_name || user.username || 'Игрок';
        document.getElementById('user-id').textContent = `ID: ${user.id}`;
        
        if (user.photo_url) {
            document.getElementById('user-photo').src = user.photo_url;
        }
    }
}

// Загрузка игры
function loadGame() {
    const saved = localStorage.getItem('telegramClickerGame');
    if (saved) {
        try {
            const loadedState = JSON.parse(saved);
            // Проверка версии
            if (loadedState.version === gameState.version) {
                gameState = { ...gameState, ...loadedState };
                updateUI();
                checkAchievements();
                showNotification('Игра загружена!');
            }
        } catch (e) {
            console.error('Ошибка загрузки:', e);
        }
    }
}

// Сохранение игры
function saveGame() {
    gameState.lastSave = Date.now();
    localStorage.setItem('telegramClickerGame', JSON.stringify(gameState));
    showNotification('Игра сохранена!');
}

// Обновление интерфейса
function updateUI() {
    // Основные показатели
    document.getElementById('score').textContent = 
        formatNumber(gameState.score);
    document.getElementById('level').textContent = 
        `Уровень: ${gameState.level}`;
    document.getElementById('click-power').textContent = 
        gameState.clickPower;
    document.getElementById('total-clicks').textContent = 
        gameState.totalClicks;
    document.getElementById('income-per-second').textContent = 
        gameState.incomePerSecond;
    
    // Улучшения клика
    document.getElementById('upgrade-1-count').textContent = 
        gameState.upgrades.upgrade1.count;
    document.getElementById('upgrade-1-price').textContent = 
        calculatePrice(gameState.upgrades.upgrade1);
    
    document.getElementById('upgrade-2-count').textContent = 
        gameState.upgrades.upgrade2.count;
    document.getElementById('upgrade-2-price').textContent = 
        calculatePrice(gameState.upgrades.upgrade2);
    
    // Автоматические улучшения
    document.getElementById('auto-1-count').textContent = 
        gameState.autoUpgrades.auto1.count;
    document.getElementById('auto-1-price').textContent = 
        calculatePrice(gameState.autoUpgrades.auto1);
    
    document.getElementById('auto-2-count').textContent = 
        gameState.autoUpgrades.auto2.count;
    document.getElementById('auto-2-price').textContent = 
        calculatePrice(gameState.autoUpgrades.auto2);
    
    document.getElementById('auto-3-count').textContent = 
        gameState.autoUpgrades.auto3.count;
    document.getElementById('auto-3-price').textContent = 
        calculatePrice(gameState.autoUpgrades.auto3);
    
    // Обновление кнопок покупки
    updateBuyButtons();
    updateAchievementsUI();
}

// Форматирование чисел
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return Math.floor(num);
}

// Расчет цены
function calculatePrice(upgrade) {
    return Math.floor(upgrade.price * Math.pow(1.15, upgrade.count));
}

// Покупка улучшения
function buyUpgrade(type, id) {
    let upgrade;
    if (type === 'click') {
        upgrade = gameState.upgrades[id];
    } else {
        upgrade = gameState.autoUpgrades[id];
    }
    
    const price = calculatePrice(upgrade);
    
    if (gameState.score >= price) {
        gameState.score -= price;
        upgrade.count++;
        
        if (type === 'click') {
            gameState.clickPower += upgrade.power;
        } else {
            gameState.incomePerSecond += upgrade.income;
        }
        
        updateUI();
        checkLevelUp();
        showNotification('Улучшение куплено!');
    } else {
        showNotification('Недостаточно монет!', true);
    }
}

// Проверка достижений
function checkAchievements() {
    const achievements = {
        '100': 100,
        '1000': 1000,
        '10000': 10000
    };
    
    Object.keys(achievements).forEach(key => {
        if (gameState.totalClicks >= achievements[key] && !gameState.achievements[key]) {
            gameState.achievements[key] = true;
            gameState.score += achievements[key] * 10; // Бонус за достижение
            showNotification(`Достижение разблокировано: ${achievements[key]} кликов!`);
        }
    });
}

// Обновление достижений в UI
function updateAchievementsUI() {
    Object.keys(gameState.achievements).forEach(key => {
        const achievementEl = document.getElementById(`achievement-${key}`);
        if (gameState.achievements[key]) {
            achievementEl.classList.add('unlocked');
        } else {
            achievementEl.classList.remove('unlocked');
        }
    });
}

// Проверка уровня
function checkLevelUp() {
    const newLevel = Math.floor(gameState.totalClicks / 1000) + 1;
    if (newLevel > gameState.level) {
        gameState.level = newLevel;
        showNotification(`Новый уровень: ${gameState.level}!`);
    }
}

// Обновление кнопок покупки
function updateBuyButtons() {
    // Кнопки улучшений клика
    Object.keys(gameState.upgrades).forEach(key => {
        const btn = document.querySelector(`[data-upgrade="${key}"]`);
        const price = calculatePrice(gameState.upgrades[key]);
        btn.disabled = gameState.score < price;
    });
    
    // Кнопки автоматических улучшений
    Object.keys(gameState.autoUpgrades).forEach(key => {
        const btn = document.querySelector(`[data-upgrade="${key}"]`);
        const price = calculatePrice(gameState.autoUpgrades[key]);
        btn.disabled = gameState.score < price;
    });
}

// Автоматический доход
function autoIncome() {
    gameState.score += gameState.incomePerSecond;
    updateUI();
}

// Сброс игры
function resetGame() {
    if (confirm('Вы уверены? Весь прогресс будет потерян!')) {
        localStorage.removeItem('telegramClickerGame');
        gameState = {
            score: 0,
            totalClicks: 0,
            clickPower: 1,
            level: 1,
            incomePerSecond: 0,
            upgrades: {
                upgrade1: { count: 0, price: 10, power: 1 },
                upgrade2: { count: 0, price: 100, power: 5 },
            },
            autoUpgrades: {
                auto1: { count: 0, price: 50, income: 1 },
                auto2: { count: 0, price: 500, income: 10 },
                auto3: { count: 0, price: 2500, income: 50 },
            },
            achievements: {
                '100': false,
                '1000': false,
                '10000': false
            },
            lastSave: Date.now(),
            version: '1.0'
        };
        updateUI();
        showNotification('Игра сброшена!');
    }
}

// Поделиться результатом
function shareGame() {
    const shareText = `🎮 Я играю в Telegram Clicker Game! 
    Уровень: ${gameState.level}
    Монет: ${formatNumber(gameState.score)}
    Кликов: ${gameState.totalClicks}
    
    Присоединяйся!`;
    
    tg.share(shareText);
}

// Уведомления
function showNotification(message, isError = false) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.style.background = isError ? '#e74c3c' : '#2ecc71';
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Анимация клика
function createClickAnimation(x, y) {
    const animation = document.getElementById('click-animation');
    animation.style.left = `${x - 25}px`;
    animation.style.top = `${y - 25}px`;
    
    // Создаем новую анимацию
    animation.style.animation = 'none';
    setTimeout(() => {
        animation.style.animation = 'clickEffect 0.5s ease-out forwards';
    }, 10);
}

// Обработка клика
function handleClick(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    createClickAnimation(x, y);
    
    // Добавляем очки
    gameState.score += gameState.clickPower;
    gameState.totalClicks++;
    
    // Проверяем достижения
    checkAchievements();
    checkLevelUp();
    
    updateUI();
    
    // Вибрация (если доступна)
    if (navigator.vibrate) {
        navigator.vibrate(50);
    }
}

// Инициализация
function init() {
    initUser();
    loadGame();
    
    // Настройка авто-дохода
    setInterval(autoIncome, 1000);
    
    // Автосохранение
    setInterval(saveGame, 30000);
    
    // Обработчик клика
    document.getElementById('click-area').addEventListener('click', handleClick);
    
    // Обработчики кнопок покупки
    document.querySelectorAll('.buy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const upgradeId = e.currentTarget.dataset.upgrade;
            if (upgradeId.startsWith('upgrade')) {
                buyUpgrade('click', upgradeId);
            } else {
                buyUpgrade('auto', upgradeId);
            }
        });
    });
    
    // Кнопки управления
    document.getElementById('save-btn').addEventListener('click', saveGame);
    document.getElementById('reset-btn').addEventListener('click', resetGame);
    document.getElementById('share-btn').addEventListener('click', shareGame);
    
    // Отправка данных в Telegram при закрытии
    tg.onEvent('viewportChanged', saveGame);
    window.addEventListener('beforeunload', saveGame);
}

// Запуск игры
document.addEventListener('DOMContentLoaded', init);
