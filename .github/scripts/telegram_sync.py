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
NOTES_FILE    = 'calendar_notes.json'

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

def load_notes():
    if not os.path.exists(NOTES_FILE):
        return []
    with open(NOTES_FILE, encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    return json.loads(content)

def save_notes(notes):
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

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
<code>/them HỌP TỔNG KẾT | 2026-07-01 | 2026-07-31 | A | ANH</code>

✏️ <b>Sửa kế hoạch:</b>
/sua tên hoặc ID | trường | giá trị mới
Trường: <b>ten</b> · <b>start</b> · <b>end</b> · <b>priority</b> · <b>nguoiphutrach</b> · <b>ghichu</b>
<code>/sua HỌP TỔNG KẾT | end | 2026-08-15</code>

📋 <b>Xem danh sách:</b>  /ds
✅ <b>Đánh dấu xong:</b>  /done tên hoặc ID
📊 <b>Cập nhật %:</b>     /update tên hoặc ID | 75
🗑 <b>Xóa kế hoạch:</b>   /xoa tên hoặc ID

📝 <b>Thêm ghi chú lịch:</b>
<code>/ghichu 2026-07-01 | Nội dung ghi chú</code>
✏️ <b>Sửa ghi chú:</b>     /suaghi ID | Nội dung mới
🗑 <b>Xóa ghi chú:</b>     /xoaghichu ID
📅 <b>Xem ghi chú ngày:</b> /xemghichu YYYY-MM-DD

Ưu tiên: <b>A</b> (cao) · <b>B</b> (vừa) · <b>C</b> (thấp) — Ngày: <b>YYYY-MM-DD</b>
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

def cmd_ghinhu(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2:
        return None, '❌ Định dạng: <code>/ghichu YYYY-MM-DD | Nội dung</code>'
    date_str = parts[0].strip()
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None, f'❌ Ngày sai định dạng: <b>{date_str}</b>\nDùng: YYYY-MM-DD'
    note = {'id': 'note' + gen_id(), 'date': date_str, 'text': parts[1].strip()}
    notes.append(note)
    return notes, (f'📝 Đã thêm ghi chú!\n\n'
                   f'📅 Ngày: <b>{date_str}</b>\n'
                   f'💬 Nội dung: {note["text"]}\n'
                   f'🆔 ID: <code>{note["id"]}</code>')

def cmd_xoanhu(text, notes):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    found = next((n for n in notes if n['id'] == keyword), None)
    if not found:
        return None, f'❌ Không tìm thấy ghi chú ID: <code>{keyword}</code>'
    notes.remove(found)
    return notes, f'🗑 Đã xóa ghi chú: <b>{found["text"][:50]}</b>'

def cmd_xemghu(text, notes):
    date_str = text.split(' ', 1)[1].strip() if ' ' in text else ''
    day_notes = [n for n in notes if n['date'] == date_str]
    if not day_notes:
        return f'📅 Không có ghi chú nào vào ngày <b>{date_str}</b>.'
    lines = [f'📅 <b>Ghi chú ngày {date_str}:</b>\n']
    for n in day_notes:
        lines.append(f'• {n["text"]}  <code>[{n["id"]}]</code>')
    return '\n'.join(lines)

def cmd_sua(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 3:
        return None, '❌ Định dạng:\n<code>/sua tên hoặc ID | trường | giá trị mới</code>\nTrường: ten · start · end · priority · nguoiphutrach · ghichu'
    t = find_task(tasks, parts[0])
    if not t:
        return None, f'❌ Không tìm thấy: <b>{parts[0]}</b>'
    field_map = {'ten': 'title', 'start': 'start', 'end': 'end',
                 'priority': 'priority', 'nguoiphutrach': 'assignee', 'ghichu': 'notes'}
    field = parts[1].lower()
    if field not in field_map:
        return None, f'❌ Trường không hợp lệ: <b>{parts[1]}</b>\nTrường hợp lệ: ten · start · end · priority · nguoiphutrach · ghichu'
    value = parts[2]
    key = field_map[field]
    if field in ('start', 'end'):
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None, f'❌ Ngày sai định dạng: <b>{value}</b>\nDùng: YYYY-MM-DD'
    if field == 'priority':
        value = value.upper()
        if value not in ('A', 'B', 'C'):
            return None, '❌ Ưu tiên phải là A, B hoặc C'
    if field == 'ten':
        value = value.upper()
    t[key] = value
    return tasks, (f'✏️ Đã cập nhật <b>{t["title"]}</b>\n'
                   f'📝 {parts[1]}: <b>{value}</b>')

def cmd_suaghi(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2:
        return None, '❌ Định dạng: <code>/suaghi ID | Nội dung mới</code>'
    found = next((n for n in notes if n['id'] == parts[0]), None)
    if not found:
        return None, f'❌ Không tìm thấy ghi chú ID: <code>{parts[0]}</code>'
    found['text'] = parts[1]
    return notes, (f'✏️ Đã cập nhật ghi chú!\n'
                   f'📅 Ngày: <b>{found["date"]}</b>\n'
                   f'💬 Nội dung mới: {found["text"]}\n'
                   f'🆔 ID: <code>{found["id"]}</code>')

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
    tasks        = load()
    notes        = load_notes()
    changed      = False
    notes_changed = False
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
        elif cmd in ('/sua', '/edit'):
            new_tasks, reply = cmd_sua(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks
                changed = True
            send(chat_id, reply)
        elif cmd in ('/suaghi', '/editnote'):
            new_notes, reply = cmd_suaghi(text, notes)
            if new_notes is not None:
                notes = new_notes
                notes_changed = True
            send(chat_id, reply)
        elif cmd in ('/ghichu', '/addnote'):
            new_notes, reply = cmd_ghinhu(text, notes)
            if new_notes is not None:
                notes = new_notes
                notes_changed = True
            send(chat_id, reply)
        elif cmd in ('/xoaghichu', '/delnote'):
            new_notes, reply = cmd_xoanhu(text, notes)
            if new_notes is not None:
                notes = new_notes
                notes_changed = True
            send(chat_id, reply)
        elif cmd in ('/xemghichu', '/viewnote'):
            send(chat_id, cmd_xemghu(text, notes))
        elif cmd in ('/help', '/start', '/huongdan'):
            send(chat_id, HELP_TEXT)
        else:
            send(chat_id, f'❓ Lệnh không hợp lệ: <code>{cmd}</code>\nGửi /help để xem hướng dẫn.')
    if changed:
        save(tasks)
        print(f'actionplan.json updated with {len(tasks)} tasks.')
    else:
        print('No task changes.')
    if notes_changed:
        save_notes(notes)
        print(f'calendar_notes.json updated with {len(notes)} notes.')
    else:
        print('No note changes.')
    save_offset(new_off)

if __name__ == '__main__':
    main()
