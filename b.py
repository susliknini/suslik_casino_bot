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
ADMIN_USERNAME = "@molni" 
CHANNEL_USERNAME = "@suslikcasino"
INITIAL_BALANCE = 5000
DB_NAME = 'suslik_casino.db'

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния FSM
class GameStates(StatesGroup):
    waiting_bet_amount = State()
    waiting_cube_bet = State()
    waiting_roulette_bet = State()
    waiting_roulette_color = State()
    waiting_roulette_number = State()

class AdminStates(StatesGroup):
    waiting_user = State()
    waiting_amount = State()
    waiting_message = State() 

# База данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Создаем таблицу users с фиксированным значением INITIAL_BALANCE
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT {INITIAL_BALANCE},
        last_daily TEXT,
        last_work TEXT,
        reg_date TEXT DEFAULT CURRENT_TIMESTAMP,
        vip_status INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        total_losses INTEGER DEFAULT 0,
        ref_count INTEGER DEFAULT 0
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bets (
        bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game_type TEXT,
        amount INTEGER,
        result TEXT,
        win_amount INTEGER,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# Функции работы с БД
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

def get_balance(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()[0]
    conn.close()
    return balance

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

# Игровая логика
def play_cube(bet_type):
    result = random.randint(1, 6)
    is_even = result % 2 == 0
    win = (bet_type == 'чет' and is_even) or (bet_type == 'нечет' and not is_even)
    return {'result': result, 'win': win}

def play_slots():
    symbols = ['🍒', '🍋', '🍊', '🍇', '🍉', '7️⃣']
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

# Клавиатуры
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton('🎰 Игры', callback_data='games'),
        InlineKeyboardButton('💰 Баланс', callback_data='balance'),
        InlineKeyboardButton('🎁 Бонус', callback_data='bonus'),
        InlineKeyboardButton('💼 Работать', callback_data='work'),
        InlineKeyboardButton('👥 Рефералы', callback_data='referrals'),
        InlineKeyboardButton('🏆 Топ игроков', callback_data='top'),
        InlineKeyboardButton('📊 Статистика', callback_data='stats')
    ]
    keyboard.add(*buttons)
    
    if ADMIN_USERNAME:
        keyboard.add(InlineKeyboardButton('👑 Админ', callback_data='admin'))
    
    return keyboard

def games_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton('🎲 Кубик', callback_data='game_cube'),
        InlineKeyboardButton('🎡 Рулетка', callback_data='game_roulette'),
        InlineKeyboardButton('🎰 Слоты', callback_data='game_slots'),
        InlineKeyboardButton('🎯 Дартс', callback_data='game_dice'),
        InlineKeyboardButton('⚽ Футбол', callback_data='game_football'),
        InlineKeyboardButton('🏀 Баскетбол', callback_data='game_basketball')
    ]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back'))
    return keyboard

def back_keyboard():
    return InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='back'))

# Обработчики команд
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
                f"🎉 Вы получили реферальный бонус: {bonus} SuslikCoin!",
                reply_markup=main_menu_keyboard()
            )
    
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "🎰 Добро пожаловать в Suslik Casino!\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == 'back')
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎰 Главное меню:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'games')
async def show_games(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎮 Выберите игру:",
        reply_markup=games_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'balance')
async def show_balance(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"💰 Ваш баланс: {user[3]} SuslikCoin\n"
        f"🏆 Всего выиграно: {user[8]}\n"
        f"💸 Всего проиграно: {user[9]}",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'bonus')
async def daily_bonus(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if user[4] == today:
        await callback.answer("Вы уже получали бонус сегодня!", show_alert=True)
        return
    
    bonus = random.randint(5000, 25000)
    update_balance(callback.from_user.id, bonus)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (today, callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"🎉 Вы получили бонус: {bonus} SuslikCoin!",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'work')
async def work(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    now = datetime.now()
    
    if user[5]:
        last_work = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
        if (now - last_work) < timedelta(minutes=30):
            wait = 30 - (now - last_work).seconds // 60
            await callback.answer(f"Вы можете работать снова через {wait} минут!", show_alert=True)
            return
    
    earnings = random.randint(500, 1000)
    update_balance(callback.from_user.id, earnings)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_work = ? WHERE user_id = ?', (now.strftime('%Y-%m-%d %H:%M:%S'), callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"💼 Вы заработали {earnings} SuslikCoin!",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'referrals')
async def show_referrals(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    ref_link = f"https://t.me/{bot.get_me().username}?start={callback.from_user.id}"
    
    await callback.message.edit_text(
        f"👥 Реферальная система\n\n"
        f"🔗 Ваша ссылка: <code>{ref_link}</code>\n"
        f"👤 Приглашено: {user[10]}\n\n"
        f"💎 За каждого приглашенного вы получаете бонус!",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'top')
async def show_top(callback: types.CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    
    text = "🏆 Топ 10 игроков:\n\n"
    for i, (username, balance) in enumerate(top, 1):
        text += f"{i}. @{username} - {balance} SC\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'stats')
async def show_stats(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(amount), SUM(win_amount) FROM bets WHERE user_id = ?', (callback.from_user.id,))
    stats = cursor.fetchone()
    conn.close()
    
    await callback.message.edit_text(
        f"📊 Ваша статистика:\n\n"
        f"🎰 Всего ставок: {stats[0] or 0}\n"
        f"💰 Всего поставлено: {stats[1] or 0} SC\n"
        f"🏆 Всего выиграно: {stats[2] or 0} SC\n"
        f"💸 Чистый доход: {(stats[2] or 0) - (stats[1] or 0)} SC\n\n"
        f"💎 VIP статус: {'✅' if user[7] else '❌'}",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

# Обработчики игр
@dp.callback_query_handler(lambda c: c.data.startswith('game_'))
async def select_game(callback: types.CallbackQuery, state: FSMContext):
    game = callback.data.split('_')[1]
    await state.update_data(game_type=game)
    await callback.message.edit_text(
        "💰 Введите сумму ставки:",
        reply_markup=back_keyboard()
    )
    await GameStates.waiting_bet_amount.set()
    await callback.answer()

@dp.message_handler(state=GameStates.waiting_bet_amount)
async def process_bet_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("Сумма должна быть положительной!")
            return
        
        balance = get_balance(message.from_user.id)
        if amount > balance:
            await message.answer("Недостаточно средств на балансе!")
            await state.finish()
            return
        
        # Сохраняем сумму ставки в состоянии
        await state.update_data(bet_amount=amount)
        
        data = await state.get_data()
        game_type = data['game_type']
        
        if game_type == 'cube':
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton('Чет', callback_data='bet_even'),
                InlineKeyboardButton('Нечет', callback_data='bet_odd')
            )
            await message.answer(
                "Выберите ставку:",
                reply_markup=keyboard
            )
            await GameStates.waiting_cube_bet.set()
        elif game_type == 'roulette':
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton('🔴 Красное (x2)', callback_data='color_red'),
                InlineKeyboardButton('⚫ Черное (x2)', callback_data='color_black'),
                InlineKeyboardButton('🟢 Зеленое (x14)', callback_data='color_green'),
                InlineKeyboardButton('🔢 Число (x36)', callback_data='bet_number')
            )
            await message.answer(
                "Выберите тип ставки:",
                reply_markup=keyboard
            )
            await GameStates.waiting_roulette_bet.set()
        else:
            await process_game(message, state)
    
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

@dp.callback_query_handler(lambda c: c.data.startswith('bet_'), state=GameStates.waiting_cube_bet)
async def cube_bet_callback(callback: types.CallbackQuery, state: FSMContext):
    bet_type = 'чет' if callback.data.endswith('even') else 'нечет'
    await state.update_data(cube_bet=bet_type)
    await process_game(callback.message, state)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('color_'), state=GameStates.waiting_roulette_bet)
async def roulette_color_callback(callback: types.CallbackQuery, state: FSMContext):
    color = {
        'color_red': 'красное',
        'color_black': 'черное',
        'color_green': 'зеленое'
    }[callback.data]
    await state.update_data(roulette_bet='color', roulette_value=color)
    await process_game(callback.message, state)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'bet_number', state=GameStates.waiting_roulette_bet)
async def roulette_number_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите число от 0 до 36:")
    await GameStates.waiting_roulette_number.set()
    await callback.answer()

@dp.message_handler(state=GameStates.waiting_roulette_number)
async def roulette_number_input(message: types.Message, state: FSMContext):
    try:
        number = int(message.text)
        if number < 0 or number > 36:
            await message.answer("Число должно быть от 0 до 36!")
            return
        
        await state.update_data(roulette_bet='number', roulette_value=number)
        await process_game(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите число от 0 до 36!")

async def process_game(message_or_call, state: FSMContext):
    if isinstance(message_or_call, types.CallbackQuery):
        message = message_or_call.message
    else:
        message = message_or_call
    
    data = await state.get_data()
    game_type = data['game_type']
    amount = data['bet_amount']
    user_id = message.from_user.id
    username = get_user(user_id)[1] or get_user(user_id)[2]
    
    # Отправка ставки в канал
    try:
        bet_msg = await bot.send_message(
            CHANNEL_USERNAME,
            f"🎰 Новая ставка!\n\n"
            f"👤 Игрок: @{username}\n"
            f"🎮 Игра: {game_type}\n"
            f"💰 Сумма: {amount} SC"
        )
        
        # Анимация
        anim_msg = await bot.send_message(CHANNEL_USERNAME, "🔄 Идет игра...")
        await asyncio.sleep(2)
        
        # Игровая логика
        if game_type == 'cube':
            bet_type = data['cube_bet']
            game_result = play_cube(bet_type)
            win_amount = amount * 2 if game_result['win'] else 0
            game_output = f"🎲 Результат: {game_result['result']} ({'чет' if game_result['result'] % 2 == 0 else 'нечет'})"
        elif game_type == 'slots':
            game_result = play_slots()
            win_amount = amount * game_result['multiplier'] if game_result['win'] else 0
            game_output = f"🎰 {' | '.join(game_result['reels'])}"
        elif game_type == 'roulette':
            bet_type = data['roulette_bet']
            bet_value = data['roulette_value']
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
        
        # Результат в канал
        result_msg = await bot.send_message(
            CHANNEL_USERNAME,
            f"{game_output}\n\n"
            f"👤 Игрок: @{username}\n"
            f"🏆 Результат: {'Выигрыш ' + str(win_amount) + ' SC' if game_result['win'] else 'Проигрыш'}"
        )
        
        # Обновление баланса
        if game_result['win']:
            update_balance(user_id, win_amount - amount)
            result_text = f"🎉 Вы выиграли {win_amount} SC!"
        else:
            update_balance(user_id, -amount)
            result_text = "😢 Вы проиграли."
        
        save_bet(user_id, game_type, amount, 'win' if game_result['win'] else 'lose', win_amount)
        
        # Отправка результата пользователю
        await message.answer(
            f"🎰 Ваша ставка: {bet_msg.url}\n"
            f"🏆 Результат: {result_msg.url}\n\n"
            f"{result_text}\n"
            f"💳 Текущий баланс: {get_balance(user_id)} SC",
            reply_markup=main_menu_keyboard()
        )
    
    except Exception as e:
        await message.answer("Произошла ошибка при обработке ставки. Попробуйте позже.")
        print(f"Error: {e}")
    
    await state.finish()

# Админ-панель
@dp.callback_query_handler(lambda c: c.data == 'admin')
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('💰 Выдать деньги', callback_data='admin_give'),
        InlineKeyboardButton('❌ Забрать деньги', callback_data='admin_take'),
        InlineKeyboardButton('📢 Рассылка', callback_data='admin_mail'),
        InlineKeyboardButton('📊 Статистика', callback_data='admin_stats'),
        InlineKeyboardButton('🔙 Назад', callback_data='back')
    )
    
    await callback.message.edit_text(
        "👑 Админ-панель:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
async def admin_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    
    if action == 'give':
        await callback.message.edit_text(
            "Введите username пользователя для выдачи денег:",
            reply_markup=back_keyboard()
        )
        await AdminStates.waiting_user.set()
        await state.update_data(action='give')
    elif action == 'take':
        await callback.message.edit_text(
            "Введите username пользователя для изъятия денег:",
            reply_markup=back_keyboard()
        )
        await AdminStates.waiting_user.set()
        await state.update_data(action='take')
    elif action == 'mail':
        await callback.message.edit_text(
            "Введите сообщение для рассылки:",
            reply_markup=back_keyboard()
        )
        await AdminStates.waiting_message.set()
    elif action == 'stats':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM bets')
        total_bets = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(win_amount) FROM bets WHERE result = "win"')
        total_wins = cursor.fetchone()[0] or 0
        
        conn.close()
        
        await callback.message.edit_text(
            f"📊 Статистика казино:\n\n"
            f"👥 Пользователей: {total_users}\n"
            f"💰 Общий баланс: {total_balance} SC\n"
            f"🎰 Всего ставок: {total_bets} SC\n"
            f"🏆 Всего выиграно: {total_wins} SC\n"
            f"💸 Доход казино: {total_bets - total_wins} SC",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('🔙 Назад', callback_data='admin'))
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
        await message.answer("Пользователь не найден!")
        await state.finish()
        return
    
    data = await state.get_data()
    action = data.get('action')
    
    await state.update_data(user_id=user[0], username=username)
    await message.answer(
        f"Пользователь: @{username}\n"
        f"Текущий баланс: {user[3]} SC\n\n"
        f"Введите сумму для {'выдачи' if action == 'give' else 'изъятия'}:",
        reply_markup=back_keyboard()
    )
    await AdminStates.waiting_amount.set()

@dp.message_handler(state=AdminStates.waiting_amount)
async def admin_amount_input(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("Сумма должна быть положительной!")
            return
        
        data = await state.get_data()
        user_id = data.get('user_id')
        username = data.get('username')
        action = data.get('action')
        
        if action == 'take':
            if get_balance(user_id) < amount:
                await message.answer("У пользователя недостаточно средств!")
                await state.finish()
                return
            amount = -amount
        
        update_balance(user_id, amount)
        
        await message.answer(
            f"✅ Успешно! {'Выдано' if action == 'give' else 'Изъято'} {abs(amount)} SC пользователю @{username}",
            reply_markup=main_menu_keyboard()
        )
        
        try:
            await bot.send_message(
                user_id,
                f"👑 Администратор {'начислил' if action == 'give' else 'изъял'} вам {abs(amount)} SuslikCoin"
            )
        except:
            pass
        
        await state.finish()
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

@dp.message_handler(state=AdminStates.waiting_message)
async def admin_mail_input(message: types.Message, state: FSMContext):
    mail_text = message.text
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 Сообщение от администрации:\n\n{mail_text}")
            success += 1
        except:
            continue
    
    await message.answer(
        f"✅ Рассылка завершена! Доставлено {success} пользователям.",
        reply_markup=main_menu_keyboard()
    )
    await state.finish()

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)




