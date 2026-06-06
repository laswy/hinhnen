import json
import os
import sys
import requests
import random
import string
from datetime import datetime

BOT_TOKEN    = os.environ['ZALO_BOT_TOKEN']
ALLOWED_CHAT = os.environ['ZALO_CHAT_ID']   # group_id hoặc user_id được phép dùng lệnh
OFFSET_FILE  = '.github/zalo_offset.txt'
DATA_FILE    = 'actionplan.json'
NOTES_FILE   = 'calendar_notes.json'

BASE_URL = f'https://bot-api.zapps.me/bot{BOT_TOKEN}'

# ── Zalo Bot helpers ──────────────────────────────────────────────────
# API: POST https://bot-api.zapps.me/bot{token}/{endpoint}
# getUpdates trả về 1 update tại một thời điểm (không phải list)
# Cần loop tăng offset để lấy hết

def get_update(offset=None):
    """Lấy 1 update từ server. Trả về dict hoặc {} nếu không có gì mới."""
    data = {'timeout': 0}
    if offset is not None:
        data['offset'] = offset
    r = requests.post(f'{BASE_URL}/getUpdates', json=data, timeout=20)
    return r.json()

def fetch_all_updates(start_offset):
    """Loop lấy tất cả updates mới, trả về list các raw dict."""
    updates = []
    offset = start_offset
    while True:
        result = get_update(offset)
        if not result or not result.get('message'):
            break
        updates.append(result)
        update_id = result.get('update_id')
        if update_id is None:
            break
        offset = update_id + 1
    return updates, offset

def send(chat_id, text):
    requests.post(
        f'{BASE_URL}/sendMessage',
        json={'chat_id': str(chat_id), 'text': text},
        timeout=15
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
    return json.loads(content) if content else []

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
Bot Ke Hoach - Huong dan:

Them ke hoach:
/them Ten | Tu ngay | Den ngay | Uu tien | Phu trach
Vi du: /them HOP TONG KET | 2026-07-01 | 2026-07-31 | A | ANH

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
Ngay: YYYY-MM-DD (vd: 2026-07-01)
Huong dan: /help"""

def cmd_them(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 3:
        return None, 'Thieu thong tin.\nDinh dang: /them Ten | Tu ngay | Den ngay | Uu tien | Phu trach'
    for dt_str in [parts[1], parts[2]]:
        try:
            datetime.strptime(dt_str, '%Y-%m-%d')
        except ValueError:
            return None, f'Ngay sai dinh dang: {dt_str}\nDung: YYYY-MM-DD (vd: 2026-07-01)'
    prio = parts[3].upper() if len(parts) > 3 else 'B'
    if prio not in ('A', 'B', 'C'):
        prio = 'B'
    task = {
        'id':       gen_id(),
        'title':    parts[0].upper(),
        'category': 'Other',
        'priority': prio,
        'status':   'Chua bat dau',
        'assignee': parts[4] if len(parts) > 4 else '',
        'start':    parts[1],
        'end':      parts[2],
        'progress': 0,
        'notes':    parts[5] if len(parts) > 5 else '',
        'result':   ''
    }
    tasks.append(task)
    reply = (f'Da them ke hoach!\n\n'
             f'{task["title"]}\n'
             f'{task["start"]} -> {task["end"]}\n'
             f'Uu tien: {task["priority"]}  |  Phu trach: {task["assignee"] or "—"}\n'
             f'ID: {task["id"]}')
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
        return None, f'Khong tim thay: {keyword}'
    t['status'] = 'Hoan thanh'
    t['progress'] = 100
    return tasks, f'Hoan thanh: {t["title"]}'

def cmd_update(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 2 or not parts[1].isdigit():
        return None, 'Dinh dang: /update ten hoac ID | 75'
    t = find_task(tasks, parts[0])
    if not t:
        return None, f'Khong tim thay: {parts[0]}'
    pct = max(0, min(100, int(parts[1])))
    t['progress'] = pct
    if pct == 100:
        t['status'] = 'Hoan thanh'
    elif pct > 0:
        t['status'] = 'Dang thuc hien'
    return tasks, f'Cap nhat {t["title"]}: {pct}%'

def cmd_xoa(text, tasks):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    t = find_task(tasks, keyword)
    if not t:
        return None, f'Khong tim thay: {keyword}'
    tasks.remove(t)
    return tasks, f'Da xoa: {t["title"]}'

def cmd_ghinhu(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2:
        return None, 'Dinh dang: /ghichu YYYY-MM-DD | Noi dung'
    date_str = parts[0].strip()
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None, f'Ngay sai dinh dang: {date_str}\nDung: YYYY-MM-DD'
    note = {'id': 'note' + gen_id(), 'date': date_str, 'text': parts[1].strip()}
    notes.append(note)
    return notes, (f'Da them ghi chu!\n\n'
                   f'Ngay: {date_str}\n'
                   f'Noi dung: {note["text"]}\n'
                   f'ID: {note["id"]}')

def cmd_xoanhu(text, notes):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    found = next((n for n in notes if n['id'] == keyword), None)
    if not found:
        return None, f'Khong tim thay ghi chu ID: {keyword}'
    notes.remove(found)
    return notes, f'Da xoa ghi chu: {found["text"][:50]}'

def cmd_xemghu(text, notes):
    date_str = text.split(' ', 1)[1].strip() if ' ' in text else ''
    day_notes = [n for n in notes if n['date'] == date_str]
    if not day_notes:
        return f'Khong co ghi chu nao vao ngay {date_str}.'
    lines = [f'Ghi chu ngay {date_str}:\n']
    for n in day_notes:
        lines.append(f'• {n["text"]}  [{n["id"]}]')
    return '\n'.join(lines)

def cmd_sua(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 3:
        return None, 'Dinh dang:\n/sua ten hoac ID | truong | gia tri moi\nTruong: ten | start | end | priority | nguoiphutrach | ghichu'
    t = find_task(tasks, parts[0])
    if not t:
        return None, f'Khong tim thay: {parts[0]}'
    field_map = {'ten': 'title', 'start': 'start', 'end': 'end',
                 'priority': 'priority', 'nguoiphutrach': 'assignee', 'ghichu': 'notes'}
    field = parts[1].lower()
    if field not in field_map:
        return None, f'Truong khong hop le: {parts[1]}\nTruong hop le: ten | start | end | priority | nguoiphutrach | ghichu'
    value = parts[2]
    key = field_map[field]
    if field in ('start', 'end'):
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None, f'Ngay sai dinh dang: {value}\nDung: YYYY-MM-DD'
    if field == 'priority':
        value = value.upper()
        if value not in ('A', 'B', 'C'):
            return None, 'Uu tien phai la A, B hoac C'
    if field == 'ten':
        value = value.upper()
    t[key] = value
    return tasks, f'Da cap nhat {t["title"]}\n{parts[1]}: {value}'

def cmd_suaghi(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2:
        return None, 'Dinh dang: /suaghi ID | Noi dung moi'
    found = next((n for n in notes if n['id'] == parts[0]), None)
    if not found:
        return None, f'Khong tim thay ghi chu ID: {parts[0]}'
    found['text'] = parts[1]
    return notes, (f'Da cap nhat ghi chu!\n'
                   f'Ngay: {found["date"]}\n'
                   f'Noi dung moi: {found["text"]}\n'
                   f'ID: {found["id"]}')

def cmd_ds(tasks):
    if not tasks:
        return 'Chua co ke hoach nao.'
    STATUS = {'Hoan thanh': '[Xong]', 'Dang thuc hien': '[Dang lam]', 'Chua bat dau': '[Chua]'}
    lines = ['Danh sach ke hoach:\n']
    for t in tasks:
        icon = STATUS.get(t.get('status', ''), '•')
        lines.append(f'{icon} {t["title"]}')
        lines.append(f'   {t["start"]} -> {t["end"]}  [{t["priority"]}]  {t["progress"]}%')
    return '\n'.join(lines)

# ── Main ──────────────────────────────────────────────────────────────

def main():
    start_offset  = load_offset()
    updates, new_off = fetch_all_updates(start_offset)

    if not updates:
        print('Khong co tin nhan moi.')
        return

    tasks         = load()
    notes         = load_notes()
    changed       = False
    notes_changed = False

    for raw in updates:
        msg     = raw.get('message', {})
        chat_id = str(msg.get('chat', {}).get('id', ''))
        text    = (msg.get('text') or '').strip()

        if chat_id != str(ALLOWED_CHAT):
            print(f'Bo qua tin nhan tu chat {chat_id}')
            continue
        if not text:
            continue

        cmd = text.split()[0].lower().split('@')[0]
        print(f'Xu ly lenh: {cmd} tu chat {chat_id}')

        if cmd in ('/them', '/add'):
            new_tasks, reply = cmd_them(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks; changed = True
            send(chat_id, reply)

        elif cmd in ('/done', '/xong'):
            new_tasks, reply = cmd_done(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks; changed = True
            send(chat_id, reply)

        elif cmd == '/update':
            new_tasks, reply = cmd_update(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks; changed = True
            send(chat_id, reply)

        elif cmd in ('/xoa', '/del', '/delete'):
            new_tasks, reply = cmd_xoa(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks; changed = True
            send(chat_id, reply)

        elif cmd in ('/ds', '/list', '/danhsach'):
            send(chat_id, cmd_ds(tasks))

        elif cmd in ('/sua', '/edit'):
            new_tasks, reply = cmd_sua(text, tasks)
            if new_tasks is not None:
                tasks = new_tasks; changed = True
            send(chat_id, reply)

        elif cmd in ('/suaghi', '/editnote'):
            new_notes, reply = cmd_suaghi(text, notes)
            if new_notes is not None:
                notes = new_notes; notes_changed = True
            send(chat_id, reply)

        elif cmd in ('/ghichu', '/addnote'):
            new_notes, reply = cmd_ghinhu(text, notes)
            if new_notes is not None:
                notes = new_notes; notes_changed = True
            send(chat_id, reply)

        elif cmd in ('/xoaghichu', '/delnote'):
            new_notes, reply = cmd_xoanhu(text, notes)
            if new_notes is not None:
                notes = new_notes; notes_changed = True
            send(chat_id, reply)

        elif cmd in ('/xemghichu', '/viewnote'):
            send(chat_id, cmd_xemghu(text, notes))

        elif cmd in ('/help', '/start', '/huongdan'):
            send(chat_id, HELP_TEXT)

        else:
            send(chat_id, f'Lenh khong hop le: {cmd}\nGui /help de xem huong dan.')

    if changed:
        save(tasks)
        print(f'actionplan.json cap nhat: {len(tasks)} ke hoach.')
    else:
        print('Khong co thay doi ke hoach.')

    if notes_changed:
        save_notes(notes)
        print(f'calendar_notes.json cap nhat: {len(notes)} ghi chu.')
    else:
        print('Khong co thay doi ghi chu.')

    save_offset(new_off)
    print(f'Offset moi: {new_off}')

if __name__ == '__main__':
    main()
