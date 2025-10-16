import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    # ComfyUI Configuration
    COMFYUI_SERVER_URL = os.getenv("COMFYUI_SERVER_URL", "http://localhost:8188")
    COMFYUI_CLIENT_ID = os.getenv("COMFYUI_CLIENT_ID", "comfyui_client")
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,webp").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Storage backend - chỉ sử dụng Firebase
    STORAGE_BACKEND = "firebase"
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

config = Config()
