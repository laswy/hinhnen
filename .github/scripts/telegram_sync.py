import json
import os
import sys
import requests
import random
import string
from datetime import datetime

BOT_TOKEN     = os.environ['TELEGRAM_BOT_TOKEN']
ALLOWED_CHAT  = int(os.environ['TELEGRAM_CHAT_ID'])
OFFSET_FILE   = '.github/telegram_offset.txt'
DATA_FILE     = 'actionplan.json'

# ── Telegram helpers ─────────────────────────────────────────────────
def get_updates(offset=None):
    p = {'timeout': 0, 'allowed_updates': ['message']}
    if offset:
        p['offset'] = offset
    r = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates', params=p, timeout=10)
    return r.json()

def send(chat_id, text):
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
        timeout=10
    )

# ── Data helpers ──────────────────────────────────────────────────────
def gen_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def load():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding='utf-8') as f:
        return json.load(f)

def save(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def load_offset():
    if os.path.exists(OFFSET_FILE):
        t = open(OFFSET_FILE).read().strip()
        if t.isdigit():
            return int(t)
    return None

def save_offset(v):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, 'w') as f:
        f.write(str(v))

# ── Command parsers ───────────────────────────────────────────────────

HELP_TEXT = """\
📋 <b>Bot Kế Hoạch — Hướng dẫn:</b>

➕ <b>Thêm kế hoạch:</b>
/them Tên | Từ ngày | Đến ngày | Ưu tiên | Phụ trách
Ví dụ:
<code>/them HỌP TỔNG KẾT | 2026-07-01 | 2026-07-31 | A | ANH</code>

Ưu tiên: <b>A</b> (cao) · <b>B</b> (vừa) · <b>C</b> (thấp)
Ngày định dạng: <b>YYYY-MM-DD</b>

📋 <b>Xem danh sách:</b>  /ds
✅ <b>Đánh dấu xong:</b>  /done tên hoặc ID
✏️ <b>Cập nhật %:</b>     /update tên hoặc ID | 75
🗑 <b>Xóa kế hoạch:</b>   /xoa tên hoặc ID
❓ <b>Hướng dẫn:</b>      /help"""

def cmd_them(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 3:
        return None, '❌ Thiếu thông tin.\n\nĐịnh dạng:\n<code>/them Tên | Từ ngày | Đến ngày | Ưu tiên | Phụ trách</code>'
    for dt_str in [parts[1], parts[2]]:
        try:
            datetime.strptime(dt_str, '%Y-%m-%d')
        except ValueError:
            return None, f'❌ Ngày sai định dạng: <b>{dt_str}</b>\nDùng: YYYY-MM-DD (vd: 2026-07-01)'
    prio = parts[3].upper() if len(parts) > 3 else 'B'
    if prio not in ('A', 'B', 'C'):
        prio = 'B'
    task = {
        'id':        gen_id(),
        'title':     parts[0].upper(),
        'category':  'Other',
        'priority':  prio,
        'status':    'Chưa bắt đầu',
        'assignee':  parts[4] if len(parts) > 4 else '',
        'start':     parts[1],
        'end':       parts[2],
        'progress':  0,
        'notes':     parts[5] if len(parts) > 5 else '',
        'result':    ''
    }
    tasks.append(task)
    reply = (f'✅ Đã thêm kế hoạch!\n\n'
             f'📌 <b>{task["title"]}</b>\n'
             f'📅 {task["start"]} → {task["end"]}\n'
             f'⚡ Ưu tiên: {task["priority"]}  |  👤 {task["assignee"] or "—"}\n'
             f'🆔 ID: <code>{task["id"]}</code>')
    return tasks, reply

def find_task(tasks, keyword):
    kw = keyword.lower().strip()
    for t in tasks:
        if t['id'] == kw:
            return t
    for t in tasks:
        if kw in t['title'].lower():
            return t
    return None

def cmd_done(text, tasks):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    t = find_task(tasks, keyword)
    if not t:
        return None, f'❌ Không tìm thấy: <b>{keyword}</b>'
    t['status'] = 'Hoàn thành'
    t['progress'] = 100
    return tasks, f'✅ Hoàn thành: <b>{t["title"]}</b>'

def cmd_update(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 2 or not parts[1].isdigit():
        return None, '❌ Định dạng: <code>/update tên hoặc ID | 75</code>'
    t = find_task(tasks, parts[0])
    if not t:
        return None, f'❌ Không tìm thấy: <b>{parts[0]}</b>'
    pct = max(0, min(100, int(parts[1])))
    t['progress'] = pct
    if pct == 100:
        t['status'] = 'Hoàn thành'
    elif pct > 0:
        t['status'] = 'Đang thực hiện'
    return tasks, f'✏️ Cập nhật <b>{t["title"]}</b>: {pct}%'

def cmd_xoa(text, tasks):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    t = find_task(tasks, keyword)
    if not t:
        return None, f'❌ Không tìm thấy: <b>{keyword}</b>'
    tasks.remove(t)
    return tasks, f'🗑 Đã xóa: <b>{t["title"]}</b>'

def cmd_ds(tasks):
    if not tasks:
        return '📋 Chưa có kế hoạch nào.'
    STATUS_ICON = {'Hoàn thành': '✅', 'Đang thực hiện': '🔵', 'Chưa bắt đầu': '⏳'}
    lines = ['📋 <b>Danh sách kế hoạch:</b>\n']
    for t in tasks:
        icon = STATUS_ICON.get(t['status'], '•')
        lines.append(f'{icon} <b>{t["title"]}</b>')
        lines.append(f'   {t["start"]} → {t["end"]}  [{t["priority"]}]  {t["progress"]}%')
    return '\n'.join(lines)

# ── Main ──────────────────────────────────────────────────────────────
def main():
    offset  = load_offset()
    updates = get_updates(offset)
    if not updates.get('ok'):
        print('Telegram API error:', updates)
        sys.exit(1)
    results = updates.get('result', [])
    if not results:
        print('No new messages.')
        return
    tasks   = load()
    changed = False
    new_off = offset
    for upd in results:
        new_off = upd['update_id'] + 1
        msg     = upd.get('message', {})
        chat_id = msg.get('chat', {}).get('id')
        text    = (msg.get('text') or '').strip()
        if chat_id != ALLOWED_CHAT:
            print(f'Ignored message from chat {chat_id}')
            continue
        if not text:
            continue
        cmd = text.split()[0].lower().split('@')[0]
        if cmd in ('/them', '/add'):
            new_tasks, reply = cmd_them(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks
                changed = True
            send(chat_id, reply)
        elif cmd in ('/done', '/xong'):
            new_tasks, reply = cmd_done(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks
                changed = True
            send(chat_id, reply)
        elif cmd == '/update':
            new_tasks, reply = cmd_update(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks
                changed = True
            send(chat_id, reply)
        elif cmd in ('/xoa', '/del', '/delete'):
            new_tasks, reply = cmd_xoa(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks
                changed = True
            send(chat_id, reply)
        elif cmd in ('/ds', '/list', '/danhsach'):
            send(chat_id, cmd_ds(tasks))
        elif cmd in ('/help', '/start', '/huongdan'):
            send(chat_id, HELP_TEXT)
        else:
            send(chat_id, f'❓ Lệnh không hợp lệ: <code>{cmd}</code>\nGửi /help để xem hướng dẫn.')
    if changed:
        save(tasks)
        print(f'actionplan.json updated with {len(tasks)} tasks.')
    else:
        print('No data changes.')
    save_offset(new_off)

if __name__ == '__main__':
    main()
