import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

# ================= TOKEN =================

load_dotenv("bot.env")
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan")


# ================= DATABASE =================

def init_db():

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS jadwal(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        hari TEXT,
        jam TEXT,
        matkul TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS todo(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task TEXT,
        deadline TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


# ================= MENU =================

def menu_utama():

    keyboard = [
        [KeyboardButton("📅 Jadwal Kuliah")],
        [KeyboardButton("📝 ToDo List")],
        [KeyboardButton("📊 Progress")]
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def menu_jadwal():

    keyboard = [
        [KeyboardButton("➕ Tambah Jadwal")],
        [KeyboardButton("📋 Lihat Jadwal")],
        [KeyboardButton("❌ Hapus Jadwal")],
        [KeyboardButton("⬅️ Kembali")]
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def menu_todo():

    keyboard = [
        [KeyboardButton("➕ Tambah Task")],
        [KeyboardButton("📋 Lihat Task")],
        [KeyboardButton("⬅️ Kembali")]
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot Reminder Kuliah\n\nPilih menu:",
        reply_markup=menu_utama()
    )


# ================= NAVIGASI =================

async def buka_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📅 Menu Jadwal",
        reply_markup=menu_jadwal()
    )


async def buka_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📝 Menu ToDo",
        reply_markup=menu_todo()
    )


async def kembali(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await start(update, context)


# ================= TAMBAH JADWAL =================

HARI, JAM, MATKUL = range(3)


async def tambah_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Masukkan hari kuliah.\n\nContoh:\nSenin"
    )

    return HARI


async def input_hari(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["hari"] = update.message.text

    await update.message.reply_text(
        "Masukkan jam kuliah.\n\nContoh:\n08:00\n\nFormat:\nHH:MM"
    )

    return JAM


async def input_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["jam"] = update.message.text

    await update.message.reply_text(
        "Masukkan nama mata kuliah.\n\nContoh:\nAlgoritma"
    )

    return MATKUL


async def input_matkul(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    hari = context.user_data["hari"]
    jam = context.user_data["jam"]
    matkul = update.message.text

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO jadwal(user_id,hari,jam,matkul) VALUES(?,?,?,?)",
        (user_id, hari, jam, matkul)
    )

    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Jadwal berhasil ditambahkan")

    return ConversationHandler.END


# ================= TODO =================

TASK_NAME, TASK_DATE, TASK_TIME = range(3)


async def tambah_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Masukkan nama task.\n\n"
        "Contoh:\n"
        "Tugas Matematika Bab 3"
    )

    return TASK_NAME


async def input_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["task"] = update.message.text

    await update.message.reply_text(
        "Masukkan tanggal deadline.\n\n"
        "Contoh:\n"
        "27-01-2026\n\n"
        "Format:\n"
        "DD-MM-YYYY"
    )

    return TASK_DATE


async def input_task_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["tanggal"] = update.message.text

    await update.message.reply_text(
        "Masukkan jam deadline.\n\n"
        "Contoh:\n"
        "18:30\n\n"
        "Format:\n"
        "HH:MM (24 jam)"
    )

    return TASK_TIME


async def input_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    task = context.user_data["task"]
    tanggal = context.user_data["tanggal"]
    jam = update.message.text

    deadline = f"{tanggal} {jam}"

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO todo(user_id,task,deadline,status) VALUES(?,?,?,?)",
        (user_id, task, deadline, "pending")
    )

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Task berhasil ditambahkan\n\n"
        f"📝 Task : {task}\n"
        f"⏰ Deadline : {deadline}"
    )

    return ConversationHandler.END


# ================= LIHAT TODO =================

async def lihat_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT id,task,deadline,status FROM todo WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    conn.close()

    if not rows:
        await update.message.reply_text("Belum ada task")
        return

    for r in rows:

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Selesai", callback_data=f"done_{r[0]}")]
        ])

        text = f"""
📝 {r[1]}

Deadline: {r[2]}
Status: {r[3]}
"""

        await update.message.reply_text(text, reply_markup=keyboard)


async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    id_task = query.data.split("_")[1]

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("UPDATE todo SET status='done' WHERE id=?", (id_task,))

    conn.commit()
    conn.close()

    await query.edit_message_text("✅ Task selesai")


# ================= PROGRESS =================

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM todo WHERE user_id=?", (user_id,))
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM todo WHERE user_id=? AND status='done'", (user_id,))
    done = c.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        f"📊 Progress Task\n\n{done}/{total} selesai"
    )


# ================= REMINDER =================

async def cek_deadline(context: ContextTypes.DEFAULT_TYPE):

    now = datetime.now()

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT user_id,task,deadline FROM todo WHERE status='pending'")
    rows = c.fetchall()

    for r in rows:

        deadline = datetime.strptime(r[2], "%d-%m-%Y %H:%M")

        if deadline - now <= timedelta(hours=1) and deadline > now:

            await context.bot.send_message(
                r[0],
                f"⚠️ Deadline 1 jam lagi!\n\n📝 {r[1]}\n⏰ {r[2]}"
            )

    conn.close()


# ================= MAIN =================

def main():

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    conv_task = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Tambah Task"), tambah_task)],
        states={
            TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_name)],
            TASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_date)],
            TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task_time)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("📅 Jadwal Kuliah"), buka_jadwal))
    app.add_handler(MessageHandler(filters.Regex("📝 ToDo List"), buka_todo))
    app.add_handler(MessageHandler(filters.Regex("📊 Progress"), progress))
    app.add_handler(MessageHandler(filters.Regex("📋 Lihat Task"), lihat_task))
    app.add_handler(MessageHandler(filters.Regex("⬅️ Kembali"), kembali))

    app.add_handler(conv_task)
    app.add_handler(CallbackQueryHandler(done_task, pattern="done_"))

    # Scheduler reminder
    app.job_queue.run_repeating(cek_deadline, interval=60, first=10)

    print("BOT RUNNING...")

    app.run_polling()


if __name__ == "__main__":
    main()
