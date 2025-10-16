# Image Recovery Bot API

API để phục hồi ảnh sử dụng ComfyUI với khả năng upload lên Firebase Storage và Telegram Bot.

## Tính năng

- 🖼️ Phục hồi ảnh sử dụng ComfyUI
- ☁️ Upload kết quả lên Firebase Storage
- 🔄 API RESTful với FastAPI
- 📱 Telegram Bot để tương tác dễ dàng
- 📊 Theo dõi job processing
- 🛡️ Validation đầu vào và xử lý lỗi
- 📝 Logging chi tiết

## Yêu cầu hệ thống

- Python 3.8+
- ComfyUI đã được cài đặt và chạy
- Firebase Storage credentials
- Telegram Bot Token (để sử dụng Telegram Bot)

## Cài đặt

### Cài đặt nhanh (Khuyến nghị)

```bash
python setup_complete.py
```

Script này sẽ tự động:
- Kiểm tra Python version
- Cài đặt dependencies
- Tạo cấu trúc thư mục
- Thiết lập file .env
- Hướng dẫn cấu hình storage và bot

### Cài đặt thủ công

1. Clone repository và cài đặt dependencies:

```bash
pip install -r requirements.txt
```

2. Sao chép file cấu hình:

```bash
cp env.example .env
```

3. Cấu hình file `.env`:

```env
# ComfyUI Configuration
COMFYUI_SERVER_URL=http://localhost:8188
COMFYUI_CLIENT_ID=your_client_id

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE_MB=10
ALLOWED_EXTENSIONS=jpg,jpeg,png,webp
LOG_LEVEL=INFO

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=http://localhost:8000
```

## Cấu hình Firebase Storage

**Hướng dẫn chi tiết:** [docs/firebase_setup.md](docs/firebase_setup.md)

### Các bước thiết lập:

1. **Tạo Firebase project:**
   - Vào https://console.firebase.google.com/
   - Tạo project mới

2. **Kích hoạt Firebase Storage:**
   - Chọn Storage trong menu
   - Nhấn "Get started"
   - Chọn region (ví dụ: asia-southeast1)

3. **Tạo Service Account:**
   - Vào Project Settings → Service accounts
   - Tạo service account mới
   - Download file JSON credentials

4. **Cấu hình trong dự án:**
   ```env
   FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json
   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
   ```

### Test Firebase Storage

```bash
# Test kết nối Firebase
python scripts/setup_storage.py

# Demo upload file
python scripts/demo_storage.py
```

## Chạy ứng dụng

### Chạy API server

```bash
python main.py
```

Hoặc sử dụng uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API sẽ chạy tại: `http://localhost:8000`

### Chạy Telegram Bot

1. **Thiết lập Telegram Bot:**
```bash
python scripts/setup_telegram_bot.py
```

2. **Chạy bot:**
```bash
python run_bot.py
```

### Chạy cả API và Bot cùng lúc

```bash
python run_all.py
```

## API Documentation

### Swagger UI
Truy cập: `http://localhost:8000/docs`

### ReDoc
Truy cập: `http://localhost:8000/redoc`

## API Endpoints

### 1. Health Check

```http
GET /
GET /health
```

### 2. Phục hồi ảnh (Upload File)

```http
POST /recover-image
```

**Parameters:**
- `image`: File ảnh cần phục hồi (multipart/form-data)
- `prompt`: Mô tả chi tiết về việc phục hồi ảnh
- `strength`: Độ mạnh của việc phục hồi (0.0-1.0, mặc định: 0.8)
- `steps`: Số bước xử lý (1-100, mặc định: 20)
- `guidance_scale`: Tỷ lệ hướng dẫn (1.0-20.0, mặc định: 7.5)
- `seed`: Seed để tạo ảnh (tùy chọn)

### 3. Phục hồi ảnh (Từ URL)

```http
POST /recover-image-from-url
```

**Parameters:**
- `image_url`: URL của ảnh cần phục hồi
- `prompt`: Mô tả chi tiết về việc phục hồi ảnh
- `strength`: Độ mạnh của việc phục hồi (0.0-1.0, mặc định: 0.8)
- `steps`: Số bước xử lý (1-100, mặc định: 20)
- `guidance_scale`: Tỷ lệ hướng dẫn (1.0-20.0, mặc định: 7.5)
- `seed`: Seed để tạo ảnh (tùy chọn)

**Response (cả hai endpoint):**
```json
{
  "success": true,
  "message": "Phục hồi ảnh thành công",
  "result_image_url": "https://storage.googleapis.com/...",
  "job_id": "uuid-string",
  "processing_time": 45.67
}
```

### 4. Theo dõi Job

```http
GET /job/{job_id}
GET /jobs
DELETE /job/{job_id}
```

## Ví dụ sử dụng

### Sử dụng curl

**Phục hồi ảnh từ file:**
```bash
curl -X POST "http://localhost:8000/recover-image" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@damaged_image.jpg" \
  -F "prompt=restore and enhance this damaged image, fix scratches and improve quality" \
  -F "strength=0.8" \
  -F "steps=25" \
  -F "guidance_scale=8.0"
```

**Phục hồi ảnh từ URL:**
```bash
curl -X POST "http://localhost:8000/recover-image-from-url" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/damaged_image.jpg",
    "prompt": "restore and enhance this damaged image, fix scratches and improve quality",
    "strength": 0.8,
    "steps": 25,
    "guidance_scale": 8.0
  }'
```

### Sử dụng Python

**Phục hồi ảnh từ file:**
```python
import requests

url = "http://localhost:8000/recover-image"

files = {
    'image': open('damaged_image.jpg', 'rb')
}

data = {
    'prompt': 'restore and enhance this damaged image, fix scratches and improve quality',
    'strength': 0.8,
    'steps': 25,
    'guidance_scale': 8.0
}

response = requests.post(url, files=files, data=data)
result = response.json()

if result['success']:
    print(f"Ảnh đã được phục hồi: {result['result_image_url']}")
else:
    print(f"Lỗi: {result['message']}")
```

**Phục hồi ảnh từ URL:**
```python
import requests

url = "http://localhost:8000/recover-image-from-url"

data = {
    'image_url': 'https://example.com/damaged_image.jpg',
    'prompt': 'restore and enhance this damaged image, fix scratches and improve quality',
    'strength': 0.8,
    'steps': 25,
    'guidance_scale': 8.0
}

response = requests.post(url, json=data)
result = response.json()

if result['success']:
    print(f"Ảnh đã được phục hồi: {result['result_image_url']}")
else:
    print(f"Lỗi: {result['message']}")
```

### Sử dụng JavaScript

**Phục hồi ảnh từ file:**
```javascript
const formData = new FormData();
formData.append('image', imageFile);
formData.append('prompt', 'restore and enhance this damaged image');
formData.append('strength', '0.8');
formData.append('steps', '25');
formData.append('guidance_scale', '8.0');

fetch('http://localhost:8000/recover-image', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Ảnh đã được phục hồi:', data.result_image_url);
    } else {
        console.error('Lỗi:', data.message);
    }
});
```

**Phục hồi ảnh từ URL:**
```javascript
const data = {
    image_url: 'https://example.com/damaged_image.jpg',
    prompt: 'restore and enhance this damaged image',
    strength: 0.8,
    steps: 25,
    guidance_scale: 8.0
};

fetch('http://localhost:8000/recover-image-from-url', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Ảnh đã được phục hồi:', data.result_image_url);
    } else {
        console.error('Lỗi:', data.message);
    }
});
```

## Sử dụng Telegram Bot

### Tạo Telegram Bot

1. **Tìm @BotFather trên Telegram**
2. **Gửi lệnh `/newbot`**
3. **Đặt tên bot (ví dụ: Image Recovery Bot)**
4. **Đặt username (phải kết thúc bằng 'bot')**
5. **Copy token được cung cấp**

### Thiết lập Bot

```bash
python scripts/setup_telegram_bot.py
```

Script sẽ hướng dẫn bạn:
- Nhập token bot
- Test kết nối
- Cấu hình webhook (tùy chọn)

### Sử dụng Bot

1. **Tìm bot trên Telegram và gửi `/start`**
2. **Gửi ảnh cần phục hồi**
3. **Nhập mô tả chi tiết (prompt)**
4. **Chờ kết quả (30-60 giây)**
5. **Nhận ảnh đã được phục hồi**

### Lệnh Bot

- `/start` - Bắt đầu và hiển thị menu
- `/help` - Hướng dẫn chi tiết
- `/settings` - Cài đặt tham số mặc định
- `/status` - Kiểm tra trạng thái API

### Ví dụ sử dụng

```
User: /start
Bot: Chào mừng đến với Image Recovery Bot! Gửi ảnh để bắt đầu.

User: [Gửi ảnh]
Bot: Ảnh đã được nhận! Bây giờ hãy gửi mô tả về việc phục hồi ảnh.

User: restore this damaged photo, fix scratches and improve colors
Bot: Đang xử lý ảnh... Quá trình này có thể mất 30-60 giây.

Bot: [Gửi ảnh đã phục hồi] Phục hồi ảnh thành công!
```

## Cấu trúc dự án

```
recover-image-bot/
├── main.py                    # FastAPI server chính
├── models.py                  # Pydantic models
├── comfyui_client.py          # ComfyUI client
├── storage_service.py         # Cloud storage services
├── telegram_bot.py            # Telegram Bot
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── env.example               # Environment variables example
├── README.md                 # Documentation
├── run_bot.py                # Script chạy Telegram Bot
├── run_all.py                # Script chạy cả API và Bot
├── input_images/             # Thư mục chứa ảnh đầu vào
├── output_images/            # Thư mục chứa ảnh đầu ra
├── scripts/                  # Scripts hỗ trợ
│   ├── setup.py             # Thiết lập dự án
│   ├── setup_telegram_bot.py # Thiết lập Telegram Bot
│   ├── test_api.py          # Test API
│   └── demo_url.py          # Demo API với URL
├── temp/                    # Thư mục tạm
└── workflows/               # ComfyUI workflows
```

## Troubleshooting

### ComfyUI không kết nối được

1. Kiểm tra ComfyUI đã chạy: `http://localhost:8188`
2. Kiểm tra `COMFYUI_SERVER_URL` trong file `.env`
3. Kiểm tra firewall và network

### Storage service lỗi

1. Kiểm tra credentials file tồn tại
2. Kiểm tra permissions của service account
3. Kiểm tra bucket name đúng

### Memory issues

1. Giảm `MAX_FILE_SIZE_MB` trong config
2. Xóa các job cũ khỏi memory
3. Sử dụng Redis thay vì in-memory storage

### Telegram Bot không hoạt động

1. **Kiểm tra token bot:**
   ```bash
   python scripts/setup_telegram_bot.py
   ```

2. **Kiểm tra API đang chạy:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Kiểm tra log bot:**
   - Xem console output khi chạy bot
   - Kiểm tra file log nếu có

4. **Test bot manually:**
   - Gửi `/start` cho bot trên Telegram
   - Kiểm tra bot có phản hồi không

5. **Lỗi thường gặp:**
   - Token không đúng: Tạo bot mới với @BotFather
   - API không chạy: Chạy `python main.py` trước
   - Firewall: Mở port 8000
   - Network: Kiểm tra kết nối internet

## Development

### Chạy tests

```bash
pytest tests/
```

### Code formatting

```bash
black .
isort .
```

### Type checking

```bash
mypy .
```

## License

MIT License

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request
