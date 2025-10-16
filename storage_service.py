import os
import logging
from typing import Optional
from abc import ABC, abstractmethod
from config import config

logger = logging.getLogger(__name__)

class StorageService(ABC):
    """Abstract base class cho storage service"""
    
    @abstractmethod
    async def upload_image(self, image_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
        """Upload ảnh và trả về URL"""
        pass

class FirebaseStorageService(StorageService):
    """Firebase Storage implementation"""
    
    def __init__(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, storage
            
            if not firebase_admin._apps:
                if config.FIREBASE_CREDENTIALS_PATH and os.path.exists(config.FIREBASE_CREDENTIALS_PATH):
                    cred = credentials.Certificate(config.FIREBASE_CREDENTIALS_PATH)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': config.FIREBASE_STORAGE_BUCKET
                    })
                else:
                    # Sử dụng default credentials (cho production)
                    firebase_admin.initialize_app()
            
            self.bucket = storage.bucket()
            logger.info("Firebase Storage initialized successfully")
            
        except ImportError:
            raise Exception("firebase-admin package not installed. Run: pip install firebase-admin")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Storage: {str(e)}")
            raise
    
    async def upload_image(self, image_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
        """Upload ảnh lên Firebase Storage"""
        try:
            import firebase_admin
            from firebase_admin import storage
            
            # Tạo blob reference
            blob_name = f"recovered_images/{filename}"
            blob = self.bucket.blob(blob_name)
            
            # Upload image
            blob.upload_from_string(
                image_bytes,
                content_type=content_type
            )
            
            # Làm cho file public (tùy chọn)
            blob.make_public()
            
            # Trả về public URL
            public_url = blob.public_url
            logger.info(f"Image uploaded to Firebase Storage: {public_url}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload image to Firebase Storage: {str(e)}")
            raise


def get_storage_service() -> StorageService:
    """Factory function để tạo storage service - chỉ sử dụng Firebase"""
    try:
        logger.info("Initializing Firebase Storage service...")
        return FirebaseStorageService()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Storage: {str(e)}")
        raise Exception("Cannot initialize Firebase Storage service")
