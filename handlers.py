import re
import time
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from exchange import exchange_client

logger = logging.getLogger(__name__)

# Anti-spam cache: {user_id: [(timestamp, text), ...]}
user_msg_cache = defaultdict(list)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    text = update.message.text
    chat = update.message.chat
    chat_type = chat.type
    chat_id = chat.id

    # Register or update group info
    if chat_type in ['group', 'supergroup']:
        db.add_or_update_group(chat_id, chat.title)

    # 1. Banned words check
    banned_words = db.get_banned_words(chat_id)
    if any(bw in text for bw in banned_words):
        await update.message.delete()
        await update.message.reply_text(f"⚠️ {user.first_name}님, 금칙어가 포함된 메시지는 삭제되었습니다.")
        return

    # 2. Anti-spam check
    spam_limit = db.get_setting(chat_id, "spam_limit", 5)
    spam_time = db.get_setting(chat_id, "spam_time", 10)
    now = time.time()
    
    # Filter old messages
    user_msg_cache[user.id] = [m for m in user_msg_cache[user.id] if now - m[0] <= spam_time]
    user_msg_cache[user.id].append((now, text))
    
    # Count identical messages
    same_msg_count = sum(1 for m in user_msg_cache[user.id] if m[1] == text)
    if same_msg_count >= spam_limit:
        await update.message.delete()
        # Optionally warn or restrict
        if same_msg_count == spam_limit:
            await update.message.reply_text(f"🚫 {user.first_name}님, 동일 메시지 도배로 인해 메시지가 삭제됩니다.")
        return

    # 3. Username change notification
    old_user = db.get_user(user.id)
    if old_user:
        old_name = old_user.get('first_name')
        if old_name and old_name != user.first_name:
            if db.get_setting(chat_id, "nick_alert", False):
                await update.message.reply_text(f"🔔 사용자명 변경 알림\n{old_name} 님이 {user.first_name} 님으로 이름을 변경했습니다.")

    # Register or update user info
    db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)

    if chat_type in ['group', 'supergroup']:
        # Increment chat count
        db.increment_chat_count(user.id, chat_id)

        # Check attendance
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

async def process_attendance(update: Update, user, chat_id, manual=False):
    success = db.record_attendance(user.id, chat_id)
    name = user.first_name or user.username or "사용자"
    if success:
        count = db.get_attendance_count(user.id, chat_id)
        await update.message.reply_text(f"✅ {name}님 출석체크 완료! (누적 {count}회)")
    elif manual:
        await update.message.reply_text(f"⚠️ {name}님은 오늘 이미 출석하셨습니다.")

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

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /stats can be an alias to /rank or show both my stats and rank
    await cmd_rank(update, context)

async def cmd_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id
    db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await process_attendance(update, user, chat_id, manual=True)

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
