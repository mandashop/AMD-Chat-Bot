import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from handlers import handle_message, cmd_rank, cmd_mystats, cmd_stats, cmd_attend, cmd_attendrank
from admin import get_admin_conversation_handler, cmd_backup
from scheduler import setup_scheduler

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("안녕하세요! 봇이 시작되었습니다.")

def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN이 설정되지 않았습니다.")
        return

    # 봇 애플리케이션 생성
    application = Application.builder().token(config.BOT_TOKEN).post_init(setup_scheduler).build()

    # 핸들러 추가
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rank", cmd_rank))
    application.add_handler(CommandHandler("mystats", cmd_mystats))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("attend", cmd_attend))
    application.add_handler(CommandHandler("attendrank", cmd_attendrank))
    application.add_handler(CommandHandler("backup", cmd_backup))
    
    # 관리자 메뉴 ConversationHandler
    application.add_handler(get_admin_conversation_handler())
    
    # 메시지 리스너 (명령어 제외 모든 텍스트)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 웹 서버 스레드 시작
    import threading
    from server import app
    def run_flask():
        app.run(host="0.0.0.0", port=config.PORT, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 봇 시작 (polling)
    print("Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Polling ended!")

if __name__ == "__main__":
    main()
