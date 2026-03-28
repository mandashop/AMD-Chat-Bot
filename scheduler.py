import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database as db
from telegram.error import BadRequest
import datetime

logger = logging.getLogger(__name__)

async def reset_daily_attendance():
    """매일 자정 - 출석은 날짜별로 자동 관리되므로 별도 처리 불필요"""
    logger.info("매일 자정 스케줄러 실행")
    pass

async def monthly_ranking_announce(bot):
    """매월 말일 12:00 - 랭킹 공지"""
    groups = db.get_all_groups()
    for group in groups:
        chat_id = group['chat_id']
        top_chatters = db.get_top_chatters(chat_id, 10)
        top_attendance = db.get_top_attendance(chat_id, 10)

        msg = "🏆 **이달의 채팅 랭킹 Top 10** 🏆\n\n"
        if top_chatters:
            for i, user in enumerate(top_chatters, 1):
                name = user.get('first_name') or user.get('username') or f"User{user.get('user_id')}"
                msg += f"{i}위: {name} ({user.get('chat_count')}회)\n"
        else:
            msg += "기록 없음\n"

        msg += "\n📅 **이달의 출석 랭킹 Top 10** 📅\n\n"
        if top_attendance:
            for i, user in enumerate(top_attendance, 1):
                name = user.get('first_name') or user.get('username') or f"User{user.get('user_id')}"
                msg += f"{i}위: {name} ({user.get('attend_count')}회)\n"
        else:
            msg += "기록 없음\n"

        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            logger.info(f"월간 랭킹 공지 완료 (chat_id: {chat_id})")
        except Exception as e:
            logger.error(f"월간 랭킹 공지 실패 (chat_id: {chat_id}): {e}")

async def monthly_reset(bot):
    """매월 말일 23:59 - 통계 초기화"""
    groups = db.get_all_groups()
    for group in groups:
        chat_id = group['chat_id']
        try:
            # 출석 및 채팅 통계 초기화
            db.reset_all_user_stats(chat_id)
            db.reset_all_attendance(chat_id)
            logger.info(f"월간 통계 초기화 완료 (chat_id: {chat_id})")
        except Exception as e:
            logger.error(f"월간 통계 초기화 실패 (chat_id: {chat_id}): {e}")
    
    logger.info("월간 통계 초기화 완료")

async def kick_deleted_accounts(bot):
    """탈퇴한 계정 추방"""
    groups = db.get_all_groups()
    
    for group in groups:
        chat_id = group['chat_id']
        
        # DB에서 해당 그룹의 유저 목록 가져오기 (채팅 기록이 있는 유저들)
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM user_stats WHERE chat_id = ?", (chat_id,))
        users = c.fetchall()
        conn.close()

        kicked_count = 0
        for u in users:
            user_id = u['user_id']
            try:
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                if member.user.is_bot:
                    continue
            except BadRequest as e:
                if "User not found" in str(e):
                    try:
                        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                        kicked_count += 1
                    except Exception:
                        pass
            except Exception as e:
                pass
                
        if kicked_count > 0:
            logger.info(f"탈퇴한 계정 {kicked_count}명 추방 완료 (chat_id: {chat_id})")

async def send_scheduled_messages(bot):
    """예약 메시지 전송"""
    msgs = db.get_scheduled_messages()
    now_str = datetime.datetime.now().strftime("%H:%M")
    
    for m in msgs:
        if m['schedule_time'] == now_str:
            chat_id = m['chat_id']
            try:
                await bot.send_message(chat_id=chat_id, text=m['message'])
                if m['repeat_type'] == 'none':
                    db.delete_scheduled_message(chat_id, m['id'])
            except Exception as e:
                logger.error(f"예약 메시지 전송 실패 (chat_id: {chat_id}): {e}")

async def setup_scheduler(application):
    bot = application.bot
    scheduler = AsyncIOScheduler()

    # 매일 자정
    scheduler.add_job(reset_daily_attendance, 'cron', hour=0, minute=0)

    # 매월 말일 12:00 랭킹 공지
    scheduler.add_job(monthly_ranking_announce, 'cron', day='last', hour=12, minute=0, args=[bot])

    # 매월 말일 23:59 통계 초기화
    scheduler.add_job(monthly_reset, 'cron', day='last', hour=23, minute=59, args=[bot])

    # 예약 메시지 (매 분마다 체크)
    scheduler.add_job(send_scheduled_messages, 'cron', minute='*', args=[bot])

    # 탈퇴 계정 추방 스케줄링 (예: 매주 일요일 새벽 3시)
    scheduler.add_job(kick_deleted_accounts, 'cron', day_of_week='sun', hour=3, minute=0, args=[bot])

    scheduler.start()
    return scheduler
