#!/usr/bin/env python3
"""
Script để thiết lập và test Firebase/Google Cloud Storage
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Kiểm tra file .env"""
    print("🔍 Kiểm tra file cấu hình...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ File .env không tồn tại!")
        print("💡 Chạy: python scripts/setup.py")
        return False
    
    print("✅ File .env tồn tại")
    return True

def check_firebase_setup():
    """Kiểm tra cấu hình Firebase"""
    print("\n🔥 Kiểm tra cấu hình Firebase...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    
    if not credentials_path:
        print("❌ FIREBASE_CREDENTIALS_PATH không được thiết lập")
        return False
    
    if not bucket_name:
        print("❌ FIREBASE_STORAGE_BUCKET không được thiết lập")
        return False
    
    # Kiểm tra file credentials
    if not Path(credentials_path).exists():
        print(f"❌ File credentials không tồn tại: {credentials_path}")
        return False
    
    print("✅ Firebase credentials file tồn tại")
    print(f"   Credentials: {credentials_path}")
    print(f"   Bucket: {bucket_name}")
    
    return True


def test_firebase_connection():
    """Test kết nối Firebase"""
    print("\n🧪 Test kết nối Firebase Storage...")
    
    try:
        from storage_service import FirebaseStorageService
        
        storage = FirebaseStorageService()
        print("✅ Firebase Storage khởi tạo thành công!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Cài đặt: pip install firebase-admin")
        return False
    except Exception as e:
        print(f"❌ Lỗi kết nối Firebase: {e}")
        return False


def test_upload():
    """Test upload file"""
    print("\n📤 Test upload file...")
    
    try:
        from storage_service import get_storage_service
        import asyncio
        
        async def upload_test():
            storage = get_storage_service()
            
            # Tạo test data
            test_data = b"test image data for upload"
            filename = "test_upload.txt"
            
            print("   Đang upload test file...")
            url = await storage.upload_image(
                image_bytes=test_data,
                filename=filename,
                content_type="text/plain"
            )
            
            print(f"✅ Upload thành công!")
            print(f"   URL: {url}")
            return True
        
        return asyncio.run(upload_test())
        
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        return False

def show_setup_instructions():
    """Hiển thị hướng dẫn thiết lập"""
    print("\n📋 Hướng dẫn thiết lập Firebase Storage:")
    print("=" * 50)
    
    print("\n🔥 Firebase Storage:")
    print("1. Tạo project tại https://console.firebase.google.com/")
    print("2. Kích hoạt Storage")
    print("3. Tạo Service Account và download JSON")
    print("4. Cập nhật .env:")
    print("   FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json")
    print("   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com")
    print("\n📚 Xem hướng dẫn chi tiết: docs/firebase_setup.md")

def main():
    """Main function"""
    print("🚀 Storage Setup & Test Tool")
    print("=" * 50)
    
    # Kiểm tra environment
    if not check_environment():
        return
    
    # Kiểm tra cấu hình Firebase
    firebase_ok = check_firebase_setup()
    
    if not firebase_ok:
        print("\n❌ Firebase Storage chưa được cấu hình!")
        show_setup_instructions()
        return
    
    # Test kết nối Firebase
    firebase_test = test_firebase_connection()
    
    # Test upload
    if firebase_test:
        upload_test = test_upload()
        
        if upload_test:
            print("\n🎉 Tất cả tests đã passed!")
            print("✅ Firebase Storage sẵn sàng sử dụng")
        else:
            print("\n⚠️ Upload test thất bại")
    else:
        print("\n❌ Không thể kết nối Firebase Storage")
        print("💡 Kiểm tra lại credentials và network")

if __name__ == "__main__":
    main()
