import os
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "2200914529:AAGLJuHZwBDtu032T2J7MfjoO0VcAORZ6as/test"
ADMIN_USERNAME = "@suslikbank" 
CHANNEL_USERNAME = "@suslikcasino"
INITIAL_BALANCE = 5000
DB_NAME = 'suslik_casino.db'

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

BLUE_THEME = {
    'primary': '#3498db',
    'secondary': '#2980b9',
    'light': '#ecf0f1',
    'dark': '#2c3e50',
    'success': '#2ecc71',
    'danger': '#e74c3c',
    'text': '#ffffff'
}

class GameStates(StatesGroup):
    waiting_bet_amount = State()
    waiting_cube_bet = State()
    waiting_slot_bet = State()
    waiting_roulette_bet = State()
    waiting_roulette_color = State()
    waiting_roulette_number = State()
    waiting_dice_bet = State()
    waiting_football_bet = State()
    waiting_basketball_bet = State()

class AdminStates(StatesGroup):
    waiting_user = State()
    waiting_amount = State()
    waiting_message = State()

def blue_card(title, content):
    return f"""
<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>
<b>{title}</b>
{content}
<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>
"""

def blue_button(text):
    return f"<span style='color: {BLUE_THEME['primary']};'><b>»</b></span> {text}"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 10000,
        last_daily TEXT,
        last_work TEXT,
        reg_date TEXT DEFAULT CURRENT_TIMESTAMP,
        vip_status INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        total_losses INTEGER DEFAULT 0,
        ref_count INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bets (
        bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game_type TEXT,
        amount INTEGER,
        result TEXT,
        win_amount INTEGER,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    
    # Создаем таблицу рефералов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(user_id),
        FOREIGN KEY(referred_id) REFERENCES users(user_id)
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        effect TEXT
    )''')
    
    cursor.executemany('''
    INSERT OR IGNORE INTO items (name, price, effect) VALUES (?, ?, ?)
    ''', [
        ('VIP статус', 50000, 'vip'),
        ('Удвоитель выигрыша', 20000, 'double_win'),
        ('Бесплатная ставка', 15000, 'free_bet')
    ])
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, balance) 
    VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, INITIAL_BALANCE))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    
    if amount > 0:
        cursor.execute('UPDATE users SET total_wins = total_wins + ? WHERE user_id = ?', (amount, user_id))
    else:
        cursor.execute('UPDATE users SET total_losses = total_losses + ? WHERE user_id = ?', (abs(amount), user_id))
    
    conn.commit()
    conn.close()

def save_bet(user_id, game_type, amount, result, win_amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO bets (user_id, game_type, amount, result, win_amount)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, game_type, amount, result, win_amount))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
    cursor.execute('UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()

def play_cube(bet_type):
    result = random.randint(1, 6)
    is_even = result % 2 == 0
    win = (bet_type == 'чет' and is_even) or (bet_type == 'нечет' and not is_even)
    return {'result': result, 'win': win}

def play_slots():
    symbols = ['🍒', '🍋', '🍊', '🍇', '🍉', '7️⃣', '💰', '🎁']
    reels = [random.choice(symbols) for _ in range(3)]
    
    if reels[0] == reels[1] == reels[2] == '7️⃣':
        return {'reels': reels, 'win': True, 'multiplier': 10}
    elif reels[0] == reels[1] == reels[2]:
        return {'reels': reels, 'win': True, 'multiplier': 5}
    elif len(set(reels)) == 2:
        return {'reels': reels, 'win': True, 'multiplier': 2}
    return {'reels': reels, 'win': False}

def play_roulette(bet_type, bet_value):
    number = random.randint(0, 36)
    is_red = number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    
    if bet_type == 'color':
        if bet_value == 'красное' and is_red:
            return {'number': number, 'color': 'красное', 'win': True, 'multiplier': 2}
        elif bet_value == 'черное' and not is_red and number != 0:
            return {'number': number, 'color': 'черное', 'win': True, 'multiplier': 2}
        elif bet_value == 'зеленое' and number == 0:
            return {'number': number, 'color': 'зеленое', 'win': True, 'multiplier': 14}
    elif bet_type == 'number' and bet_value == number:
        return {'number': number, 'win': True, 'multiplier': 36}
    
    return {'number': number, 'color': 'красное' if is_red else 'черное', 'win': False}

def play_dice():
    return {'result': random.randint(1, 6), 'win': random.random() < 0.5}

def play_football():
    return {'win': random.random() < 0.55}

def play_basketball():
    return {'win': random.random() < 0.5}

def calculate_possible_win(game_type, amount):
    multipliers = {
        'cube': 2,
        'slots': 10,
        'roulette': 36,
        'dice': 4,
        'football': 1.8,
        'basketball': 2
    }
    return int(amount * multipliers[game_type])

def main_keyboard(admin=False):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton(blue_button("🎰 Игры")),
        KeyboardButton(blue_button("💰 Баланс")),
        KeyboardButton(blue_button("🏆 Топ")),
        KeyboardButton(blue_button("🎁 Бонус")),
        KeyboardButton(blue_button("💼 Работать")),
        KeyboardButton(blue_button("👥 Рефералы")),
        KeyboardButton(blue_button("🛍️ Магазин")),
        KeyboardButton(blue_button("📊 Статистика"))
    ]
    keyboard.add(*buttons)
    
    if admin:
        keyboard.add(KeyboardButton(blue_button("👑 Админ")))
    
    return keyboard

def games_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton('🎲 Кубик (x2)', callback_data='game_cube'),
        InlineKeyboardButton('🎰 Слоты (x2-x10)', callback_data='game_slots'),
        InlineKeyboardButton('🎡 Рулетка (x2-x36)', callback_data='game_roulette'),
        InlineKeyboardButton('🎯 Дартс (x4)', callback_data='game_dice'),
        InlineKeyboardButton('⚽ Футбол (x1.8)', callback_data='game_football'),
        InlineKeyboardButton('🏀 Баскетбол (x2)', callback_data='game_basketball')
    ]
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    args = message.get_args()
    if args and args.isdigit():
        referrer_id = int(args)
        if referrer_id != message.from_user.id and get_user(referrer_id):
            add_referral(referrer_id, message.from_user.id)
            bonus = random.randint(500, 2000)
            update_balance(message.from_user.id, bonus)
            await message.answer(
                blue_card("🎉 РЕФЕРАЛЬНЫЙ БОНУС", 
                f"Вы получили: {bonus} SuslikCoin!\n"
                f"Приглашайте друзей и получайте бонусы!"),
                reply_markup=main_keyboard()
            )
    
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        blue_card("🎰 ДОБРО ПОЖАЛОВАТЬ В SUSLIK CASINO", 
        "💰 Играй, выигрывай и становись лучшим!\n"
        "👇 Выберите действие из меню ниже:"),
        reply_markup=main_keyboard(message.from_user.username == ADMIN_USERNAME)
    )

@dp.message_handler(text=blue_button("🎰 Игры"))
async def show_games_menu(message: types.Message):
    await message.answer(
        blue_card("🎮 ВЫБОР ИГРЫ", 
        "Выберите игру из списка ниже:"),
        reply_markup=games_keyboard()
    )

@dp.message_handler(text=blue_button("💰 Баланс"))
async def show_balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(
        blue_card("💼 ВАШ БАЛАНС", 
        f"💰 На счету: {user[3]} SuslikCoin\n"
        f"🏆 Всего выиграно: {user[8]}\n"
        f"💸 Всего проиграно: {user[9]}")
    )

@dp.message_handler(text=blue_button("🏆 Топ"))
async def show_top(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    
    text = "🏆 <b>ТОП 10 ИГРОКОВ</b>\n\n"
    for i, (username, balance) in enumerate(top, 1):
        text += f"{i}. @{username} - {balance} SC\n"
    
    await message.answer(blue_card("🏆 ТОП ИГРОКОВ", text))

@dp.message_handler(text=blue_button("🎁 Бонус"))
async def daily_bonus(message: types.Message):
    user = get_user(message.from_user.id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user[4] == today:
        await message.answer(blue_card("🚫 УЖЕ ПОЛУЧАЛИ", "Вы уже получали бонус сегодня!"))
        return
    
    bonus = random.randint(5000, 25000)
    update_balance(message.from_user.id, bonus)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (today, message.from_user.id))
    conn.commit()
    conn.close()
    
    await message.answer(blue_card("🎉 БОНУС", f"Вы получили: {bonus} SuslikCoin!"))

@dp.message_handler(text=blue_button("💼 Работать"))
async def work(message: types.Message):
    user = get_user(message.from_user.id)
    now = datetime.now()
    
    if user[5]:
        last_work = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
        if (now - last_work) < timedelta(minutes=30):
            wait = 30 - (now - last_work).seconds // 60
            await message.answer(blue_card("⏳ ОЖИДАНИЕ", f"Вы можете работать снова через {wait} минут!"))
            return
    
    earnings = random.randint(500, 1000)
    update_balance(message.from_user.id, earnings)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_work = ? WHERE user_id = ?', (now.strftime('%Y-%m-%d %H:%M:%S'), message.from_user.id))
    conn.commit()
    conn.close()
    
    await message.answer(blue_card("💼 ЗАРАБОТОК", f"Вы заработали: {earnings} SuslikCoin!"))

@dp.message_handler(text=blue_button("👥 Рефералы"))
async def show_refs(message: types.Message):
    user = get_user(message.from_user.id)
    ref_link = f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"
    
    await message.answer(
        blue_card("👥 РЕФЕРАЛЫ", 
        f"🔗 Ваша ссылка: <code>{ref_link}</code>\n"
        f"👤 Приглашено: {user[10]}\n\n"
        f"💎 За каждого приглашенного вы получаете бонус!")
    )

@dp.message_handler(text=blue_button("🛍️ Магазин"))
async def show_shop(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton('💎 VIP статус (7 дней) - 50000 SC', callback_data='buy_vip'),
        InlineKeyboardButton('🎁 Удвоитель выигрыша - 20000 SC', callback_data='buy_double'),
        InlineKeyboardButton('🎫 Бесплатная ставка - 15000 SC', callback_data='buy_freebet')
    )
    
    await message.answer(
        blue_card("🛍️ МАГАЗИН", 
        "Приобретайте бонусы для улучшения игры!"),
        reply_markup=keyboard
    )

@dp.message_handler(text=blue_button("📊 Статистика"))
async def show_stats(message: types.Message):
    user = get_user(message.from_user.id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(amount), SUM(win_amount) FROM bets WHERE user_id = ?', (message.from_user.id,))
    stats = cursor.fetchone()
    conn.close()
    
    await message.answer(
        blue_card("📊 ВАША СТАТИСТИКА", 
        f"🎰 Всего ставок: {stats[0] or 0}\n"
        f"💰 Всего поставлено: {stats[1] or 0} SC\n"
        f"🏆 Всего выиграно: {stats[2] or 0} SC\n"
        f"💸 Чистый доход: {(stats[2] or 0) - (stats[1] or 0)} SC\n\n"
        f"💎 VIP статус: {'✅' if user[7] else '❌'}")
    )

@dp.message_handler(text=blue_button("👑 Админ"))
async def admin_panel(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        await message.answer(blue_card("🚫 ОШИБКА", "Доступ запрещен!"))
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('💰 Выдать деньги', callback_data='admin_give'),
        InlineKeyboardButton('❌ Забрать деньги', callback_data='admin_take'),
        InlineKeyboardButton('🚷 Бан', callback_data='admin_ban'),
        InlineKeyboardButton('✅ Разбан', callback_data='admin_unban'),
        InlineKeyboardButton('📢 Рассылка', callback_data='admin_mail'),
        InlineKeyboardButton('📊 Статистика', callback_data='admin_stats')
    )
    
    await message.answer(blue_card("👑 АДМИН ПАНЕЛЬ", "Выберите действие:"), reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
async def admin_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    
    if action == 'give':
        await callback.message.answer(blue_card("💰 ВЫДАТЬ ДЕНЬГИ", "Введите username пользователя:"))
        await AdminStates.waiting_user.set()
        await state.update_data(action='give')
    elif action == 'take':
        await callback.message.answer(blue_card("❌ ЗАБРАТЬ ДЕНЬГИ", "Введите username пользователя:"))
        await AdminStates.waiting_user.set()
        await state.update_data(action='take')
    elif action == 'ban':
        await callback.message.answer(blue_card("🚷 ЗАБАНИТЬ", "Введите username пользователя:"))
        await AdminStates.waiting_user.set()
        await state.update_data(action='ban')
    elif action == 'unban':
        await callback.message.answer(blue_card("✅ РАЗБАНИТЬ", "Введите username пользователя:"))
        await AdminStates.waiting_user.set()
        await state.update_data(action='unban')
    elif action == 'mail':
        await callback.message.answer(blue_card("📢 РАССЫЛКА", "Введите сообщение для рассылки:"))
        await AdminStates.waiting_message.set()
    elif action == 'stats':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 1')
        banned_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) FROM bets')
        total_bets = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(win_amount) FROM bets WHERE result = "win"')
        total_wins = cursor.fetchone()[0] or 0
        
        conn.close()
        
        await callback.message.answer(
            blue_card("📊 СТАТИСТИКА КАЗИНО", 
            f"👥 Пользователей: {total_users}\n"
            f"🚷 Забанено: {banned_users}\n"
            f"💰 Общий баланс: {total_balance} SC\n"
            f"🎰 Всего ставок: {total_bets} SC\n"
            f"🏆 Всего выиграно: {total_wins} SC\n"
            f"💸 Доход казино: {total_bets - total_wins} SC")
        )
    
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_user)
async def admin_user_input(message: types.Message, state: FSMContext):
    username = message.text.replace('@', '')
    user = None
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        await message.answer(blue_card("❌ ОШИБКА", "Пользователь не найден!"))
        await state.finish()
        return
    
    data = await state.get_data()
    action = data.get('action')
    
    if action in ['give', 'take']:
        await message.answer(blue_card(f"{'💰 ВЫДАТЬ' if action == 'give' else '❌ ЗАБРАТЬ'}", f"Введите сумму для @{username}:"))
        await state.update_data(user_id=user[0], username=username)
        await AdminStates.waiting_amount.set()
    elif action == 'ban':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user[0],))
        conn.commit()
        conn.close()
        
        await message.answer(blue_card("✅ УСПЕХ", f"Пользователь @{username} забанен!"))
        await state.finish()
    elif action == 'unban':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user[0],))
        conn.commit()
        conn.close()
        
        await message.answer(blue_card("✅ УСПЕХ", f"Пользователь @{username} разбанен!"))
        await state.finish()

@dp.message_handler(state=AdminStates.waiting_amount)
async def admin_amount_input(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer(blue_card("❌ ОШИБКА", "Сумма должна быть положительной!"))
            return
        
        data = await state.get_data()
        user_id = data.get('user_id')
        username = data.get('username')
        action = data.get('action')
        
        if action == 'take':
            if get_balance(user_id) < amount:
                await message.answer(blue_card("❌ ОШИБКА", "У пользователя недостаточно средств!"))
                await state.finish()
                return
            amount = -amount
        
        update_balance(user_id, amount)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO admin_logs (admin_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
        ''', (message.from_user.id, user_id, action, f"Amount: {abs(amount)}"))
        conn.commit()
        conn.close()
        
        await message.answer(
            blue_card("✅ УСПЕХ", 
            f"{'Выдано' if action == 'give' else 'Изъято'} {abs(amount)} SC пользователю @{username}")
        )
        
        try:
            await bot.send_message(
                user_id,
                blue_card("👑 АДМИНИСТРАТОР", 
                f"Вам {'начислили' if action == 'give' else 'изъяли'} {abs(amount)} SuslikCoin")
            )
        except:
            pass
        
        await state.finish()
    except ValueError:
        await message.answer(blue_card("❌ ОШИБКА", "Пожалуйста, введите число!"))

@dp.message_handler(state=AdminStates.waiting_message)
async def admin_mail_input(message: types.Message, state: FSMContext):
    mail_text = message.text
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE banned = 0')
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    for user in users:
        try:
            await bot.send_message(user[0], blue_card("📢 СООБЩЕНИЕ ОТ АДМИНИСТРАЦИИ", mail_text))
            success += 1
        except:
            continue
    
    await message.answer(blue_card("✅ УСПЕХ", f"Рассылка завершена! Доставлено {success} пользователям."))
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('game_'))
async def game_callback(callback: types.CallbackQuery, state: FSMContext):
    game = callback.data.split('_')[1]
    await bot.answer_callback_query(callback.id)
    
    await state.update_data(game_type=game)
    await bot.send_message(
        callback.from_user.id,
        blue_card("💰 СУММА СТАВКИ", 
        "Введите сумму, которую хотите поставить:"),
    )
    await GameStates.waiting_bet_amount.set()

@dp.message_handler(state=GameStates.waiting_bet_amount)
async def bet_amount_input(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer(blue_card("❌ ОШИБКА", "Сумма должна быть положительной!"))
            return
        
        user_balance = get_balance(message.from_user.id)
        if amount > user_balance:
            await message.answer(blue_card("❌ ОШИБКА", "Недостаточно средств на балансе!"))
            await state.finish()
            return
        
        data = await state.get_data()
        game_type = data.get('game_type')
        
        await state.update_data(bet_amount=amount)
        
        if game_type == 'cube':
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton('🔵 Чет', callback_data='bet_even'),
                InlineKeyboardButton('⚫ Нечет', callback_data='bet_odd')
            )
            await message.answer(
                blue_card("🎲 ВЫБОР СТАВКИ", 
                "Выберите, на что ставите:"),
                reply_markup=keyboard
            )
            await GameStates.waiting_cube_bet.set()
        elif game_type == 'roulette':
            keyboard = InlineKeyboardMarkup(row_width=2)
            buttons = [
                InlineKeyboardButton('🔴 Красное (x2)', callback_data='color_red'),
                InlineKeyboardButton('⚫ Черное (x2)', callback_data='color_black'),
                InlineKeyboardButton('🟢 Зеленое (x14)', callback_data='color_green'),
                InlineKeyboardButton('🔢 Число (x36)', callback_data='bet_number')
            ]
            keyboard.add(*buttons)
            await message.answer(
                blue_card("🎡 ВЫБОР СТАВКИ", 
                "Выберите тип ставки в рулетке:"),
                reply_markup=keyboard
            )
            await GameStates.waiting_roulette_bet.set()
        else:
            await process_game(message, state)
    
    except ValueError:
        await message.answer(blue_card("❌ ОШИБКА", "Пожалуйста, введите число!"))

@dp.callback_query_handler(lambda c: c.data.startswith('bet_'), state=GameStates.waiting_cube_bet)
async def cube_bet_callback(callback: types.CallbackQuery, state: FSMContext):
    bet_type = 'чет' if callback.data.endswith('even') else 'нечет'
    await state.update_data(cube_bet=bet_type)
    await bot.answer_callback_query(callback.id)
    await process_game(callback.message, state)

@dp.callback_query_handler(lambda c: c.data.startswith('color_'), state=GameStates.waiting_roulette_bet)
async def roulette_color_callback(callback: types.CallbackQuery, state: FSMContext):
    color = {
        'color_red': 'красное',
        'color_black': 'черное',
        'color_green': 'зеленое'
    }[callback.data]
    
    await state.update_data(roulette_bet='color', roulette_value=color)
    await bot.answer_callback_query(callback.id)
    await process_game(callback.message, state)

@dp.callback_query_handler(lambda c: c.data == 'bet_number', state=GameStates.waiting_roulette_bet)
async def roulette_number_callback(callback: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback.id)
    await callback.message.answer(blue_card("🔢 ВЫБОР ЧИСЛА", "Введите число от 0 до 36:"))
    await GameStates.waiting_roulette_number.set()

@dp.message_handler(state=GameStates.waiting_roulette_number)
async def roulette_number_input(message: types.Message, state: FSMContext):
    try:
        number = int(message.text)
        if number < 0 or number > 36:
            await message.answer(blue_card("❌ ОШИБКА", "Число должно быть от 0 до 36!"))
            return
        
        await state.update_data(roulette_bet='number', roulette_value=number)
        await process_game(message, state)
    except ValueError:
        await message.answer(blue_card("❌ ОШИБКА", "Пожалуйста, введите число от 0 до 36!"))

async def process_game(message: types.Message, state: FSMContext):
    data = await state.get_data()
    game_type = data.get('game_type')
    amount = data.get('bet_amount')
    user_id = message.from_user.id
    user = get_user(user_id)
    username = user[1] or user[2]
    
    if user[11]:
        await message.answer(blue_card("🚫 ОШИБКА", "Ваш аккаунт заблокирован!"))
        await state.finish()
        return
    
    try:
        bet_msg = await bot.send_message(
            CHANNEL_USERNAME,
            blue_card(f"🎰 НОВАЯ СТАВКА ({game_type.upper()})",
            f"👤 Игрок: @{username}\n"
            f"💰 Сумма: {amount} SC\n"
            f"🏆 Возможный выигрыш: {calculate_possible_win(game_type, amount)} SC")
        )
        
        anim_msg = await bot.send_message(
            CHANNEL_USERNAME,
            blue_card("🔄 ИГРА НАЧИНАЕТСЯ",
            "Подождите, идет обработка ставки...")
        )
        
        await asyncio.sleep(2)
        
        if game_type == 'cube':
            bet_type = data.get('cube_bet')
            game_result = play_cube(bet_type)
            win_amount = amount * 2 if game_result['win'] else 0
            game_output = f"🎲 Результат: {game_result['result']} ({'чет' if game_result['result'] % 2 == 0 else 'нечет'})"
        elif game_type == 'slots':
            game_result = play_slots()
            win_amount = amount * game_result['multiplier'] if game_result['win'] else 0
            game_output = f"🎰 {' | '.join(game_result['reels'])}"
        elif game_type == 'roulette':
            bet_type = data.get('roulette_bet')
            bet_value = data.get('roulette_value')
            game_result = play_roulette(bet_type, bet_value)
            win_amount = amount * game_result.get('multiplier', 0) if game_result['win'] else 0
            game_output = f"🎡 Выпало: {game_result['number']} ({game_result['color']})"
        elif game_type == 'dice':
            game_result = play_dice()
            win_amount = amount * 4 if game_result['win'] else 0
            game_output = "🎯 Вы " + ("попали в цель!" if game_result['win'] else "промахнулись!")
        elif game_type == 'football':
            game_result = play_football()
            win_amount = int(amount * 1.8) if game_result['win'] else 0
            game_output = "⚽ Вы " + ("забили гол!" if game_result['win'] else "промахнулись!")
        elif game_type == 'basketball':
            game_result = play_basketball()
            win_amount = amount * 2 if game_result['win'] else 0
            game_output = "🏀 Вы " + ("попали в кольцо!" if game_result['win'] else "промахнулись!")
        
        await bot.delete_message(CHANNEL_USERNAME, anim_msg.message_id)
        
        result_msg = await bot.send_message(
            CHANNEL_USERNAME,
            blue_card(f"🏆 РЕЗУЛЬТАТ ({game_type.upper()})",
            f"{game_output}\n\n"
            f"👤 Игрок: @{username}\n"
            f"💰 Ставка: {amount} SC\n"
            f"🏆 Результат: {'Выигрыш ' + str(win_amount) + ' SC' if game_result['win'] else 'Проигрыш'}")
        )
        
        if game_result['win']:
            update_balance(user_id, win_amount - amount)
            result_text = f"🎉 Вы выиграли {win_amount} SC!"
        else:
            update_balance(user_id, -amount)
            result_text = "😢 Вы проиграли."
        
        save_bet(
            user_id=user_id,
            game_type=game_type,
            amount=amount,
            result='win' if game_result['win'] else 'lose',
            win_amount=win_amount if game_result['win'] else 0
        )
        
        await message.answer(
            blue_card("🎰 РЕЗУЛЬТАТ ВАШЕЙ СТАВКИ",
            f"Ссылка на ставку: {bet_msg.url}\n"
            f"Ссылка на результат: {result_msg.url}\n\n"
            f"{result_text}\n"
            f"💳 Текущий баланс: {get_balance(user_id)} SC")
        )
        
    except Exception as e:
        await message.answer(blue_card("❌ ОШИБКА", "Произошла ошибка при обработке ставки. Попробуйте позже."))
        print(f"Error: {e}")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def buy_item(callback: types.CallbackQuery):
    item_type = callback.data.split('_')[1]
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    items = {
        'vip': {'name': 'VIP статус', 'price': 50000, 'days': 7},
        'double': {'name': 'Удвоитель выигрыша', 'price': 20000, 'uses': 1},
        'freebet': {'name': 'Бесплатная ставка', 'price': 15000, 'uses': 1}
    }
    
    if item_type not in items:
        await callback.answer("Товар не найден!")
        return
    
    item = items[item_type]
    
    if user[3] < item['price']:
        await callback.answer("Недостаточно средств!")
        return
    
    update_balance(user_id, -item['price'])
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if item_type == 'vip':
        expire_date = (datetime.now() + timedelta(days=item['days'])).strftime('%Y-%m-%d')
        cursor.execute('UPDATE users SET vip_status = 1 WHERE user_id = ?', (user_id,))
    elif item_type == 'double':
        cursor.execute('INSERT INTO items (user_id, name, effect) VALUES (?, ?, ?)', 
                      (user_id, item['name'], 'double_win'))
    elif item_type == 'freebet':
        cursor.execute('INSERT INTO items (user_id, name, effect) VALUES (?, ?, ?)', 
                      (user_id, item['name'], 'free_bet'))
    
    conn.commit()
    conn.close()
    
    await callback.answer(f"Вы приобрели {item['name']}!")
    await bot.send_message(
        user_id,
        blue_card("🛍️ ПОКУПКА",
        f"Вы успешно приобрели {item['name']} за {item['price']} SC!\n\n"
        f"💳 Текущий баланс: {get_balance(user_id)} SC")
    )

if __name__ == '__main__':
    init_db()

    executor.start_polling(dp, skip_updates=True)



