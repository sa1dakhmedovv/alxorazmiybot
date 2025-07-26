from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from db import add_admin, remove_admin, get_admins, is_admin
from telegram.ext import ConversationHandler

ASK_BROADCAST = range(1)


MAIN_ADMIN_ID = 5802051984  # Sizning asosiy admin user_id

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("📢 Yuboriladigan xabarni jo‘nating (matn, rasm yoki rasm+caption).")
    return ASK_BROADCAST

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()

    sent = 0
    failed = 0

    if update.message.photo:  # Rasm yoki rasm+caption
        photo = update.message.photo[-1].file_id
        caption = update.message.caption if update.message.caption else ""
        for uid in users:
            try:
                await context.bot.send_photo(uid, photo=photo, caption=caption)
                sent += 1
            except:
                failed += 1

    elif update.message.text:  # Faqat matn
        text = update.message.text
        for uid in users:
            try:
                await context.bot.send_message(uid, text)
                sent += 1
            except:
                failed += 1

    await update.message.reply_text(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")
    return ConversationHandler.END



async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("✅ Foydalanish: /addadmin <user_id>")
        return

    user_id = int(context.args[0])
    add_admin(user_id)
    await update.message.reply_text(f"✅ {user_id} admin sifatida qo‘shildi.")

async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("✅ Foydalanish: /removeadmin <user_id>")
        return

    user_id = int(context.args[0])
    remove_admin(user_id)
    await update.message.reply_text(f"❌ {user_id} adminlar ro‘yxatidan o‘chirildi.")

async def list_admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    admins = get_admins()
    if not admins:
        await update.message.reply_text("Hozircha adminlar yo‘q.")
    else:
        text = "👮 Adminlar ro‘yxati:\n" + "\n".join([str(a) for a in admins])
        await update.message.reply_text(text)

import re
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

ASK_NAME, ASK_PHONE, ASK_CLASS, ASK_BRANCH = range(4)

DB_NAME = "bot_data.db"

def add_user_to_db(user_id, name, phone, clas, branch, username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (user_id, name, phone, class, branch, username, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, phone, clas, branch, username, "bog‘lanmadi"))
    conn.commit()
    conn.close()



async def ask_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["branch"] = query.data.replace("branch_", "")
    user = update.effective_user

    # --- Yangi foydalanuvchi ma'lumotini DB ga yozish ---
    request_id = add_user_to_db(
        user_id=user.id,
        name=context.user_data["name"],
        phone=context.user_data["phone"],
        clas=context.user_data["class"],
        branch=context.user_data["branch"],
        username=user.username
    )

    # --- Adminlarga xabar yuborish ---
    await notify_admins(
        {
            "user_id": user.id,
            "name": context.user_data["name"],
            "phone": context.user_data["phone"],
            "class": context.user_data["class"],
            "branch": context.user_data["branch"],
            "username": user.username
        },
        request_id,   # <-- bu YANGI qo‘shilgan argument
        context
    )

    # --- Eski xabarni o‘chirib, yangi xabar yuborish ---
    await query.message.delete()
    await query.message.reply_text(
        "✅ Muvaffaqiyatli ro‘yxatdan o‘tdingiz!\nAdminlar tez orada siz bilan bog‘lanadi."
    )

    # --- Asosiy menyuni ko‘rsatish ---
    await show_main_menu(update, context)
    return ConversationHandler.END



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Ro'yxatdan o'tish", callback_data="register")],
        [InlineKeyboardButton("ℹ️ Maktab haqida", callback_data="about")],
        [InlineKeyboardButton("📞 Aloqa", callback_data="contact")]
    ]
    await update.message.reply_text(
        "Asosiy menyu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Ro‘yxatdan o‘tish", callback_data="register")],
        [InlineKeyboardButton("ℹ️ Maktab haqida", callback_data="about")],
        [InlineKeyboardButton("📞 Aloqa", callback_data="contact")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.message.reply_text("Asosiy menyu:", reply_markup=markup)
    elif hasattr(update, "message") and update.message:
        await update.message.reply_text("Asosiy menyu:", reply_markup=markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "register":
        await query.message.delete()
        await query.message.reply_text("Ismingizni kiriting:")
        return ASK_NAME

    if data == "about":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        try:
            await query.message.delete()
        except:
            pass

        await query.message.reply_text(
            "ℹ️ Maktab haqida ma'lumot (keyinchalik admin yangilaydi).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "contact":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        try:
            await query.message.delete()
        except:
            pass

        await query.message.reply_text(
            "📞 Aloqa: +998xx xxx xx xx",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "back_to_menu":
        await show_main_menu(update, context)


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Telefon raqamingizni +998 formatda kiriting:\nNamuna: +998901234567")
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not re.fullmatch(r"\+998\d{9}", phone):
        await update.message.reply_text("❌ Noto‘g‘ri format. Namuna: +998901234567")
        return ASK_PHONE

    context.user_data["phone"] = phone
    keyboard = [[InlineKeyboardButton(f"{i}-sinf", callback_data=f"class_{i}")] for i in range(1, 12)]
    await update.message.reply_text("Sinfingizni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_CLASS

async def ask_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["class"] = query.data.replace("class_", "")
    keyboard = [
        [InlineKeyboardButton("Filial 1", callback_data="branch_1")],
        [InlineKeyboardButton("Filial 2", callback_data="branch_2")]
    ]
    await query.message.delete()
    await query.message.reply_text("Filialni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_BRANCH


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, phone, class, branch, username, status FROM users")
    users = c.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text("❌ Hozircha foydalanuvchilar yo‘q.")
        return

    text = "📋 Ro‘yxatdan o‘tganlar:\n\n"
    for i, (user_id, name, phone, clas, branch, username, status) in enumerate(users, 1):
        text += (
            f"{i}. 👤 {name} (ID: {user_id})\n"
            f"   📞 {phone}\n"
            f"   🏫 {clas}-sinf\n"
            f"   📍 Filial: {branch}\n"
            f"   🔗 Username: @{username if username else 'yo‘q'}\n"
            f"   ✅ Status: {status}\n\n"
        )

    # Juda uzun bo‘lsa bo‘lib yuborish
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk)



from openpyxl import Workbook
from io import BytesIO

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, phone, class, branch, username, status FROM users")
    data = c.fetchall()
    conn.close()

    if not data:
        await update.message.reply_text("❌ Ma'lumot yo‘q.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Users"
    headers = ["Ism", "Telefon", "Sinf", "Filial", "Username", "Status"]
    ws.append(headers)

    for row in data:
        ws.append(row)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    await update.message.reply_document(document=output, filename="users_export.xlsx")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Foydalanish: /broadcast matn yoki rasm yuboring.")
        return

    msg = " ".join(context.args)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()

    for uid in users:
        try:
            await context.bot.send_message(uid, msg)
        except:
            continue

    await update.message.reply_text("✅ Broadcast yuborildi.")







import sqlite3
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

DB_NAME = "bot_data.db"

# --- Jadval yaratish ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        phone TEXT,
        class TEXT,
        branch TEXT,
        username TEXT,
        status TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS admin_notifications (
        request_id INTEGER,
        admin_id INTEGER,
        message_id INTEGER,
        PRIMARY KEY(request_id, admin_id)
    )
    """)
    conn.commit()
    conn.close()




def add_user_to_db(user_id, name, phone, clas, branch, username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, name, phone, class, branch, username, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, phone, clas, branch, username, "bog‘lanmadi"))
    request_id = c.lastrowid  # <-- Har bir yozuv uchun unik ID
    conn.commit()
    conn.close()
    return request_id



async def notify_admins(user_data, request_id, context):
    admins = get_admins()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Bog‘landim", callback_data=f"connected_{request_id}")]
    ])

    text = (
        f"🆕 Yangi ro‘yxatdan o‘tuvchi:\n"
        f"👤 Ism: {user_data['name']}\n"
        f"📞 Telefon: {user_data['phone']}\n"
        f"🏫 Sinf: {user_data['class']}\n"
        f"📍 Filial: {user_data['branch']}\n"
        f"🔗 Username: @{user_data['username'] if user_data['username'] else 'yo‘q'}"
    )

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    for admin_id in admins:
        try:
            sent_msg = await context.bot.send_message(admin_id, text, reply_markup=keyboard)
            c.execute("""
                INSERT OR REPLACE INTO admin_notifications (request_id, admin_id, message_id)
                VALUES (?, ?, ?)
            """, (request_id, admin_id, sent_msg.message_id))
        except:
            continue

    conn.commit()
    conn.close()



async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer()
        return

    if query.data.startswith("connected_"):
        request_id = int(query.data.split("_")[1])
        admin_id = query.from_user.id

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET status='bog‘landi' WHERE request_id=?", (request_id,))
        conn.commit()

        # Shu request_id bo‘yicha barcha xabarlarni olish
        c.execute("SELECT admin_id, message_id FROM admin_notifications WHERE request_id=?", (request_id,))
        rows = c.fetchall()
        conn.close()

        old_text = query.message.text
        try:
            await query.message.edit_text(old_text + "\n\n✅ Bog‘landi")
        except:
            pass

        for a_id, msg_id in rows:
            if a_id != admin_id:
                try:
                    await context.bot.edit_message_reply_markup(
                        chat_id=a_id,
                        message_id=msg_id,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❌ Allaqachon bog‘langan", callback_data="none")]
                        ])
                    )
                except:
                    continue

        await query.answer("Status yangilandi ✅")





from telegram.ext import ApplicationBuilder
from db import *

def main():
    init_db()
    app = ApplicationBuilder().token("8314115787:AAF4agTO0ePznKmSC__qIMPGhMBshoj4fQo").build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="register")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_CLASS: [CallbackQueryHandler(ask_class, pattern=r"class_")],
            ASK_BRANCH: [CallbackQueryHandler(ask_branch, pattern=r"branch_")]
        },
        fallbacks=[]
    )

    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            ASK_BROADCAST: [MessageHandler(filters.TEXT | filters.PHOTO, broadcast_send)],
        },
        fallbacks=[],
    )
    app.add_handler(broadcast_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^connected_"))  # birinchi
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))  # umumiy handler keyin

    app.add_handler(CommandHandler("addadmin", add_admin_cmd))
    app.add_handler(CommandHandler("removeadmin", remove_admin_cmd))
    app.add_handler(CommandHandler("listadmins", list_admins_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("export", export_cmd))


    app.run_polling()

if __name__ == "__main__":
    main()