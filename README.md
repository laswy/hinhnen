# Hình Nền — VN–JP Wallpaper

Trang web hình nền tương tác tĩnh, kích thước 1366×768px cho desktop và responsive cho mobile.

🌐 **Live:** https://laswy.github.io/hinhnen/

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| 🗓 **Lịch âm dương** | Hiển thị 2 tháng, âm lịch, ngày lễ, sự kiện công ty. Nút ◀ ▶ để chuyển tháng |
| 🕐 **Đồng hồ** | Giờ Việt Nam & Nhật Bản thời gian thực |
| 🌤 **Thời tiết** | Nhiệt độ, độ ẩm, gió tại Bắc Ninh (Open-Meteo) |
| 📋 **Gantt kế hoạch** | Đọc từ `actionplan.json`, tự tính % tiến độ theo thời gian, đường đỏ ngày hôm nay |
| 💹 **Giá Crypto** | 3 tab: Yêu thích / Trending / Top Gainers — CoinGecko, cập nhật mỗi 2 phút |
| 📌 **Calendar sync** | Chấm màu trên lịch cho ngày bắt đầu/kết thúc kế hoạch và ghi chú cá nhân |
| 💬 **Popup ghi chú** | Click vào ngày bất kỳ để xem kế hoạch và ghi chú trong ngày đó |
| 🌙 **Sáng / Tối** | Nút chuyển chế độ góc trên phải |
| 📱 **Mobile** | Layout responsive dọc: Đồng hồ → Thời tiết → Lịch → Kế hoạch → Crypto |

---

## Cấu trúc file

```
index.html                      # Ứng dụng chính
actionplan.json                 # Dữ liệu kế hoạch hành động
calendar_notes.json             # Ghi chú cá nhân theo ngày
.github/
  scripts/
    telegram_sync.py            # Bot Telegram xử lý lệnh
  workflows/
    deploy.yml                  # Tự động deploy lên GitHub Pages
    telegram-sync.yml           # Cron đồng bộ Telegram (mỗi 2 tiếng, 7h–19h VN)
```

---

## Telegram Bot

Bot tự động đồng bộ dữ liệu với repo qua GitHub Actions.

### Kế hoạch hành động

| Lệnh | Mô tả |
|------|-------|
| `/them Tên \| YYYY-MM-DD \| YYYY-MM-DD \| A/B/C \| Người phụ trách` | Thêm kế hoạch |
| `/ds` | Xem danh sách |
| `/done tên hoặc ID` | Đánh dấu hoàn thành |
| `/update tên hoặc ID \| 75` | Cập nhật % tiến độ |
| `/xoa tên hoặc ID` | Xóa kế hoạch |

**Ưu tiên:** `A` cao · `B` vừa · `C` thấp — **Ngày:** `YYYY-MM-DD`

### Ghi chú lịch

| Lệnh | Mô tả |
|------|-------|
| `/ghichu YYYY-MM-DD \| Nội dung` | Thêm ghi chú vào ngày |
| `/xemghichu YYYY-MM-DD` | Xem ghi chú trong ngày |
| `/xoaghichu ID` | Xóa ghi chú theo ID |

---

## Cài đặt Bot

1. Tạo bot qua [@BotFather](https://t.me/BotFather), lấy token
2. Lấy Chat ID (gửi tin nhắn rồi dùng `getUpdates` để lấy)
3. Vào repo → **Settings → Secrets and variables → Actions**, thêm:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Vào **Actions → Telegram Sync → Run workflow** để test ngay

---

## Chỉ báo màu trên lịch

| Màu | Ý nghĩa |
|-----|---------|
| 🟢 Teal `#64C8B4` | Ngày bắt đầu kế hoạch |
| 🟠 Cam `#FF9050` | Ngày kết thúc kế hoạch |
| 🟣 Tím `#B08CE0` | Có ghi chú cá nhân |

Hover vào chấm để xem nội dung. Các ngày trong khoảng hôm nay ±2 ngày hiển thị nội dung luôn mà không cần hover.
