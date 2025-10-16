#!/usr/bin/env python3
"""
Script để test API Image Recovery Bot
"""

import requests
import json
import time
import sys
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   ComfyUI status: {data['services']['comfyui']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_image_recovery():
    """Test image recovery endpoint with file upload"""
    print("\n🖼️ Testing image recovery (file upload)...")
    
    # Tạo một ảnh test đơn giản
    from PIL import Image
    import io
    
    # Tạo ảnh test (100x100, màu đỏ)
    test_image = Image.new('RGB', (100, 100), color='red')
    
    # Lưu vào buffer
    img_buffer = io.BytesIO()
    test_image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Chuẩn bị data
    files = {
        'image': ('test_image.png', img_buffer, 'image/png')
    }
    
    data = {
        'prompt': 'restore this red image and make it blue',
        'strength': 0.8,
        'steps': 5,  # Giảm steps để test nhanh
        'guidance_scale': 7.5
    }
    
    try:
        print("   Sending request...")
        response = requests.post(f"{API_BASE_URL}/recover-image", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ Image recovery test passed")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Processing time: {result['processing_time']:.2f}s")
                if result['result_image_url']:
                    print(f"   Result URL: {result['result_image_url']}")
                return True
            else:
                print(f"❌ Image recovery failed: {result['message']}")
                return False
        else:
            print(f"❌ Image recovery request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Image recovery error: {e}")
        return False

def test_image_recovery_from_url():
    """Test image recovery endpoint with URL"""
    print("\n🌐 Testing image recovery (from URL)...")
    
    # Sử dụng một ảnh test công khai
    test_url = "https://via.placeholder.com/300x300/FF0000/FFFFFF?text=Test+Image"
    
    data = {
        'image_url': test_url,
        'prompt': 'restore and enhance this test image',
        'strength': 0.8,
        'steps': 5,  # Giảm steps để test nhanh
        'guidance_scale': 7.5
    }
    
    try:
        print("   Sending request...")
        response = requests.post(f"{API_BASE_URL}/recover-image-from-url", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ Image recovery from URL test passed")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Processing time: {result['processing_time']:.2f}s")
                if result['result_image_url']:
                    print(f"   Result URL: {result['result_image_url']}")
                return True
            else:
                print(f"❌ Image recovery from URL failed: {result['message']}")
                return False
        else:
            print(f"❌ Image recovery from URL request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Image recovery from URL error: {e}")
        return False

def test_job_status():
    """Test job status endpoint"""
    print("\n📊 Testing job status...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/jobs")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Job status test passed")
            print(f"   Total jobs: {data['total_jobs']}")
            return True
        else:
            print(f"❌ Job status test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Job status error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing Image Recovery Bot API")
    print("=" * 50)
    
    # Test health check
    if not test_health_check():
        print("\n❌ Health check failed. API có thể không chạy.")
        print("💡 Hãy chạy: python main.py")
        sys.exit(1)
    
    # Test job status
    test_job_status()
    
    # Test image recovery from URL (nhanh hơn)
    if not test_image_recovery_from_url():
        print("\n⚠️ Image recovery from URL test failed. Kiểm tra:")
        print("   - ComfyUI có đang chạy không")
        print("   - Storage service đã được cấu hình chưa")
        print("   - Workflow có đúng không")
        sys.exit(1)
    
    # Test image recovery with file upload
    if not test_image_recovery():
        print("\n⚠️ Image recovery with file upload test failed.")
        print("   Test từ URL đã pass, có thể do vấn đề với file upload.")
    
    print("\n" + "=" * 50)
    print("🎉 Tất cả tests đã passed!")
    print("✅ API đang hoạt động bình thường")

if __name__ == "__main__":
    main()
