#!/usr/bin/env python3
"""
Script để chạy Telegram Bot
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent))

from telegram_bot import main
from config import config

def check_requirements():
    """Kiểm tra các yêu cầu cần thiết"""
    print("🔍 Kiểm tra yêu cầu hệ thống...")
    
    # Kiểm tra token Telegram
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN không được thiết lập!")
        print("💡 Vui lòng:")
        print("   1. Tạo bot mới với @BotFather trên Telegram")
        print("   2. Lấy token từ BotFather")
        print("   3. Cập nhật TELEGRAM_BOT_TOKEN trong file .env")
        return False
    
    # Kiểm tra API
    try:
        import requests
        response = requests.get(f"{config.API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API đang hoạt động")
        else:
            print("⚠️ API không phản hồi đúng")
            return False
    except Exception as e:
        print(f"❌ Không thể kết nối API: {e}")
        print("💡 Vui lòng chạy API trước: python main.py")
        return False
    
    print("✅ Tất cả yêu cầu đã được đáp ứng")
    return True

def main_sync():
    """Main function đồng bộ"""
    print("🤖 Starting Telegram Image Recovery Bot")
    print("=" * 50)
    
    if not check_requirements():
        sys.exit(1)
    
    print("🚀 Khởi động bot...")
    print("📱 Bot sẽ phản hồi tin nhắn từ Telegram")
    print("⏹️ Nhấn Ctrl+C để dừng bot")
    print("-" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot đã được dừng")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_sync()
