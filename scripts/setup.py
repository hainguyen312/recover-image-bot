#!/usr/bin/env python3
"""
Script để thiết lập môi trường cho Image Recovery Bot
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description):
    """Chạy command và hiển thị kết quả"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} thành công")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} thất bại: {e.stderr}")
        return False

def check_python_version():
    """Kiểm tra phiên bản Python"""
    print("🐍 Kiểm tra phiên bản Python...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} không được hỗ trợ. Cần Python 3.8+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_dependencies():
    """Cài đặt dependencies"""
    return run_command("pip install -r requirements.txt", "Cài đặt dependencies")

def setup_environment():
    """Thiết lập file environment"""
    print("\n🔧 Thiết lập file environment...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_example.exists():
        print("❌ File env.example không tồn tại")
        return False
    
    if env_file.exists():
        response = input("File .env đã tồn tại. Bạn có muốn ghi đè không? (y/N): ")
        if response.lower() != 'y':
            print("⏭️ Bỏ qua thiết lập .env")
            return True
    
    # Sao chép file env.example thành .env
    with open(env_example, 'r') as f:
        content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ File .env đã được tạo")
    print("⚠️ Vui lòng cập nhật các giá trị trong file .env")
    return True

def create_directories():
    """Tạo các thư mục cần thiết"""
    print("\n📁 Tạo các thư mục cần thiết...")
    
    directories = [
        "input_images",
        "output_images", 
        "temp",
        "workflows",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Tạo thư mục: {directory}")
    
    return True

def check_comfyui():
    """Kiểm tra ComfyUI"""
    print("\n🎨 Kiểm tra ComfyUI...")
    
    try:
        import requests
        response = requests.get("http://localhost:8188/system_stats", timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI đang chạy tại http://localhost:8188")
            return True
        else:
            print("⚠️ ComfyUI không phản hồi đúng")
            return False
    except:
        print("❌ ComfyUI không chạy hoặc không thể kết nối")
        print("💡 Vui lòng chạy ComfyUI trước khi sử dụng API")
        return False

def main():
    """Hàm main"""
    print("🚀 Thiết lập Image Recovery Bot API")
    print("=" * 50)
    
    # Kiểm tra Python version
    if not check_python_version():
        sys.exit(1)
    
    # Tạo thư mục
    if not create_directories():
        sys.exit(1)
    
    # Cài đặt dependencies
    if not install_dependencies():
        print("❌ Không thể cài đặt dependencies")
        sys.exit(1)
    
    # Thiết lập environment
    if not setup_environment():
        sys.exit(1)
    
    # Kiểm tra ComfyUI
    check_comfyui()
    
    print("\n" + "=" * 50)
    print("🎉 Thiết lập hoàn tất!")
    print("\n📋 Các bước tiếp theo:")
    print("1. Cập nhật file .env với thông tin của bạn")
    print("2. Đảm bảo ComfyUI đang chạy")
    print("3. Chạy API: python main.py")
    print("4. Truy cập: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
