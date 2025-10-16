#!/usr/bin/env python3
"""
Script tổng hợp để setup toàn bộ hệ thống Image Recovery Bot
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description, check=True):
    """Chạy command và hiển thị kết quả"""
    print(f"\n🔄 {description}...")
    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        else:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} thành công")
            return True
        else:
            print(f"❌ {description} thất bại: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} thất bại: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ {description} lỗi: {e}")
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

def setup_project():
    """Thiết lập dự án cơ bản"""
    print("\n📁 Thiết lập dự án...")
    
    # Tạo thư mục cần thiết
    directories = ["input_images", "output_images", "temp", "workflows", "logs", "credentials", "docs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Tạo thư mục: {directory}")
    
    return True

def install_dependencies():
    """Cài đặt dependencies"""
    return run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Cài đặt dependencies"
    )

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

def setup_storage():
    """Thiết lập Firebase Storage"""
    print("\n🔥 Thiết lập Firebase Storage...")
    
    setup_storage = input("Bạn có muốn thiết lập Firebase Storage không? (y/N): ").strip().lower()
    
    if setup_storage == 'y':
        print("\n📚 Hướng dẫn Firebase Storage:")
        print("1. Tạo project tại https://console.firebase.google.com/")
        print("2. Kích hoạt Firebase Storage")
        print("3. Tạo Service Account và download JSON")
        print("4. Cập nhật .env:")
        print("   FIREBASE_CREDENTIALS_PATH=credentials/firebase-service-account.json")
        print("   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com")
        print("\n📖 Hướng dẫn chi tiết: docs/firebase_setup.md")
        print("🧪 Test: python scripts/setup_storage.py")
    else:
        print("⏭️ Bỏ qua thiết lập Firebase Storage")
    
    return True

def setup_telegram_bot():
    """Thiết lập Telegram Bot"""
    print("\n🤖 Thiết lập Telegram Bot...")
    
    setup_bot = input("Bạn có muốn thiết lập Telegram Bot không? (y/N): ").strip().lower()
    
    if setup_bot == 'y':
        print("📚 Hướng dẫn thiết lập Telegram Bot:")
        print("1. Tìm @BotFather trên Telegram")
        print("2. Tạo bot mới với /newbot")
        print("3. Copy token")
        print("4. Chạy: python scripts/setup_telegram_bot.py")
        print("5. Cập nhật TELEGRAM_BOT_TOKEN trong .env")
    else:
        print("⏭️ Bỏ qua thiết lập Telegram Bot")
    
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

def run_tests():
    """Chạy các tests"""
    print("\n🧪 Chạy tests...")
    
    # Test API
    print("\n📡 Testing API...")
    api_test = run_command(
        [sys.executable, "scripts/test_api.py"],
        "Test API",
        check=False
    )
    
    # Test Storage
    print("\n☁️ Testing Storage...")
    storage_test = run_command(
        [sys.executable, "scripts/setup_storage.py"],
        "Test Storage",
        check=False
    )
    
    return api_test, storage_test

def show_next_steps():
    """Hiển thị các bước tiếp theo"""
    print("\n" + "=" * 60)
    print("🎉 Thiết lập hoàn tất!")
    print("=" * 60)
    
    print("\n📋 Các bước tiếp theo:")
    print()
    print("1. 🔧 Cập nhật file .env với thông tin của bạn:")
    print("   - Storage credentials")
    print("   - Telegram bot token (nếu có)")
    print("   - API configuration")
    print()
    print("2. 🎨 Đảm bảo ComfyUI đang chạy:")
    print("   - Start ComfyUI server")
    print("   - Test tại http://localhost:8188")
    print()
    print("3. 🚀 Chạy hệ thống:")
    print("   # Chạy API + Bot cùng lúc")
    print("   python run_all.py")
    print()
    print("   # Hoặc chạy riêng lẻ")
    print("   python main.py        # Terminal 1: API")
    print("   python run_bot.py     # Terminal 2: Bot")
    print()
    print("4. 🧪 Test hệ thống:")
    print("   python scripts/test_api.py")
    print("   python scripts/demo_storage.py")
    print()
    print("5. 📱 Sử dụng:")
    print("   - API: http://localhost:8000/docs")
    print("   - Telegram: Tìm bot và gửi /start")
    print()
    print("📚 Documentation:")
    print("   - Firebase Storage: docs/firebase_setup.md")
    print("   - API & Bot: README.md")

def main():
    """Main function"""
    print("🚀 Image Recovery Bot - Complete Setup")
    print("=" * 60)
    print("Thiết lập toàn bộ hệ thống từ đầu")
    print("=" * 60)
    
    # Kiểm tra Python version
    if not check_python_version():
        sys.exit(1)
    
    # Thiết lập dự án
    if not setup_project():
        sys.exit(1)
    
    # Cài đặt dependencies
    if not install_dependencies():
        print("❌ Không thể cài đặt dependencies")
        sys.exit(1)
    
    # Thiết lập environment
    if not setup_environment():
        sys.exit(1)
    
    # Thiết lập storage
    setup_storage()
    
    # Thiết lập Telegram Bot
    setup_telegram_bot()
    
    # Kiểm tra ComfyUI
    comfyui_ok = check_comfyui()
    
    # Chạy tests (không bắt buộc)
    run_tests_input = input("\nBạn có muốn chạy tests không? (y/N): ").strip().lower()
    if run_tests_input == 'y':
        run_tests()
    
    # Hiển thị next steps
    show_next_steps()

if __name__ == "__main__":
    main()
