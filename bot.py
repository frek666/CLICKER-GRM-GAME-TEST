import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('brainrot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            money INTEGER DEFAULT 0,
            total_clicks INTEGER DEFAULT 0,
            click_power INTEGER DEFAULT 1,
            auto_clickers INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            premium_until INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица платежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            currency TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Реферальная система
    referral_bonus = False
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        if referrer_id != user.id:
            # Начисляем бонус рефереру
            conn = sqlite3.connect('brainrot.db')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET money = money + 100, referrals = referrals + 1 WHERE user_id = ?",
                (referrer_id,)
            )
            conn.commit()
            conn.close()
            referral_bonus = True
    
    # Регистрация пользователя
    conn = sqlite3.connect('brainrot.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    
    # Бонус новичку
    if referral_bonus:
        cursor.execute(
            "UPDATE users SET money = money + 50 WHERE user_id = ?",
            (user.id,)
        )
    
    conn.commit()
    conn.close()
    
    # Приветственное сообщение
    welcome_text = f"""
    🌀 *Добро пожаловать в Brainrot Clicker!* 🌀

    *Что это такое?*
    Токсичный кликер в духе Brainrot контента! 
    Кликай, зарабатывай монеты, покупай улучшения!

    *Основные команды:*
    /play - Открыть игру в WebApp
    /profile - Ваш профиль
    /leaderboard - Таблица лидеров
    /shop - Магазин улучшений

    *Реферальная система:*
    Приглашай друзей и получай бонусы!
    Твоя реферальная ссылка:
    `https://t.me/your_bot?start={user.id}`
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data='play_game')],
        [InlineKeyboardButton("👤 Профиль", callback_data='profile')],
        [InlineKeyboardButton("🏆 Лидеры", callback_data='leaderboard')]
    ]
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Команда /play
async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # URL вашего WebApp
    web_app_url = "https://ваш-сайт.com/brainrot-clicker"
    
    keyboard = [[
        InlineKeyboardButton(
            "🎮 Открыть игру",
            web_app={"url": web_app_url}
        )
    ]]
    
    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть игру:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка платежей
async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    
    conn = sqlite3.connect('brainrot.db')
    cursor = conn.cursor()
    
    # Записываем платеж
    cursor.execute(
        "INSERT INTO payments (user_id, amount, currency, status) VALUES (?, ?, ?, ?)",
        (user.id, payment.total_amount / 100, payment.currency, 'completed')
    )
    
    # Начисляем премиум статус или монеты
    if "booster" in payment.invoice_payload:
        # Активируем бустер
        pass
    elif "premium" in payment.invoice_payload:
        # Активируем премиум
        import time
        premium_until = int(time.time()) + 30 * 24 * 60 * 60  # 30 дней
        cursor.execute(
            "UPDATE users SET premium_until = ? WHERE user_id = ?",
            (premium_until, user.id)
        )
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ Спасибо за покупку! Премиум функции активированы."
    )

# API для получения данных пользователя
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_data(user_id):
    conn = sqlite3.connect('brainrot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return jsonify({
            'user_id': user[0],
            'money': user[3],
            'click_power': user[5],
            'auto_clickers': user[6],
            'premium_until': user[8]
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/save', methods=['POST'])
def save_game_data():
    data = request.json
    user_id = data.get('user_id')
    
    conn = sqlite3.connect('brainrot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET 
        money = ?,
        total_clicks = ?,
        click_power = ?,
        auto_clickers = ?
        WHERE user_id = ?
    ''', (
        data.get('money', 0),
        data.get('total_clicks', 0),
        data.get('click_power', 1),
        data.get('auto_clickers', 0),
        user_id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения бота
    application = Application.builder().token("8570592029:AAH67EK50--YOznrZw8Y6-zmgBBXB78G_fM").build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play_game))
    
    # Обработчики платежей
    application.add_handler(CommandHandler("successful_payment", handle_successful_payment))
    
    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_UPDATES)

if __name__ == '__main__':
    main()