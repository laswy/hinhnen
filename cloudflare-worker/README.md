# Zalo Bot — Cloudflare Worker (webhook)

Thay cho cách polling cũ (GitHub Actions chạy 2h/lần, hay timeout vì server Zalo
ở Việt Nam còn runner ở Mỹ), Worker này nhận tin nhắn **tức thời** qua webhook:

```
Zalo  ──webhook──▶  Cloudflare Worker  ──GitHub API──▶  commit JSON
  ▲                        │
  └────── tra loi ─────────┘
```

Commit vào repo sẽ tự kích hoạt workflow deploy → cập nhật trang.

## Cần chuẩn bị

1. **Tài khoản Cloudflare** (miễn phí): https://dash.cloudflare.com/sign-up
2. **GitHub Personal Access Token** (fine-grained):
   - Vào https://github.com/settings/personal-access-tokens/new
   - Repository access → chỉ chọn `laswy/hinhnen`
   - Permissions → Repository → **Contents: Read and write**
   - Tạo và copy token (dạng `github_pat_...`)
3. **Node.js** trên máy (để chạy `npx wrangler`): https://nodejs.org

## Các bước triển khai

Mở terminal (PowerShell trên Windows), `cd` vào thư mục này:

```bash
cd cloudflare-worker
```

### 1. Đăng nhập Cloudflare

```bash
npx wrangler login
```

### 2. Đặt các biến bí mật

Chạy từng lệnh, dán giá trị khi được hỏi:

```bash
npx wrangler secret put ZALO_BOT_TOKEN     # token bot Zalo (id:secret)
npx wrangler secret put ZALO_CHAT_ID       # id nhom/chat duoc phep
npx wrangler secret put GITHUB_TOKEN       # GitHub PAT o tren
npx wrangler secret put WEBHOOK_SECRET     # tu dat 1 chuoi ngau nhien, vd: k7Hq2mZ9xR
```

> `GITHUB_REPO` và `GITHUB_BRANCH` đã có sẵn trong `wrangler.toml`, không cần đặt.

### 3. Deploy

```bash
npx wrangler deploy
```

Sau khi xong, Cloudflare in ra URL dạng:

```
https://zalo-bot.<ten-cua-ban>.workers.dev
```

### 4. Đăng ký webhook với Zalo

Dùng script kèm theo (thay giá trị thật):

```bash
ZALO_BOT_TOKEN="3160...:Uzh..." \
WORKER_URL="https://zalo-bot.<ten-cua-ban>.workers.dev" \
WEBHOOK_SECRET="k7Hq2mZ9xR" \
bash set_webhook.sh
```

`WEBHOOK_SECRET` phải **trùng** với giá trị đã đặt ở bước 2.

## Xong!

Vào nhóm Zalo, gõ `/help`. Bot sẽ trả lời ngay lập tức. Thử:

```
/them HOP TONG KET | 2026-06-10 | 2026-06-30 | A | ANH
/ds
/xoa HOP TONG KET
```

Mỗi lệnh sẽ commit vào GitHub và trang web cập nhật sau ~1 phút.

## Lấy ZALO_CHAT_ID

Nếu chưa biết id nhóm: tạm thời thêm dòng debug, hoặc nhắn cho bot rồi xem log
Worker bằng `npx wrangler tail` — nó sẽ in chat id của tin nhắn gửi tới.

## Quay lại polling (nếu cần)

```bash
ZALO_BOT_TOKEN="..." bash set_webhook.sh delete
```

## Xem log thời gian thực

```bash
npx wrangler tail
```
