#!/usr/bin/env python3
"""
Script để cấu hình Firebase với file credentials đã có
"""

import os
import shutil
from pathlib import Path

def setup_firebase_credentials():
    """Thiết lập Firebase credentials"""
    print("🔥 Cấu hình Firebase Storage")
    print("=" * 50)
    
    # Kiểm tra file credentials trong thư mục credentials
    creds_dir = Path("credentials")
    target_file = creds_dir / "firebase-service-account.json"
    
    if target_file.exists():
        print("✅ File credentials đã tồn tại trong credentials/firebase-service-account.json")
    else:
        # Tìm file gốc
        original_file = Path("my-image-recovery-firebase-adminsdk-fbsvc-a5b2b89c6b.json")
        
        if original_file.exists():
            creds_dir.mkdir(exist_ok=True)
            shutil.copy2(original_file, target_file)
            print("✅ Đã copy file credentials từ thư mục gốc")
        else:
            print("❌ Không tìm thấy file credentials!")
            print("💡 Đảm bảo file credentials có trong thư mục gốc hoặc credentials/")
            return False
    
    # Cấu hình .env
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ File .env không tồn tại!")
        print("💡 Chạy: cp env.example .env")
        return False
    
    # Đọc và cập nhật .env
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Cập nhật Firebase config
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('FIREBASE_CREDENTIALS_PATH='):
            lines[i] = 'FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json'
            updated = True
        elif line.startswith('FIREBASE_STORAGE_BUCKET='):
            lines[i] = 'FIREBASE_STORAGE_BUCKET=my-image-recovery.appspot.com'
            updated = True
    
    # Ghi lại file
    with open(env_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print("✅ Đã cập nhật file .env")
    print("   FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json")
    print("   FIREBASE_STORAGE_BUCKET=my-image-recovery.appspot.com")
    
    return True

def test_firebase_connection():
    """Test kết nối Firebase"""
    print("\n🧪 Test kết nối Firebase...")
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        from storage_service import FirebaseStorageService
        
        storage = FirebaseStorageService()
        print("✅ Firebase Storage kết nối thành công!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Cấu hình Firebase với file credentials có sẵn")
    print("=" * 60)
    
    # Setup credentials
    if not setup_firebase_credentials():
        return
    
    # Test kết nối
    if test_firebase_connection():
        print("\n🎉 Firebase Storage đã được cấu hình thành công!")
        print("✅ Bạn có thể chạy API và Bot ngay bây giờ")
        print("\n📋 Các bước tiếp theo:")
        print("1. Chạy API: python main.py")
        print("2. Chạy Bot: python run_bot.py")
        print("3. Hoặc chạy cả hai: python run_all.py")
    else:
        print("\n⚠️ Cần kiểm tra lại cấu hình")
        print("💡 Đảm bảo:")
        print("   - File credentials đúng")
        print("   - Firebase project đã kích hoạt Storage")
        print("   - Service account có quyền Storage Admin")

if __name__ == "__main__":
    main()
