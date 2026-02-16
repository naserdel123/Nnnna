import os
import logging
import re
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from youtubesearchpython import VideosSearch

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قائمة الكلمات الممنوعة (عدّلها حسب احتياجك)
PROHIBITED_WORDS = ['سب', 'شتم', 'كلمة سيئة', 'سخاف', 'زنا', 'قحبة']  # أضف المزيد

# توكن البوت من المتغيرات البيئية
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("لم يتم تعيين BOT_TOKEN في المتغيرات البيئية")

# إنشاء تطبيق البوت
application = Application.builder().token(BOT_TOKEN).build()

# ------------------- الوظائف -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة ترحيب عند /start"""
    welcome_text = (
        "👋 مرحباً! أنا بوت مفيد.\n"
        "يمكنك إضافتي إلى مجموعتك وسأقوم بما يلي:\n"
        "• البحث في يوتيوب (اكتب بحث + اسم الأغنية)\n"
        "• حماية المجموعة من الكلمات البذيئة (سيتم طرد المخالف)\n"
        "• إظهار ID المستخدم بالرد على رسالته وكتابة id\n"
        "• للبحث عن أغنية: بحث <اسم الأغنية>\n"
        "• للاستعلام عن ID: (قم بالرد على رسالة الشخص واكتب id)"
    )
    await update.message.reply_text(welcome_text)

async def youtube_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث في يوتيوب عندما تبدأ الرسالة بـ 'بحث'"""
    text = update.message.text.strip()
    if text.startswith('بحث'):
        query = text[2:].strip()
        if not query:
            await update.message.reply_text("❌ يرجى كتابة اسم الأغنية بعد 'بحث'")
            return

        try:
            videos_search = VideosSearch(query, limit=3)
            results = videos_search.result()['result']
            if not results:
                await update.message.reply_text("❌ لم أجد أي نتائج.")
                return

            response = "🔍 نتائج البحث:\n\n"
            for idx, video in enumerate(results, 1):
                title = video['title']
                duration = video.get('duration', 'غير معروف')
                link = video['link']
                response += f"{idx}. {title} ({duration})\n{link}\n\n"

            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"خطأ في البحث: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء البحث. حاول مرة أخرى لاحقاً.")
    else:
        # إذا لم تكن رسالة بحث، نمررها للمعالج العام
        await handle_prohibited_words(update, context)

async def handle_prohibited_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الرسائل في المجموعات وحذف وطرد المخالف"""
    if update.message and update.message.chat.type in ['group', 'supergroup']:
        text = update.message.text or ''
        if any(word in text for word in PROHIBITED_WORDS):
            try:
                await update.message.delete()
                await update.message.chat.ban_member(update.message.from_user.id)
                # إلغاء الحظر فوراً حتى يتمكن من العودة لاحقاً إذا أراد
                await update.message.chat.unban_member(update.message.from_user.id)
                logger.info(f"تم طرد المستخدم {update.message.from_user.id} بسبب كلمة ممنوعة.")
            except Exception as e:
                logger.error(f"خطأ في الحذف/الطرد: {e}")
                await update.message.reply_text("❌ لا يمكنني تنفيذ الإجراء. تأكد أنني مشرف في المجموعة.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرجاع ID المستخدم الذي تم الرد عليه عند كتابة 'id'"""
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        await update.message.reply_text(f"🆔 معرف المستخدم: `{user_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ يجب الرد على رسالة الشخص أولاً.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}")

# ------------------- إضافة المعالجات -------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^بحث'), youtube_search))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^id$'), get_id))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_prohibited_words))
application.add_error_handler(error_handler)

# ------------------- إعداد Flask لاستقبال Webhook -------------------
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """استقبال التحديثات من تيليجرام"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return 'OK', 200

@app.route('/')
def index():
    return 'البوت يعمل!'

if __name__ == '__main__':
    # تعيين webhook عند بدء التشغيل
    PORT = int(os.environ.get('PORT', 5000))
    # احصل على رابط التطبيق من Render (سيتم استبداله تلقائياً إذا استخدمت المتغير RENDER_EXTERNAL_URL)
    # لكن من الأفضل ضبطه يدوياً بعد النشر، أو استخدام متغير بيئي.
    RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
    else:
        # للاختبار المحلي، استخدم ngrok أو شيء مشابه
        webhook_url = "https://your-app.onrender.com/webhook"  # استبدل بعد النشر

    # تعيين webhook
    application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    # تشغيل خادم Flask
    app.run(host='0.0.0.0', port=PORT)