import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = "8643610358:AAEX7KII2wZC3lPoDKkJ28yMmQhyXYHqUcA"
ADMIN_ID = 3643610358                  # আপনার টেলিগ্রাম ID
SUPPORT_USERNAME = "SHANTOBD71"     # আপনার টেলিগ্রাম ইউজারনেম (@ ছাড়া)
# -------------------------------------------------

# Conversation States
SELECT_METHOD, ENTER_NUMBER, ENTER_AMOUNT = range(3)

users = {}

def get_user_data(user_id, name="User"):
    if user_id not in users:
        users[user_id] = {
            'balance': 0.0,
            'total_earned': 0.0,
            'submissions': 0,
            'name': name
        }
    return users[user_id]

def main_menu():
    keyboard = [
        ["📤 File Submit"],
        ["💰 My Balance", "👤 Profile"],
        ["💸 Withdraw", "🆘 Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id, user.full_name)
    
    welcome_text = (
        f"হ্যালো {user.first_name}!\n"
        "আমাদের কাজ এবং ইনকাম বটে আপনাকে স্বাগতম।\n"
        "নিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশন বেছে নিন।"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu())

# --- WITHDRAW CONVERSATION FLOW ---
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = get_user_data(user.id, user.full_name)

    if u_data['balance'] < 20:
        await update.message.reply_text(
            f"❌ উইথড্র করার জন্য সর্বনিম্ন **২০ টাকা** প্রয়োজন।\n"
            f"আপনার বর্তমান ব্যালেন্স: {u_data['balance']} BDT",
            reply_markup=main_menu()
        )
        return ConversationHandler.END

    keyboard = [["Bkash 📱", "Nagad 📱"], ["❌ Cancel"]]
    await update.message.reply_text(
        "💳 **উইথড্র করার জন্য পেমেন্ট মেথড সিলেক্ট করুন:**",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return SELECT_METHOD

async def method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "❌ Cancel":
        await update.message.reply_text("❌ উইথড্র বাতিল করা হয়েছে।", reply_markup=main_menu())
        return ConversationHandler.END

    if text in ["Bkash 📱", "Nagad 📱"]:
        context.user_data['withdraw_method'] = text.replace(" 📱", "")
        await update.message.reply_text(
            f"📱 আপনার **{context.user_data['withdraw_method']}** নম্বরটি লিখুন:"
        )
        return ENTER_NUMBER
    else:
        await update.message.reply_text("⚠️ অনুগ্রহ করে নিচের বাটন থেকে মেথড সিলেক্ট করুন।")
        return SELECT_METHOD

async def number_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text
    context.user_data['withdraw_number'] = number

    await update.message.reply_text(
        "💵 আপনি কত টাকা তুলতে চান? (সর্বনিম্ন ২০ টাকা)"
    )
    return ENTER_AMOUNT

async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = get_user_data(user.id, user.full_name)
    
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ অনুগ্রহ করে সঠিক টাকার সংখ্যা লিখুন। (যেমন: 20 বা 50)")
        return ENTER_AMOUNT

    if amount < 20:
        await update.message.reply_text("❌ সর্বনিম্ন উইথড্র ২০ টাকা। আবার চেষ্টা করুন:")
        return ENTER_AMOUNT

    if amount > u_data['balance']:
        await update.message.reply_text(
            f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই!\n"
            f"আপনার বর্তমান ব্যালেন্স: {u_data['balance']} BDT"
        )
        return ENTER_AMOUNT

    method = context.user_data['withdraw_method']
    number = context.user_data['withdraw_number']

    # ইউজারের ব্যালেন্স কেটে নেওয়া
    u_data['balance'] -= amount

    await update.message.reply_text(
        f"✅ **উইথড্র রিকোয়েস্ট জমা হয়েছে!**\n\n"
        f"🔹 Method: {method}\n"
        f"📱 Number: `{number}`\n"
        f"💵 Amount: {amount} BDT\n\n"
        f"অ্যাডমিন শীঘ্রই পেমেন্টটি প্রসেস করবে।",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

    # অ্যাডমিনকে নোটিফিকেশন পাঠানো
    admin_msg = (
        f"💸 **NEW WITHDRAW REQUEST!**\n\n"
        f"👤 User: {user.full_name} (`{user.id}`)\n"
        f"💳 Method: {method}\n"
        f"📱 Number: `{number}`\n"
        f"💵 Amount: {amount} BDT"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Payment Done", callback_data=f"pdone_{user.id}_{amount}")]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_msg,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ অপশন বাতিল করা হয়েছে।", reply_markup=main_menu())
    return ConversationHandler.END

# --- OTHER HANDLERS ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    u_data = get_user_data(user.id, user.full_name)

    if text == "📤 File Submit":
        await update.message.reply_text(
            "🟢 FILE SUBMIT OPEN\n\n"
            "আপনার Excel File এখন পাঠান (ফরম্যাট: .xlsx, .xls, .csv)"
        )

    elif text == "💰 My Balance":
        await update.message.reply_text(
            f"💰 Your Balance: {u_data['balance']} BDT\n"
            f"📈 Total Earned: {u_data['total_earned']} BDT"
        )

    elif text == "👤 Profile":
        profile_msg = (
            f"👤 User Profile\n\n"
            f"🆔 User ID: {user.id}\n"
            f"👤 Name: {user.full_name}\n"
            f"📥 Total Submissions: {u_data['submissions']}\n"
            f"💰 Current Balance: {u_data['balance']} BDT\n"
            f"💵 Total Earned: {u_data['total_earned']} BDT"
        )
        await update.message.reply_text(profile_msg)

    elif text == "🆘 Support":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        await update.message.reply_text(
            "যেকোনো সমস্যা বা সহায়তার জন্য যোগাযোগ করুন:",
            reply_markup=keyboard
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    doc = update.message.document
    u_data = get_user_data(user.id, user.full_name)

    if doc.file_name.endswith(('.xlsx', '.xls', '.csv')):
        u_data['submissions'] += 1
        
        await update.message.reply_text(
            f"✅ File Submitted Successfully\n\n"
            f"File: {doc.file_name}\n"
            f"Status: 🟡 Pending Review"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve (+10 Tk)", callback_data=f"approve_{user.id}_10")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}")]
        ])
        
        caption = (
            f"📥 New File Submission!\n\n"
            f"From: {user.full_name} ({user.id})\n"
            f"File: {doc.file_name}"
        )
        
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=doc.file_id,
            caption=caption,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text("❌ শুধু Excel/CSV ফাইল সাপোর্ট করবে।")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    target_user_id = int(data[1])

    u_data = get_user_data(target_user_id)

    if action == "approve":
        amount = float(data[2]) if len(data) > 2 else 10.0
        u_data['balance'] += amount
        u_data['total_earned'] += amount

        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ Approved (+{amount} BDT)")
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 File Approved!\n\nআপনার অ্যাকাউন্টে {amount} BDT যোগ করা হয়েছে।"
        )

    elif action == "reject":
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ Rejected")
        await context.bot.send_message(
            chat_id=target_user_id,
            text="❌ আপনার পাঠানো ফাইলটি বাতিল করা হয়েছে।"
        )

    elif action == "pdone":
        amount = float(data[2])
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ **Payment Status: Paid**", parse_mode="Markdown")
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"✅ আপনার {amount} BDT-এর উইথড্র পেমেন্ট সফলভাবে পাঠিয়ে দেওয়া হয়েছে!"
        )

async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        u_data = get_user_data(target_id)
        u_data['balance'] += amount
        u_data['total_earned'] += amount

        await update.message.reply_text(f"✅ User {target_id}-এর ব্যালেন্সে {amount} BDT যোগ করা হয়েছে।")
        await context.bot.send_message(
            chat_id=target_id,
            text=f"💳 আপনার অ্যাকাউন্টে **{amount} BDT** যোগ করা হয়েছে!"
        )
    except Exception:
        await update.message.reply_text("ব্যবহারবিধি: /addbalance <user_id> <amount>")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Withdraw Conversation Handler
    withdraw_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^💸 Withdraw$'), withdraw_start)],
        states={
            SELECT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, method_selected)],
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, number_entered)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
        },
        fallbacks=[CommandHandler('cancel', cancel_withdraw)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addbalance", add_balance_command))
    app.add_handler(withdraw_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()