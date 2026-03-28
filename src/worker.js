// AMD Chat Bot - Cloudflare Workers
// Telegram Bot with attendance, ranking, and stats features

const TELEGRAM_API = 'https://api.telegram.org/bot';

// 출석체크 키워드
const ATTENDANCE_KEYWORDS = ['ㅊㅊ', '출첵', '출석체크'];

// 메인 요청 핸들러
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // GET 요청 - 상태 확인
    if (request.method === 'GET') {
      return new Response('✅ AMD Chat Bot is running on Cloudflare Workers!', { 
        status: 200,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }
    
    // POST 요청 - Telegram webhook
    if (request.method === 'POST') {
      try {
        const update = await request.json();
        await handleUpdate(update, env);
        return new Response('OK', { status: 200 });
      } catch (error) {
        console.error('Error handling update:', error);
        return new Response('Error', { status: 500 });
      }
    }
    
    return new Response('Method not allowed', { status: 405 });
  }
};

// 업데이트 처리
async function handleUpdate(update, env) {
  const botToken = env.BOT_TOKEN;
  
  if (!botToken) {
    console.error('BOT_TOKEN not set');
    return;
  }
  
  // 메시지 처리
  if (update.message) {
    await handleMessage(update.message, botToken, env);
  }
  
  // 콜백 쿼리 처리
  if (update.callback_query) {
    await handleCallbackQuery(update.callback_query, botToken, env);
  }
}

// 메시지 처리
async function handleMessage(message, botToken, env) {
  const chatId = message.chat.id;
  const userId = message.from.id;
  const text = message.text || '';
  const chatType = message.chat.type;
  const username = message.from.username;
  const firstName = message.from.first_name;
  
  // 사용자 정보 저장
  await saveUserInfo(userId, { username, first_name: firstName }, env);
  
  // 개인 채팅 처리
  if (chatType === 'private') {
    if (text === '/start') {
      await sendMessage(botToken, chatId, 
        '안녕하세요! 🤖 AMD Chat Bot입니다.\n\n' +
        '이 봇은 그룹 채팅에서 다음 기능을 제공합니다:\n' +
        '• 출석체크 (ㅊㅊ, 출첵, 출석체크)\n' +
        '• 채팅 순위 (/rank)\n' +
        '• 출석 순위 (/attendrank)\n' +
        '• 개인 통계 (/mystats)\n\n' +
        '그룹에 추가해서 사용핸보세요!'
      );
    }
    return;
  }
  
  // 그룹/슈퍼그룹 처리
  if (chatType === 'group' || chatType === 'supergroup') {
    // 명령어 처리
    if (text.startsWith('/')) {
      await handleCommand(message, botToken, env);
      return;
    }
    
    // 출석체크 처리
    if (ATTENDANCE_KEYWORDS.some(keyword => text.includes(keyword))) {
      await handleAttendance(userId, chatId, firstName, botToken, env);
      return;
    }
    
    // 메시지 카운트 증가
    await incrementMessageCount(userId, chatId, env);
  }
}

// 명령어 처리
async function handleCommand(message, botToken, env) {
  const chatId = message.chat.id;
  const userId = message.from.id;
  const text = message.text;
  const firstName = message.from.first_name;
  
  const command = text.split(' ')[0].split('@')[0];
  const args = text.split(' ').slice(1);
  
  switch (command) {
    case '/start':
      await sendMessage(botToken, chatId, 
        '✅ AMD Chat Bot이 활성화되었습니다!\n\n' +
        '사용 가능한 명령어:\n' +
        '/help - 도움말\n' +
        '/mystats - 내 메시지 수량\n' +
        '/rank - 채팅 순위 Top 10\n' +
        '/attend - 출석체크\n' +
        '/attendrank - 출석 순위 Top 10\n\n' +
        '또는 "ㅊㅊ", "출첵", "출석체크"로 출석체크!'
      );
      break;
      
    case '/help':
      await sendMessage(botToken, chatId, 
        '🤖 **AMD Chat Bot 명령어 안내**\n\n' +
        '📝 **기본 명령어**\n' +
        '/start - 봇 시작\n' +
        '/help - 이 도움말\n\n' +
        '📊 **통계 명령어**\n' +
        '/mystats - 내 메시지 수량 확인\n' +
        '/rank - 채팅 순위 Top 10\n' +
        '/attendrank - 출석 순위 Top 10\n\n' +
        '✅ **출석체크**\n' +
        '/attend 또는\n' +
        'ㅊㅊ / 출첵 / 출석체크'
      );
      break;
      
    case '/mystats':
      const myCount = await getMessageCount(userId, chatId, env);
      await sendMessage(botToken, chatId, `💬 ${firstName}님의 채팅 횟수: ${myCount}회`);
      break;
      
    case '/rank':
      await handleRank(chatId, botToken, env);
      break;
      
    case '/attend':
      await handleAttendance(userId, chatId, firstName, botToken, env);
      break;
      
    case '/attendrank':
      await handleAttendRank(chatId, botToken, env);
      break;
      
    default:
      break;
  }
}

// 출석체크 처리
async function handleAttendance(userId, chatId, firstName, botToken, env) {
  const today = new Date().toISOString().split('T')[0];
  const todayKey = `attendance:${chatId}:${userId}:${today}`;
  const countKey = `attendance_count:${chatId}:${userId}`;
  
  // 오늘 이미 출석했는지 확인
  const alreadyAttended = await env.KV.get(todayKey);
  
  if (alreadyAttended) {
    const totalCount = await env.KV.get(countKey) || '0';
    await sendMessage(botToken, chatId, 
      `⚠️ ${firstName}님은 오늘 이미 출석하셨습니다.\n(누적 ${totalCount}회)`
    );
    return;
  }
  
  // 출석 처리
  await env.KV.put(todayKey, '1', { expirationTtl: 86400 });
  
  // 누적 출석 수 증가
  const currentCount = parseInt(await env.KV.get(countKey) || '0');
  const newCount = currentCount + 1;
  await env.KV.put(countKey, newCount.toString());
  
  await sendMessage(botToken, chatId, 
    `✅ ${firstName}님 출석체크 완료!\n(누적 ${newCount}회)`
  );
}

// 채팅 순위 처리
async function handleRank(chatId, botToken, env) {
  const prefix = `msg_count:${chatId}:`;
  const listResult = await env.KV.list({ prefix });
  
  const users = [];
  for (const key of listResult.keys) {
    const userId = key.name.replace(prefix, '');
    const count = await env.KV.get(key.name);
    const userInfo = await env.KV.get(`user_info:${userId}`);
    const userData = userInfo ? JSON.parse(userInfo) : { first_name: `User${userId}` };
    
    users.push({
      name: userData.first_name || userData.username || `User${userId}`,
      count: parseInt(count || 0)
    });
  }
  
  users.sort((a, b) => b.count - a.count);
  const top10 = users.slice(0, 10);
  
  if (top10.length === 0) {
    await sendMessage(botToken, chatId, '📝 아직 채팅 기록이 없습니다.');
    return;
  }
  
  let msg = '🏆 **채팅 순위 Top 10** 🏆\n\n';
  top10.forEach((user, index) => {
    const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '•';
    msg += `${medal} ${index + 1}위: ${user.name} (${user.count}회)\n`;
  });
  
  await sendMessage(botToken, chatId, msg);
}

// 출석 순위 처리
async function handleAttendRank(chatId, botToken, env) {
  const prefix = `attendance_count:${chatId}:`;
  const listResult = await env.KV.list({ prefix });
  
  const users = [];
  for (const key of listResult.keys) {
    const userId = key.name.replace(prefix, '');
    const count = await env.KV.get(key.name);
    const userInfo = await env.KV.get(`user_info:${userId}`);
    const userData = userInfo ? JSON.parse(userInfo) : { first_name: `User${userId}` };
    
    users.push({
      name: userData.first_name || userData.username || `User${userId}`,
      count: parseInt(count || 0)
    });
  }
  
  users.sort((a, b) => b.count - a.count);
  const top10 = users.slice(0, 10);
  
  if (top10.length === 0) {
    await sendMessage(botToken, chatId, '📝 아직 출석 기록이 없습니다.');
    return;
  }
  
  let msg = '📅 **출석 순위 Top 10** 📅\n\n';
  top10.forEach((user, index) => {
    const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '•';
    msg += `${medal} ${index + 1}위: ${user.name} (${user.count}회)\n`;
  });
  
  await sendMessage(botToken, chatId, msg);
}

// 메시지 수량 증가
async function incrementMessageCount(userId, chatId, env) {
  const key = `msg_count:${chatId}:${userId}`;
  const currentCount = parseInt(await env.KV.get(key) || '0');
  await env.KV.put(key, (currentCount + 1).toString());
}

// 메시지 수량 조회
async function getMessageCount(userId, chatId, env) {
  const key = `msg_count:${chatId}:${userId}`;
  return parseInt(await env.KV.get(key) || '0');
}

// 사용자 정보 저장
async function saveUserInfo(userId, userData, env) {
  const key = `user_info:${userId}`;
  await env.KV.put(key, JSON.stringify(userData));
}

// 콜백 쿼리 처리
async function handleCallbackQuery(callbackQuery, botToken, env) {
  await answerCallbackQuery(botToken, callbackQuery.id);
}

// Telegram API - 메시지 보내기
async function sendMessage(botToken, chatId, text) {
  const url = `${TELEGRAM_API}${botToken}/sendMessage`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
        parse_mode: 'Markdown'
      })
    });
    
    if (!response.ok) {
      const error = await response.text();
      console.error('Telegram API error:', error);
    }
  } catch (error) {
    console.error('Error sending message:', error);
  }
}

// Telegram API - 콜백 응답
async function answerCallbackQuery(botToken, callbackQueryId) {
  const url = `${TELEGRAM_API}${botToken}/answerCallbackQuery`;
  
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ callback_query_id: callbackQueryId })
    });
  } catch (error) {
    console.error('Error answering callback:', error);
  }
}
