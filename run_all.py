#!/usr/bin/env python3
"""
Script để chạy cả API và Telegram Bot cùng lúc
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def run_api():
    """Chạy API server"""
    print("🚀 Starting API server...")
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ API server failed: {e}")
    except KeyboardInterrupt:
        print("⏹️ API server stopped")

def run_bot():
    """Chạy Telegram bot"""
    print("🤖 Starting Telegram bot...")
    try:
        subprocess.run([sys.executable, "run_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Telegram bot failed: {e}")
    except KeyboardInterrupt:
        print("⏹️ Telegram bot stopped")

def signal_handler(sig, frame):
    """Xử lý tín hiệu dừng"""
    print("\n👋 Đang dừng tất cả services...")
    sys.exit(0)

def main():
    """Main function"""
    print("🚀 Starting Image Recovery Bot System")
    print("=" * 50)
    print("📡 API Server + 🤖 Telegram Bot")
    print("=" * 50)
    
    # Đăng ký signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Kiểm tra file .env
    if not Path(".env").exists():
        print("❌ File .env không tồn tại!")
        print("💡 Chạy: python scripts/setup.py")
        sys.exit(1)
    
    print("✅ Environment file found")
    print("🔄 Starting services...")
    print()
    print("📋 Services:")
    print("   🌐 API: http://localhost:8000")
    print("   📚 Docs: http://localhost:8000/docs")
    print("   🤖 Bot: Running in background")
    print()
    print("⏹️ Nhấn Ctrl+C để dừng tất cả")
    print("-" * 50)
    
    # Tạo threads để chạy song song
    api_thread = threading.Thread(target=run_api, daemon=True)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    
    # Bắt đầu API trước
    api_thread.start()
    
    # Đợi API khởi động
    print("⏳ Waiting for API to start...")
    time.sleep(5)
    
    # Bắt đầu bot
    bot_thread.start()
    
    # Đợi cả hai threads
    try:
        api_thread.join()
        bot_thread.join()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
