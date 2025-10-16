# 🤖 Image Recovery Bot - Hướng dẫn sử dụng

## 📋 Tổng quan

Bot Telegram tự động phục hồi ảnh sử dụng AI với ComfyUI và Firebase Storage.

## ✅ Trạng thái hiện tại

- **API Server**: ✅ Hoạt động trên `http://localhost:8000`
- **Firebase Storage**: ✅ Đã cấu hình
- **Telegram Bot**: ✅ Sẵn sàng
- **ComfyUI Integration**: ✅ Hoạt động với 2 KSampler
- **Workflow Parameters**: ✅ Đã kiểm tra và cập nhật đúng

## 🚀 Cách sử dụng

### 1. Chạy API Server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Chạy Telegram Bot

```bash
python run_bot.py
```

### 3. Sử dụng Bot trên Telegram

1. **Tìm bot** trên Telegram bằng username
2. **Gửi lệnh** `/start`
3. **Gửi ảnh** cần phục hồi
4. **Nhập prompt** mô tả (ví dụ: "restore this damaged photo, fix scratches, improve colors")
5. **Chờ kết quả** (30-60 giây)

## 🔧 Cấu hình

### File .env
```env
# ComfyUI Configuration
COMFYUI_SERVER_URL=http://localhost:8188
COMFYUI_CLIENT_ID=comfyui_client

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE_MB=10
ALLOWED_EXTENSIONS=jpg,jpeg,png,webp

# Logging
LOG_LEVEL=INFO

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=http://localhost:8000
```

### Firebase Setup

1. **Tạo Firebase project** tại [Firebase Console](https://console.firebase.google.com/)
2. **Kích hoạt Storage**
3. **Tạo Service Account** và download JSON key
4. **Đặt file** `firebase-service-account.json` vào thư mục `credentials/`
5. **Cập nhật** `FIREBASE_STORAGE_BUCKET` trong `.env`

### Telegram Bot Setup

1. **Tạo bot** với [@BotFather](https://t.me/botfather)
2. **Lấy token** từ BotFather
3. **Cập nhật** `TELEGRAM_BOT_TOKEN` trong `.env`

## 📁 Cấu trúc dự án

```
recover-image-bot/
├── main.py                 # FastAPI server
├── telegram_bot.py         # Telegram bot
├── comfyui_client.py      # ComfyUI integration
├── storage_service.py      # Storage (Firebase/Local)
├── config.py              # Configuration
├── models.py              # Pydantic models
├── run_bot.py             # Bot runner
├── workflows/
│   └── Restore.json       # ComfyUI workflow
├── credentials/
│   └── firebase-service-account.json
├── output_images/         # Local storage output
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── SETUP_GUIDE.md        # Hướng dẫn này
```

## ⚙️ Workflow Parameters

Bot sử dụng workflow ComfyUI với:

### **2 KSampler:**
- **KSampler 1 (Flux)**: euler, normal scheduler
- **KSampler 2 (SDXL)**: dpmpp_2s_ancestral_cfg_pp, karras scheduler

### **3 ControlNet:**
- **ControlNet 1**: Strength 0.5, auto type
- **ControlNet 2**: Strength 0.2, canny/lineart type  
- **ControlNet 3**: Strength 0.1, depth type

### **Prompt Inputs:**
- **Main Prompt**: Node 60 (StringFunction)
- **Restore Prompt**: Node 71 (CLIPTextEncode)
- **Negative Prompt**: Node 7 (CLIPTextEncode)

## 🔌 API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Upload Image
```bash
curl -X POST "http://localhost:8000/recover-image" \
  -F "image=@your_image.jpg" \
  -F "prompt=restore this damaged photo" \
  -F "strength=0.8" \
  -F "steps=20" \
  -F "guidance_scale=7.5"
```

### Process from URL
```bash
curl -X POST "http://localhost:8000/recover-image-from-url" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "prompt": "restore this damaged photo",
    "strength": 0.8,
    "steps": 20,
    "guidance_scale": 7.5
  }'
```

## 🛠️ Troubleshooting

### Bot không phản hồi
- Kiểm tra token Telegram trong `.env`
- Đảm bảo chỉ chạy 1 instance bot
- Reset webhook: `python -c "import requests; requests.post(f'https://api.telegram.org/bot{TOKEN}/deleteWebhook')"`

### API lỗi
- Kiểm tra ComfyUI có chạy trên port 8188
- Kiểm tra Firebase credentials
- Xem logs trong terminal

### Storage lỗi
- Kiểm tra Firebase project và bucket
- Đảm bảo service account có quyền Storage
- Fallback sẽ dùng Local Storage

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra logs trong terminal
2. Test API endpoints trước
3. Kiểm tra cấu hình `.env`
4. Đảm bảo ComfyUI đang chạy

---

**Bot đã sẵn sàng sử dụng!** 🎉
