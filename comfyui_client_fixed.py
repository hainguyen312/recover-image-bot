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
        
    def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        """Gửi prompt đến ComfyUI và nhận về prompt_id"""
        try:
            p = {"prompt": prompt, "client_id": self.client_id}
            
            response = requests.post(
                f"{self.server_url}/prompt",
                json=p,
                headers={'Content-Type': 'application/json'}
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
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Lấy ảnh từ ComfyUI server"""
        try:
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            url = f"{self.server_url}/view"
            
            response = requests.get(url, params=data)
            
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Failed to get image: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting image: {str(e)}")
            raise
    
    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Lấy lịch sử xử lý của prompt"""
        try:
            response = requests.get(f"{self.server_url}/history/{prompt_id}")
            
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
        """Chạy workflow đúng theo JSON export gốc (workflows/Restore.json),
        chỉ ghi đè 2 chỗ: filename trong node LoadImage và text_b của node StringFunction|pysssss.

        Trả về filename ảnh kết quả trên server ComfyUI.
        """
        try:
            # 1) Đọc workflow export gốc
            workflow_file = "workflows/Restore.json"
            with open(workflow_file, "r", encoding="utf-8") as f:
                workflow = json.load(f)

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
            
            image_filename = filename
            logger.info(f"Uploaded image: {image_filename}")

            # 3) Ghi đè parameters trong workflow gốc (không convert format)
            workflow = self._apply_overrides_to_workflow(workflow, image_filename, prompt)

            # 4) Gửi prompt và đợi hoàn tất
            prompt_id = self.queue_prompt(workflow)
            result = self.wait_for_completion(prompt_id)

            # 5) Chọn filename ảnh output
            outputs = result.get("outputs", {}) or {}
            candidate = None
            for node_id, out in outputs.items():
                if not isinstance(out, dict):
                    continue
                images = out.get("images") or []
                if not images:
                    continue
                try:
                    nid = int(node_id)
                except Exception:
                    nid = -1
                filename = images[0].get("filename")
                if nid == 18 and filename:  # Ưu tiên node 18 (RESULT)
                    logger.info(f"Found result image in node 18: {filename}")
                    return filename
                if candidate is None and nid != 19 and filename:  # Loại node 19 (ORIGINAL IMAGE)
                    candidate = filename
            
            if candidate:
                logger.info(f"Using fallback result image: {candidate}")
                return candidate
            
            raise Exception("Không tìm thấy ảnh output trong kết quả.")

        except Exception as e:
            logger.error(f"Error in process_image_recovery_exact: {str(e)}")
            raise

    def _apply_overrides_to_workflow(self, workflow: Dict[str, Any], image_filename: Optional[str], prompt_text: Optional[str]) -> Dict[str, Any]:
        """Chỉ ghi đè 2 chỗ: filename của LoadImage và text_b của StringFunction|pysssss.
        
        Giữ nguyên workflow ở format export gốc để gửi trực tiếp đến ComfyUI API.
        """
        try:
            if not isinstance(workflow, dict) or "nodes" not in workflow:
                logger.warning("Workflow không có 'nodes', trả về nguyên bản")
                return workflow
            
            # Tạo bản copy để không thay đổi workflow gốc
            workflow_copy = json.loads(json.dumps(workflow))
            
            # Ghi đè parameters
            for node in workflow_copy["nodes"]:
                ntype = node.get("type")
                widgets = node.get("widgets_values")
                
                if ntype == "LoadImage" and image_filename and isinstance(widgets, list) and len(widgets) >= 1:
                    widgets[0] = image_filename  # Ghi đè filename
                    logger.info(f"Updated LoadImage node {node.get('id')} with filename: {image_filename}")
                    
                elif ntype == "StringFunction|pysssss" and prompt_text and isinstance(widgets, list) and len(widgets) >= 4:
                    # widgets: [action, tidy_tags, text_a, text_b, text_c]
                    widgets[3] = prompt_text  # Ghi đè text_b
                    logger.info(f"Updated StringFunction node {node.get('id')} with prompt: {prompt_text}")
            
            logger.info("Applied overrides to workflow successfully")
            return workflow_copy
            
        except Exception as e:
            logger.error(f"Error applying overrides to workflow: {str(e)}")
            raise

    def process_image_recovery(self, input_image_path: str, prompt: str, 
                             strength: float = 0.8, steps: int = 20, 
                             guidance_scale: float = 7.5, seed: Optional[int] = None) -> str:
        """Xử lý phục hồi ảnh với ComfyUI - sử dụng workflow Restore.json"""
        try:
            logger.info(f"=== PROCESSING IMAGE RECOVERY ===")
            logger.info(f"Input image path: {input_image_path}")
            logger.info(f"User prompt: '{prompt}'")
            logger.info(f"Strength: {strength}, Steps: {steps}, Guidance: {guidance_scale}, Seed: {seed}")

            # Sử dụng workflow từ Restore.json thay vì tạo mới
            return self.process_image_recovery_exact(input_image_path, prompt)

        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            raise
