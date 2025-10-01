import random
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def animated_print(text, delay=0.03):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def get_display_length(text):
    import unicodedata
    
    length = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W'):
            length += 2
        elif char == '️':
            continue
        else:
            length += 1
    
    return length

def create_box(lines, width=None):
    if not lines:
        return
    if width is None:
        width = max(get_display_length(line) for line in lines) + 4
    
    print("╔" + "═" * (width - 2) + "╗")
    for line in lines:
        if line == "":
            print("║" + " " * (width - 2) + "║")
        else:
            display_len = get_display_length(line)
            padding = width - display_len - 3
            print(f"║ {line}{' ' * padding}║")
    print("╚" + "═" * (width - 2) + "╝")

def create_menu_box(title, options, width=40):
    print("╔" + "═" * (width - 2) + "╗")
    title_display_len = get_display_length(title)
    title_padding = (width - 2 - title_display_len) // 2
    title_line = " " * title_padding + title + " " * (width - 2 - title_padding - title_display_len)
    print(f"║{title_line}║")
    print("╠" + "═" * (width - 2) + "╣")
    for option in options:
        option_display_len = get_display_length(option)
        option_padding = width - option_display_len - 4
        print(f"║  {option}{' ' * option_padding}║")
    print("╚" + "═" * (width - 2) + "╝")

def print_header():
    create_box([
        "⚔️  SZÖRNYEK ÉS FEGYVEREK  ⚔️",
        "Kaland a sötétségben"
    ], 60)

def print_divider(length=60):
    print("═" * length)

def get_random_monster():
    monsters = {
        "sárkány": {"emoji": "🐲", "desc": "Tüzet okádó sárkány"},
        "troll": {"emoji": "👹", "desc": "Hatalmas kőtroll"}, 
        "boszorkány": {"emoji": "🧙‍♀️", "desc": "Gonosz boszorkány"}
    }
    monster_name = random.choice(list(monsters.keys()))
    return monster_name, monsters[monster_name]

def get_weapon_choice():
    create_menu_box("🗡️  FEGYVER VALASZTAS  🗡️", [
        "1. ⚡ Varazspalca (Sarkany ellen jo)",
        "2. 🏹 Ij (Boszorkany ellen jo)",
        "3. ⚔️  Kard (Troll ellen jo)"
    ], 42)
    
    weapon_map = {
        "1": ("varazspalca", "⚡"),
        "2": ("ij", "🏹"), 
        "3": ("kard", "⚔️")
    }
    
    while True:
        choice = input("\n➤ Valassz fegyvert (1-3): ")
        if choice in weapon_map:
            return weapon_map[choice]
        print("❌ Ervenytelen valasztas! Kerlek valassz 1, 2 vagy 3-at!")

def calculate_win_chance(monster, weapon):
    good_combinations = [
        ("troll", "kard"),
        ("boszorkány", "ij"), 
        ("sárkány", "varazspalca")
    ]
    return 85 if (monster, weapon) in good_combinations else 25

def show_battle_result(won, win_chance):
    if won and win_chance == 25:
        create_box(["🌟 HEROIKUS GYŐZELEM! 🌟", "Rossz fegyverrel győztél!", "+2 életpont! ⬆️⬆️"], 36)
        return 2
    elif won:
        create_box(["🎉 GYŐZELEM! 🎉", "+1 életpont! ⬆️"], 32)
        return 1
    else:
        create_box(["💀 VERESÉG! 💀", "-2 életpont! ⬇️"], 32)
        return -2

def show_character_sheet(name, weapon, weapon_emoji, hp):
    hp_display = "❤️ " * max(0, hp) + "💔" * max(0, 5 - hp)
    create_box([
        "📋 TULAJDONSÁGLAP 📋",
        "",
        f"🏆 Harcos neve:      {name}",
        f"{weapon_emoji} Választott fegyver: {weapon}",
        f"❤️  Életpont:        {hp} ({hp_display})"
    ], 50)

def show_game_over(name):
    create_box([
        "💀 JÁTÉK VÉGE 💀",
        "",
        f"{name} hősi halált halt...",
        "A sötétség győzedelmeskedett!"
    ], 44)

def create_stats():
    return {
        "gyozelmek": 0,
        "veresegek": 0,
        "heroikus_gyozelmek": 0,
        "ossz_hp_nyert": 0,
        "ossz_hp_veszitett": 0,
        "legjobb_sorozat": 0,
        "jelenlegi_sorozat": 0,
        "szornyek": {"sárkány": 0, "troll": 0, "boszorkány": 0},
        "fegyverek": {"varazspalca": 0, "ij": 0, "kard": 0},
        "pontok": 0
    }

def update_stats(stats, monster, weapon, won, hp_change, win_chance):
    stats["szornyek"][monster] += 1
    stats["fegyverek"][weapon] += 1
    
    if won:
        stats["gyozelmek"] += 1
        stats["jelenlegi_sorozat"] += 1
        stats["legjobb_sorozat"] = max(stats["legjobb_sorozat"], stats["jelenlegi_sorozat"])
        if win_chance == 25:
            stats["heroikus_gyozelmek"] += 1
            stats["pontok"] += 50
        else:
            stats["pontok"] += 25
    else:
        stats["veresegek"] += 1
        stats["jelenlegi_sorozat"] = 0
        stats["pontok"] -= 10
    
    if hp_change > 0:
        stats["ossz_hp_nyert"] += hp_change
    else:
        stats["ossz_hp_veszitett"] += abs(hp_change)

def show_stats_summary(stats, battle_num, max_battles):
    win_rate = (stats["gyozelmek"] / battle_num * 100) if battle_num > 0 else 0
    create_box([
        "📊 STATISZTIKÁK 📊",
        "",
        f"⚔️  Harcok: {battle_num}/{max_battles}",
        f"🏆 Győzelmek: {stats['gyozelmek']} ({win_rate:.1f}%)",
        f"💀 Vereségek: {stats['veresegek']}",
        f"🌟 Heroikus győzelmek: {stats['heroikus_gyozelmek']}",
        f"🔥 Legjobb sorozat: {stats['legjobb_sorozat']}",
        f"💰 Pontok: {stats['pontok']}"
    ], 40)

# This file contains only the functions needed for importing
# The main game logic is kept separate to avoid auto-execution