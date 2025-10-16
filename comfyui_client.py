import json
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
            data = json.dumps(p).encode('utf-8')
            
            response = requests.post(
                f"{self.server_url}/prompt",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result['prompt_id']
                logger.info(f"Prompt queued successfully with ID: {prompt_id}")
                return prompt_id
            else:
                raise Exception(f"Failed to queue prompt: {response.text}")
                
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
    
    def process_image_recovery(self, input_image_path: str, prompt: str, 
                             strength: float = 0.8, steps: int = 20, 
                             guidance_scale: float = 7.5, seed: Optional[int] = None) -> str:
        """Xử lý phục hồi ảnh với ComfyUI"""
        try:
            # Tạo workflow cho phục hồi ảnh
            workflow = self._create_recovery_workflow(
                input_image_path, prompt, strength, steps, guidance_scale, seed
            )
            
            # Gửi prompt đến ComfyUI
            prompt_id = self.queue_prompt(workflow)
            
            # Đợi hoàn tất
            result = self.wait_for_completion(prompt_id)
            
            # Lấy tên file ảnh kết quả
            outputs = result.get('outputs', {})
            for node_id, output_data in outputs.items():
                if 'images' in output_data:
                    images = output_data['images']
                    if images:
                        filename = images[0]['filename']
                        return filename
            
            raise Exception("Không tìm thấy ảnh kết quả trong output")
            
        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            raise
    
    def _create_recovery_workflow(self, input_image_path: str, prompt: str,
                                strength: float, steps: int, guidance_scale: float,
                                seed: Optional[int]) -> Dict[str, Any]:
        """Tạo workflow cho phục hồi ảnh"""
        
        # Đây là một ví dụ workflow cơ bản cho phục hồi ảnh
        # Bạn cần điều chỉnh theo workflow thực tế của ComfyUI
        workflow = {
            "1": {
                "inputs": {
                    "image": input_image_path,
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {
                    "title": "Load Image"
                }
            },
            "2": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "3": {
                "inputs": {
                    "text": "",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "4": {
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "Load Checkpoint"
                }
            },
            "5": {
                "inputs": {
                    "conditioning_1": ["2", 0],
                    "conditioning_2": ["3", 0],
                    "model": ["4", 0],
                    "control_net": ["6", 0],
                    "image": ["1", 0],
                    "strength": strength
                },
                "class_type": "ControlNetApply",
                "_meta": {
                    "title": "Apply ControlNet"
                }
            },
            "6": {
                "inputs": {
                    "control_net_name": "control_v11p_sd15_inpaint.pth"
                },
                "class_type": "ControlNetLoader",
                "_meta": {
                    "title": "Load ControlNet Model"
                }
            },
            "7": {
                "inputs": {
                    "seed": seed if seed is not None else 123456789,
                    "steps": steps,
                    "cfg": guidance_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["5", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["8", 0]
                },
                "class_type": "KSampler",
                "_meta": {
                    "title": "KSampler"
                }
            },
            "8": {
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "9": {
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "10": {
                "inputs": {
                    "filename_prefix": "recovered_image",
                    "images": ["9", 0]
                },
                "class_type": "SaveImage",
                "_meta": {
                    "title": "Save Image"
                }
            }
        }
        
        return workflow
