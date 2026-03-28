import re
import time
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from exchange import exchange_client

logger = logging.getLogger(__name__)

# Anti-spam cache: {(chat_id, user_id): [(timestamp, text), ...]}
# 그룹별 + 사용자별로 캐시를 분리
user_msg_cache = defaultdict(list)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    text = update.message.text
    chat = update.message.chat
    chat_type = chat.type
    chat_id = chat.id
    message_id = update.message.message_id

    # Register or update group info
    if chat_type in ['group', 'supergroup']:
        db.add_or_update_group(chat_id, chat.title)

    # 1. Banned words check
    banned_words = db.get_banned_words(chat_id)
    if any(bw in text for bw in banned_words):
        await update.message.delete()
        await update.message.reply_text(f"⚠️ {user.first_name}님, 금칙어가 포함된 메시지는 삭제되었습니다.")
        return

    # 2. Anti-spam check (그룹별 + 사용자별)
    spam_limit = db.get_setting(chat_id, "spam_limit", 5)
    spam_time_minutes = db.get_setting(chat_id, "spam_time_minutes", 10)  # 분 단위로 변경
    spam_time_seconds = spam_time_minutes * 60  # 초로 변환
    
    now = time.time()
    cache_key = (chat_id, user.id)
    
    # Filter old messages (설정된 시간 이전의 메시지만 필터링)
    user_msg_cache[cache_key] = [m for m in user_msg_cache[cache_key] if now - m[0] <= spam_time_seconds]
    user_msg_cache[cache_key].append((now, text))
    
    # Count identical messages
    same_msg_count = sum(1 for m in user_msg_cache[cache_key] if m[1] == text)
    if same_msg_count >= spam_limit:
        # 먼저 경고 메시지를 답글로 전송 (메시지 삭제하기 전에!)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 {user.first_name}님, {spam_time_minutes}분 내 동일 메시지 제한횟수({spam_limit}회)를 초과하였습니다.",
                reply_to_message_id=message_id
            )
        except Exception as e:
            logger.error(f"Failed to send warning message: {e}")
        # 그 다음 메시지 삭제
        await update.message.delete()
        return

    # 3. Username change notification (@username 변경 감지)
    old_user = db.get_user(user.id)
    if old_user:
        old_username = old_user.get('username')
        new_username = user.username
        if old_username != new_username:
            if db.get_setting(chat_id, "username_alert", False):
                # 답글로 변경 전/후 안내
                old_name_str = f"@{old_username}" if old_username else "(없음)"
                new_name_str = f"@{new_username}" if new_username else "(없음)"
                await update.message.reply_text(
                    f"🔔 사용자명 변경 알림\n{old_name_str} → {new_name_str}",
                    reply_to_message_id=message_id
                )

    # Register or update user info
    db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)

    if chat_type in ['group', 'supergroup']:
        # Increment chat count
        db.increment_chat_count(user.id, chat_id)

        # Check attendance - 출석체크 키워드 확인
        attendance_keywords = ['ㅊㅊ', '출첵', '출석체크']
        if any(keyword in text for keyword in attendance_keywords):
            await process_attendance(update, user, chat_id)

    # Check for currency conversion
    match = re.search(r'^([A-Za-z]+)\s*([\d\,\.]+)\s*>\s*([A-Za-z]+)$', text.strip())
    if match:
        from_symbol = match.group(1).upper()
        amount_str = match.group(2).replace(',', '')
        to_symbol = match.group(3).upper()

        try:
            amount = float(amount_str)
            # Check if symbols are supported
            is_supported_from = exchange_client.is_fiat(from_symbol) or exchange_client.is_crypto(from_symbol)
            is_supported_to = exchange_client.is_fiat(to_symbol) or exchange_client.is_crypto(to_symbol)

            if is_supported_from and is_supported_to:
                result = exchange_client.convert(amount, from_symbol, to_symbol)
                if result is not None:
                    # Format numbers nicely
                    amount_fmt = f"{amount:,.8g}"
                    result_fmt = f"{result:,.8g}"
                    await update.message.reply_text(f"💱 {amount_fmt} {from_symbol} = {result_fmt} {to_symbol}")
                else:
                    await update.message.reply_text("❌ 환율 정보를 가져오는데 실패했습니다.")
        except ValueError:
            pass

async def process_attendance(update: Update, user, chat_id):
    """출석체크 처리 - 항상 응답 메시지를 볃냄"""
    success = db.record_attendance(user.id, chat_id)
    name = user.first_name or user.username or "사용자"
    if success:
        count = db.get_attendance_count(user.id, chat_id)
        await update.message.reply_text(f"✅ {name}님 출석체크 완료! (누적 {count}회)")
    else:
        # 이미 출석한 경우에도 알려줌
        count = db.get_attendance_count(user.id, chat_id)
        await update.message.reply_text(f"⚠️ {name}님은 오늘 이미 출석하셨습니다. (누적 {count}회)")

async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    top_chatters = db.get_top_chatters(chat_id, 10)
    if not top_chatters:
        await update.message.reply_text("아직 채팅 기록이 없습니다.")
        return

    msg = "🏆 **채팅 순위 Top 10** 🏆\n\n"
    for i, user in enumerate(top_chatters, 1):
        name = user.get('first_name') or user.get('username') or f"User{user.get('user_id')}"
        msg += f"{i}위: {name} ({user.get('chat_count')}회)\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    stats = db.get_user_stats(user_id, chat_id)
    count = stats.get('chat_count', 0) if stats else 0
    await update.message.reply_text(f"💬 내 채팅 횟수: {count}회")

async def cmd_userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자명으로 다른 사람의 메시지 수량 확인"""
    chat_id = update.message.chat_id
    
    # 명령어에서 사용자명 추출 (/userstats @username 또는 /userstats username)
    args = update.message.text.split()
    if len(args) < 2:
        await update.message.reply_text("사용법: /userstats @사용자명 또는 /userstats 사용자명")
        return
    
    target_username = args[1].lstrip('@')  # @ 제거
    
    # 데이터베이스에서 사용자 검색
    user_stats = db.get_user_stats_by_username(target_username, chat_id)
    
    if user_stats:
        name = user_stats.get('first_name') or user_stats.get('username') or target_username
        count = user_stats.get('chat_count', 0)
        await update.message.reply_text(f"💬 {name}님의 채팅 횟수: {count}회")
    else:
        await update.message.reply_text(f"❌ @{target_username} 사용자를 찾을 수 없거나 채팅 기록이 없습니다.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /stats can be an alias to /rank or show both my stats and rank
    await cmd_rank(update, context)

async def cmd_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id
    db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await process_attendance(update, user, chat_id)

async def cmd_attendrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    top_attendance = db.get_top_attendance(chat_id, 10)
    if not top_attendance:
        await update.message.reply_text("아직 출석 기록이 없습니다.")
        return

    msg = "📅 **출석 순위 Top 10** 📅\n\n"
    for i, user in enumerate(top_attendance, 1):
        name = user.get('first_name') or user.get('username') or f"User{user.get('user_id')}"
        msg += f"{i}위: {name} ({user.get('attend_count')}회)\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')
