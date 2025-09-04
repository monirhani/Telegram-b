import os
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

# تنظیمات پایه - این مقادیر از متغیرهای محیطی خوانده می‌شوند
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8238948579:AAGktvxW6LhuKBXRRA_WsfD9n2bsMMC-izg')
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', 7798986445))

# تنظیمات پیش‌فرض
DEFAULT_REACTION = "❤️"
CHANNEL_ADD_COST = 5

# راه‌اندازی لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره‌سازی موقت داده‌ها
users = {}
channels = {}
groups = {}
gift_codes = {}
gift_code_usage = {}

# مقداردهی اولیه مالک اصلی
if ADMIN_CHAT_ID:
    users[ADMIN_CHAT_ID] = {
        'username': 'owner',
        'first_name': 'Owner',
        'last_name': '',
        'role': 'owner',
        'credit': 999999999,
        'invited_by': None,
        'join_date': datetime.now()
    }

# تابع کمکی برای بررسی دسترسی ادمین
def is_admin(user_id):
    user = users.get(user_id)
    return user and user['role'] in ['owner', 'admin']

# تابع کمکی برای بررسی دسترسی مالک
def is_owner(user_id):
    user = users.get(user_id)
    return user and user['role'] == 'owner'

# تابع ایجاد پنل شیشه ای
async def show_glass_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("شما دسترسی به پنل مدیریت را ندارید.")
        return
    
    # ایجاد کیبورد شیشه ای
    keyboard = [
        [InlineKeyboardButton("📊 آمار ربات", callback_data="stats")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="user_management")],
        [InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data="channel_management")],
        [InlineKeyboardButton("🎁 مدیریت کدهای هدیه", callback_data="gift_management")],
        [InlineKeyboardButton("⚙️ تنظیمات رای‌اکشن", callback_data="reaction_settings")]
    ]
    
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("👑 مدیریت ادمین‌ها", callback_data="admin_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🖥️ *پنل مدیریت شیشه ای*\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# هندلرهای callback query
async def handle_glass_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("شما دسترسی به پنل مدیریت را ندارید.")
        return
    
    data = query.data
    
    if data == "stats":
        # نمایش آمار ربات
        total_users = len(users)
        total_channels = len(channels)
        total_credits = sum(user['credit'] for user in users.values() if user['credit'] is not None)
        
        text = f"""
📊 *آمار ربات*
        
👥 تعداد کاربران: {total_users}
📢 تعداد کانال‌ها: {total_channels}
⭐ مجموع امتیازات: {total_credits}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "user_management":
        # مدیریت کاربران
        text = "👥 *مدیریت کاربران*\n\n"
        for uid, user in list(users.items())[:10]:  # نمایش ۱۰ کاربر اول
            text += f"🆔 {uid} - 👤 {user.get('first_name', '')} - 🏆 {user.get('role', '')} - ⭐ {user.get('credit', 0)}\n"
        
        if len(users) > 10:
            text += f"\n... و {len(users) - 10} کاربر دیگر"
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن امتیاز", callback_data="add_credit_menu")],
            [InlineKeyboardButton("➖ کسر امتیاز", callback_data="remove_credit_menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "channel_management":
        # مدیریت کانال‌ها
        text = "📢 *مدیریت کانال‌ها*\n\n"
        for cid, channel in channels.items():
            text += f"🆔 {cid} - 📢 {channel.get('channel_username', '')} - {channel.get('reaction_setting', DEFAULT_REACTION)}\n"
        
        keyboard = [
            [InlineKeyboardButton("⚙️ تغییر رای‌اکشن", callback_data="change_channel_reaction")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "gift_management":
        # مدیریت کدهای هدیه
        text = "🎁 *مدیریت کدهای هدیه*\n\nاز این بخش می‌توانید کدهای هدیه ایجاد و مدیریت کنید."
        
        keyboard = [
            [InlineKeyboardButton("🎫 ایجاد کد هدیه", callback_data="create_gift_code")],
            [InlineKeyboardButton("📋 لیست کدهای فعال", callback_data="active_gift_codes")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "reaction_settings":
        # تنظیمات رای‌اکشن
        text = "⚙️ *تنظیمات رای‌اکشن*\n\nاز این بخش می‌توانید رای‌اکشن پیش‌فرض را تغییر دهید."
        
        keyboard = [
            [InlineKeyboardButton("❤️ تغییر رای‌اکشن پیش‌فرض", callback_data="change_default_reaction")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "admin_management" and is_owner(user_id):
        # مدیریت ادمین‌ها (فقط برای مالک)
        admins = {uid: user for uid, user in users.items() if user.get('role') == 'admin'}
        
        text = "👑 *مدیریت ادمین‌ها*\n\n"
        for uid, admin in admins.items():
            text += f"🆔 {uid} - 👤 {admin.get('first_name', '')}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")],
            [InlineKeyboardButton("➖ حذف ادمین", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "back_to_panel":
        # بازگشت به پنل اصلی
        await show_glass_panel(update, context)

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # افزودن کاربر اگر وجود ندارد
    if user.id not in users:
        users[user.id] = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': 'user',
            'credit': 0,
            'invited_by': None,
            'join_date': datetime.now()
        }
    
    # بررسی اگر کاربر با لینک دعوت آمده
    if context.args and context.args[0].startswith('ref_'):
        try:
            inviter_id = int(context.args[0][4:])
            if inviter_id in users:
                # افزودن امتیاز به دعوت کننده
                if users[inviter_id]['role'] not in ['owner', 'admin']:
                    users[inviter_id]['credit'] += 5
                # ثبت دعوت شده
                users[user.id]['invited_by'] = inviter_id
        except ValueError:
            pass
    
    await update.message.reply_text(
        f"سلام {user.first_name}!\n\nبه ربات مدیریت کانال‌های تلگرام خوش آمدید.\n\n"
        "برای دسترسی به پنل مدیریت از دستور /panel استفاده کنید."
    )

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_glass_panel(update, context)

async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("فقط مالک ربات می‌تواند ادمین اضافه کند.")
        return
    
    if not context.args:
        await update.message.reply_text("لطفاً آیدی کاربر را وارد کنید: /addadmin <user_id>")
        return
    
    try:
        new_admin_id = int(context.args[0])
        if new_admin_id in users:
            users[new_admin_id]['role'] = 'admin'
            await update.message.reply_text(f"کاربر {new_admin_id} با موفقیت به عنوان ادمین افزوده شد.")
        else:
            await update.message.reply_text("کاربر یافت نشد.")
    except ValueError:
        await update.message.reply_text("آدی کاربر باید یک عدد باشد.")

async def credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users:
        await update.message.reply_text("شما در سیستم ثبت نشده‌اید. لطفاً /start را بزنید.")
        return
    
    user = users[user_id]
    if user['role'] in ['owner', 'admin']:
        await update.message.reply_text("شما به عنوان ادمین، اعتبار نامحدود دارید. ⭐")
    else:
        await update.message.reply_text(f"اعتبار فعلی شما: {user['credit']} امتیاز ⭐")

async def gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفاً کد هدیه را وارد کنید: /gift <code>")
        return
    
    code = context.args[0]
    user_id = update.effective_user.id
    
    if user_id not in users:
        await update.message.reply_text("شما در سیستم ثبت نشده‌اید. لطفاً /start را بزنید.")
        return
    
    # بررسی وجود کد هدیه
    if code not in gift_codes:
        await update.message.reply_text("کد هدیه نامعتبر است.")
        return
    
    gift_data = gift_codes[code]
    
    # بررسی انقضا
    if gift_data['expiry_date'] and datetime.now() > gift_data['expiry_date']:
        await update.message.reply_text("کد هدیه منقضی شده است.")
        return
    
    # بررسی تعداد استفاده
    if gift_data['used_count'] >= gift_data['max_usage']:
        await update.message.reply_text("این کد قبلاً استفاده شده است.")
        return
    
    # افزایش تعداد استفاده
    gift_data['used_count'] += 1
    
    # افزودن امتیاز به کاربر
    users[user_id]['credit'] += gift_data['credit_amount']
    
    # ثبت استفاده از کد
    if user_id not in gift_code_usage:
        gift_code_usage[user_id] = []
    gift_code_usage[user_id].append({
        'code': code,
        'used_date': datetime.now()
    })
    
    await update.message.reply_text(f"{gift_data['credit_amount']} امتیاز به حساب شما افزوده شد.")

async def create_gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("فقط ادمین‌ها می‌توانند کد هدیه ایجاد کنند.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("لطفاً مقدار امتیاز را وارد کنید: /creategift <credit_amount> [max_usage]")
        return
    
    try:
        credit_amount = int(context.args[0])
        max_usage = int(context.args[1]) if len(context.args) > 1 else 1
        
        # ایجاد کد هدیه
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry_date = datetime.now() + timedelta(days=30)
        
        gift_codes[code] = {
            'credit_amount': credit_amount,
            'created_by': user_id,
            'created_date': datetime.now(),
            'expiry_date': expiry_date,
            'used_count': 0,
            'max_usage': max_usage
        }
        
        await update.message.reply_text(
            f"کد هدیه با موفقیت ایجاد شد:\n\n"
            f"🎫 کد: `{code}`\n"
            f"⭐ امتیاز: {credit_amount}\n"
            f"🔢 تعداد استفاده: {max_usage}\n\n"
            "کاربران می‌توانند با دستور /gift از این کد استفاده کنند.",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await update.message.reply_text("مقدار امتیاز و تعداد استفاده باید عدد باشد.")

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users:
        await update.message.reply_text("شما در سیستم ثبت نشده‌اید. لطفاً /start را بزنید.")
        return
    
    user = users[user_id]
    
    # بررسی اعتبار کاربر
    if user['role'] not in ['owner', 'admin'] and user['credit'] < CHANNEL_ADD_COST:
        await update.message.reply_text(f"اعتبار کافی ندارید. افزودن کانال {CHANNEL_ADD_COST} امتیاز هزینه دارد.")
        return
    
    if not context.args:
        await update.message.reply_text("لطفاً آیدی کانال را وارد کنید: /addchannel <channel_id> [channel_username]")
        return
    
    try:
        channel_id = int(context.args[0])
        channel_username = context.args[1] if len(context.args) > 1 else ""
        
        channels[channel_id] = {
            'channel_username': channel_username,
            'added_by': user_id,
            'added_date': datetime.now(),
            'reaction_setting': DEFAULT_REACTION
        }
        
        # کسر امتیاز از کاربران عادی
        if user['role'] not in ['owner', 'admin']:
            user['credit'] -= CHANNEL_ADD_COST
        
        await update.message.reply_text(f"کانال با آیدی {channel_id} با موفقیت افزوده شد.")
    except ValueError:
        await update.message.reply_text("آدی کانال باید یک عدد باشد.")

async def set_reaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("فقط ادمین‌ها می‌توانند رای‌اکشن را تغییر دهند.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("لطفاً آیدی کانال و رای‌اکشن را وارد کنید: /setreaction <channel_id> <reaction>")
        return
    
    try:
        channel_id = int(context.args[0])
        reaction = context.args[1]
        
        if channel_id in channels:
            channels[channel_id]['reaction_setting'] = reaction
            await update.message.reply_text(f"رای‌اکشن کانال {channel_id} به {reaction} تغییر یافت.")
        else:
            await update.message.reply_text("کانال یافت نشد.")
    except ValueError:
        await update.message.reply_text("آدی کانال باید یک عدد باشد.")

# هندلر برای رای‌اکشن خودکار روی پست‌های کانال
async def auto_react_to_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    
    channel_id = update.channel_post.chat.id
    message_id = update.channel_post.message_id
    
    # دریافت رای‌اکشن تنظیم شده برای این کانال
    reaction = DEFAULT_REACTION
    if channel_id in channels:
        reaction = channels[channel_id].get('reaction_setting', DEFAULT_REACTION)
    
    # اعمال رای‌اکشن
    try:
        await context.bot.set_message_reaction(
            chat_id=channel_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji(reaction)]
        )
    except Exception as e:
        logger.error(f"Error setting reaction: {e}")

# تابع اصلی
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    # ایجاد برنامه ربات
    application = Application.builder().token(BOT_TOKEN).build()

    # افزودن هندلرهای دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel_command))
    application.add_handler(CommandHandler("addadmin", add_admin_command))
    application.add_handler(CommandHandler("credit", credit_command))
    application.add_handler(CommandHandler("gift", gift_command))
    application.add_handler(CommandHandler("creategift", create_gift_command))
    application.add_handler(CommandHandler("addchannel", add_channel_command))
    application.add_handler(CommandHandler("setreaction", set_reaction_command))
    
    # افزودن هندلر برای callback queries
    application.add_handler(CallbackQueryHandler(handle_glass_panel_callback))
    
    # افزودن هندلر برای پست‌های کانال
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_react_to_channel_post))

    # شروع ربات
    application.run_polling()

if __name__ == "__main__":
    main()
