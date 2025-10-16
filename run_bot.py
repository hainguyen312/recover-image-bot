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
    print("Kiem tra yeu cau he thong...")
    
    # Kiểm tra token Telegram
    if not config.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN khong duoc thiet lap!")
        print("Vui long:")
        print("   1. Tao bot moi voi @BotFather tren Telegram")
        print("   2. Lay token tu BotFather")
        print("   3. Cap nhat TELEGRAM_BOT_TOKEN trong file .env")
        return False
    
    # Kiểm tra API
    try:
        import requests
        response = requests.get(f"{config.API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("API dang hoat dong")
        else:
            print("API khong phan hoi dung")
            return False
    except Exception as e:
        print(f"Khong the ket noi API: {e}")
        print("Vui long chay API truoc: python main.py")
        return False
    
    print("Tat ca yeu cau da duoc dap ung")
    return True

def main_sync():
    """Main function đồng bộ"""
    print("Starting Telegram Image Recovery Bot")
    print("=" * 50)
    
    if not check_requirements():
        sys.exit(1)
    
    print("Khoi dong bot...")
    print("Bot se phan hoi tin nhan tu Telegram")
    print("Nhan Ctrl+C de dung bot")
    print("-" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot da duoc dung")
    except Exception as e:
        print(f"Loi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_sync()
