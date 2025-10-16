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
        
        # Thử load workflow từ file JSON trước
        workflow_file = "workflows/Restore.json"
        try:
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
                logger.info(f"Loaded workflow from {workflow_file}")
                
                # Cập nhật parameters trong workflow
                self._update_workflow_parameters(workflow, input_image_path, prompt, 
                                               strength, steps, guidance_scale, seed)
                return workflow
        except FileNotFoundError:
            logger.warning(f"Workflow file {workflow_file} not found, using default workflow")
        except Exception as e:
            logger.error(f"Error loading workflow: {e}, using default workflow")
        
        # Fallback: sử dụng workflow mặc định
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
    
    def _update_workflow_parameters(self, workflow: Dict[str, Any], input_image_path: str, 
                                   prompt: str, strength: float, steps: int, 
                                   guidance_scale: float, seed: Optional[int]) -> None:
        """Cập nhật parameters trong workflow"""
        
        # Xử lý format workflow thực tế của ComfyUI
        if "nodes" in workflow:
            # Format mới: {"nodes": [...], "links": [...]}
            for node in workflow["nodes"]:
                node_type = node.get("type", "")
                
                if node_type == "LoadImage":
                    # Cập nhật đường dẫn ảnh input
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        node["widgets_values"][0] = input_image_path
                    
                elif node_type == "CLIPTextEncode":
                    # Cập nhật prompt
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        # Tìm node có prompt về restore
                        current_text = node["widgets_values"][0]
                        if "restore" in current_text.lower() or "photo" in current_text.lower():
                            node["widgets_values"][0] = prompt
                    
                elif node_type == "KSampler":
                    # Cập nhật sampling parameters
                    if "widgets_values" in node:
                        if len(node["widgets_values"]) >= 6:
                            if seed is not None:
                                node["widgets_values"][0] = seed
                            node["widgets_values"][2] = steps
                            node["widgets_values"][3] = guidance_scale
                    
                elif "ControlNetApply" in node_type:
                    # Cập nhật strength
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        node["widgets_values"][0] = strength
        else:
            # Format cũ: {"1": {...}, "2": {...}}
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "LoadImage":
                    # Cập nhật đường dẫn ảnh input
                    node_data["inputs"]["image"] = input_image_path
                    
                elif node_data.get("class_type") == "CLIPTextEncode":
                    # Cập nhật prompt (thường là node đầu tiên)
                    if "text" in node_data["inputs"] and not node_data["inputs"]["text"]:
                        node_data["inputs"]["text"] = prompt
                        
                elif node_data.get("class_type") == "KSampler":
                    # Cập nhật sampling parameters
                    node_data["inputs"]["steps"] = steps
                    node_data["inputs"]["cfg"] = guidance_scale
                    if seed is not None:
                        node_data["inputs"]["seed"] = seed
                        
                elif node_data.get("class_type") == "ControlNetApply":
                    # Cập nhật strength
                    node_data["inputs"]["strength"] = strength
