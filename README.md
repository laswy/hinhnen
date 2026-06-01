# Hình Nền — VN–JP Wallpaper 1366×768

Wallpaper tương tác tĩnh chạy trên GitHub Pages, kích thước cố định 1366×768px.

**Live:** https://laswy.github.io/hinhnen/

---

## Tính năng

- **Lịch âm dương** — tháng hiện tại và tháng tới, hiển thị ngày âm lịch, ngày lễ, sự kiện công ty
- **Đồng hồ & thời tiết** — giờ Việt Nam thời gian thực, nhiệt độ Hà Nội
- **Gantt kế hoạch** — đọc từ `actionplan.json`, tự tính % tiến độ theo thời gian, đường đỏ ngày hôm nay
- **Crypto giá** — 3 tab: Yêu thích / Trending / Top Gainers, lấy dữ liệu từ CoinGecko, cập nhật mỗi 2 phút
- **Calendar sync** — chấm màu trên lịch cho ngày bắt đầu/kết thúc kế hoạch và ghi chú cá nhân; click vào ngày để xem popup chi tiết
- **Chế độ sáng/tối** — nút chuyển góc trên phải
- **Telegram Bot** — quản lý kế hoạch và ghi chú cá nhân qua Telegram, GitHub Actions tự động đồng bộ 2 tiếng/lần (7h–19h giờ VN)

---

## Cấu trúc file

```
index.html              # Wallpaper chính
actionplan.json         # Dữ liệu kế hoạch hành động
calendar_notes.json     # Ghi chú cá nhân theo ngày
.github/
  scripts/
    telegram_sync.py    # Bot Telegram
  workflows/
    deploy.yml          # GitHub Pages deploy
    telegram-sync.yml   # Cron đồng bộ Telegram
```

---

## Telegram Bot — Lệnh

### Kế hoạch hành động

| Lệnh | Mô tả |
|------|-------|
| `/them Tên \| YYYY-MM-DD \| YYYY-MM-DD \| A/B/C \| Người phụ trách` | Thêm kế hoạch mới |
| `/ds` | Xem danh sách kế hoạch |
| `/done tên hoặc ID` | Đánh dấu hoàn thành |
| `/update tên hoặc ID \| 75` | Cập nhật % tiến độ |
| `/xoa tên hoặc ID` | Xóa kế hoạch |

**Ưu tiên:** `A` (cao) · `B` (vừa) · `C` (thấp)  
**Định dạng ngày:** `YYYY-MM-DD` (vd: `2026-07-01`)

### Ghi chú lịch cá nhân

| Lệnh | Mô tả |
|------|-------|
| `/ghichu YYYY-MM-DD \| Nội dung` | Thêm ghi chú vào ngày |
| `/xemghichu YYYY-MM-DD` | Xem ghi chú của ngày |
| `/xoaghichu ID` | Xóa ghi chú theo ID |

---

## Cài đặt Telegram Bot

1. Tạo bot qua [@BotFather](https://t.me/BotFather), lấy token
2. Lấy Chat ID của nhóm/cá nhân
3. Vào repo → **Settings → Secrets and variables → Actions**, thêm:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Vào **Actions → Telegram Sync → Run workflow** để chạy thử ngay

---

## Màu chỉ báo trên lịch

| Màu | Ý nghĩa |
|-----|---------|
| 🟢 Teal | Ngày bắt đầu kế hoạch |
| 🟠 Cam | Ngày kết thúc kế hoạch |
| 🟡 Vàng | Có ghi chú cá nhân |
