#!/usr/bin/env python3
"""
Script để thiết lập Telegram Bot
"""

import os
import sys
import requests
from pathlib import Path

def create_telegram_bot():
    """Hướng dẫn tạo Telegram bot"""
    print("🤖 Thiết lập Telegram Bot")
    print("=" * 50)
    
    print("📋 Các bước tạo Telegram Bot:")
    print()
    print("1️⃣ Mở Telegram và tìm @BotFather")
    print("   - Gõ @BotFather trong tìm kiếm")
    print("   - Nhấn vào kết quả đầu tiên")
    print()
    print("2️⃣ Bắt đầu chat với BotFather")
    print("   - Gõ /start")
    print("   - Gõ /newbot")
    print()
    print("3️⃣ Đặt tên cho bot")
    print("   - Nhập tên hiển thị (ví dụ: Image Recovery Bot)")
    print("   - Nhập username (phải kết thúc bằng 'bot', ví dụ: image_recovery_bot)")
    print()
    print("4️⃣ Lấy token")
    print("   - BotFather sẽ gửi cho bạn một token")
    print("   - Copy token này (dạng: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz)")
    print()
    
    token = input("🔑 Nhập token bot (hoặc Enter để bỏ qua): ").strip()
    
    if token:
        # Cập nhật file .env
        env_file = Path(".env")
        if env_file.exists():
            # Đọc file hiện tại
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Cập nhật token
            if "TELEGRAM_BOT_TOKEN=" in content:
                # Thay thế token cũ
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        lines[i] = f"TELEGRAM_BOT_TOKEN={token}"
                        break
                content = '\n'.join(lines)
            else:
                # Thêm token mới
                content += f"\nTELEGRAM_BOT_TOKEN={token}\n"
            
            # Ghi lại file
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Token đã được lưu vào file .env")
        else:
            print("❌ File .env không tồn tại. Vui lòng chạy setup.py trước.")
            return False
    
    print()
    print("📝 Các bước tiếp theo:")
    print("1. Chạy API: python main.py")
    print("2. Chạy bot: python run_bot.py")
    print("3. Tìm bot trên Telegram và bắt đầu chat")
    print()
    
    return True

def test_bot_connection():
    """Test kết nối bot"""
    print("🧪 Test kết nối bot...")
    
    from config import config
    
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN không được thiết lập")
        return False
    
    try:
        # Test API call đến Telegram
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_info = data['result']
                print("✅ Bot kết nối thành công!")
                print(f"   Tên bot: {bot_info['first_name']}")
                print(f"   Username: @{bot_info['username']}")
                print(f"   ID: {bot_info['id']}")
                return True
            else:
                print("❌ Token không hợp lệ")
                return False
        else:
            print(f"❌ Lỗi API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return False

def setup_webhook():
    """Thiết lập webhook (tùy chọn)"""
    print("\n🔗 Thiết lập Webhook (tùy chọn)")
    print("Webhook cho phép bot nhận tin nhắn qua HTTPS thay vì polling")
    
    setup = input("Bạn có muốn thiết lập webhook không? (y/N): ").strip().lower()
    
    if setup == 'y':
        webhook_url = input("Nhập URL webhook (ví dụ: https://yourdomain.com/webhook): ").strip()
        
        if webhook_url:
            from config import config
            
            try:
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/setWebhook"
                data = {'url': webhook_url}
                
                response = requests.post(url, data=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result['ok']:
                        print("✅ Webhook đã được thiết lập!")
                    else:
                        print(f"❌ Lỗi thiết lập webhook: {result['description']}")
                else:
                    print(f"❌ Lỗi HTTP: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Lỗi: {e}")
        else:
            print("⚠️ URL webhook không hợp lệ")
    else:
        print("⏭️ Bỏ qua thiết lập webhook")

def main():
    """Main function"""
    print("🚀 Thiết lập Telegram Bot cho Image Recovery")
    print("=" * 60)
    
    # Tạo bot
    if not create_telegram_bot():
        return
    
    # Test kết nối
    if test_bot_connection():
        print("\n🎉 Bot đã được thiết lập thành công!")
        
        # Thiết lập webhook
        setup_webhook()
        
        print("\n📋 Hướng dẫn sử dụng:")
        print("1. Chạy API server: python main.py")
        print("2. Chạy bot: python run_bot.py")
        print("3. Tìm bot trên Telegram và gửi /start")
        print("4. Gửi ảnh và prompt để phục hồi ảnh")
        
    else:
        print("\n❌ Thiết lập bot thất bại")
        print("Vui lòng kiểm tra lại token và thử lại")

if __name__ == "__main__":
    main()
