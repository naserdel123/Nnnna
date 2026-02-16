import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

# كلمات ممنوعة (عدّلها)
bad_words = ["سب", "كلمة_سيئة"]

logging.basicConfig(level=logging.INFO)

# رسالة البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك 👋\n"
        "أضفني إلى قروبك واجعلني مشرف.\n"
        "اكتب: بحث + اسم الأغنية للبحث في يوتيوب.\n"
        "واكتب id بالرد على شخص لمعرفة الآيدي."
    )

# البحث في يوتيوب
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("اكتب: بحث + اسم الأغنية")
        return

    query = " ".join(context.args)

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'default_search': 'ytsearch1'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            video = info['entries'][0]
            url = f"https://www.youtube.com/watch?v={video['id']}"
            await update.message.reply_text(f"وجدت:\n{video['title']}\n{url}")
        else:
            await update.message.reply_text("لم يتم العثور على نتائج")

# حذف الكلمات المخالفة
async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    for word in bad_words:
        if word in text:
            try:
                await update.message.delete()
            except:
                pass
            break

# جلب الآيدي
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        await update.message.reply_text(f"ID المستخدم: {user_id}")
    else:
        await update.message.reply_text("رد على رسالة شخص ثم اكتب id")

# تشغيل البوت
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("بحث", search))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate))

    app.run_polling()

if __name__ == "__main__":
    main()