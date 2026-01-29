import asyncio
import sqlite3
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ============= КОНСТАНТЫ И НАСТРОЙКИ =============
BOT_TOKEN = "8570592029:AAH67EK50--YOznrZw8Y6-zmgBBXB78G_fM"
MAX_PLAYERS = 3

# ============= МОДЕЛИ ДАННЫХ =============
class PlayerClass(Enum):
    WARRIOR = "Воин"
    MAGE = "Маг"
    ROGUE = "Разбойник"
    ARCHER = "Лучник"

class LocationType(Enum):
    FOREST = "Лес"
    DUNGEON = "Подземелье"
    MOUNTAINS = "Горы"
    VILLAGE = "Деревня"
    RUINS = "Руины"

class ItemType(Enum):
    WEAPON = "Оружие"
    ARMOR = "Броня"
    POTION = "Зелье"
    ARTIFACT = "Артефакт"
    MATERIAL = "Материал"

@dataclass
class Item:
    id: int
    name: str
    type: ItemType
    power: int = 0
    price: int = 0
    description: str = ""
    effects: Dict = field(default_factory=dict)

@dataclass
class Monster:
    id: int
    name: str
    level: int
    health: int
    damage: int
    experience: int
    loot: List[Item] = field(default_factory=list)
    description: str = ""

@dataclass
class Location:
    id: int
    name: str
    type: LocationType
    description: str
    monsters: List[Monster] = field(default_factory=list)
    connections: List[int] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    required_level: int = 1

@dataclass
class Player:
    user_id: int
    username: str
    health: int = 100
    max_health: int = 100
    experience: int = 0
    level: int = 1
    gold: int = 50
    location_id: int = 1
    player_class: PlayerClass = PlayerClass.WARRIOR
    inventory: List[Item] = field(default_factory=list)
    equipment: Dict[str, Optional[Item]] = field(default_factory=lambda: {
        "weapon": None,
        "armor": None,
        "artifact": None
    })
    in_battle: bool = False
    current_monster: Optional[Monster] = None

# ============= БАЗА ДАННЫХ =============
class Database:
    def __init__(self, db_name="game.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
        self.init_game_data()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Игроки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                health INTEGER,
                max_health INTEGER,
                experience INTEGER,
                level INTEGER,
                gold INTEGER,
                location_id INTEGER,
                player_class TEXT,
                inventory TEXT,
                equipment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Предметы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                power INTEGER,
                price INTEGER,
                description TEXT
            )
        ''')
        
        # Локации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                description TEXT,
                connections TEXT,
                required_level INTEGER
            )
        ''')
        
        # Монстры
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monsters (
                id INTEGER PRIMARY KEY,
                name TEXT,
                level INTEGER,
                health INTEGER,
                damage INTEGER,
                experience INTEGER,
                location_id INTEGER,
                description TEXT
            )
        ''')
        
        # Лут монстров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monster_loot (
                monster_id INTEGER,
                item_id INTEGER,
                drop_chance REAL
            )
        ''')
        
        self.conn.commit()
    
    def init_game_data(self):
        cursor = self.conn.cursor()
        
        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM locations")
        if cursor.fetchone()[0] == 0:
            self.create_initial_data()
    
    def create_initial_data(self):
        cursor = self.conn.cursor()
        
        # Создаем предметы
        items = [
            (1, "Ржавый меч", "WEAPON", 10, 20, "Старый, но острый"),
            (2, "Деревянный щит", "ARMOR", 5, 15, "Простой щит из дуба"),
            (3, "Кожаный доспех", "ARMOR", 8, 30, "Легкая броня"),
            (4, "Зелье здоровья", "POTION", 20, 10, "Восстанавливает здоровье"),
            (5, "Посох мага", "WEAPON", 15, 50, "Усиливает магию"),
            (6, "Лук охотника", "WEAPON", 12, 40, "Точный и быстрый"),
            (7, "Кольцо силы", "ARTIFACT", 5, 100, "Увеличивает силу"),
            (8, "Амулет защиты", "ARTIFACT", 3, 80, "Защищает от урона"),
            (9, "Золотой ключ", "ARTIFACT", 0, 0, "Открывает тайные двери"),
            (10, "Эликсир маны", "POTION", 0, 25, "Восстанавливает ману"),
        ]
        
        cursor.executemany(
            "INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)",
            items
        )
        
        # Создаем локации
        locations = [
            (1, "Стартовая деревня", "VILLAGE", "Мирная деревня у подножья гор. Здесь начинается ваше приключение.", "2,3", 1),
            (2, "Темный лес", "FOREST", "Густой лес, полный опасностей и тайн.", "1,4", 2),
            (3, "Горный перевал", "MOUNTAINS", "Высоко в горах, где дуют холодные ветра.", "1,5", 3),
            (4, "Заброшенные руины", "RUINS", "Древние развалины, хранящие древние секреты.", "2,6", 4),
            (5, "Пещера гоблинов", "DUNGEON", "Темная пещера, кишащая гоблинами.", "3,6", 5),
            (6, "Логово дракона", "DUNGEON", "Огненная пещера, где обитает древний дракон.", "4,5", 10),
        ]
        
        cursor.executemany(
            "INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?)",
            locations
        )
        
        # Создаем монстров
        monsters = [
            (1, "Гоблин", 2, 30, 8, 20, 2, "Маленький, но злобный"),
            (2, "Волк", 1, 25, 6, 15, 2, "Дикий лесной волк"),
            (3, "Скелет", 3, 40, 10, 30, 4, "Неупокоенный воин"),
            (4, "Орк", 4, 60, 15, 50, 3, "Сильный и жестокий"),
            (5, "Горный тролль", 5, 80, 20, 70, 3, "Медленный, но могучий"),
            (6, "Дракон", 10, 200, 35, 300, 6, "Древнее огнедышащее чудовище"),
            (7, "Призрак", 3, 35, 12, 35, 4, "Бестелесный дух"),
            (8, "Паук-гигант", 2, 45, 9, 25, 2, "Огромный ядовитый паук"),
        ]
        
        cursor.executemany(
            "INSERT INTO monsters VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            monsters
        )
        
        # Лут монстров
        loot = [
            (1, 1, 0.5),   # Гоблин -> Ржавый меч
            (1, 4, 0.3),   # Гоблин -> Зелье здоровья
            (2, 4, 0.4),   # Волк -> Зелье здоровья
            (3, 2, 0.3),   # Скелет -> Деревянный щит
            (4, 3, 0.4),   # Орк -> Кожаный доспех
            (5, 5, 0.2),   # Тролль -> Посох мага
            (6, 9, 1.0),   # Дракон -> Золотой ключ (гарантированно)
            (6, 7, 0.5),   # Дракон -> Кольцо силы
        ]
        
        cursor.executemany(
            "INSERT INTO monster_loot VALUES (?, ?, ?)",
            loot
        )
        
        self.conn.commit()
    
    def save_player(self, player: Player):
        cursor = self.conn.cursor()
        
        # Преобразуем инвентарь и экипировку в JSON строки
        import json
        inventory_json = json.dumps([item.id for item in player.inventory])
        
        equipment_json = json.dumps({
            slot: item.id if item else None
            for slot, item in player.equipment.items()
        })
        
        cursor.execute('''
            INSERT OR REPLACE INTO players 
            (user_id, username, health, max_health, experience, level, gold, 
             location_id, player_class, inventory, equipment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            player.user_id, player.username, player.health, player.max_health,
            player.experience, player.level, player.gold, player.location_id,
            player.player_class.value, inventory_json, equipment_json
        ))
        
        self.conn.commit()
    
    def load_player(self, user_id: int) -> Optional[Player]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        import json
        player = Player(
            user_id=row[0],
            username=row[1],
            health=row[2],
            max_health=row[3],
            experience=row[4],
            level=row[5],
            gold=row[6],
            location_id=row[7],
            player_class=PlayerClass(row[8])
        )
        
        # Загружаем инвентарь
        inventory_ids = json.loads(row[9]) if row[9] else []
        player.inventory = [self.get_item(item_id) for item_id in inventory_ids if self.get_item(item_id)]
        
        # Загружаем экипировку
        equipment_data = json.loads(row[10]) if row[10] else {}
        for slot, item_id in equipment_data.items():
            if item_id:
                player.equipment[slot] = self.get_item(item_id)
        
        return player
    
    def get_item(self, item_id: int) -> Optional[Item]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if row:
            return Item(
                id=row[0],
                name=row[1],
                type=ItemType(row[2]),
                power=row[3],
                price=row[4],
                description=row[5]
            )
        return None
    
    def get_location(self, location_id: int) -> Optional[Location]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        location = Location(
            id=row[0],
            name=row[1],
            type=LocationType(row[2]),
            description=row[3],
            required_level=row[5]
        )
        
        # Загружаем связи локаций
        if row[4]:
            location.connections = [int(x) for x in row[4].split(',')]
        
        # Загружаем монстров для этой локации
        cursor.execute("SELECT * FROM monsters WHERE location_id = ?", (location_id,))
        monster_rows = cursor.fetchall()
        
        for monster_row in monster_rows:
            monster = Monster(
                id=monster_row[0],
                name=monster_row[1],
                level=monster_row[2],
                health=monster_row[3],
                damage=monster_row[4],
                experience=monster_row[5],
                description=monster_row[7]
            )
            
            # Загружаем лут для монстра
            cursor.execute(
                "SELECT item_id FROM monster_loot WHERE monster_id = ? AND drop_chance >= ?",
                (monster.id, random.random())
            )
            loot_rows = cursor.fetchall()
            
            for loot_row in loot_rows:
                item = self.get_item(loot_row[0])
                if item:
                    monster.loot.append(item)
            
            location.monsters.append(monster)
        
        return location
    
    def get_all_locations(self) -> List[Location]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM locations")
        return [self.get_location(row[0]) for row in cursor.fetchall()]

# ============= ИГРОВОЙ МЕНЕДЖЕР =============
class GameManager:
    def __init__(self):
        self.db = Database()
        self.players: Dict[int, Player] = {}
        self.active_players = set()
    
    def register_player(self, user_id: int, username: str) -> Player:
        if len(self.active_players) >= MAX_PLAYERS and user_id not in self.active_players:
            raise Exception(f"Достигнут максимум игроков ({MAX_PLAYERS})")
        
        player = self.db.load_player(user_id)
        if not player:
            player = Player(
                user_id=user_id,
                username=username,
                health=100,
                max_health=100,
                experience=0,
                level=1,
                gold=50,
                location_id=1,
                player_class=PlayerClass.WARRIOR
            )
        
        self.players[user_id] = player
        self.active_players.add(user_id)
        return player
    
    def save_player(self, user_id: int):
        if user_id in self.players:
            self.db.save_player(self.players[user_id])
    
    def get_player(self, user_id: int) -> Optional[Player]:
        return self.players.get(user_id)
    
    def remove_player(self, user_id: int):
        if user_id in self.players:
            self.save_player(user_id)
            del self.players[user_id]
            self.active_players.discard(user_id)
    
    def get_random_monster(self, location_id: int) -> Optional[Monster]:
        location = self.db.get_location(location_id)
        if location and location.monsters:
            return random.choice(location.monsters)
        return None
    
    def calculate_damage(self, player: Player, monster: Monster) -> int:
        base_damage = 10 + player.level * 2
        
        # Бонус от класса
        if player.player_class == PlayerClass.WARRIOR:
            base_damage += 5
        elif player.player_class == PlayerClass.ARCHER:
            base_damage += 3
        
        # Бонус от оружия
        if player.equipment.get("weapon"):
            base_damage += player.equipment["weapon"].power
        
        # Случайный множитель
        damage = int(base_damage * random.uniform(0.8, 1.2))
        
        # Критический удар
        if random.random() < 0.1:  # 10% шанс крита
            damage *= 2
        
        return max(1, damage)
    
    def calculate_monster_damage(self, monster: Monster) -> int:
        return int(monster.damage * random.uniform(0.9, 1.1))
    
    def gain_experience(self, player: Player, experience: int):
        player.experience += experience
        while player.experience >= self.get_exp_for_level(player.level):
            player.experience -= self.get_exp_for_level(player.level)
            player.level += 1
            player.max_health += 20
            player.health = player.max_health
    
    def get_exp_for_level(self, level: int) -> int:
        return 100 * level
    
    def get_connected_locations(self, location_id: int) -> List[Location]:
        location = self.db.get_location(location_id)
        if not location:
            return []
        
        return [self.db.get_location(conn_id) for conn_id in location.connections]

# ============= СОСТОЯНИЯ FSM =============
class GameStates(StatesGroup):
    choosing_class = State()
    main_menu = State()
    exploring = State()
    in_battle = State()
    inventory = State()
    character = State()
    trading = State()

# ============= ИНИЦИАЛИЗАЦИЯ БОТА =============
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

game_manager = GameManager()

# ============= КЛАВИАТУРЫ =============
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Исследовать", callback_data="explore")],
            [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
            [InlineKeyboardButton(text="👤 Персонаж", callback_data="character")],
            [InlineKeyboardButton(text="⚔️ Найти бой", callback_data="battle")],
            [InlineKeyboardButton(text="🏘️ Локации", callback_data="locations")],
        ]
    )

def get_class_choose_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Воин", callback_data="class_warrior")],
            [InlineKeyboardButton(text="🔮 Маг", callback_data="class_mage")],
            [InlineKeyboardButton(text="🗡️ Разбойник", callback_data="class_rogue")],
            [InlineKeyboardButton(text="🏹 Лучник", callback_data="class_archer")],
        ]
    )

def get_battle_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="attack")],
            [InlineKeyboardButton(text="🏃 Сбежать", callback_data="flee")],
            [InlineKeyboardButton(text="💊 Использовать зелье", callback_data="use_potion")],
        ]
    )

def get_location_keyboard(location_id: int):
    locations = game_manager.get_connected_locations(location_id)
    keyboard = []
    
    for location in locations:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📍 {location.name} (Ур. {location.required_level})",
                callback_data=f"move_{location.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_inventory_keyboard(player: Player):
    keyboard = []
    
    for i, item in enumerate(player.inventory[:10]):  # Показываем первые 10 предметов
        keyboard.append([
            InlineKeyboardButton(
                text=f"{item.name} ({item.type.value})",
                callback_data=f"item_{i}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============= ОБРАБОТЧИКИ КОМАНД =============
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        player = game_manager.register_player(user_id, message.from_user.username or message.from_user.first_name)
        
        if player.level == 1 and not player.player_class:
            await message.answer(
                "Добро пожаловать в мир приключений!\n"
                "Выберите класс вашего персонажа:",
                reply_markup=get_class_choose_keyboard()
            )
            await state.set_state(GameStates.choosing_class)
        else:
            await show_main_menu(message, player)
            await state.set_state(GameStates.main_menu)
            
    except Exception as e:
        await message.answer(f"❌ {str(e)}")

@router.message(Command("status"))
async def cmd_status(message: Message):
    player = game_manager.get_player(message.from_user.id)
    if player:
        await show_character_info(message, player)
    else:
        await message.answer("Сначала начните игру с помощью /start")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
    🎮 *Квестовая игра в Telegram*
    
    *Основные команды:*
    /start - Начать игру
    /status - Показать статус персонажа
    /help - Показать это сообщение
    
    *Игровой процесс:*
    1. Выберите класс персонажа
    2. Исследуйте различные локации
    3. Сражайтесь с монстрами
    4. Собирайте добычу и артефакты
    5. Улучшайте своего персонажа
    
    *Особенности:*
    • Максимум 3 игрока одновременно
    • 6 уникальных локаций
    • 4 класса персонажей
    • Система уровней и экипировки
    • Случайная генерация монстров
    
    Удачи в приключениях! 🗡️
    """
    await message.answer(help_text, parse_mode="Markdown")

# ============= ОБРАБОТЧИКИ КНОПОК =============
@router.callback_query(F.data.startswith("class_"))
async def process_class_choose(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    class_map = {
        "class_warrior": PlayerClass.WARRIOR,
        "class_mage": PlayerClass.MAGE,
        "class_rogue": PlayerClass.ROGUE,
        "class_archer": PlayerClass.ARCHER
    }
    
    player.player_class = class_map[callback.data]
    
    # Даем стартовые предметы в зависимости от класса
    if player.player_class == PlayerClass.WARRIOR:
        player.inventory.append(game_manager.db.get_item(1))  # Ржавый меч
        player.inventory.append(game_manager.db.get_item(2))  # Деревянный щит
    elif player.player_class == PlayerClass.MAGE:
        player.inventory.append(game_manager.db.get_item(5))  # Посох мага
        player.inventory.append(game_manager.db.get_item(10)) # Эликсир маны
    elif player.player_class == PlayerClass.ROGUE:
        player.inventory.append(game_manager.db.get_item(1))  # Ржавый меч
        player.inventory.append(game_manager.db.get_item(4))  # Зелье здоровья
    elif player.player_class == PlayerClass.ARCHER:
        player.inventory.append(game_manager.db.get_item(6))  # Лук охотника
        player.inventory.append(game_manager.db.get_item(4))  # Зелье здоровья
    
    game_manager.save_player(user_id)
    
    await callback.message.edit_text(
        f"🎉 Отличный выбор! Вы теперь {player.player_class.value}!\n"
        f"Вам выданы стартовые предметы.\n\n"
        f"*Здоровье:* {player.health}/{player.max_health}\n"
        f"*Уровень:* {player.level}\n"
        f"*Опыт:* {player.experience}/{game_manager.get_exp_for_level(player.level)}\n"
        f"*Золото:* {player.gold}💰\n\n"
        f"Отправляйтесь в приключения!",
        parse_mode="Markdown"
    )
    
    await show_main_menu(callback.message, player)
    await state.set_state(GameStates.main_menu)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if player:
        await show_main_menu(callback.message, player)
        await state.set_state(GameStates.main_menu)
    await callback.answer()

@router.callback_query(F.data == "explore")
async def process_explore(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    location = game_manager.db.get_location(player.location_id)
    
    if not location:
        await callback.answer("Локация не найдена!")
        return
    
    # Случайное событие при исследовании
    event_chance = random.random()
    
    if event_chance < 0.4:  # 40% шанс найти монстра
        monster = game_manager.get_random_monster(player.location_id)
        if monster:
            player.in_battle = True
            player.current_monster = monster
            
            await callback.message.edit_text(
                f"🦖 *Внезапная атака!*\n\n"
                f"Вы встретили *{monster.name}* (Ур. {monster.level})!\n"
                f"*Здоровье:* {monster.health}\n"
                f"*Урон:* {monster.damage}\n\n"
                f"{monster.description}\n\n"
                f"Выберите действие:",
                parse_mode="Markdown",
                reply_markup=get_battle_keyboard()
            )
            await state.set_state(GameStates.in_battle)
        else:
            await callback.message.edit_text(
                f"📍 *{location.name}*\n\n"
                f"{location.description}\n\n"
                f"Вы внимательно осматриваете местность, "
                f"но ничего интересного не находите.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔍 Продолжить исследовать", callback_data="explore")],
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ]
                )
            )
    
    elif event_chance < 0.7:  # 30% шанс найти предмет
        items = game_manager.db.get_location(player.location_id).items
        if random.random() < 0.5:  # 50% шанс найти что-то
            all_items = [game_manager.db.get_item(i) for i in range(1, 11)]
            found_item = random.choice(all_items)
            
            player.inventory.append(found_item)
            game_manager.save_player(user_id)
            
            await callback.message.edit_text(
                f"🎁 *Вы нашли сокровище!*\n\n"
                f"*Найден предмет:* {found_item.name}\n"
                f"*Тип:* {found_item.type.value}\n"
                f"*Описание:* {found_item.description}\n\n"
                f"Предмет добавлен в инвентарь!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔍 Продолжить исследовать", callback_data="explore")],
                        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ]
                )
            )
        else:
            gold_found = random.randint(5, 20)
            player.gold += gold_found
            
            await callback.message.edit_text(
                f"💰 *Вы нашли золото!*\n\n"
                f"В старом сундуке вы нашли *{gold_found}* золотых монет!\n"
                f"Теперь у вас *{player.gold}*💰",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔍 Продолжить исследовать", callback_data="explore")],
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ]
                )
            )
    
    else:  # 30% шанс ничего не найти
        await callback.message.edit_text(
            f"📍 *{location.name}*\n\n"
            f"{location.description}\n\n"
            f"Вы бродите по окрестностям, "
            f"но сегодняшний день кажется спокойным.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Продолжить исследовать", callback_data="explore")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]
            )
        )
    
    await callback.answer()

@router.callback_query(F.data == "battle")
async def process_battle(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    monster = game_manager.get_random_monster(player.location_id)
    
    if not monster:
        await callback.message.edit_text(
            "В этой локации сейчас тихо. Попробуйте исследовать другие места!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌍 Исследовать", callback_data="explore")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]
            )
        )
        await callback.answer()
        return
    
    player.in_battle = True
    player.current_monster = monster
    
    await callback.message.edit_text(
        f"⚔️ *Битва начинается!*\n\n"
        f"*Противник:* {monster.name} (Ур. {monster.level})\n"
        f"*Здоровье:* {monster.health}\n"
        f"*Урон:* {monster.damage}\n\n"
        f"{monster.description}\n\n"
        f"*Ваше здоровье:* {player.health}/{player.max_health}\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_battle_keyboard()
    )
    await state.set_state(GameStates.in_battle)
    await callback.answer()

@router.callback_query(F.data == "attack", GameStates.in_battle)
async def process_attack(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player or not player.in_battle or not player.current_monster:
        await callback.answer("Битва не найдена!")
        return
    
    monster = player.current_monster
    
    # Игрок атакует
    player_damage = game_manager.calculate_damage(player, monster)
    monster.health -= player_damage
    
    battle_log = f"⚔️ Вы нанесли *{player_damage}* урона!\n"
    battle_log += f"У монстра осталось *{max(0, monster.health)}* HP\n\n"
    
    # Проверяем, умер ли монстр
    if monster.health <= 0:
        # Награда за победу
        exp_gained = monster.experience
        gold_gained = random.randint(10, 30)
        
        game_manager.gain_experience(player, exp_gained)
        player.gold += gold_gained
        
        # Лут с монстра
        loot_text = ""
        if monster.loot:
            for item in monster.loot:
                player.inventory.append(item)
                loot_text += f"• {item.name}\n"
        
        player.in_battle = False
        player.current_monster = None
        game_manager.save_player(user_id)
        
        await callback.message.edit_text(
            f"🎉 *Победа!*\n\n"
            f"Вы победили *{monster.name}*!\n\n"
            f"*Награды:*\n"
            f"Опыт: +{exp_gained}\n"
            f"Золото: +{gold_gained}💰\n"
            f"*Уровень:* {player.level}\n"
            f"*Опыт:* {player.experience}/{game_manager.get_exp_for_level(player.level)}\n\n"
            f"*Добыча:*\n{loot_text if loot_text else 'Нет'}\n"
            f"Что будем делать дальше?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌍 Исследовать", callback_data="explore")],
                    [InlineKeyboardButton(text="⚔️ Новый бой", callback_data="battle")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]
            )
        )
        await state.set_state(GameStates.main_menu)
        await callback.answer()
        return
    
    # Монстр атакует в ответ
    monster_damage = game_manager.calculate_monster_damage(monster)
    player.health -= monster_damage
    
    battle_log += f"🦖 {monster.name} наносит вам *{monster_damage}* урона!\n"
    battle_log += f"У вас осталось *{player.health}* HP\n\n"
    
    # Проверяем, умер ли игрок
    if player.health <= 0:
        player.health = player.max_health // 2  # Воскрешение с половиной HP
        player.in_battle = False
        player.current_monster = None
        player.gold = max(0, player.gold // 2)  # Теряем половину золота
        game_manager.save_player(user_id)
        
        await callback.message.edit_text(
            f"💀 *Поражение!*\n\n"
            f"Вы были повержены {monster.name}!\n\n"
            f"Вы теряете сознание и просыпаетесь в стартовой локации.\n"
            f"Потеряно половина золота.\n\n"
            f"*Текущее здоровье:* {player.health}/{player.max_health}\n"
            f"*Золото:* {player.gold}💰\n\n"
            f"Будьте осторожнее в следующий раз!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌍 Исследовать", callback_data="explore")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]
            )
        )
        await state.set_state(GameStates.main_menu)
        await callback.answer()
        return
    
    # Продолжаем битву
    await callback.message.edit_text(
        f"{battle_log}"
        f"*{monster.name}* (Ур. {monster.level})\n"
        f"Здоровье: {monster.health}\n\n"
        f"*{player.username}* (Ур. {player.level})\n"
        f"Здоровье: {player.health}/{player.max_health}\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_battle_keyboard()
    )
    
    await callback.answer()

@router.callback_query(F.data == "flee", GameStates.in_battle)
async def process_flee(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player or not player.in_battle:
        await callback.answer("Битва не найдена!")
        return
    
    flee_chance = 0.6  # 60% шанс сбежать
    
    if random.random() < flee_chance:
        player.in_battle = False
        player.current_monster = None
        
        await callback.message.edit_text(
            "🏃 *Вы успешно сбежали!*\n\n"
            "Вам удалось оторваться от противника и скрыться.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌍 Исследовать", callback_data="explore")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]
            )
        )
        await state.set_state(GameStates.main_menu)
    else:
        # Не удалось сбежать, монстр атакует
        monster = player.current_monster
        monster_damage = game_manager.calculate_monster_damage(monster)
        player.health -= monster_damage
        
        await callback.message.edit_text(
            f"❌ *Не удалось сбежать!*\n\n"
            f"Пока вы пытались бежать, {monster.name} атаковал вас!\n"
            f"Получено *{monster_damage}* урона.\n\n"
            f"*Ваше здоровье:* {player.health}/{player.max_health}\n\n"
            f"Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_battle_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data == "use_potion", GameStates.in_battle)
async def process_use_potion(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player or not player.in_battle:
        await callback.answer("Битва не найдена!")
        return
    
    # Ищем зелье здоровья в инвентаре
    potion = next((item for item in player.inventory if item.type == ItemType.POTION), None)
    
    if potion:
        # Используем зелье
        player.health = min(player.max_health, player.health + potion.power)
        player.inventory.remove(potion)
        
        # Монстр атакует пока вы пьете зелье
        monster = player.current_monster
        monster_damage = game_manager.calculate_monster_damage(monster)
        player.health -= monster_damage
        
        await callback.message.edit_text(
            f"💊 *Вы использовали {potion.name}!*\n\n"
            f"Восстановлено {potion.power} здоровья.\n"
            f"Но {monster.name} атаковал вас, пока вы пили зелье!\n"
            f"Получено *{monster_damage}* урона.\n\n"
            f"*Ваше здоровье:* {player.health}/{player.max_health}\n\n"
            f"Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_battle_keyboard()
        )
    else:
        await callback.answer("У вас нет зелий!", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "inventory")
async def process_inventory(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    inventory_text = "🎒 *Ваш инвентарь*\n\n"
    
    if not player.inventory:
        inventory_text += "Инвентарь пуст.\n"
    else:
        for i, item in enumerate(player.inventory):
            inventory_text += f"{i+1}. *{item.name}*\n"
            inventory_text += f"   Тип: {item.type.value}\n"
            if item.power > 0:
                inventory_text += f"   Сила: {item.power}\n"
            inventory_text += f"   Описание: {item.description}\n\n"
    
    inventory_text += f"\n*Экипировка:*\n"
    for slot, item in player.equipment.items():
        item_name = item.name if item else "Пусто"
        inventory_text += f"• {slot}: {item_name}\n"
    
    inventory_text += f"\n*Золото:* {player.gold}💰"
    
    await callback.message.edit_text(
        inventory_text,
        parse_mode="Markdown",
        reply_markup=get_inventory_keyboard(player)
    )
    await state.set_state(GameStates.inventory)
    await callback.answer()

@router.callback_query(F.data.startswith("item_"), GameStates.inventory)
async def process_item_action(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    item_index = int(callback.data.split("_")[1])
    
    if item_index >= len(player.inventory):
        await callback.answer("Предмет не найден!")
        return
    
    item = player.inventory[item_index]
    
    # Определяем возможные действия для предмета
    keyboard = []
    
    if item.type == ItemType.WEAPON:
        keyboard.append([InlineKeyboardButton(text="🗡️ Экипировать как оружие", callback_data=f"equip_weapon_{item_index}")])
    elif item.type == ItemType.ARMOR:
        keyboard.append([InlineKeyboardButton(text="🛡️ Экипировать как броню", callback_data=f"equip_armor_{item_index}")])
    elif item.type == ItemType.ARTIFACT:
        keyboard.append([InlineKeyboardButton(text="💎 Экипировать как артефакт", callback_data=f"equip_artifact_{item_index}")])
    elif item.type == ItemType.POTION:
        keyboard.append([InlineKeyboardButton(text="💊 Использовать", callback_data=f"use_{item_index}")])
    
    keyboard.append([InlineKeyboardButton(text="💰 Продать", callback_data=f"sell_{item_index}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к инвентарю", callback_data="inventory")])
    
    await callback.message.edit_text(
        f"*{item.name}*\n\n"
        f"*Тип:* {item.type.value}\n"
        f"*Сила:* {item.power}\n"
        f"*Цена:* {item.price}💰\n"
        f"*Описание:* {item.description}\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("equip_"))
async def process_equip(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    _, slot, item_index = callback.data.split("_")
    item_index = int(item_index)
    
    if item_index >= len(player.inventory):
        await callback.answer("Предмет не найден!")
        return
    
    item = player.inventory[item_index]
    
    # Снимаем текущую экипировку (если есть)
    old_item = player.equipment.get(slot)
    if old_item:
        player.inventory.append(old_item)
    
    # Экипируем новый предмет
    player.equipment[slot] = item
    player.inventory.pop(item_index)
    
    game_manager.save_player(user_id)
    
    await callback.answer(f"Предмет {item.name} экипирован!", show_alert=True)
    await process_inventory(callback, None)

@router.callback_query(F.data.startswith("use_"))
async def process_use_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    item_index = int(callback.data.split("_")[1])
    
    if item_index >= len(player.inventory):
        await callback.answer("Предмет не найден!")
        return
    
    item = player.inventory[item_index]
    
    if item.type == ItemType.POTION:
        player.health = min(player.max_health, player.health + item.power)
        player.inventory.pop(item_index)
        game_manager.save_player(user_id)
        
        await callback.answer(f"Использовано {item.name}! Здоровье: {player.health}/{player.max_health}", show_alert=True)
        await process_inventory(callback, None)
    else:
        await callback.answer("Этот предмет нельзя использовать так!", show_alert=True)

@router.callback_query(F.data.startswith("sell_"))
async def process_sell_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    item_index = int(callback.data.split("_")[1])
    
    if item_index >= len(player.inventory):
        await callback.answer("Предмет не найден!")
        return
    
    item = player.inventory[item_index]
    sell_price = item.price // 2  # Продаем за полцены
    
    player.gold += sell_price
    player.inventory.pop(item_index)
    game_manager.save_player(user_id)
    
    await callback.answer(f"Предмет продан за {sell_price}💰", show_alert=True)
    await process_inventory(callback, None)

@router.callback_query(F.data == "character")
async def process_character(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if player:
        await show_character_info(callback.message, player)
        await state.set_state(GameStates.character)
    await callback.answer()

@router.callback_query(F.data == "locations")
async def process_locations(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    location = game_manager.db.get_location(player.location_id)
    
    if not location:
        await callback.answer("Локация не найдена!")
        return
    
    await callback.message.edit_text(
        f"📍 *Текущая локация: {location.name}*\n\n"
        f"{location.description}\n\n"
        f"*Тип:* {location.type.value}\n"
        f"*Требуемый уровень:* {location.required_level}\n\n"
        f"Вы можете отправиться в:",
        parse_mode="Markdown",
        reply_markup=get_location_keyboard(player.location_id)
    )
    await state.set_state(GameStates.exploring)
    await callback.answer()

@router.callback_query(F.data.startswith("move_"))
async def process_move(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = game_manager.get_player(user_id)
    
    if not player:
        await callback.answer("Игрок не найден!")
        return
    
    target_location_id = int(callback.data.split("_")[1])
    target_location = game_manager.db.get_location(target_location_id)
    
    if not target_location:
        await callback.answer("Локация не найдена!")
        return
    
    # Проверяем уровень
    if player.level < target_location.required_level:
        await callback.answer(
            f"Недостаточный уровень! Требуется: {target_location.required_level}",
            show_alert=True
        )
        return
    
    # Проверяем, связана ли локация
    current_location = game_manager.db.get_location(player.location_id)
    if target_location_id not in current_location.connections:
        await callback.answer("Нельзя перейти в эту локацию отсюда!", show_alert=True)
        return
    
    player.location_id = target_location_id
    game_manager.save_player(user_id)
    
    await callback.message.edit_text(
        f"🚶 *Вы переместились в {target_location.name}!*\n\n"
        f"{target_location.description}\n\n"
        f"Что будем делать здесь?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Исследовать", callback_data="explore")],
                [InlineKeyboardButton(text="⚔️ Найти бой", callback_data="battle")],
                [InlineKeyboardButton(text="📍 Другие локации", callback_data="locations")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
            ]
        )
    )
    await callback.answer()

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============
async def show_main_menu(message, player: Player):
    location = game_manager.db.get_location(player.location_id)
    location_name = location.name if location else "Неизвестно"
    
    text = (
        f"🎮 *Главное меню*\n\n"
        f"👤 *{player.username}*\n"
        f"⚔️ *Класс:* {player.player_class.value}\n"
        f"❤️ *Здоровье:* {player.health}/{player.max_health}\n"
        f"⭐ *Уровень:* {player.level}\n"
        f"📊 *Опыт:* {player.experience}/{game_manager.get_exp_for_level(player.level)}\n"
        f"💰 *Золото:* {player.gold}\n"
        f"📍 *Локация:* {location_name}\n\n"
        f"Выберите действие:"
    )
    
    if isinstance(message, Message):
        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
    else:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

async def show_character_info(message, player: Player):
    location = game_manager.db.get_location(player.location_id)
    location_name = location.name if location else "Неизвестно"
    
    # Статистика урона
    base_damage = 10 + player.level * 2
    if player.player_class == PlayerClass.WARRIOR:
        base_damage += 5
    elif player.player_class == PlayerClass.ARCHER:
        base_damage += 3
    
    text = (
        f"👤 *Статистика персонажа*\n\n"
        f"*Имя:* {player.username}\n"
        f"*Класс:* {player.player_class.value}\n"
        f"*Уровень:* {player.level}\n"
        f"*Опыт:* {player.experience}/{game_manager.get_exp_for_level(player.level)}\n\n"
        f"*Характеристики:*\n"
        f"❤️ Здоровье: {player.health}/{player.max_health}\n"
        f"⚔️ Урон: ~{base_damage}\n"
        f"💰 Золото: {player.gold}\n"
        f"📍 Локация: {location_name}\n\n"
        f"*Экипировка:*\n"
    )
    
    for slot, item in player.equipment.items():
        item_name = item.name if item else "Пусто"
        text += f"• {slot}: {item_name}\n"
    
    text += f"\n*Следующий уровень через:* {game_manager.get_exp_for_level(player.level) - player.experience} опыта"
    
    if isinstance(message, Message):
        await message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
            ]
        ))
    else:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
            ]
        ))

# ============= ЗАПУСК БОТА =============
async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
