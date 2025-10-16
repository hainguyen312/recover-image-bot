import os
import logging
import asyncio
import tempfile
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import httpx
import json
from io import BytesIO
from PIL import Image

from config import config

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, api_base_url: str = "http://localhost:8000"):
        self.token = token
        self.api_base_url = api_base_url
        self.application = None
        self.user_sessions = {}  # Lưu trữ session của người dùng
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /start"""
        user = update.effective_user
        welcome_text = f"""
🤖 **Chào mừng đến với Image Recovery Bot!**

Xin chào {user.first_name}! Tôi có thể giúp bạn phục hồi và cải thiện ảnh bằng AI.

**Cách sử dụng:**
1. 📸 Gửi ảnh cần phục hồi
2. ✍️ Nhập mô tả chi tiết về việc phục hồi
3. ⚙️ Chọn các tham số (tùy chọn)
4. 🎯 Chờ kết quả!

**Lệnh có sẵn:**
/start - Hiển thị menu chính
/help - Hướng dẫn chi tiết
/settings - Cài đặt tham số mặc định
/status - Kiểm tra trạng thái API

Hãy gửi ảnh để bắt đầu! 🚀
        """
        
        keyboard = [
            [InlineKeyboardButton("📖 Hướng dẫn", callback_data="help")],
            [InlineKeyboardButton("⚙️ Cài đặt", callback_data="settings")],
            [InlineKeyboardButton("📊 Trạng thái", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /help"""
        help_text = """
📖 **Hướng dẫn sử dụng Image Recovery Bot**

**Bước 1: Gửi ảnh**
- Gửi ảnh cần phục hồi (jpg, png, webp)
- Kích thước tối đa: 10MB

**Bước 2: Nhập prompt**
- Mô tả chi tiết về việc phục hồi
- Ví dụ: "restore this damaged photo, fix scratches, improve colors"

**Bước 3: Chọn tham số (tùy chọn)**
- Strength: Độ mạnh phục hồi (0.1-1.0)
- Steps: Số bước xử lý (1-50)
- Guidance: Tỷ lệ hướng dẫn (1.0-20.0)

**Ví dụ prompt tốt:**
✅ "restore this old photo, fix scratches and stains, enhance colors"
✅ "improve image quality, remove noise, make it sharper"
✅ "fix damaged areas, restore missing parts, enhance details"

**Lưu ý:**
- Quá trình xử lý có thể mất 30-60 giây
- Kết quả sẽ được lưu trên cloud storage
- Bot hỗ trợ tiếng Việt và tiếng Anh
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /settings"""
        user_id = update.effective_user.id
        
        # Lấy settings hiện tại của user
        current_settings = self.user_sessions.get(user_id, {}).get('settings', {
            'strength': 0.8,
            'steps': 20,
            'guidance_scale': 7.5
        })
        
        settings_text = f"""
⚙️ **Cài đặt hiện tại:**

🔧 **Strength:** {current_settings['strength']}
📊 **Steps:** {current_settings['steps']}
🎯 **Guidance Scale:** {current_settings['guidance_scale']}

Sử dụng các nút bên dưới để thay đổi:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔧 Strength", callback_data="set_strength"),
                InlineKeyboardButton("📊 Steps", callback_data="set_steps")
            ],
            [
                InlineKeyboardButton("🎯 Guidance", callback_data="set_guidance"),
                InlineKeyboardButton("🔄 Reset", callback_data="reset_settings")
            ],
            [InlineKeyboardButton("✅ Hoàn thành", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kiểm tra trạng thái API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base_url}/health", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    status_text = f"""
📊 **Trạng thái hệ thống:**

🟢 **API:** Hoạt động bình thường
🤖 **ComfyUI:** {data['services']['comfyui']}
☁️ **Storage:** {data['services']['storage']}

Sẵn sàng xử lý ảnh! 🚀
                    """
                else:
                    status_text = "🔴 API không hoạt động. Vui lòng thử lại sau."
                    
        except Exception as e:
            status_text = f"❌ Không thể kết nối API: {str(e)}"
        
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý khi người dùng gửi ảnh"""
        user_id = update.effective_user.id
        
        # Lưu thông tin ảnh vào session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {'waiting_for_prompt': False}
        
        # Lấy ảnh có độ phân giải cao nhất
        photo = update.message.photo[-1]
        
        # Lưu file_id để sử dụng sau
        self.user_sessions[user_id]['photo_file_id'] = photo.file_id
        self.user_sessions[user_id]['waiting_for_prompt'] = True
        
        await update.message.reply_text(
            "📸 **Ảnh đã được nhận!**\n\n"
            "Bây giờ hãy gửi mô tả về việc phục hồi ảnh (prompt):\n\n"
            "Ví dụ: \"restore this damaged photo, fix scratches, improve colors\"",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tin nhắn văn bản"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Kiểm tra nếu user đang nhập prompt
        if user_id in self.user_sessions and self.user_sessions[user_id].get('waiting_for_prompt'):
            await self.process_image_recovery(update, context, text)
            return
        
        # Xử lý các lệnh khác
        if text.startswith('/'):
            await update.message.reply_text(
                "❓ Lệnh không được nhận diện. Sử dụng /help để xem danh sách lệnh."
            )
        else:
            await update.message.reply_text(
                "🤔 Tôi không hiểu. Hãy gửi ảnh để bắt đầu phục hồi hoặc sử dụng /help để xem hướng dẫn."
            )
    
    async def process_image_recovery(self, update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
        """Xử lý phục hồi ảnh"""
        user_id = update.effective_user.id
        
        try:
            # Gửi thông báo đang xử lý
            processing_msg = await update.message.reply_text(
                "🔄 **Đang xử lý ảnh...**\n\n"
                "Quá trình này có thể mất 30-60 giây.\n"
                "Vui lòng chờ trong giây lát... ⏳",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Lấy ảnh từ Telegram
            photo_file_id = self.user_sessions[user_id]['photo_file_id']
            file = await context.bot.get_file(photo_file_id)
            
            # Download ảnh
            image_bytes = await file.download_as_bytearray()
            
            # Lấy settings của user
            settings = self.user_sessions.get(user_id, {}).get('settings', {
                'strength': 0.8,
                'steps': 20,
                'guidance_scale': 7.5
            })
            
            # Gọi API phục hồi ảnh
            async with httpx.AsyncClient(timeout=120.0) as client:
                files = {
                    'image': ('image.jpg', image_bytes, 'image/jpeg')
                }
                data = {
                    'prompt': prompt,
                    'strength': settings['strength'],
                    'steps': settings['steps'],
                    'guidance_scale': settings['guidance_scale']
                }
                
                response = await client.post(
                    f"{self.api_base_url}/recover-image",
                    files=files,
                    data=data
                )
            
            # Xóa thông báo đang xử lý
            await processing_msg.delete()
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    # Gửi kết quả thành công
                    success_text = f"""
✅ **Phục hồi ảnh thành công!**

⏱️ **Thời gian xử lý:** {result['processing_time']:.1f} giây
🆔 **Job ID:** `{result['job_id']}`

**Prompt đã sử dụng:** {prompt}

Kết quả sẽ được gửi trong giây lát... 🎉
                    """
                    
                    await update.message.reply_text(
                        success_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Gửi ảnh kết quả
                    await update.message.reply_photo(
                        photo=result['result_image_url'],
                        caption=f"🎨 **Ảnh đã được phục hồi!**\n\nPrompt: {prompt}"
                    )
                    
                    # Reset session
                    self.user_sessions[user_id]['waiting_for_prompt'] = False
                    del self.user_sessions[user_id]['photo_file_id']
                    
                else:
                    await update.message.reply_text(
                        f"❌ **Lỗi xử lý ảnh:**\n\n{result['message']}",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(
                    f"❌ **Lỗi API:** HTTP {response.status_code}\n\n{response.text}"
                )
                
        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            await update.message.reply_text(
                f"❌ **Đã xảy ra lỗi:**\n\n{str(e)}\n\nVui lòng thử lại sau."
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý callback từ inline keyboard"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "help":
            await self.help_command(update, context)
        elif query.data == "settings":
            await self.settings_command(update, context)
        elif query.data == "status":
            await self.status_command(update, context)
        elif query.data == "close_settings":
            await query.edit_message_text("✅ Cài đặt đã được lưu!")
        # Có thể thêm các callback khác cho settings...
    
    def setup_handlers(self):
        """Thiết lập các handler"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def run(self):
        """Chạy bot"""
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram bot is running...")
        
        # Giữ bot chạy
        await asyncio.Event().wait()

async def main():
    """Main function"""
    # Lấy token từ environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        return
    
    api_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    
    bot = TelegramBot(bot_token, api_url)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
