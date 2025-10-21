import json
import os
import requests
import time
import uuid
import logging
from typing import Dict, Any, Optional
from config import config

logger = logging.getLogger(__name__)

class ComfyUIClient:
    def __init__(self, server_url: str = None):
        self.server_url = server_url or config.COMFYUI_SERVER_URL
        self.client_id = config.COMFYUI_CLIENT_ID
        # Timeout mặc định cho các request (giây)
        try:
            self.timeout = int(os.getenv("COMFYUI_TIMEOUT", "15"))
        except Exception:
            self.timeout = 15

    def health_check(self) -> bool:
        """Kiểm tra khả năng kết nối tới ComfyUI server.

        Trả về True nếu kết nối được, False nếu không.
        """
        try:
            # Dùng endpoint nhẹ để kiểm tra (history/0)
            url = f"{self.server_url}/history/0"
            response = requests.get(url, timeout=self.timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
        
    def clear_cache(self) -> bool:
        """Xóa cache ComfyUI để đảm bảo workflow chạy đầy đủ"""
        try:
            # Gửi request để clear cache
            url = f"{self.server_url}/system_stats"
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info("ComfyUI cache cleared")
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not clear cache: {e}")
            return False
        
    def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        """Gửi prompt đến ComfyUI và nhận về prompt_id"""
        try:
            p = {"prompt": prompt, "client_id": self.client_id}
            
            response = requests.post(
                f"{self.server_url}/prompt",
                json=p,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            logger.info(f"API Response Headers: {response.headers}")
            logger.info(f"API Response Text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result['prompt_id']
                logger.info(f"Prompt queued successfully with ID: {prompt_id}")
                return prompt_id
            else:
                error_msg = f"Failed to queue prompt: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error queueing prompt: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error queueing prompt: {str(e)}")
            raise
    

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = None) -> bytes:
        """Lấy ảnh từ ComfyUI server"""
        try:
            # Thử tìm trong temp folder trước
            folder_types = ["temp", "output"] if folder_type is None else [folder_type]
            
            for ft in folder_types:
                data = {"filename": filename, "subfolder": subfolder, "type": ft}
                url = f"{self.server_url}/view"
                
                response = requests.get(url, params=data, timeout=self.timeout)
                
                if response.status_code == 200:
                    logger.info(f"Found image in {ft} folder: {filename}")
                    return response.content
            
            raise Exception(f"Failed to get image from any folder: {filename}")
                
        except Exception as e:
            logger.error(f"Error getting image: {str(e)}")
            raise
    
    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Lấy lịch sử xử lý của prompt"""
        try:
            response = requests.get(f"{self.server_url}/history/{prompt_id}", timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get history: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            raise
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Lấy thông tin queue hiện tại của ComfyUI"""
        try:
            response = requests.get(f"{self.server_url}/queue", timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get queue status: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            raise
    
    def get_progress(self) -> Dict[str, Any]:
        """Lấy thông tin progress hiện tại của ComfyUI"""
        try:
            response = requests.get(f"{self.server_url}/progress", timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get progress: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting progress: {str(e)}")
            raise
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Đợi cho đến khi xử lý hoàn tất"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                history = self.get_history(prompt_id)
                
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    
                    if 'status' in prompt_data:
                        status = prompt_data['status']
                        
                        if status.get('status_str') == 'success':
                            return prompt_data
                        elif status.get('status_str') == 'error':
                            error_message = status.get('messages', ['Unknown error'])
                            raise Exception(f"ComfyUI processing failed: {error_message}")
                
                time.sleep(2)  # Đợi 2 giây trước khi kiểm tra lại
                
            except Exception as e:
                logger.error(f"Error waiting for completion: {str(e)}")
                raise
        
        raise Exception(f"Timeout waiting for ComfyUI completion after {timeout} seconds")
    
    def wait_for_completion_with_progress(self, prompt_id: str, progress_callback=None, timeout: int = 300) -> Dict[str, Any]:
        """Đợi cho đến khi xử lý hoàn tất với callback để hiển thị progress"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Lấy thông tin progress
                progress_info = self.get_progress()
                
                # Gọi callback nếu có
                if progress_callback:
                    progress_callback(progress_info)
                
                # Kiểm tra history
                history = self.get_history(prompt_id)
                
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    
                    if 'status' in prompt_data:
                        status = prompt_data['status']
                        
                        if status.get('status_str') == 'success':
                            return prompt_data
                        elif status.get('status_str') == 'error':
                            error_message = status.get('messages', ['Unknown error'])
                            raise Exception(f"ComfyUI processing failed: {error_message}")
                
                time.sleep(2)  # Đợi 2 giây trước khi kiểm tra lại
                
            except Exception as e:
                logger.error(f"Error waiting for completion: {str(e)}")
                raise
        
        raise Exception(f"Timeout waiting for ComfyUI completion after {timeout} seconds")
    

    def process_image_recovery(self, input_image_path: str, prompt: str, 
                             strength: float = 0.8, steps: int = 20, 
                             guidance_scale: float = 7.5, seed: Optional[int] = None) -> str:
        """Xử lý phục hồi ảnh với ComfyUI sử dụng Restore.json gốc.
        
        Chỉ thay đổi:
        - Node 75 (LoadImage): filename ảnh input
        - Node 60 (StringFunction|pysssss): text_b prompt
        
        Args:
            input_image_path: Đường dẫn ảnh input
            prompt: Prompt từ user
            strength: Không sử dụng (giữ nguyên workflow gốc)
            steps: Không sử dụng (giữ nguyên workflow gốc)
            guidance_scale: Không sử dụng (giữ nguyên workflow gốc)
            seed: Không sử dụng (giữ nguyên workflow gốc)
            
        Returns:
            Tên file ảnh kết quả trên ComfyUI server
        """
        try:
            logger.info(f"=== PROCESSING IMAGE RECOVERY ===")
            logger.info(f"Input image path: {input_image_path}")
            logger.info(f"User prompt: '{prompt}'")
            logger.info("Using original Restore.json parameters (no changes to seed, steps, cfg, guidance)")

            # 1) Upload ảnh lên ComfyUI server với unique filename
            if not input_image_path:
                raise Exception("input_image_path is required")
            
            # Tạo unique filename để tránh conflict
            import time
            import uuid
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            original_filename = os.path.basename(input_image_path)
            name, ext = os.path.splitext(original_filename)
            unique_filename = f"{name}_{timestamp}_{unique_id}{ext}"
            
            # Upload lên ComfyUI server
            url = f"{self.server_url.rstrip('/')}/upload/image"
            with open(input_image_path, "rb") as f:
                files = {"image": (unique_filename, f, "application/octet-stream")}
                response = requests.post(url, files=files)
                response.raise_for_status()
            
            # Kiểm tra response để đảm bảo upload thành công
            logger.info(f"Upload response status: {response.status_code}")
            logger.info(f"Upload response text: {response.text}")
            
            image_filename = unique_filename
            logger.info(f"Uploaded image with unique name: {image_filename}")
            
            # Kiểm tra xem file có tồn tại trên ComfyUI không
            try:
                check_url = f"{self.server_url}/view"
                check_params = {"filename": image_filename, "type": "input"}
                check_response = requests.get(check_url, params=check_params, timeout=5)
                if check_response.status_code == 200:
                    logger.info(f"✅ File {image_filename} exists on ComfyUI server")
                else:
                    logger.warning(f"⚠️ File {image_filename} not found on ComfyUI server")
            except Exception as e:
                logger.warning(f"Could not verify file existence: {e}")
            
            # 2) Upload backup lên Firebase Storage để lưu trữ
            try:
                with open(input_image_path, "rb") as f:
                    image_bytes = f.read()
                
                from storage_service import get_storage_service
                storage = get_storage_service()
                
                # Upload backup với path: input/{unique_filename}
                firebase_path = f"input/{unique_filename}"
                import asyncio
                image_url = asyncio.run(storage.upload_image(
                    image_bytes, 
                    firebase_path, 
                    content_type="image/jpeg"
                ))
                
                logger.info(f"Backup uploaded to Firebase: {firebase_path}")
                logger.info(f"Firebase URL: {image_url}")
            except Exception as e:
                logger.warning(f"Failed to upload backup to Firebase: {e}")

            # 2) Clear cache ComfyUI để đảm bảo workflow chạy đầy đủ
            self.clear_cache()

            # 3) Đọc workflow gốc từ Restore.json (tạo bản copy mới mỗi lần)
            with open("workflows/Restore.json", "r", encoding="utf-8") as f:
                workflow = json.loads(f.read())  # Đảm bảo tạo object mới
            
            # 4) Chỉ thay đổi 2 thứ: ảnh input và prompt
            # Lưu filename cũ để debug
            old_filename = workflow["75"]["inputs"]["image"]
            workflow["75"]["inputs"]["image"] = image_filename  # Sử dụng ComfyUI filename
            workflow["60"]["inputs"]["text_b"] = prompt
            
            logger.info(f"Updated LoadImage node 75: '{old_filename}' -> '{image_filename}'")
            logger.info(f"Updated StringFunction node 60 with prompt: {prompt}")
            logger.info(f"Workflow contains {len(workflow)} nodes")
            
            # Debug: Kiểm tra node 75 có đúng không
            logger.info(f"Node 75 inputs: {workflow['75']['inputs']}")

            # 5) Gửi workflow và đợi kết quả
            prompt_id = self.queue_prompt(workflow)
            logger.info(f"Queued prompt {prompt_id}, waiting for completion...")
            result = self.wait_for_completion(prompt_id)
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
