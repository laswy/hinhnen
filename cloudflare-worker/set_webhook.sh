#!/usr/bin/env bash
# Đăng ký webhook cho Zalo Bot.
# Cách dùng:
#   ZALO_BOT_TOKEN="id:secret" \
#   WORKER_URL="https://zalo-bot.<ten>.workers.dev" \
#   WEBHOOK_SECRET="chuoi-bi-mat" \
#   bash set_webhook.sh
#
# Hoặc xóa webhook (quay lại polling):
#   ZALO_BOT_TOKEN="id:secret" bash set_webhook.sh delete

set -euo pipefail

: "${ZALO_BOT_TOKEN:?Thieu ZALO_BOT_TOKEN}"
API="https://bot-api.zapps.me/bot${ZALO_BOT_TOKEN}"

if [[ "${1:-}" == "delete" ]]; then
  echo "Xoa webhook..."
  curl -s -X POST "${API}/deleteWebhook" -d "x=1"; echo
  exit 0
fi

: "${WORKER_URL:?Thieu WORKER_URL}"
: "${WEBHOOK_SECRET:?Thieu WEBHOOK_SECRET}"

FULL_URL="${WORKER_URL%/}/${WEBHOOK_SECRET}"
echo "Dang ky webhook: ${FULL_URL}"
curl -s -X POST "${API}/setWebhook" \
  --data-urlencode "url=${FULL_URL}" \
  --data-urlencode "secret_token=${WEBHOOK_SECRET}"
echo
echo "Kiem tra:"
curl -s -X POST "${API}/getWebhookInfo" -d "x=1"; echo
