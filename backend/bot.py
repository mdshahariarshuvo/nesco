import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

# Conversation states
ADD_METER_NUMBER, ADD_METER_NAME, SET_MIN_METER, SET_MIN_AMOUNT = range(4)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to call backend
def call_backend(endpoint, data=None, method='POST'):
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method == 'POST':
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.get(url, params=data, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Backend call failed: {str(e)}")
        return {'success': False, 'error': str(e)}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = call_backend('/webhook/telegram', {
        'command': 'start',
        'telegram_user_id': user_id
    })
    
    await update.message.reply_text(result.get('message', 'Welcome to NESCO Meter Bot!'))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 *Available Commands:*

/start - Start the bot
/add - Add a new meter
/list - List all your meters
/check - Check balances for all meters
/remove - Remove a meter
/minbalance - Set minimum balance alert
/reminder - Toggle daily reminder (11 AM)
/help - Show this help message

💡 *How it works:*
1. Add your meter(s) with /add
2. Check balances anytime with /check
3. Get alerts when balance is low
4. Receive daily reminders at 11 AM
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Add meter conversation
async def add_meter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Let's add a new meter!\n\n"
        "Please send your meter number (e.g., 31041051783)\n"
        "Send /cancel to abort."
    )
    return ADD_METER_NUMBER

async def add_meter_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meter_number = update.message.text.strip()
    
    if not meter_number.isdigit():
        await update.message.reply_text("❌ Please send a valid meter number (only digits)")
        return ADD_METER_NUMBER
    
    context.user_data['meter_number'] = meter_number
    await update.message.reply_text("Great! Now send a name for this meter (e.g., Home, Shop, Office)")
    return ADD_METER_NAME

async def add_meter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meter_name = update.message.text.strip()
    meter_number = context.user_data['meter_number']
    user_id = update.effective_user.id
    
    await update.message.reply_text("⏳ Adding meter and verifying with NESCO...")
    
    result = call_backend('/api/add-meter', {
        'telegram_user_id': user_id,
        'meter_number': meter_number,
        'meter_name': meter_name
    })
    
    if result.get('success'):
        await update.message.reply_text(result['message'])
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def list_meters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = call_backend('/api/list-meters', {'telegram_user_id': user_id})
    
    if not result.get('success'):
        await update.message.reply_text(f"❌ Error: {result.get('error')}")
        return
    
    meters = result.get('meters', [])
    if not meters:
        await update.message.reply_text(result.get('message', 'No meters found'))
        return
    
    message = "📊 *Your Meters:*\n\n"
    for i, meter in enumerate(meters, 1):
        message += f"{i}. *{meter['name']}*\n"
        message += f"   Number: `{meter['number']}`\n"
        message += f"   Min Balance: {meter['min_balance']} BDT\n"
        if meter['last_balance']:
            message += f"   Last Balance: {meter['last_balance']} BDT\n"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def check_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Checking balances from NESCO... This may take a moment...")
    
    result = call_backend('/api/check-balances', {'telegram_user_id': user_id})
    
    if not result.get('success'):
        await update.message.reply_text(f"❌ Error: {result.get('error')}")
        return
    
    results = result.get('results', [])
    timestamp = result.get('timestamp', '')
    
    message = f"💰 *Balance Report*\n_{timestamp}_\n\n"
    
    for i, meter in enumerate(results, 1):
        if 'error' in meter:
            message += f"{i}. *{meter['name']}* ({meter['number']})\n"
            message += f"   ❌ Error: {meter['error']}\n\n"
        else:
            alert_emoji = "⚠️" if meter.get('alert') else "✅"
            message += f"{i}. {alert_emoji} *{meter['name']}* ({meter['number']})\n"
            message += f"   Current: *{meter['balance']} BDT*\n"
            
            if meter['yesterday_usage'] is not None:
                message += f"   Yesterday: {meter['yesterday_usage']:.2f} BDT\n"
            else:
                message += f"   Yesterday: Not available yet\n"
            
            if meter.get('alert'):
                message += f"   🚨 Below minimum ({meter['min_balance']} BDT)!\n"
            
            message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def remove_meter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = call_backend('/api/list-meters', {'telegram_user_id': user_id})
    
    if not result.get('success') or not result.get('meters'):
        await update.message.reply_text("No meters to remove. Add one with /add")
        return
    
    meters = result['meters']
    keyboard = [[f"{i}. {m['name']} ({m['number']})"] for i, m in enumerate(meters, 1)]
    keyboard.append(["Cancel"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.user_data['remove_meters'] = meters
    
    await update.message.reply_text(
        "Select a meter to remove:",
        reply_markup=reply_markup
    )

async def remove_meter_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "Cancel":
        await update.message.reply_text("Cancelled", reply_markup=ReplyKeyboardRemove())
        return
    
    try:
        index = int(text.split('.')[0]) - 1
        meters = context.user_data.get('remove_meters', [])
        meter = meters[index]
        
        user_id = update.effective_user.id
        result = call_backend('/api/remove-meter', {
            'telegram_user_id': user_id,
            'meter_id': meter['id']
        })
        
        if result.get('success'):
            await update.message.reply_text(result['message'], reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"❌ Error: {result.get('error')}", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("Invalid selection", reply_markup=ReplyKeyboardRemove())

# Min balance conversation
async def minbalance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = call_backend('/api/list-meters', {'telegram_user_id': user_id})
    
    if not result.get('success') or not result.get('meters'):
        await update.message.reply_text("No meters found. Add one with /add")
        return ConversationHandler.END
    
    meters = result['meters']
    keyboard = [[f"{i}. {m['name']}"] for i, m in enumerate(meters, 1)]
    keyboard.append(["Cancel"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.user_data['minbalance_meters'] = meters
    
    await update.message.reply_text("Select a meter:", reply_markup=reply_markup)
    return SET_MIN_METER

async def minbalance_meter_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "Cancel":
        await update.message.reply_text("Cancelled", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    try:
        index = int(text.split('.')[0]) - 1
        meters = context.user_data.get('minbalance_meters', [])
        meter = meters[index]
        
        context.user_data['selected_meter'] = meter
        await update.message.reply_text(
            f"Send minimum balance amount for *{meter['name']}* (in BDT):",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_MIN_AMOUNT
    except:
        await update.message.reply_text("Invalid selection", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def minbalance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        meter = context.user_data['selected_meter']
        user_id = update.effective_user.id
        
        result = call_backend('/api/set-min-balance', {
            'telegram_user_id': user_id,
            'meter_id': meter['id'],
            'min_balance': amount
        })
        
        if result.get('success'):
            await update.message.reply_text(result['message'])
        else:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number")
    
    context.user_data.clear()
    return ConversationHandler.END

async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = call_backend('/api/toggle-reminder', {'telegram_user_id': user_id})
    
    if result.get('success'):
        await update.message.reply_text(result['message'])
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_meters))
    application.add_handler(CommandHandler("check", check_balances))
    application.add_handler(CommandHandler("reminder", toggle_reminder))
    
    # Add meter conversation
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_meter_start)],
        states={
            ADD_METER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meter_number)],
            ADD_METER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meter_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(add_conv)
    
    # Min balance conversation
    minbalance_conv = ConversationHandler(
        entry_points=[CommandHandler("minbalance", minbalance_start)],
        states={
            SET_MIN_METER: [MessageHandler(filters.TEXT & ~filters.COMMAND, minbalance_meter_selected)],
            SET_MIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, minbalance_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(minbalance_conv)
    
    # Remove meter (simplified, can be conversation if needed)
    application.add_handler(CommandHandler("remove", remove_meter_start))
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
