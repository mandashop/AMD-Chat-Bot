import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import config
import database as db

# States for ConversationHandler
(
    AWAITING_BANNED_WORD,
    AWAITING_BANNED_WORD_REMOVE,
    AWAITING_SPAM_LIMIT,
    AWAITING_SPAM_TIME,
    AWAITING_SCHEDULE_MSG,
    AWAITING_SCHEDULE_TIME,
    AWAITING_SCHEDULE_REPEAT,
    AWAITING_SCHEDULE_REMOVE
) = range(8)

async def check_admin_rights(bot, chat_id, user_id):
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status == 'creator':
            return True
        elif user_member.status == 'administrator':
            return getattr(user_member, 'can_change_info', False)
        return False
    except Exception:
        return False

async def check_bot_admin(bot, chat_id):
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        return bot_member.status in ['administrator', 'creator']
    except Exception:
        return False

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("관리자 명령어는 그룹 채팅에서만 사용 가능합니다.")
        return

    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if not await check_bot_admin(context.bot, chat_id):
        await update.message.reply_text("봇이 이 그룹의 관리자가 아닙니다. 관리자로 지정해주세요.")
        return ConversationHandler.END

    if not await check_admin_rights(context.bot, chat_id, user_id):
        await update.message.reply_text("이 명령어를 사용하려면 그룹 정보 변경 권한(can_change_info)이 있는 관리자여야 합니다.")
        return ConversationHandler.END

    await send_main_menu(update.message)
    return ConversationHandler.END

async def send_main_menu(message_or_query, edit=False):
    keyboard = [
        [InlineKeyboardButton("도배 방지 설정", callback_data="admin_spam")],
        [InlineKeyboardButton("닉네임 변경 알림 설정", callback_data="admin_nick")],
        [InlineKeyboardButton("금칙어 관리", callback_data="admin_banned")],
        [InlineKeyboardButton("예약 메시지 관리", callback_data="admin_schedule")],
        [InlineKeyboardButton("통계 데이터 관리", callback_data="admin_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔧 **관리자 메뉴**\n원하는 설정을 선택하세요."
    
    if edit:
        await message_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    
    if not await check_admin_rights(context.bot, chat_id, user_id):
        await query.answer("권한이 없습니다.")
        return

    await query.answer()
    data = query.data

    if data == "admin_main":
        await send_main_menu(query, edit=True)
        return ConversationHandler.END
        
    elif data == "admin_spam":
        limit = db.get_setting(chat_id, "spam_limit", 5)
        time_sec = db.get_setting(chat_id, "spam_time", 10)
        keyboard = [
            [InlineKeyboardButton("횟수 제한 변경", callback_data="spam_limit")],
            [InlineKeyboardButton("시간 제한 변경", callback_data="spam_time")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🚫 **도배 방지 설정**\n현재 설정: {time_sec}초 내에 {limit}회 동일 메시지 전송 시 제재"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    elif data == "admin_nick":
        is_on = db.get_setting(chat_id, "nick_alert", False)
        status = "켜짐" if is_on else "꺼짐"
        keyboard = [
            [InlineKeyboardButton("상태 토글", callback_data="nick_toggle")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🔔 **닉네임 변경 알림**\n현재 상태: {status}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "nick_toggle":
        is_on = db.get_setting(chat_id, "nick_alert", False)
        db.set_setting(chat_id, "nick_alert", not is_on)
        is_on = not is_on
        status = "켜짐" if is_on else "꺼짐"
        keyboard = [
            [InlineKeyboardButton("상태 토글", callback_data="nick_toggle")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🔔 **닉네임 변경 알림**\n현재 상태: {status}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "admin_banned":
        words = db.get_banned_words(chat_id)
        word_list = ", ".join(words) if words else "없음"
        keyboard = [
            [InlineKeyboardButton("금칙어 추가", callback_data="banned_add")],
            [InlineKeyboardButton("금칙어 삭제", callback_data="banned_remove")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🤬 **금칙어 관리**\n현재 등록된 금칙어:\n{word_list}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "admin_schedule":
        msgs = db.get_scheduled_messages(chat_id)
        text = "📅 **예약 메시지 관리**\n\n"
        if msgs:
            for m in msgs:
                text += f"ID: {m['id']} | 시간: {m['schedule_time']} | 반복: {m['repeat_type']}\n내용: {m['message'][:20]}...\n\n"
        else:
            text += "등록된 예약 메시지가 없습니다.\n"
            
        keyboard = [
            [InlineKeyboardButton("예약 메시지 추가", callback_data="schedule_add")],
            [InlineKeyboardButton("예약 메시지 삭제", callback_data="schedule_remove")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "admin_stats":
        keyboard = [
            [InlineKeyboardButton("통계 초기화", callback_data="stats_reset")],
            [InlineKeyboardButton("데이터 백업 (.TXT)", callback_data="stats_backup")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = "📊 **통계 데이터 관리**"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "spam_limit":
        await query.edit_message_text("새로운 도배 제한 횟수를 숫자로 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_spam")]]))
        return AWAITING_SPAM_LIMIT

    elif data == "spam_time":
        await query.edit_message_text("새로운 도배 제한 시간(초)을 숫자로 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_spam")]]))
        return AWAITING_SPAM_TIME

    elif data == "banned_add":
        await query.edit_message_text("추가할 금칙어를 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_banned")]]))
        return AWAITING_BANNED_WORD

    elif data == "banned_remove":
        await query.edit_message_text("삭제할 금칙어를 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_banned")]]))
        return AWAITING_BANNED_WORD_REMOVE

    elif data == "schedule_add":
        await query.edit_message_text("발송할 예약 메시지 내용을 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_schedule")]]))
        return AWAITING_SCHEDULE_MSG

    elif data == "schedule_remove":
        await query.edit_message_text("삭제할 예약 메시지 ID를 숫자로 입력하세요.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_schedule")]]))
        return AWAITING_SCHEDULE_REMOVE

    elif data == "stats_reset":
        db.reset_all_user_stats(chat_id)
        db.reset_all_attendance(chat_id)
        await query.edit_message_text("✅ 통계 데이터가 초기화되었습니다.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("뒤로가기", callback_data="admin_stats")]]))

    elif data == "stats_backup":
        await send_backup(query.message, chat_id)
        await query.edit_message_text("✅ 백업 파일이 전송되었습니다.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("뒤로가기", callback_data="admin_stats")]]))

    return ConversationHandler.END

async def send_backup(message, chat_id):
    users = db.get_top_chatters(chat_id, 1000)
    attend = db.get_top_attendance(chat_id, 1000)
    
    content = "--- 사용자 채팅 통계 ---\n"
    for u in users:
        content += f"{u['user_id']} | {u['username']} | {u['first_name']} | {u['chat_count']}회\n"
        
    content += "\n--- 사용자 출석 통계 ---\n"
    for a in attend:
        content += f"{a['user_id']} | {a['username']} | {a['first_name']} | {a['attend_count']}회\n"
        
    filename = f"backup_{chat_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    with open(filename, "rb") as f:
        await message.reply_document(document=f, filename=filename)
    os.remove(filename)

async def handle_input_spam_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        limit = int(update.message.text)
        db.set_setting(chat_id, "spam_limit", limit)
        await update.message.reply_text(f"✅ 도배 제한 횟수가 {limit}회로 변경되었습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    await send_main_menu(update.message)
    return ConversationHandler.END

async def handle_input_spam_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        time_sec = int(update.message.text)
        db.set_setting(chat_id, "spam_time", time_sec)
        await update.message.reply_text(f"✅ 도배 제한 시간이 {time_sec}초로 변경되었습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    await send_main_menu(update.message)
    return ConversationHandler.END

async def handle_input_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    word = update.message.text.strip()
    if db.add_banned_word(chat_id, word):
        await update.message.reply_text(f"✅ 금칙어 '{word}' 추가 완료.")
    else:
        await update.message.reply_text("⚠️ 이미 등록된 금칙어입니다.")
    await send_main_menu(update.message)
    return ConversationHandler.END

async def handle_input_banned_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    word = update.message.text.strip()
    if db.remove_banned_word(chat_id, word):
        await update.message.reply_text(f"✅ 금칙어 '{word}' 삭제 완료.")
    else:
        await update.message.reply_text("⚠️ 등록되지 않은 금칙어입니다.")
    await send_main_menu(update.message)
    return ConversationHandler.END

async def handle_schedule_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['schedule_msg'] = update.message.text
    await update.message.reply_text("예약 시간을 입력하세요. (형식: HH:MM, 예: 14:30)")
    return AWAITING_SCHEDULE_TIME

async def handle_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text.strip()
    import re
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await update.message.reply_text("❌ 형식이 올바르지 않습니다. HH:MM 형식으로 입력하세요.")
        return AWAITING_SCHEDULE_TIME
    
    context.user_data['schedule_time'] = time_str
    keyboard = [
        [InlineKeyboardButton("매일", callback_data="rep_daily")],
        [InlineKeyboardButton("반복 안함", callback_data="rep_none")]
    ]
    await update.message.reply_text("반복 유형을 선택하세요.", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_SCHEDULE_REPEAT

async def handle_schedule_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    await query.answer()
    
    repeat_type = "daily" if query.data == "rep_daily" else "none"
    msg = context.user_data.get('schedule_msg')
    time_str = context.user_data.get('schedule_time')
    
    db.add_scheduled_message(chat_id, msg, time_str, repeat_type)
    await query.edit_message_text("✅ 예약 메시지가 등록되었습니다.")
    await send_main_menu(query.message)
    return ConversationHandler.END

async def handle_schedule_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        msg_id = int(update.message.text.strip())
        if db.delete_scheduled_message(chat_id, msg_id):
            await update.message.reply_text(f"✅ 예약 메시지 (ID: {msg_id})가 삭제되었습니다.")
        else:
            await update.message.reply_text("⚠️ 해당 ID의 예약 메시지가 없습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    await send_main_menu(update.message)
    return ConversationHandler.END

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    if not await check_admin_rights(context.bot, chat_id, user_id):
        return
    await send_backup(update.message, chat_id)

def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler('admin', cmd_admin),
            CallbackQueryHandler(admin_callback, pattern='^admin_|^spam_|^nick_|^banned_|^schedule_|^stats_')
        ],
        states={
            AWAITING_SPAM_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_spam_limit)],
            AWAITING_SPAM_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_spam_time)],
            AWAITING_BANNED_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_banned_word)],
            AWAITING_BANNED_WORD_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_banned_remove)],
            AWAITING_SCHEDULE_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_msg)],
            AWAITING_SCHEDULE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_time)],
            AWAITING_SCHEDULE_REPEAT: [CallbackQueryHandler(handle_schedule_repeat, pattern='^rep_')],
            AWAITING_SCHEDULE_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_remove)]
        },
        fallbacks=[CommandHandler('admin', cmd_admin)],
        allow_reentry=True
    )
