import asyncio
import json
import os
import random
import string
import sys
from datetime import datetime

import zalo_bot

BOT_TOKEN    = os.environ['ZALO_BOT_TOKEN']
ALLOWED_CHAT = os.environ['ZALO_CHAT_ID']
OFFSET_FILE  = '.github/zalo_offset.txt'
DATA_FILE    = 'actionplan.json'
NOTES_FILE   = 'calendar_notes.json'

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
Huong dan: /help"""

def find_task(tasks, keyword):
    kw = keyword.lower().strip()
    for t in tasks:
        if t['id'] == kw:
            return t
    for t in tasks:
        if kw in t['title'].lower():
            return t
    return None

def cmd_them(text, tasks):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|')]
    if len(parts) < 3:
        return None, 'Thieu thong tin.\nDinh dang: /them Ten | Tu ngay | Den ngay | Uu tien | Phu trach'
    for dt_str in [parts[1], parts[2]]:
        try:
            datetime.strptime(dt_str, '%Y-%m-%d')
        except ValueError:
            return None, f'Ngay sai dinh dang: {dt_str}\nDung: YYYY-MM-DD'
    prio = parts[3].upper() if len(parts) > 3 else 'B'
    if prio not in ('A', 'B', 'C'):
        prio = 'B'
    task = {
        'id': gen_id(), 'title': parts[0].upper(), 'category': 'Other',
        'priority': prio, 'status': 'Chua bat dau',
        'assignee': parts[4] if len(parts) > 4 else '',
        'start': parts[1], 'end': parts[2], 'progress': 0,
        'notes': parts[5] if len(parts) > 5 else '', 'result': ''
    }
    tasks.append(task)
    return tasks, (f'Da them ke hoach!\n\n{task["title"]}\n'
                   f'{task["start"]} -> {task["end"]}\n'
                   f'Uu tien: {task["priority"]}  |  Phu trach: {task["assignee"] or "—"}\n'
                   f'ID: {task["id"]}')

def cmd_done(text, tasks):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    t = find_task(tasks, keyword)
    if not t:
        return None, f'Khong tim thay: {keyword}'
    t['status'] = 'Hoan thanh'; t['progress'] = 100
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
    if pct == 100: t['status'] = 'Hoan thanh'
    elif pct > 0: t['status'] = 'Dang thuc hien'
    return tasks, f'Cap nhat {t["title"]}: {pct}%'

def cmd_xoa(text, tasks):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    t = find_task(tasks, keyword)
    if not t:
        return None, f'Khong tim thay: {keyword}'
    tasks.remove(t)
    return tasks, f'Da xoa: {t["title"]}'

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
        return None, f'Truong khong hop le: {parts[1]}'
    value = parts[2]
    if field in ('start', 'end'):
        try: datetime.strptime(value, '%Y-%m-%d')
        except ValueError: return None, f'Ngay sai dinh dang: {value}'
    if field == 'priority':
        value = value.upper()
        if value not in ('A', 'B', 'C'): return None, 'Uu tien phai la A, B hoac C'
    if field == 'ten': value = value.upper()
    t[field_map[field]] = value
    return tasks, f'Da cap nhat {t["title"]}\n{parts[1]}: {value}'

def cmd_ghinhu(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2:
        return None, 'Dinh dang: /ghichu YYYY-MM-DD | Noi dung'
    try: datetime.strptime(parts[0], '%Y-%m-%d')
    except ValueError: return None, f'Ngay sai dinh dang: {parts[0]}'
    note = {'id': 'note' + gen_id(), 'date': parts[0], 'text': parts[1].strip()}
    notes.append(note)
    return notes, f'Da them ghi chu!\nNgay: {note["date"]}\nNoi dung: {note["text"]}\nID: {note["id"]}'

def cmd_xoanhu(text, notes):
    keyword = text.split(' ', 1)[1].strip() if ' ' in text else ''
    found = next((n for n in notes if n['id'] == keyword), None)
    if not found: return None, f'Khong tim thay ghi chu ID: {keyword}'
    notes.remove(found)
    return notes, f'Da xoa ghi chu: {found["text"][:50]}'

def cmd_xemghu(text, notes):
    date_str = text.split(' ', 1)[1].strip() if ' ' in text else ''
    day_notes = [n for n in notes if n['date'] == date_str]
    if not day_notes: return f'Khong co ghi chu nao vao ngay {date_str}.'
    lines = [f'Ghi chu ngay {date_str}:\n']
    for n in day_notes:
        lines.append(f'• {n["text"]}  [{n["id"]}]')
    return '\n'.join(lines)

def cmd_suaghi(text, notes):
    body = text.split(' ', 1)[1] if ' ' in text else ''
    parts = [p.strip() for p in body.split('|', 1)]
    if len(parts) < 2: return None, 'Dinh dang: /suaghi ID | Noi dung moi'
    found = next((n for n in notes if n['id'] == parts[0]), None)
    if not found: return None, f'Khong tim thay ghi chu ID: {parts[0]}'
    found['text'] = parts[1]
    return notes, f'Da cap nhat ghi chu!\nNgay: {found["date"]}\nNoi dung moi: {found["text"]}\nID: {found["id"]}'

def cmd_ds(tasks):
    if not tasks: return 'Chua co ke hoach nao.'
    STATUS = {'Hoan thanh': '[Xong]', 'Dang thuc hien': '[Dang lam]', 'Chua bat dau': '[Chua]'}
    lines = ['Danh sach ke hoach:\n']
    for t in tasks:
        icon = STATUS.get(t.get('status', ''), '•')
        lines.append(f'{icon} {t["title"]}')
        lines.append(f'   {t["start"]} -> {t["end"]}  [{t["priority"]}]  {t["progress"]}%')
    return '\n'.join(lines)

# ── Async core ────────────────────────────────────────────────────────

async def run():
    offset = load_offset()
    raw_updates = []

    try:
        async with zalo_bot.Bot(BOT_TOKEN) as bot:
            print('Ket noi Zalo Bot thanh cong.')
            # Lấy hết updates mới
            while True:
                try:
                    update = await bot.get_update(offset=offset, timeout=30, limit=10)
                except Exception as e:
                    print(f'Zalo API loi: {e}')
                    break
                if update is None or update.message is None:
                    print('Khong co tin nhan moi.')
                    break
                raw_updates.append(update)
                uid = update.api_kwargs.get('update_id')
                if uid is not None:
                    offset = int(uid) + 1
                else:
                    break
    except Exception as e:
        print(f'Khong the ket noi Zalo Bot: {e}')
        return

    if not raw_updates:
        return

    tasks         = load()
    notes         = load_notes()
    changed       = False
    notes_changed = False

    async with zalo_bot.Bot(BOT_TOKEN) as bot:
        for update in raw_updates:
            msg     = update.message
            chat_id = msg.chat.id if msg and msg.chat else None
            text    = (msg.text or '').strip() if msg else ''

            print(f'Tin nhan tu chat {chat_id}: {text[:50]}')

            if str(chat_id) != str(ALLOWED_CHAT):
                print(f'Bo qua chat {chat_id}')
                continue
            if not text:
                continue

            cmd = text.split()[0].lower().split('@')[0]
            print(f'Xu ly lenh: {cmd}')

            async def reply(txt):
                try:
                    await bot.send_message(str(chat_id), txt)
                except Exception as e:
                    print(f'Loi gui tin: {e}')

            if cmd in ('/them', '/add'):
                new_tasks, r = cmd_them(text, tasks)
                if new_tasks is not None: tasks = new_tasks; changed = True
                await reply(r)
            elif cmd in ('/done', '/xong'):
                new_tasks, r = cmd_done(text, tasks)
                if new_tasks is not None: tasks = new_tasks; changed = True
                await reply(r)
            elif cmd == '/update':
                new_tasks, r = cmd_update(text, tasks)
                if new_tasks is not None: tasks = new_tasks; changed = True
                await reply(r)
            elif cmd in ('/xoa', '/del', '/delete'):
                new_tasks, r = cmd_xoa(text, tasks)
                if new_tasks is not None: tasks = new_tasks; changed = True
                await reply(r)
            elif cmd in ('/ds', '/list', '/danhsach'):
                await reply(cmd_ds(tasks))
            elif cmd in ('/sua', '/edit'):
                new_tasks, r = cmd_sua(text, tasks)
                if new_tasks is not None: tasks = new_tasks; changed = True
                await reply(r)
            elif cmd in ('/ghichu', '/addnote'):
                new_notes, r = cmd_ghinhu(text, notes)
                if new_notes is not None: notes = new_notes; notes_changed = True
                await reply(r)
            elif cmd in ('/xoaghichu', '/delnote'):
                new_notes, r = cmd_xoanhu(text, notes)
                if new_notes is not None: notes = new_notes; notes_changed = True
                await reply(r)
            elif cmd in ('/xemghichu', '/viewnote'):
                await reply(cmd_xemghu(text, notes))
            elif cmd in ('/suaghi', '/editnote'):
                new_notes, r = cmd_suaghi(text, notes)
                if new_notes is not None: notes = new_notes; notes_changed = True
                await reply(r)
            elif cmd in ('/help', '/start', '/huongdan'):
                await reply(HELP_TEXT)
            else:
                await reply(f'Lenh khong hop le: {cmd}\nGui /help de xem huong dan.')

    if changed:
        save(tasks)
        print(f'actionplan.json cap nhat: {len(tasks)} ke hoach.')
    if notes_changed:
        save_notes(notes)
        print(f'calendar_notes.json cap nhat: {len(notes)} ghi chu.')
    save_offset(offset)
    print(f'Offset moi: {offset}')

if __name__ == '__main__':
    asyncio.run(run())
