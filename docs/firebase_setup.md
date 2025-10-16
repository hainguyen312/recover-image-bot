# Hướng dẫn thiết lập Firebase Storage

## Bước 1: Tạo Firebase Project

1. **Truy cập Firebase Console:**
   - Vào https://console.firebase.google.com/
   - Đăng nhập bằng tài khoản Google

2. **Tạo project mới:**
   - Nhấn "Create a project" hoặc "Add project"
   - Nhập tên project (ví dụ: `image-recovery-bot`)
   - Chọn có/không bật Google Analytics (tùy chọn)
   - Nhấn "Create project"

3. **Chọn plan:**
   - Chọn "Spark" (free plan) hoặc "Blaze" (pay-as-you-go)
   - Spark plan có giới hạn 5GB storage miễn phí

## Bước 2: Kích hoạt Firebase Storage

1. **Trong Firebase Console:**
   - Chọn project vừa tạo
   - Trong menu bên trái, chọn "Storage"
   - Nhấn "Get started"

2. **Thiết lập Security Rules:**
   ```
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /{allPaths=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

3. **Chọn location:**
   - Chọn region gần nhất (ví dụ: `asia-southeast1`)
   - Nhấn "Done"

## Bước 3: Tạo Service Account

1. **Vào Google Cloud Console:**
   - Từ Firebase Console, nhấn "Project settings" (⚙️)
   - Tab "General" → "Project ID" → nhấn vào link

2. **Tạo Service Account:**
   - Trong Google Cloud Console, vào "IAM & Admin" → "Service Accounts"
   - Nhấn "Create Service Account"
   - Nhập tên: `firebase-storage-admin`
   - Mô tả: `Service account for Firebase Storage access`
   - Nhấn "Create and Continue"

3. **Gán quyền:**
   - Role: `Storage Admin` hoặc `Firebase Admin`
   - Nhấn "Continue" → "Done"

4. **Tạo key:**
   - Nhấn vào service account vừa tạo
   - Tab "Keys" → "Add Key" → "Create new key"
   - Chọn "JSON" → "Create"
   - **Lưu file JSON này an toàn!**

## Bước 4: Cấu hình trong dự án

1. **Đặt file credentials:**
   ```bash
   # Tạo thư mục credentials
   mkdir credentials
   
   # Copy file JSON vào thư mục
   cp ~/Downloads/firebase-service-account.json credentials/
   ```

2. **Cập nhật file .env:**
   ```env
   FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json
   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
   STORAGE_BACKEND=firebase
   ```

3. **Lấy Storage Bucket URL:**
   - Trong Firebase Console → Storage
   - Copy URL bucket (dạng: `your-project-id.appspot.com`)

## Bước 5: Test kết nối

```bash
# Test Firebase connection
python -c "
from storage_service import get_storage_service
import asyncio

async def test():
    try:
        storage = get_storage_service()
        print('✅ Firebase Storage connected successfully!')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

## Bước 6: Cấu hình Security Rules (Tùy chọn)

Để cho phép public access (chỉ đọc):

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /recovered_images/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## Troubleshooting

### Lỗi thường gặp:

1. **"Permission denied":**
   - Kiểm tra service account có quyền Storage Admin
   - Kiểm tra file credentials đúng path

2. **"Bucket not found":**
   - Kiểm tra bucket name trong .env
   - Đảm bảo Storage đã được kích hoạt

3. **"Invalid credentials":**
   - Tải lại file JSON từ Google Cloud Console
   - Kiểm tra file không bị corrupt

### Test upload:

```bash
# Test upload một file
python -c "
import asyncio
from storage_service import get_storage_service

async def test_upload():
    storage = get_storage_service()
    test_data = b'test image data'
    url = await storage.upload_image(test_data, 'test.jpg', 'image/jpeg')
    print(f'Upload successful: {url}')

asyncio.run(test_upload())
"
```
