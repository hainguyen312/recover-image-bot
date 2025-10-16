#!/usr/bin/env python3
"""
Demo script để test Firebase và Google Cloud Storage
"""

import asyncio
import os
import sys
from pathlib import Path
from PIL import Image
import io

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent.parent))

from storage_service import FirebaseStorageService, get_storage_service

def create_test_image():
    """Tạo ảnh test"""
    # Tạo ảnh test 100x100 màu đỏ
    img = Image.new('RGB', (100, 100), color='red')
    
    # Convert thành bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_bytes = img_buffer.getvalue()
    
    return img_bytes

async def test_firebase():
    """Test Firebase Storage"""
    print("🔥 Testing Firebase Storage...")
    
    try:
        # Kiểm tra config
        credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        
        if not credentials_path or not bucket_name:
            print("❌ Firebase config không đầy đủ")
            print("   FIREBASE_CREDENTIALS_PATH:", credentials_path)
            print("   FIREBASE_STORAGE_BUCKET:", bucket_name)
            return False
        
        if not Path(credentials_path).exists():
            print(f"❌ File credentials không tồn tại: {credentials_path}")
            return False
        
        # Test connection
        storage = FirebaseStorageService()
        print("✅ Firebase Storage khởi tạo thành công")
        
        # Test upload
        test_data = create_test_image()
        filename = "test_firebase.png"
        
        print("   Đang upload test image...")
        url = await storage.upload_image(
            image_bytes=test_data,
            filename=filename,
            content_type="image/png"
        )
        
        print(f"✅ Upload thành công!")
        print(f"   URL: {url}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi Firebase: {e}")
        return False


async def test_auto_storage():
    """Test auto storage selection"""
    print("\n🤖 Testing Auto Storage Selection...")
    
    try:
        storage = get_storage_service()
        storage_type = type(storage).__name__
        
        print(f"✅ Auto-selected storage: {storage_type}")
        
        # Test upload
        test_data = create_test_image()
        filename = "test_auto.png"
        
        print("   Đang upload test image...")
        url = await storage.upload_image(
            image_bytes=test_data,
            filename=filename,
            content_type="image/png"
        )
        
        print(f"✅ Upload thành công!")
        print(f"   URL: {url}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi auto storage: {e}")
        return False

def show_config_status():
    """Hiển thị trạng thái config"""
    print("📋 Firebase Storage Configuration Status:")
    print("=" * 50)
    
    # Firebase config
    firebase_creds = os.getenv("FIREBASE_CREDENTIALS_PATH")
    firebase_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
    
    print(f"🔥 Firebase Storage:")
    print(f"   Credentials: {'✅' if firebase_creds and Path(firebase_creds).exists() else '❌'} {firebase_creds or 'Not set'}")
    print(f"   Bucket: {'✅' if firebase_bucket else '❌'} {firebase_bucket or 'Not set'}")

async def main():
    """Main function"""
    print("🚀 Storage Demo & Test")
    print("=" * 50)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Hiển thị config status
    show_config_status()
    
    print("\n🧪 Running Tests...")
    print("-" * 50)
    
    # Test Firebase
    firebase_success = await test_firebase()
    
    # Test auto selection
    auto_success = await test_auto_storage()
    
    # Tổng kết
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"🔥 Firebase Storage: {'✅ PASS' if firebase_success else '❌ FAIL'}")
    print(f"🤖 Auto Storage Selection: {'✅ PASS' if auto_success else '❌ FAIL'}")
    
    if firebase_success:
        print("\n🎉 Firebase Storage hoạt động tốt!")
        print("✅ Hệ thống sẵn sàng để sử dụng")
    else:
        print("\n❌ Firebase Storage không hoạt động")
        print("💡 Vui lòng cấu hình lại Firebase Storage")
        print("\n📚 Hướng dẫn: docs/firebase_setup.md")

if __name__ == "__main__":
    asyncio.run(main())
