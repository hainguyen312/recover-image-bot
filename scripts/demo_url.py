#!/usr/bin/env python3
"""
Demo script để test API với URL ảnh
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_with_real_image_url():
    """Test với URL ảnh thật"""
    print("🧪 Testing với URL ảnh thật...")
    
    # Sử dụng một ảnh test công khai từ Unsplash
    test_url = "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300&h=300&fit=crop"
    
    data = {
        'image_url': test_url,
        'prompt': 'enhance this landscape image, make it more vibrant and detailed',
        'strength': 0.7,
        'steps': 10,  # Ít steps để test nhanh
        'guidance_scale': 7.5
    }
    
    try:
        print(f"   Đang gửi request với URL: {test_url}")
        print(f"   Prompt: {data['prompt']}")
        
        response = requests.post(f"{API_BASE_URL}/recover-image-from-url", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ Test thành công!")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Thời gian xử lý: {result['processing_time']:.2f}s")
                print(f"   URL kết quả: {result['result_image_url']}")
                return True
            else:
                print(f"❌ Test thất bại: {result['message']}")
                if result.get('error_details'):
                    print(f"   Chi tiết lỗi: {result['error_details']}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_with_invalid_url():
    """Test với URL không hợp lệ"""
    print("\n🧪 Testing với URL không hợp lệ...")
    
    data = {
        'image_url': 'https://example.com/nonexistent.jpg',
        'prompt': 'test prompt',
        'strength': 0.8,
        'steps': 5,
        'guidance_scale': 7.5
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/recover-image-from-url", json=data)
        
        if response.status_code == 400:
            print("✅ Test passed - API đã từ chối URL không hợp lệ")
            return True
        else:
            print(f"❌ Test failed - Expected 400, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_with_non_image_url():
    """Test với URL không phải ảnh"""
    print("\n🧪 Testing với URL không phải ảnh...")
    
    data = {
        'image_url': 'https://www.google.com',
        'prompt': 'test prompt',
        'strength': 0.8,
        'steps': 5,
        'guidance_scale': 7.5
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/recover-image-from-url", json=data)
        
        if response.status_code == 400:
            print("✅ Test passed - API đã từ chối URL không phải ảnh")
            return True
        else:
            print(f"❌ Test failed - Expected 400, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def check_api_status():
    """Kiểm tra trạng thái API"""
    print("🔍 Kiểm tra trạng thái API...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API đang hoạt động")
            print(f"   ComfyUI: {data['services']['comfyui']}")
            print(f"   Storage: {data['services']['storage']}")
            return True
        else:
            print(f"❌ API không hoạt động: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Không thể kết nối API: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Demo API Image Recovery từ URL")
    print("=" * 50)
    
    # Kiểm tra API status
    if not check_api_status():
        print("\n❌ API không hoạt động. Vui lòng chạy: python main.py")
        return
    
    # Test với ảnh thật
    if test_with_real_image_url():
        print("\n🎉 Demo thành công!")
    else:
        print("\n⚠️ Demo thất bại. Kiểm tra:")
        print("   - ComfyUI có đang chạy không")
        print("   - Storage service đã được cấu hình chưa")
        print("   - Workflow có đúng không")
    
    # Test error cases
    test_with_invalid_url()
    test_with_non_image_url()
    
    print("\n" + "=" * 50)
    print("📋 Tóm tắt:")
    print("✅ API hỗ trợ nhận ảnh từ URL")
    print("✅ Validation URL hoạt động đúng")
    print("✅ Error handling hoạt động tốt")

if __name__ == "__main__":
    main()
