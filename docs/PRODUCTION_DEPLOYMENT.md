# Hướng Dẫn Triển Khai Production — AI Inbox & Sales Management Platform

Tài liệu hướng dẫn chi tiết quy trình đóng gói và triển khai nền tảng **AI Inbox & Sales Management** lên máy chủ đám mây (Cloud VPS / Dedicated Server) dành cho môi trường sản xuất.

---

## 0. Mô hình chi phí thấp (Render Free + PostgreSQL)

Nếu dùng Render Free, không gắn Persistent Disk vì Render không hỗ trợ disk trên
free tier. Hãy tạo PostgreSQL (Supabase hoặc dịch vụ tương đương), sau đó thêm
`DATABASE_URL` vào Environment Variables của service. Backend tự động chọn
PostgreSQL khi biến này tồn tại; nếu không có, local development vẫn dùng SQLite.

Blueprint `render.yaml` đã để `DATABASE_URL` ở chế độ `sync: false` để secret
không bị commit vào Git.

---

## 1. Kiến Trúc Vận Hành

- **Runtime**: Python 3.13 (Thuần Standard Library: `http.server`, `sqlite3`, `json`, `urllib`).
- **Database**: SQLite3 Local-first với cơ chế Write-Ahead Logging (WAL) và isolation đa workspace (`workspaces`, `products`, `customers`, `conversations`, `messages`, `leads`).
- **Client Interfaces**:
  - Website Widget: `<script src="https://yourdomain.com/widget/chat_widget.js"></script>`
  - Admin Command Center: `https://yourdomain.com/admin`
  - Demo Storefront: `https://yourdomain.com/demo`
- **Integrations**:
  - Facebook Messenger: `POST /api/webhooks/facebook`
  - Telegram Alerts: Bắn thông báo ngay khi Lead đạt điểm HOT (>= 75) hoặc có số điện thoại.

---

## 2. Triển Khai Nhanh Bằng Docker Compose (Khuyên dùng)

### Bước 1: Chuẩn bị máy chủ VPS (Ubuntu 22.04 / 24.04 LTS)

Cài đặt Docker và Docker Compose:
```bash
sudo apt update && sudo apt install -y curl git ca-certificates
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Bước 2: Clone repository và tạo file cấu hình môi trường

```bash
git clone https://github.com/your-org/affiliate-automation.git /opt/ai-inbox
cd /opt/ai-inbox
```

Tạo file `.env`:
```env
PORT=8080
HOST=0.0.0.0
APP_BASE_URL=https://inbox.yourshop.vn

# Facebook Webhook (Tùy chọn)
FB_VERIFY_TOKEN=inbox_secret_token_2026
FB_PAGE_ACCESS_TOKEN=your_page_access_token_here

# Telegram Alerts (Tùy chọn)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-1001234567890
```

### Bước 3: Khởi động container

```bash
docker compose up -d --build
```

Kiểm tra trạng thái container và healthcheck:
```bash
docker ps
docker compose logs -f
```

Kiểm tra API Healthcheck trực tiếp:
```bash
curl http://localhost:8080/api/health
```
Phản hồi mẫu:
```json
{
  "status": "healthy",
  "service": "ai-inbox-sales-platform",
  "database": "connected",
  "timestamp": "2026-10-18T14:20:00.000000+00:00"
}
```

---

## 3. Cấu Hình Nginx Reverse Proxy & SSL (HTTPS)

### Bước 1: Cài đặt Nginx & Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### Bước 2: Tạo cấu hình Nginx cho tên miền

Tạo file `/etc/nginx/sites-available/ai-inbox.conf`:
```nginx
server {
    server_name inbox.yourshop.vn;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Hỗ trợ widget polling và streaming
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

Kích hoạt site:
```bash
sudo ln -s /etc/nginx/sites-available/ai-inbox.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Bước 3: Cấp chứng chỉ SSL Let's Encrypt miễn phí

```bash
sudo certbot --nginx -d inbox.yourshop.vn
```

---

## 4. Tích Hợp Kênh Bán Hàng

### A. Nhúng Chat Widget vào Website Bán Hàng
Chỉ cần dán thẻ sau vào trước thẻ `</body>` trên bất kỳ trang web nào (Shopify, WordPress, Haravan, LadiPage, hoặc custom HTML):
```html
<script src="https://inbox.yourshop.vn/widget/chat_widget.js"></script>
```

### B. Kết Nối Facebook Fanpage Webhook
1. Truy cập [Meta for Developers](https://developers.facebook.com/) -> App của bạn -> **Messenger** -> **Settings**.
2. Tại mục **Webhooks**:
   - **Callback URL**: `https://inbox.yourshop.vn/api/webhooks/facebook`
   - **Verify Token**: Giá trị cấu hình trong `FB_VERIFY_TOKEN` (ví dụ `inbox_secret_token_2026`).
3. Nhấn **Verify and Save**.
4. Chọn đăng ký (Subscribe) các trường: `messages`, `messaging_postbacks`.

### C. Cài Đặt Thông Báo HOT Lead qua Telegram
1. Chat với [@BotFather](https://t.me/BotFather) trên Telegram để tạo Bot mới và nhận `TELEGRAM_BOT_TOKEN`.
2. Tạo một nhóm chat nội bộ cho đội Telesale/Chăm sóc khách hàng, thêm Bot vào nhóm.
3. Lấy `TELEGRAM_CHAT_ID` của nhóm.
4. Cập nhật vào file `.env` và khởi động lại container:
```bash
docker compose up -d
```
Mỗi khi khách hàng chat chốt đơn, để lại số điện thoại hoặc điểm mua hàng >= 75, Telegram Bot sẽ lập tức bắn tin nhắn kèm link deep-link để nhân viên click vào chốt đơn ngay.

---

## 5. Sao Lưu Dữ Liệu Tự Động (SQLite Backup)

Tạo script sao lưu định kỳ `/opt/ai-inbox/scripts/backup_db.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/ai-inbox/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Sử dụng lệnh backup an toàn của SQLite mà không cần dừng ứng dụng
sqlite3 /opt/ai-inbox/data/inbox.db ".backup '$BACKUP_DIR/inbox_backup_$TIMESTAMP.db'"

# Giữ lại bản sao lưu trong 14 ngày gần nhất
find "$BACKUP_DIR" -type f -name "inbox_backup_*.db" -mtime +14 -delete
```

Phân quyền và cấu hình crontab chạy 3h sáng mỗi ngày:
```bash
chmod +x /opt/ai-inbox/scripts/backup_db.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/ai-inbox/scripts/backup_db.sh") | crontab -
```

---

## 6. Lệnh Vận Hành Thường Dùng

| Thao tác | Câu lệnh |
| :--- | :--- |
| **Xem logs thời gian thực** | `docker compose logs -f --tail=100` |
| **Khởi động lại hệ thống** | `docker compose restart` |
| **Cập nhật phiên bản mới** | `git pull && docker compose up -d --build` |
| **Kiểm tra trạng thái sức khỏe** | `curl -s http://localhost:8080/api/health \| jq .` |
| **Xuất danh sách Lead ra Excel** | Mở trình duyệt: `https://inbox.yourshop.vn/api/dashboard/leads/export` |
