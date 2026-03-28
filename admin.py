import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import config
import database as db

# States for ConversationHandler
(
    SELECT_GROUP,
    MAIN_MENU,
    AWAITING_BANNED_WORD,
    AWAITING_BANNED_WORD_REMOVE,
    AWAITING_SPAM_LIMIT,
    AWAITING_SPAM_TIME_MINUTES,
    AWAITING_SCHEDULE_MSG,
    AWAITING_SCHEDULE_TIME,
    AWAITING_SCHEDULE_REPEAT,
    AWAITING_SCHEDULE_REMOVE
) = range(10)

async def check_admin_rights(bot, chat_id, user_id):
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status == 'creator':
            return True
        elif user_member.status == 'administrator':
            return getattr(user_member, 'can_change_info', False)
        return False
    except Exception as e:
        print(f"Error checking admin rights: {e}")
        return False

async def check_bot_admin(bot, chat_id):
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        return bot_member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"Error checking bot admin: {e}")
        return False

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ConversationHandler.END
        
    if update.message.chat.type != 'private':
        await update.message.reply_text("관리자 명령어는 봇과의 1:1 개인 채팅에서만 사용 가능합니다.")
        return ConversationHandler.END

    user_id = update.message.from_user.id
    groups = db.get_all_groups()
    valid_groups = []

    print(f"[ADMIN] Found {len(groups)} groups in database")

    # 봇이 관리자인 그룹 & 유저가 정보 변경 권한이 있는 그룹 찾기
    for group in groups:
        chat_id = group['chat_id']
        print(f"[ADMIN] Checking group {chat_id}: {group.get('title', 'Unknown')}")
        
        is_bot_admin = await check_bot_admin(context.bot, chat_id)
        print(f"[ADMIN]   - Bot admin: {is_bot_admin}")
        
        if is_bot_admin:
            is_user_admin = await check_admin_rights(context.bot, chat_id, user_id)
            print(f"[ADMIN]   - User admin with rights: {is_user_admin}")
            
            if is_user_admin:
                try:
                    chat = await context.bot.get_chat(chat_id)
                    title = chat.title if chat.title else f"그룹 ({chat_id})"
                    valid_groups.append((chat_id, title))
                    print(f"[ADMIN]   - Added to valid groups: {title}")
                except Exception as e:
                    print(f"[ADMIN]   - Error getting chat info: {e}")
                    # Use stored title if available
                    title = group.get('title', f"그룹 ({chat_id})")
                    valid_groups.append((chat_id, title))

    if not valid_groups:
        await update.message.reply_text(
            "현재 관리자로 설정할 수 있는 그룹이 없습니다.\n\n"
            "조건:\n"
            "1. 봇이 그룹의 관리자여야 함\n"
            "2. 회원님도 해당 그룹에서 '정보 변경' 권한이 있는 관리자여야 함\n\n"
            "봇을 그룹에 추가하고 관리자로 지정한 후 다시 시도해주세요."
        )
        return ConversationHandler.END

    keyboard = []
    for chat_id, title in valid_groups:
        keyboard.append([InlineKeyboardButton(title, callback_data=f"select_group_{chat_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚙️ **설정할 그룹을 선택해주세요.**\n\n"
        "아래 목록에서 관리할 그룹을 선택하세요.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SELECT_GROUP

async def handle_group_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extract chat_id from callback_data
    chat_id_str = query.data.replace("select_group_", "")
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        await query.edit_message_text("❌ 오류가 발생했습니다. 다시 시도해주세요.")
        return ConversationHandler.END

    # Verify user still has admin rights
    user_id = query.from_user.id
    if not await check_admin_rights(context.bot, chat_id, user_id):
        await query.edit_message_text("❌ 해당 그룹에 대한 관리자 권한이 없습니다.")
        return ConversationHandler.END

    # Save to user_data
    context.user_data['admin_chat_id'] = chat_id
    
    try:
        chat = await context.bot.get_chat(chat_id)
        context.user_data['admin_chat_title'] = chat.title if chat.title else f"그룹 ({chat_id})"
    except:
        context.user_data['admin_chat_title'] = f"그룹 ({chat_id})"
    
    print(f"[ADMIN] Group selected: {context.user_data['admin_chat_title']} ({chat_id})")
    
    # Show main menu
    await send_main_menu(query, edit=True, context=context)
    return MAIN_MENU

async def send_main_menu(message_or_query, edit=False, context=None):
    keyboard = [
        [InlineKeyboardButton("🚫 도배 방지 설정", callback_data="admin_spam")],
        [InlineKeyboardButton("🔔 사용자명 변경 알림 설정", callback_data="admin_username")],
        [InlineKeyboardButton("🤬 금칙어 관리", callback_data="admin_banned")],
        [InlineKeyboardButton("📅 예약 메시지 관리", callback_data="admin_schedule")],
        [InlineKeyboardButton("📊 통계 데이터 관리", callback_data="admin_stats")],
        [InlineKeyboardButton("🔄 그룹 다시 선택", callback_data="admin_reselect")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if context and 'admin_chat_title' in context.user_data:
        title = context.user_data['admin_chat_title']
        text = f"🔧 **관리자 메뉴**\n\n그룹: {title}\n\n원하는 설정을 선택하세요."
    else:
        text = "🔧 **관리자 메뉴**\n\n원하는 설정을 선택하세요."
    
    if edit:
        await message_or_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "admin_reselect":
        await query.answer()
        if 'admin_chat_id' in context.user_data:
            del context.user_data['admin_chat_id']
        if 'admin_chat_title' in context.user_data:
            del context.user_data['admin_chat_title']
        await query.edit_message_text("다시 설정하려면 `/admin` 명령어를 입력해주세요.", parse_mode='Markdown')
        return ConversationHandler.END

    chat_id = context.user_data.get('admin_chat_id')
    user_id = query.from_user.id
    
    if not chat_id:
        await query.answer("선택된 그룹이 없습니다. /admin을 다시 입력해주세요.", show_alert=True)
        return ConversationHandler.END

    if not await check_admin_rights(context.bot, chat_id, user_id):
        await query.answer("해당 그룹에 대한 권한이 없습니다.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    data = query.data
    print(f"[ADMIN] Callback received: {data}")

    if data == "admin_main":
        await send_main_menu(query, edit=True, context=context)
        return MAIN_MENU
        
    elif data == "admin_spam":
        limit = db.get_setting(chat_id, "spam_limit", 5)
        time_minutes = db.get_setting(chat_id, "spam_time_minutes", 10)
        keyboard = [
            [InlineKeyboardButton("횟수 제한 변경", callback_data="spam_limit")],
            [InlineKeyboardButton("시간(분) 제한 변경", callback_data="spam_time")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🚫 **도배 방지 설정**\n\n현재 설정: {time_minutes}분 내에 {limit}회 동일 메시지 전송 시 제재"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU
        
    elif data == "admin_username":
        is_on = db.get_setting(chat_id, "username_alert", False)
        status = "켜짐 ✅" if is_on else "꺼짐 ❌"
        keyboard = [
            [InlineKeyboardButton("상태 토글", callback_data="username_toggle")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🔔 **사용자명(@username) 변경 알림**\n\n현재 상태: {status}\n\n사용자가 @username을 변경하면 해당 메시지에 답글로 알림을 보냅니다."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU

    elif data == "username_toggle":
        is_on = db.get_setting(chat_id, "username_alert", False)
        db.set_setting(chat_id, "username_alert", not is_on)
        is_on = not is_on
        status = "켜짐 ✅" if is_on else "꺼짐 ❌"
        keyboard = [
            [InlineKeyboardButton("상태 토글", callback_data="username_toggle")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🔔 **사용자명(@username) 변경 알림**\n\n현재 상태: {status}\n\n사용자가 @username을 변경하면 해당 메시지에 답글로 알림을 보냅니다."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU

    elif data == "admin_banned":
        words = db.get_banned_words(chat_id)
        word_list = ", ".join(words) if words else "없음"
        keyboard = [
            [InlineKeyboardButton("금칙어 추가", callback_data="banned_add")],
            [InlineKeyboardButton("금칙어 삭제", callback_data="banned_remove")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = f"🤬 **금칙어 관리**\n\n현재 등록된 금칙어:\n{word_list}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU

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
        return MAIN_MENU

    elif data == "admin_stats":
        keyboard = [
            [InlineKeyboardButton("채팅 통계 초기화", callback_data="stats_reset_chat")],
            [InlineKeyboardButton("출석 통계 초기화", callback_data="stats_reset_attend")],
            [InlineKeyboardButton("데이터 백업 (.TXT)", callback_data="stats_backup")],
            [InlineKeyboardButton("뒤로가기", callback_data="admin_main")]
        ]
        text = "📊 **통계 데이터 관리**\n\n⚠️ 초기화는 되돌릴 수 없습니다."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU

    elif data == "spam_limit":
        await query.edit_message_text(
            "새로운 도배 제한 횟수를 숫자로 입력하세요. (1 ~ 무제한)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_spam")]])
        )
        return AWAITING_SPAM_LIMIT

    elif data == "spam_time":
        await query.edit_message_text(
            "새로운 도배 제한 시간을 분 단위로 입력하세요.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_spam")]])
        )
        return AWAITING_SPAM_TIME_MINUTES

    elif data == "banned_add":
        await query.edit_message_text(
            "추가할 금칙어를 입력하세요.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_banned")]])
        )
        return AWAITING_BANNED_WORD

    elif data == "banned_remove":
        await query.edit_message_text(
            "삭제할 금칙어를 입력하세요.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_banned")]])
        )
        return AWAITING_BANNED_WORD_REMOVE

    elif data == "schedule_add":
        await query.edit_message_text(
            "발송할 예약 메시지 내용을 입력하세요.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_schedule")]])
        )
        return AWAITING_SCHEDULE_MSG

    elif data == "schedule_remove":
        await query.edit_message_text(
            "삭제할 예약 메시지 ID를 숫자로 입력하세요.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("취소", callback_data="admin_schedule")]])
        )
        return AWAITING_SCHEDULE_REMOVE

    elif data == "stats_reset_chat":
        db.reset_all_user_stats(chat_id)
        await query.edit_message_text(
            "✅ 채팅 통계 데이터가 초기화되었습니다.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("뒤로가기", callback_data="admin_stats")]])
        )
        return MAIN_MENU

    elif data == "stats_reset_attend":
        db.reset_all_attendance(chat_id)
        await query.edit_message_text(
            "✅ 출석 통계 데이터가 초기화되었습니다.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("뒤로가기", callback_data="admin_stats")]])
        )
        return MAIN_MENU

    elif data == "stats_backup":
        # 먼저 백업 파일 전송
        await send_backup(query.message, chat_id)
        # 그 다음 메시지 업데이트
        await query.edit_message_text(
            "✅ 백업 파일이 전송되었습니다.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("뒤로가기", callback_data="admin_stats")]])
        )
        return MAIN_MENU

    return MAIN_MENU

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
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await update.message.reply_text("❌ 세션이 만료되었습니다. /admin을 다시 입력해주세요.")
        return ConversationHandler.END
    
    try:
        limit = int(update.message.text)
        if limit < 1:
            await update.message.reply_text("❌ 1 이상의 숫자를 입력해주세요.")
        else:
            db.set_setting(chat_id, "spam_limit", limit)
            await update.message.reply_text(f"✅ 도배 제한 횟수가 {limit}회로 변경되었습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    
    await send_main_menu(update.message, context=context)
    return MAIN_MENU

async def handle_input_spam_time_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await update.message.reply_text("❌ 세션이 만료되었습니다. /admin을 다시 입력해주세요.")
        return ConversationHandler.END

    try:
        time_minutes = int(update.message.text)
        if time_minutes < 1:
            await update.message.reply_text("❌ 1 이상의 숫자를 입력해주세요.")
        else:
            db.set_setting(chat_id, "spam_time_minutes", time_minutes)
            await update.message.reply_text(f"✅ 도배 제한 시간이 {time_minutes}분으로 변경되었습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    
    await send_main_menu(update.message, context=context)
    return MAIN_MENU

async def handle_input_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await update.message.reply_text("❌ 세션이 만료되었습니다. /admin을 다시 입력해주세요.")
        return ConversationHandler.END

    word = update.message.text.strip()
    if db.add_banned_word(chat_id, word):
        await update.message.reply_text(f"✅ 금칙어 '{word}' 추가 완료.")
    else:
        await update.message.reply_text("⚠️ 이미 등록된 금칙어입니다.")
    
    await send_main_menu(update.message, context=context)
    return MAIN_MENU

async def handle_input_banned_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await update.message.reply_text("❌ 세션이 만료되었습니다. /admin을 다시 입력해주세요.")
        return ConversationHandler.END

    word = update.message.text.strip()
    if db.remove_banned_word(chat_id, word):
        await update.message.reply_text(f"✅ 금칙어 '{word}' 삭제 완료.")
    else:
        await update.message.reply_text("⚠️ 등록되지 않은 금칙어입니다.")
    
    await send_main_menu(update.message, context=context)
    return MAIN_MENU

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
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await query.answer("세션이 만료되었습니다.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    
    repeat_type = "daily" if query.data == "rep_daily" else "none"
    msg = context.user_data.get('schedule_msg')
    time_str = context.user_data.get('schedule_time')
    
    db.add_scheduled_message(chat_id, msg, time_str, repeat_type)
    await query.edit_message_text("✅ 예약 메시지가 등록되었습니다.")
    await send_main_menu(query.message, context=context)
    return MAIN_MENU

async def handle_schedule_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('admin_chat_id')
    if not chat_id:
        await update.message.reply_text("❌ 세션이 만료되었습니다. /admin을 다시 입력해주세요.")
        return ConversationHandler.END

    try:
        msg_id = int(update.message.text.strip())
        if db.delete_scheduled_message(chat_id, msg_id):
            await update.message.reply_text(f"✅ 예약 메시지 (ID: {msg_id})가 삭제되었습니다.")
        else:
            await update.message.reply_text("⚠️ 해당 ID의 예약 메시지가 없습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력해주세요.")
    
    await send_main_menu(update.message, context=context)
    return MAIN_MENU

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        chat_id = context.user_data.get('admin_chat_id')
        if not chat_id:
            await update.message.reply_text("/admin 을 통해 설정할 그룹을 먼저 선택해주세요.")
            return
    else:
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        if not await check_admin_rights(context.bot, chat_id, user_id):
            return
            
    await send_backup(update.message, chat_id)

def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler('admin', cmd_admin)
        ],
        states={
            SELECT_GROUP: [
                CallbackQueryHandler(handle_group_select, pattern='^select_group_')
            ],
            MAIN_MENU: [
                CallbackQueryHandler(admin_callback, pattern='^admin_|^spam_|^username_|^banned_|^schedule_|^stats_')
            ],
            AWAITING_SPAM_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_spam_limit)
            ],
            AWAITING_SPAM_TIME_MINUTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_spam_time_minutes)
            ],
            AWAITING_BANNED_WORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_banned_word)
            ],
            AWAITING_BANNED_WORD_REMOVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input_banned_remove)
            ],
            AWAITING_SCHEDULE_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_msg)
            ],
            AWAITING_SCHEDULE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_time)
            ],
            AWAITING_SCHEDULE_REPEAT: [
                CallbackQueryHandler(handle_schedule_repeat, pattern='^rep_')
            ],
            AWAITING_SCHEDULE_REMOVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_remove)
            ]
        },
        fallbacks=[
            CommandHandler('admin', cmd_admin),
            CommandHandler('cancel', lambda u, c: u.message.reply_text("취소되었습니다. /admin을 다시 입력해주세요.") or ConversationHandler.END)
        ],
        allow_reentry=True
    )
