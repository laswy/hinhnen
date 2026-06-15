/**
 * Zalo Bot — Cloudflare Worker (webhook)
 *
 * Nhận tin nhắn từ Zalo Bot qua webhook (tức thời), xử lý lệnh kế hoạch,
 * commit thay đổi vào GitHub (actionplan.json / calendar_notes.json),
 * rồi trả lời lại trên Zalo.
 *
 * Biến môi trường (Cloudflare Secrets) cần cấu hình:
 *   ZALO_BOT_TOKEN   — token bot Zalo (dạng "id:secret")
 *   ZALO_CHAT_ID     — id nhóm/chat được phép dùng lệnh
 *   GITHUB_TOKEN     — GitHub PAT (fine-grained, quyền Contents: Read & Write trên repo)
 *   GITHUB_REPO      — "laswy/hinhnen"
 *   GITHUB_BRANCH    — "main"
 *   WEBHOOK_SECRET   — chuỗi bí mật, đặt trong URL webhook để xác thực
 */

const ZALO_API = 'https://bot-api.zapps.me';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Xác thực: secret nằm trong path  →  https://<worker>/<WEBHOOK_SECRET>
    const pathSecret = url.pathname.replace(/^\/+/, '');
    if (request.method !== 'POST' || pathSecret !== env.WEBHOOK_SECRET) {
      return new Response('Not found', { status: 404 });
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return new Response('Bad request', { status: 400 });
    }

    // Webhook payload: {"result": {message:...}} hoặc {message:...}
    const update = body.result || body;
    const msg = update.message;
    if (!msg) return new Response('ok'); // không phải tin nhắn

    const chatId = msg.chat && msg.chat.id;
    const text = (msg.text || '').trim();

    // In ra để debug (xem bằng: npx wrangler tail)
    console.log(`Tin nhan tu chat_id=${chatId}: ${text.slice(0, 50)}`);

    // Chỉ xử lý chat được phép
    if (String(chatId) !== String(env.ZALO_CHAT_ID)) {
      console.log(`Bo qua: chat_id ${chatId} khong khop ZALO_CHAT_ID`);
      return new Response('ok');
    }
    if (!text) return new Response('ok');

    try {
      await handleCommand(text, chatId, env);
    } catch (e) {
      await sendMessage(env, chatId, 'Loi he thong: ' + (e.message || e));
    }
    return new Response('ok');
  },
};

// ── Xử lý lệnh ────────────────────────────────────────────────────────

async function handleCommand(text, chatId, env) {
  const cmd = text.split(/\s+/)[0].toLowerCase().split('@')[0];

  // Lệnh chỉ đọc (không cần ghi file)
  if (['/help', '/start', '/huongdan'].includes(cmd)) {
    return sendMessage(env, chatId, HELP_TEXT);
  }

  if (['/ds', '/list', '/danhsach'].includes(cmd)) {
    const tasks = await ghGetJson(env, 'actionplan.json');
    return sendMessage(env, chatId, cmdDs(tasks.data));
  }

  if (['/xemghichu', '/viewnote'].includes(cmd)) {
    const notes = await ghGetJson(env, 'calendar_notes.json');
    return sendMessage(env, chatId, cmdXemNote(text, notes.data));
  }

  // Lệnh sửa kế hoạch
  if (['/them', '/add', '/done', '/xong', '/update', '/xoa', '/del', '/delete', '/sua', '/edit'].includes(cmd)) {
    const file = await ghGetJson(env, 'actionplan.json');
    let tasks = file.data;
    let result;

    if (['/them', '/add'].includes(cmd))            result = cmdThem(text, tasks);
    else if (['/done', '/xong'].includes(cmd))      result = cmdDone(text, tasks);
    else if (cmd === '/update')                     result = cmdUpdate(text, tasks);
    else if (['/xoa', '/del', '/delete'].includes(cmd)) result = cmdXoa(text, tasks);
    else                                            result = cmdSua(text, tasks);

    if (result.tasks !== null) {
      await ghPutJson(env, 'actionplan.json', result.tasks, file.sha,
                      'Cap nhat ke hoach tu Zalo');
    }
    return sendMessage(env, chatId, result.reply);
  }

  // Lệnh ghi chú
  if (['/ghichu', '/addnote', '/xoaghichu', '/delnote', '/suaghi', '/editnote'].includes(cmd)) {
    const file = await ghGetJson(env, 'calendar_notes.json');
    let notes = file.data;
    let result;

    if (['/ghichu', '/addnote'].includes(cmd))         result = cmdGhiChu(text, notes);
    else if (['/xoaghichu', '/delnote'].includes(cmd)) result = cmdXoaNote(text, notes);
    else                                               result = cmdSuaGhi(text, notes);

    if (result.notes !== null) {
      await ghPutJson(env, 'calendar_notes.json', result.notes, file.sha,
                      'Cap nhat ghi chu tu Zalo');
    }
    return sendMessage(env, chatId, result.reply);
  }

  return sendMessage(env, chatId, `Lenh khong hop le: ${cmd}\nGui /help de xem huong dan.`);
}

// ── Logic lệnh (port từ Python) ───────────────────────────────────────

const HELP_TEXT = `Bot Ke Hoach - Huong dan:

Them ke hoach:
/them Ten | Tu ngay | Den ngay | Uu tien | Phu trach
Vi du: /them HOP TONG KET | 2026-06-10 | 2026-06-30 | A | ANH

Sua ke hoach:
/sua ten hoac ID | truong | gia tri moi
Truong: ten | start | end | priority | nguoiphutrach | ghichu
Vi du: /sua HOP TONG KET | end | 2026-08-15

Xem danh sach:  /ds
Danh dau xong:  /done ten hoac ID
Cap nhat %:     /update ten hoac ID | 75
Xoa ke hoach:   /xoa ten hoac ID

Them ghi chu lich: /ghichu YYYY-MM-DD | Noi dung
Sua ghi chu:       /suaghi ID | Noi dung moi
Xoa ghi chu:       /xoaghichu ID
Xem ghi chu ngay:  /xemghichu YYYY-MM-DD

Uu tien: A (cao) | B (vua) | C (thap)
Ngay: YYYY-MM-DD (vd: 2026-06-10)
Huong dan: /help`;

function genId() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  for (let i = 0; i < 8; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

function isValidDate(s) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(s + 'T00:00:00Z');
  return !isNaN(d.getTime()) && s === d.toISOString().slice(0, 10);
}

function findTask(tasks, keyword) {
  const kw = keyword.toLowerCase().trim();
  for (const t of tasks) if (t.id === kw) return t;
  for (const t of tasks) if (t.title.toLowerCase().includes(kw)) return t;
  return null;
}

function bodyOf(text) {
  const i = text.indexOf(' ');
  return i === -1 ? '' : text.slice(i + 1);
}

function cmdThem(text, tasks) {
  const parts = bodyOf(text).split('|').map(p => p.trim());
  if (parts.length < 3)
    return { tasks: null, reply: 'Thieu thong tin.\nDinh dang: /them Ten | Tu ngay | Den ngay | Uu tien | Phu trach' };
  for (const d of [parts[1], parts[2]])
    if (!isValidDate(d))
      return { tasks: null, reply: `Ngay sai dinh dang: ${d}\nDung: YYYY-MM-DD` };
  let prio = (parts[3] || 'B').toUpperCase();
  if (!['A', 'B', 'C'].includes(prio)) prio = 'B';
  const task = {
    id: genId(), title: parts[0].toUpperCase(), category: 'Other',
    priority: prio, status: 'Chua bat dau', assignee: parts[4] || '',
    start: parts[1], end: parts[2], progress: 0, notes: parts[5] || '', result: '',
  };
  tasks.push(task);
  return {
    tasks,
    reply: `Da them ke hoach!\n\n${task.title}\n${task.start} -> ${task.end}\n` +
           `Uu tien: ${task.priority}  |  Phu trach: ${task.assignee || '—'}\nID: ${task.id}`,
  };
}

function cmdDone(text, tasks) {
  const kw = bodyOf(text).trim();
  const t = findTask(tasks, kw);
  if (!t) return { tasks: null, reply: `Khong tim thay: ${kw}` };
  t.status = 'Hoan thanh'; t.progress = 100;
  return { tasks, reply: `Hoan thanh: ${t.title}` };
}

function cmdUpdate(text, tasks) {
  const parts = bodyOf(text).split('|').map(p => p.trim());
  if (parts.length < 2 || !/^\d+$/.test(parts[1]))
    return { tasks: null, reply: 'Dinh dang: /update ten hoac ID | 75' };
  const t = findTask(tasks, parts[0]);
  if (!t) return { tasks: null, reply: `Khong tim thay: ${parts[0]}` };
  const pct = Math.max(0, Math.min(100, parseInt(parts[1], 10)));
  t.progress = pct;
  if (pct === 100) t.status = 'Hoan thanh';
  else if (pct > 0) t.status = 'Dang thuc hien';
  return { tasks, reply: `Cap nhat ${t.title}: ${pct}%` };
}

function cmdXoa(text, tasks) {
  const kw = bodyOf(text).trim();
  const t = findTask(tasks, kw);
  if (!t) return { tasks: null, reply: `Khong tim thay: ${kw}` };
  tasks.splice(tasks.indexOf(t), 1);
  return { tasks, reply: `Da xoa: ${t.title}` };
}

function cmdSua(text, tasks) {
  const parts = bodyOf(text).split('|').map(p => p.trim());
  if (parts.length < 3)
    return { tasks: null, reply: 'Dinh dang:\n/sua ten hoac ID | truong | gia tri moi\nTruong: ten | start | end | priority | nguoiphutrach | ghichu' };
  const t = findTask(tasks, parts[0]);
  if (!t) return { tasks: null, reply: `Khong tim thay: ${parts[0]}` };
  const fieldMap = { ten: 'title', start: 'start', end: 'end', priority: 'priority', nguoiphutrach: 'assignee', ghichu: 'notes' };
  const field = parts[1].toLowerCase();
  if (!(field in fieldMap))
    return { tasks: null, reply: `Truong khong hop le: ${parts[1]}` };
  let value = parts[2];
  if (field === 'start' || field === 'end') {
    if (!isValidDate(value)) return { tasks: null, reply: `Ngay sai dinh dang: ${value}` };
  }
  if (field === 'priority') {
    value = value.toUpperCase();
    if (!['A', 'B', 'C'].includes(value)) return { tasks: null, reply: 'Uu tien phai la A, B hoac C' };
  }
  if (field === 'ten') value = value.toUpperCase();
  t[fieldMap[field]] = value;
  return { tasks, reply: `Da cap nhat ${t.title}\n${parts[1]}: ${value}` };
}

function cmdDs(tasks) {
  if (!tasks.length) return 'Chua co ke hoach nao.';
  const ICON = { 'Hoan thanh': '[Xong]', 'Dang thuc hien': '[Dang lam]', 'Chua bat dau': '[Chua]' };
  const lines = ['Danh sach ke hoach:\n'];
  for (const t of tasks) {
    lines.push(`${ICON[t.status] || '•'} ${t.title}`);
    lines.push(`   ${t.start} -> ${t.end}  [${t.priority}]  ${t.progress}%`);
  }
  return lines.join('\n');
}

function cmdGhiChu(text, notes) {
  const raw = bodyOf(text);
  const idx = raw.indexOf('|');
  const parts = idx === -1 ? [raw.trim()] : [raw.slice(0, idx).trim(), raw.slice(idx + 1).trim()];
  if (parts.length < 2)
    return { notes: null, reply: 'Dinh dang: /ghichu YYYY-MM-DD | Noi dung' };
  if (!isValidDate(parts[0]))
    return { notes: null, reply: `Ngay sai dinh dang: ${parts[0]}` };
  const note = { id: 'note' + genId(), date: parts[0], text: parts[1] };
  notes.push(note);
  return { notes, reply: `Da them ghi chu!\nNgay: ${note.date}\nNoi dung: ${note.text}\nID: ${note.id}` };
}

function cmdXoaNote(text, notes) {
  const kw = bodyOf(text).trim();
  const found = notes.find(n => n.id === kw);
  if (!found) return { notes: null, reply: `Khong tim thay ghi chu ID: ${kw}` };
  notes.splice(notes.indexOf(found), 1);
  return { notes, reply: `Da xoa ghi chu: ${found.text.slice(0, 50)}` };
}

function cmdSuaGhi(text, notes) {
  const raw = bodyOf(text);
  const idx = raw.indexOf('|');
  const parts = idx === -1 ? [raw.trim()] : [raw.slice(0, idx).trim(), raw.slice(idx + 1).trim()];
  if (parts.length < 2)
    return { notes: null, reply: 'Dinh dang: /suaghi ID | Noi dung moi' };
  const found = notes.find(n => n.id === parts[0]);
  if (!found) return { notes: null, reply: `Khong tim thay ghi chu ID: ${parts[0]}` };
  found.text = parts[1];
  return { notes, reply: `Da cap nhat ghi chu!\nNgay: ${found.date}\nNoi dung moi: ${found.text}\nID: ${found.id}` };
}

function cmdXemNote(text, notes) {
  const dateStr = bodyOf(text).trim();
  const dayNotes = notes.filter(n => n.date === dateStr);
  if (!dayNotes.length) return `Khong co ghi chu nao vao ngay ${dateStr}.`;
  const lines = [`Ghi chu ngay ${dateStr}:\n`];
  for (const n of dayNotes) lines.push(`• ${n.text}  [${n.id}]`);
  return lines.join('\n');
}

// ── Zalo API ──────────────────────────────────────────────────────────

async function sendMessage(env, chatId, text) {
  const form = new URLSearchParams();
  form.set('chat_id', String(chatId));
  form.set('text', text);
  await fetch(`${ZALO_API}/bot${env.ZALO_BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: {
      'User-Agent': 'cloudflare-worker-zalo-bot',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: form.toString(),
  });
}

// ── GitHub API ────────────────────────────────────────────────────────

function b64encodeUtf8(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function b64decodeUtf8(b64) {
  const bin = atob(b64.replace(/\s/g, ''));
  const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function ghHeaders(env) {
  return {
    'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'zalo-bot-worker',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

async function ghGetJson(env, path) {
  const branch = env.GITHUB_BRANCH || 'main';
  const r = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}?ref=${branch}`,
    { headers: ghHeaders(env) }
  );
  if (r.status === 404) return { data: [], sha: null };
  if (!r.ok) throw new Error(`GitHub GET ${path}: ${r.status} ${await r.text()}`);
  const j = await r.json();
  const content = b64decodeUtf8(j.content).trim();
  return { data: content ? JSON.parse(content) : [], sha: j.sha };
}

async function ghPutJson(env, path, data, sha, message) {
  const branch = env.GITHUB_BRANCH || 'main';
  const content = b64encodeUtf8(JSON.stringify(data, null, 2) + '\n');
  const payload = { message, content, branch };
  if (sha) payload.sha = sha;
  const r = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}`,
    { method: 'PUT', headers: ghHeaders(env), body: JSON.stringify(payload) }
  );
  if (!r.ok) throw new Error(`GitHub PUT ${path}: ${r.status} ${await r.text()}`);
}
