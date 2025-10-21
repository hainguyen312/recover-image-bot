import os
import logging
import asyncio
import tempfile
import requests
import json
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import httpx
from io import BytesIO
from PIL import Image

from config import config
from storage_service import get_storage_service
from comfyui_client import ComfyUIClient

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.user_sessions = {}  # Lưu trữ session của người dùng
        # Khởi tạo storage service (Firebase nếu có, fallback Local)
        self.storage = get_storage_service()
    
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
            'steps': 8,
            'guidance_scale': 1.8
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
                response = await client.get("http://localhost:8000/health", timeout=10)
                
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
        
        logger.info(f"User {user_id} sent photo")
        
        # Lưu thông tin ảnh vào session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {'waiting_for_prompt': False}
        
        # Lấy ảnh có độ phân giải cao nhất
        photo = update.message.photo[-1]
        
        # Lưu file_id để sử dụng sau
        self.user_sessions[user_id]['photo_file_id'] = photo.file_id
        self.user_sessions[user_id]['waiting_for_prompt'] = True
        
        logger.info(f"User {user_id} session updated: {self.user_sessions[user_id]}")
        
        await update.message.reply_text(
            "📸 Ảnh đã được nhận!\n\n"
            "Bây giờ hãy nhập mô tả chi tiết về việc phục hồi ảnh (prompt):\n\n"
            "Ví dụ: \"restore this damaged photo, fix scratches, improve colors\""
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tin nhắn văn bản"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Debug logging
        logger.info(f"User {user_id} sent text: '{text}'")
        logger.info(f"User session: {self.user_sessions.get(user_id, 'No session')}")
        
        # Kiểm tra nếu user đang nhập prompt
        if user_id in self.user_sessions and self.user_sessions[user_id].get('waiting_for_prompt'):
            logger.info(f"Processing prompt for user {user_id}: '{text}'")
            await self.process_image_recovery(update, context, text)
            return
        
        # Xử lý các lệnh khác
        if text.startswith('/'):
            await update.message.reply_text(
                "Lệnh không được nhận diện. Sử dụng /help để xem danh sách lệnh."
            )
        else:
            logger.info(f"User {user_id} sent unrecognized text, no session or not waiting for prompt")
            await update.message.reply_text(
                "Tôi không hiểu. Vui lòng gửi ảnh để bắt đầu phục hồi hoặc sử dụng /help để xem hướng dẫn."
            )
    
    async def process_image_recovery(self, update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
        """Xử lý phục hồi ảnh trực tiếp với ComfyUI bằng workflow Restore.json.
        Chỉ thay ảnh đầu vào và text_b của node StringFunction|pysssss."""
        user_id = update.effective_user.id
        processing_msg = None
        
        try:
            # Health check ComfyUI trước khi xử lý để báo lỗi sớm
            comfy = ComfyUIClient()
            if not comfy.health_check():
                await update.message.reply_text(
                    "❌ Không thể kết nối ComfyUI. Hãy kiểm tra cấu hình COMFYUI_SERVER_URL, port 8188, và firewall rồi thử lại.")
                return

            processing_msg = await update.message.reply_text(
                "🔄 Đang xử lý ảnh... Vui lòng chờ trong giây lát...",
                parse_mode=ParseMode.MARKDOWN
            )

            photo_file_id = self.user_sessions[user_id]['photo_file_id']
            file = await context.bot.get_file(photo_file_id)

            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "input.jpg")
                await file.download_to_drive(local_path)

                client = ComfyUIClient()
                
                # Lấy thông tin queue trước khi bắt đầu
                try:
                    queue_info = client.get_queue_status()
                    queue_pending = queue_info.get('queue_pending', [])
                    queue_running = queue_info.get('queue_running', [])
                    
                    if queue_pending or queue_running:
                        queue_text = f"📊 **Queue Status:**\n"
                        if queue_running:
                            queue_text += f"🔄 Đang chạy: {len(queue_running)} task(s)\n"
                        if queue_pending:
                            queue_text += f"⏳ Đang chờ: {len(queue_pending)} task(s)\n"
                        
                        await processing_msg.edit_text(
                            f"🔄 Đang xử lý ảnh...\n\n{queue_text}\n⏱️ Vui lòng chờ...",
                            parse_mode=ParseMode.MARKDOWN
                        )
                except Exception as e:
                    logger.warning(f"Could not get queue info: {e}")
                
                # Định nghĩa progress callback để cập nhật tin nhắn
                async def progress_callback(progress_info):
                    try:
                        if not processing_msg:
                            return
                            
                        # Lấy thông tin progress
                        current_step = progress_info.get('value', 0)
                        max_steps = progress_info.get('max', 1)
                        node_name = progress_info.get('node', 'Unknown')
                        
                        # Tính phần trăm
                        if max_steps > 0:
                            percentage = int((current_step / max_steps) * 100)
                        else:
                            percentage = 0
                        
                        # Tạo progress bar
                        progress_bar = "█" * (percentage // 10) + "░" * (10 - percentage // 10)
                        
                        # Cập nhật tin nhắn với progress
                        progress_text = f"🔄 **Đang xử lý ảnh...**\n\n"
                        progress_text += f"📊 **Progress:** {progress_bar} {percentage}%\n"
                        progress_text += f"🎯 **Node:** {node_name}\n"
                        progress_text += f"⏱️ **Step:** {current_step}/{max_steps}\n\n"
                        progress_text += f"⏳ Vui lòng chờ..."
                        
                        await processing_msg.edit_text(
                            progress_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.warning(f"Could not update progress: {e}")
                
                # Sử dụng method mới với progress callback
                result_filename = await self._process_with_progress(
                    client, local_path, prompt, progress_callback
                )

                # Tải ảnh kết quả từ ComfyUI
                img_bytes = client.get_image(result_filename)

            if processing_msg:
                await processing_msg.delete()

            # Upload ảnh kết quả lên storage để lấy URL
            try:
                public_url = await self.storage.upload_image(img_bytes, result_filename, content_type="image/png")
            except Exception:
                # Nếu upload lỗi, gửi ảnh trực tiếp như fallback
                await update.message.reply_photo(
                    photo=BytesIO(img_bytes),
                    caption=f"🎨 Ảnh đã được phục hồi!\n\nPrompt: {prompt}"
                )
            else:
                # Gửi ảnh qua URL
                await update.message.reply_photo(
                    photo=public_url,
                    caption=f"🎨 Ảnh đã được phục hồi!\n\nPrompt: {prompt}"
                )

            self.user_sessions[user_id]['waiting_for_prompt'] = False
            if 'photo_file_id' in self.user_sessions[user_id]:
                del self.user_sessions[user_id]['photo_file_id']

        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            
            # Xóa processing message nếu có
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
            
            # Phân loại lỗi kết nối ComfyUI để báo rõ ràng
            msg = str(e)
            if "Failed to queue prompt" in msg or "Network error queueing prompt" in msg or "Timeout" in msg:
                friendly = (
                    "❌ Không thể kết nối ComfyUI.\n\n"
                    "- Kiểm tra COMFYUI_SERVER_URL (không dùng localhost nếu bot chạy khác máy).\n"
                    "- Đảm bảo ComfyUI đang chạy và mở port 8188.\n"
                    "- Kiểm tra firewall hoặc Docker network."
                )
            else:
                friendly = f"❌ Đã xảy ra lỗi: {msg}"
            await update.message.reply_text(friendly)
    
    async def _process_with_progress(self, client: ComfyUIClient, local_path: str, prompt: str, progress_callback):
        """Xử lý ảnh với progress tracking"""
        try:
            # 1) Upload ảnh lên ComfyUI server với unique filename
            if not local_path:
                raise Exception("input_image_path is required")
            
            # Tạo unique filename để tránh conflict
            import time
            import uuid
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            original_filename = os.path.basename(local_path)
            name, ext = os.path.splitext(original_filename)
            unique_filename = f"{name}_{timestamp}_{unique_id}{ext}"
            
            # Upload lên ComfyUI server
            url = f"{client.server_url.rstrip('/')}/upload/image"
            with open(local_path, "rb") as f:
                files = {"image": (unique_filename, f, "application/octet-stream")}
                response = requests.post(url, files=files)
                response.raise_for_status()
            
            image_filename = unique_filename
            logger.info(f"Uploaded image with unique name: {image_filename}")
            
            # 2) Clear cache ComfyUI để đảm bảo workflow chạy đầy đủ
            client.clear_cache()

            # 3) Đọc workflow gốc từ Restore.json
            with open("workflows/Restore.json", "r", encoding="utf-8") as f:
                workflow = json.loads(f.read())
            
            # 4) Chỉ thay đổi 2 thứ: ảnh input và prompt
            workflow["75"]["inputs"]["image"] = image_filename
            workflow["60"]["inputs"]["text_b"] = prompt
            
            logger.info(f"Updated LoadImage node 75: '{image_filename}'")
            logger.info(f"Updated StringFunction node 60 with prompt: {prompt}")

            # 5) Gửi workflow và đợi kết quả với progress tracking
            prompt_id = client.queue_prompt(workflow)
            logger.info(f"Queued prompt {prompt_id}, waiting for completion...")
            
            # Sử dụng method mới với progress callback
            result = await self._wait_for_completion_with_progress(
                client, prompt_id, progress_callback
            )
            
            logger.info(f"Workflow completed successfully")

            # 6) Lấy ảnh kết quả
            outputs = result.get("outputs", {}) or {}
            preferred = None
            fallback = None
            any_image = None
            
            for node_id, out in outputs.items():
                if not isinstance(out, dict):
                    continue
                images = out.get("images") or []
                if not images:
                    continue
                filename = images[0].get("filename")
                if not filename:
                    continue
                
                # Lưu ảnh đầu tiên làm fallback
                if any_image is None:
                    any_image = (node_id, filename)
                
                # Ưu tiên node 18 (RESULT)
                if str(node_id) == "18":
                    preferred = (node_id, filename)
                
                # Fallback không phải node 19 (ORIGINAL)
                if str(node_id) != "19" and fallback is None:
                    fallback = (node_id, filename)

            if preferred:
                logger.info(f"Using RESULT from node {preferred[0]}: {preferred[1]}")
                return preferred[1]
            if fallback:
                logger.info(f"Using non-ORIGINAL image from node {fallback[0]}: {fallback[1]}")
                return fallback[1]
            if any_image:
                logger.info(f"Using first available image from node {any_image[0]}: {any_image[1]}")
                return any_image[1]
            
            raise Exception("Không tìm thấy ảnh output trong kết quả.")

        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            raise
    
    async def _wait_for_completion_with_progress(self, client: ComfyUIClient, prompt_id: str, progress_callback, timeout: int = 300):
        """Đợi cho đến khi xử lý hoàn tất với progress tracking"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Lấy thông tin progress
                progress_info = client.get_progress()
                
                # Gọi callback nếu có
                if progress_callback:
                    await progress_callback(progress_info)
                
                # Kiểm tra history
                history = client.get_history(prompt_id)
                
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    
                    if 'status' in prompt_data:
                        status = prompt_data['status']
                        
                        if status.get('status_str') == 'success':
                            return prompt_data
                        elif status.get('status_str') == 'error':
                            error_message = status.get('messages', ['Unknown error'])
                            raise Exception(f"ComfyUI processing failed: {error_message}")
                
                await asyncio.sleep(2)  # Đợi 2 giây trước khi kiểm tra lại
                
            except Exception as e:
                logger.error(f"Error waiting for completion: {str(e)}")
                raise
        
        raise Exception(f"Timeout waiting for ComfyUI completion after {timeout} seconds")
    
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
    
    bot = TelegramBot(bot_token)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
