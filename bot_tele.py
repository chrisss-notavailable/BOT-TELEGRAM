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

from apscheduler.schedulers.background import BackgroundScheduler


# ================= TOKEN =================

load_dotenv("bot.env")

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan di bot.env")


# ================= HARI MAP =================

hari_map = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu"
}


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
    await update.message.reply_text("📅 Menu Jadwal", reply_markup=menu_jadwal())


async def buka_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Menu ToDo", reply_markup=menu_todo())


async def kembali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ================= TAMBAH JADWAL =================

HARI, JAM, MATKUL = range(3)

async def tambah_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("Masukkan hari (Senin, Selasa, dll)")
    return HARI


async def input_hari(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["hari"] = update.message.text

    await update.message.reply_text("Masukkan jam (HH:MM)")
    return JAM


async def input_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["jam"] = update.message.text

    await update.message.reply_text("Masukkan mata kuliah")
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

    await update.message.reply_text("✅ Jadwal ditambahkan")

    return ConversationHandler.END


# ================= LIHAT JADWAL =================

async def lihat_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT hari,jam,matkul FROM jadwal WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    conn.close()

    if not rows:
        await update.message.reply_text("Belum ada jadwal")
        return

    text = "📅 Jadwal Kamu\n\n"

    for r in rows:
        text += f"{r[0]} - {r[1]} - {r[2]}\n"

    await update.message.reply_text(text)


# ================= HAPUS JADWAL =================

async def hapus_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT id,hari,jam,matkul FROM jadwal WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    conn.close()

    if not rows:
        await update.message.reply_text("❌ Tidak ada jadwal untuk dihapus.")
        return

    keyboard = []

    for r in rows:
        keyboard.append(
            [InlineKeyboardButton(f"{r[1]} {r[2]} {r[3]}", callback_data=f"hapus_{r[0]}")]
        )

    await update.message.reply_text(
        "Pilih jadwal yang ingin dihapus",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delete_jadwal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    id_jadwal = query.data.split("_")[1]

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("DELETE FROM jadwal WHERE id=?", (id_jadwal,))

    conn.commit()
    conn.close()

    await query.edit_message_text("✅ Jadwal dihapus")


# ================= TODO =================

TASK, DEADLINE = range(2)

async def tambah_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("Masukkan task")
    return TASK


async def input_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["task"] = update.message.text

    await update.message.reply_text("Masukkan deadline (YYYY-MM-DD HH:MM)")
    return DEADLINE


async def input_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    task = context.user_data["task"]
    deadline = update.message.text

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO todo(user_id,task,deadline,status) VALUES(?,?,?,?)",
        (user_id, task, deadline, "pending")
    )

    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Task ditambahkan")

    return ConversationHandler.END


# ================= LIHAT TODO =================

async def lihat_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT id,task,deadline,status FROM todo WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    conn.close()

    for r in rows:

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Selesai", callback_data=f"done_{r[0]}")]
        ])

        text = f"📝 {r[1]}\n\nDeadline: {r[2]}\nStatus: {r[3]}"

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

    await update.message.reply_text(f"📊 Progress Task\n\n{done}/{total} selesai")


# ================= REMINDER =================

async def reminder_jam7(app):

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    hari = hari_map[datetime.now().strftime("%A")]

    c.execute("SELECT user_id,jam,matkul FROM jadwal WHERE hari=?", (hari,))
    rows = c.fetchall()

    conn.close()

    for r in rows:

        await app.bot.send_message(
            r[0],
            f"📚 Jadwal Hari Ini\n\n{r[1]} - {r[2]}"
        )


async def reminder_1jam(app):

    now = datetime.now()

    target = (now + timedelta(hours=1)).strftime("%H:%M")

    hari = hari_map[now.strftime("%A")]

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT user_id,matkul,jam FROM jadwal WHERE hari=? AND jam=?", (hari, target))
    rows = c.fetchall()

    conn.close()

    for r in rows:

        await app.bot.send_message(
            r[0],
            f"⏰ 1 Jam Lagi Kelas\n\n📚 {r[1]}\n🕒 {r[2]}"
        )


# ================= MAIN =================

def main():

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    scheduler = BackgroundScheduler(timezone="Asia/Jakarta")

    scheduler.add_job(lambda: app.create_task(reminder_jam7(app)), "cron", hour=7)
    scheduler.add_job(lambda: app.create_task(reminder_1jam(app)), "interval", minutes=1)

    scheduler.start()

    conv_jadwal = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Tambah Jadwal"), tambah_jadwal)],
        states={
            HARI: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_hari)],
            JAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_jam)],
            MATKUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_matkul)],
        },
        fallbacks=[]
    )

    conv_task = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Tambah Task"), tambah_task)],
        states={
            TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_task)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_deadline)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.Regex("📅 Jadwal Kuliah"), buka_jadwal))
    app.add_handler(MessageHandler(filters.Regex("📝 ToDo List"), buka_todo))
    app.add_handler(MessageHandler(filters.Regex("📊 Progress"), progress))

    app.add_handler(MessageHandler(filters.Regex("📋 Lihat Jadwal"), lihat_jadwal))
    app.add_handler(MessageHandler(filters.Regex("❌ Hapus Jadwal"), hapus_jadwal))
    app.add_handler(MessageHandler(filters.Regex("📋 Lihat Task"), lihat_task))

    app.add_handler(MessageHandler(filters.Regex("⬅️ Kembali"), kembali))

    app.add_handler(conv_jadwal)
    app.add_handler(conv_task)

    app.add_handler(CallbackQueryHandler(delete_jadwal, pattern="hapus_"))
    app.add_handler(CallbackQueryHandler(done_task, pattern="done_"))

    print("BOT RUNNING...")

    app.run_polling()


if __name__ == "__main__":
    main()
