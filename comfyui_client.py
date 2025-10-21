import json
import os
import requests
import time
import websocket
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
    
    def process_image_recovery_exact(self, input_image_path: str, prompt: Optional[str] = None) -> str:
        """Chạy workflow trực tiếp từ API JSON format (workflows/Restore.json).
        
        Chỉ thay đổi các thông số cần thiết:
        - Node 75 (LoadImage): filename của ảnh input
        - Node 60 (StringFunction|pysssss): text_b với prompt từ user

        Trả về filename ảnh kết quả trên server ComfyUI.
        """
        try:
            # 1) Đọc workflow API JSON gốc
            workflow_file = "workflows/Restore.json"
            with open(workflow_file, "r", encoding="utf-8") as f:
                api_workflow = json.load(f)

            # 2) Upload ảnh input lên ComfyUI để có filename trên server
            if not input_image_path:
                raise Exception("input_image_path is required")
            
            # Upload ảnh lên ComfyUI
            url = f"{self.server_url.rstrip('/')}/upload/image"
            filename = os.path.basename(input_image_path)
            with open(input_image_path, "rb") as f:
                files = {"image": (filename, f, "application/octet-stream")}
                response = requests.post(url, files=files)
                response.raise_for_status()
            
            # Kiểm tra response để đảm bảo upload thành công
            logger.info(f"Upload response status: {response.status_code}")
            logger.info(f"Upload response text: {response.text}")
            
            image_filename = filename
            logger.info(f"Uploaded image: {image_filename}")

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

            # 3) Tạo bản copy và ghi đè parameters cần thiết
            workflow_copy = json.loads(json.dumps(api_workflow))
            
            # Ghi đè filename trong node LoadImage (node 75)
            if "75" in workflow_copy:
                workflow_copy["75"]["inputs"]["image"] = image_filename
                logger.info(f"Updated LoadImage node 75 with filename: {image_filename}")
            
            # Ghi đè prompt trong node StringFunction|pysssss (node 60)
            if "60" in workflow_copy and prompt:
                workflow_copy["60"]["inputs"]["text_b"] = prompt
                logger.info(f"Updated StringFunction node 60 with prompt: {prompt}")

            # 4) Gửi prompt và đợi hoàn tất
            prompt_id = self.queue_prompt(workflow_copy)
            result = self.wait_for_completion(prompt_id)

            # 5) Chọn filename ảnh output (ưu tiên node 18 RESULT, tránh node 19 ORIGINAL)
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
                # lưu bất kỳ ảnh nào để fallback cuối cùng
                if any_image is None:
                    any_image = (node_id, filename)
                # ưu tiên node 18
                if str(node_id) == "18":
                    preferred = (node_id, filename)
                # chọn ảnh không phải node 19 làm fallback cấp 1
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
            logger.error(f"Error in process_image_recovery_exact: {str(e)}")
            raise

    def create_workflow_template(self, template_file: str = "workflows/Restore_template.json") -> Dict[str, Any]:
        """Tạo template workflow với placeholder để dễ dàng thay đổi parameters.
        
        Args:
            template_file: Đường dẫn đến file template JSON
            
        Returns:
            Dict chứa workflow template với các placeholder
        """
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                template = json.load(f)
            
            logger.info("Loaded workflow template with placeholders")
            return template
            
        except Exception as e:
            logger.error(f"Error creating workflow template: {str(e)}")
            raise

    def apply_template_values(self, template: Dict[str, Any], 
                            image_filename: str, 
                            user_prompt: str,
                            **kwargs) -> Dict[str, Any]:
        """Áp dụng giá trị thực tế vào template workflow bằng string replacement.
        
        Args:
            template: Template workflow với placeholder
            image_filename: Tên file ảnh input
            user_prompt: Prompt từ user
            **kwargs: Các thông số khác có thể thay đổi (seed, steps, cfg, etc.)
            
        Returns:
            Workflow đã được điền giá trị thực tế
        """
        try:
            # Tạo bản copy để không thay đổi template gốc
            workflow = json.loads(json.dumps(template))
            
            # Tạo mapping các placeholder - chỉ thay thế khi có giá trị mới
            replacements = {
                "__IMAGE_FILENAME__": image_filename,
                "__USER_PROMPT__": user_prompt
            }
            
            # Chỉ thay thế seed nếu được cung cấp
            if "seed" in kwargs and kwargs["seed"] is not None:
                replacements["__SEED__"] = str(kwargs["seed"])
                replacements["__SEED_2__"] = str(kwargs["seed"])
            
            # Chỉ thay thế steps nếu được cung cấp
            if "steps" in kwargs:
                replacements["__STEPS__"] = str(kwargs["steps"])
                replacements["__STEPS_2__"] = str(kwargs["steps"])
            
            # Chỉ thay thế cfg nếu được cung cấp
            if "cfg" in kwargs:
                replacements["__CFG__"] = str(kwargs["cfg"])
                replacements["__CFG_2__"] = str(kwargs["cfg"])
            
            # Chỉ thay thế guidance nếu được cung cấp
            if "guidance" in kwargs:
                replacements["__GUIDANCE__"] = str(kwargs["guidance"])
            
            # Thực hiện string replacement trên toàn bộ workflow
            workflow_str = json.dumps(workflow)
            for placeholder, value in replacements.items():
                workflow_str = workflow_str.replace(placeholder, value)
            
            # Parse lại thành dict
            workflow = json.loads(workflow_str)
            
            # Đặt giá trị mặc định cho các placeholder không được thay thế
            if "__SEED__" in workflow_str:
                workflow["3"]["inputs"]["seed"] = 60747213359817
            if "__SEED_2__" in workflow_str:
                workflow["72"]["inputs"]["seed"] = 1119116492091272
            if "__STEPS__" in workflow_str:
                workflow["3"]["inputs"]["steps"] = 8
            if "__STEPS_2__" in workflow_str:
                workflow["72"]["inputs"]["steps"] = 8
            if "__CFG__" in workflow_str:
                workflow["3"]["inputs"]["cfg"] = 1.5
            if "__CFG_2__" in workflow_str:
                workflow["72"]["inputs"]["cfg"] = 1.0
            if "__GUIDANCE__" in workflow_str:
                workflow["80"]["inputs"]["guidance"] = 1.8
            
            logger.info(f"Applied template values: image={image_filename}, prompt={user_prompt}")
            logger.info(f"Applied parameters: {kwargs}")
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error applying template values: {str(e)}")
            raise

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
