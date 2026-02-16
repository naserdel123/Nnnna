import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from youtubesearchpython import VideosSearch

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قائمة الكلمات الممنوعة (يمكنك تعديلها حسب الحاجة)
PROHIBITED_WORDS = ['سب', 'شتم', 'كلمة سيئة', 'سخاف', 'زنا', 'قحبة']  # أضف الكلمات التي تريد منعها

# رمز البوت من BotFather
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # استبدل هذا برمز البوت الخاص بك

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة ترحيب عند إرسال /start"""
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

async def handle_youtube_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث في يوتيوب عندما يبدأ النص بـ 'بحث'"""
    text = update.message.text.strip()
    if text.startswith('بحث'):
        query = text[2:].strip()  # إزالة كلمة "بحث"
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
        # إذا لم تكن الرسالة بحث، نمررها للمعالج العام
        await handle_prohibited_words(update, context)

async def handle_prohibited_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الرسائل في المجموعات بحثاً عن كلمات ممنوعة وحذفها وطرد المرسل"""
    if update.message and update.message.chat.type in ['group', 'supergroup']:
        text = update.message.text or ''
        # التحقق من وجود أي كلمة ممنوعة
        if any(word in text for word in PROHIBITED_WORDS):
            try:
                # حذف الرسالة
                await update.message.delete()
                # طرد العضو (يتطلب صلاحية حظر)
                await update.message.chat.ban_member(update.message.from_user.id)
                # إلغاء الحظر فوراً ليتمكن من العودة إذا أراد (اختياري)
                await update.message.chat.unban_member(update.message.from_user.id)
                logger.info(f"تم طرد المستخدم {update.message.from_user.id} بسبب كلمة ممنوعة.")
            except Exception as e:
                logger.error(f"خطأ في حذف/طرد: {e}")
                await update.message.reply_text("❌ لا يمكنني تنفيذ الإجراء. تأكد أنني مشرف في المجموعة.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرجاع ID المستخدم الذي تم الرد عليه عند كتابة 'id'"""
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        await update.message.reply_text(f"🆔 معرف المستخدم: `{user_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ يجب الرد على رسالة الشخص أولاً.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    # معالج البحث في يوتيوب (لأي رسالة تبدأ بـ "بحث")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^بحث'), handle_youtube_search))
    # معالج ID (لأي رسالة نصها "id" فقط)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^id$'), get_id))
    # معالج الكلمات الممنوعة (لباقي الرسائل النصية في المجموعات)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_prohibited_words))

    # معالج الأخطاء
    application.add_error_handler(error_handler)

    # بدء البوت باستخدام polling
    logger.info("البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()