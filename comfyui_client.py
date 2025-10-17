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
            logger.info(f"=== PROCESSING IMAGE RECOVERY ===")
            logger.info(f"Input image path: {input_image_path}")
            logger.info(f"User prompt: '{prompt}'")
            logger.info(f"Strength: {strength}, Steps: {steps}, Guidance: {guidance_scale}, Seed: {seed}")

            # Tạo workflow cho phục hồi ảnh

            workflow = self._create_recovery_workflow(

                input_image_path, prompt, strength, steps, guidance_scale, seed

            )

            logger.info(f"Created workflow with {len(workflow)} nodes")

            # Gửi prompt đến ComfyUI

            prompt_id = self.queue_prompt(workflow)

            

            # Đợi hoàn tất

            result = self.wait_for_completion(prompt_id)

            
            # Debug: Log structure của result
            logger.info(f"Result structure: {result}")
            

            # Lấy tên file ảnh kết quả

            outputs = result.get('outputs', {})

            logger.info(f"Outputs: {outputs}")
            
            # Tìm ảnh trong các output nodes - ưu tiên node 18 (RESULT) trước
            image_nodes = []
            for node_id, output_data in outputs.items():
                logger.info(f"Node {node_id}: {output_data}")
                if 'images' in output_data:
                    images = output_data['images']
                    logger.info(f"Images in node {node_id}: {images}")
                    if images:
                        filename = images[0]['filename']
                        logger.info(f"Found image filename in node {node_id}: {filename}")
                        image_nodes.append((int(node_id), filename))
            
            # Ưu tiên node 18 (RESULT) trước, sau đó node 19 (ORIGINAL IMAGE)
            if image_nodes:
                # Tìm node 18 trước (RESULT)
                for node_id, filename in image_nodes:
                    if node_id == 18:
                        logger.info(f"Selected RESULT image from node 18: {filename}")
                        return filename
                
                # Nếu không có node 18, lấy node đầu tiên
                final_node_id, final_filename = image_nodes[0]
                logger.info(f"Selected image from node {final_node_id}: {final_filename}")
                return final_filename

            

            # Nếu không tìm thấy trong outputs, có thể ảnh được lưu ở chỗ khác
            logger.error(f"No images found in outputs. Full result: {result}")
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

                

            # Cập nhật parameters trong workflow và convert format
            converted_workflow = self._update_workflow_parameters(workflow, input_image_path, prompt, 
                                               strength, steps, guidance_scale, seed)

            return converted_workflow
        except FileNotFoundError:

            logger.warning(f"Workflow file {workflow_file} not found, using default workflow")

        except Exception as e:

            logger.error(f"Error loading workflow: {e}, using default workflow")

        

        # Fallback: sử dụng workflow mặc định

        fallback_workflow = {
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

        

        return fallback_workflow
    

    def _update_workflow_parameters(self, workflow: Dict[str, Any], input_image_path: str, 

                                   prompt: str, strength: float, steps: int, 

                                   guidance_scale: float, seed: Optional[int]) -> Dict[str, Any]:
        """Cập nhật parameters trong workflow và convert sang format API"""
        

        # Xử lý format workflow thực tế của ComfyUI

        if "nodes" in workflow:

            # Format mới: {"nodes": [...], "links": [...]} - cần convert sang format cũ
            converted_workflow = {}
            
            for node in workflow["nodes"]:

                node_id = str(node.get("id", ""))
                node_type = node.get("type", "")

                

                # Convert sang format cũ cho API
                converted_node = {
                    "class_type": node_type,
                    "inputs": {},
                    "_meta": {"title": node_type}
                }
                
                # Cập nhật parameters đặc biệt
                if node_type == "LoadImage":

                    # Cập nhật đường dẫn ảnh input

                    converted_node["inputs"]["image"] = input_image_path
                    

                elif node_type == "CLIPTextEncode":
                    # Giữ nguyên TẤT CẢ CLIPTextEncode nodes như trong workflow
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        current_text = node["widgets_values"][0]
                        logger.info(f"CLIPTextEncode node {node_id}: KEEPING ORIGINAL = '{current_text[:100]}...'")
                        converted_node["inputs"]["text"] = current_text
                
                elif node_type == "StringFunction|pysssss":
                    # Cập nhật text_b (user prompt) trong node 60, giữ nguyên text_a và text_c
                    if "widgets_values" in node and len(node["widgets_values"]) >= 5:
                        widgets = node["widgets_values"]
                        logger.info(f"StringFunction node {node_id}: widgets = {widgets}")
                        logger.info(f"StringFunction node {node_id}: USER INPUT - Setting text_b = '{prompt}'")
                        logger.info(f"StringFunction node {node_id}: KEEPING ORIGINAL - text_a = '{widgets[2]}', text_c = '{widgets[4]}'")
                        converted_node["inputs"]["action"] = widgets[0]      # "append"
                        converted_node["inputs"]["tidy_tags"] = widgets[1]  # "yes" 
                        converted_node["inputs"]["text_a"] = widgets[2]     # KEEP ORIGINAL
                        converted_node["inputs"]["text_b"] = prompt         # USER PROMPT
                        converted_node["inputs"]["text_c"] = widgets[4]     # KEEP ORIGINAL
                    

                elif node_type == "KSampler":

                    # Giữ nguyên tham số mặc định trong workflow (không chỉnh sửa tại đây)
                    pass

                elif "ControlNetApply" in node_type:

                    # Giữ nguyên strength/start/end mặc định trong workflow (không chỉnh sửa tại đây)
                    pass
                
                # Thêm các inputs khác từ widgets_values
                if "widgets_values" in node and node["widgets_values"]:
                    widgets = node["widgets_values"]
                    
                    # Xử lý các widget inputs dựa trên node type
                    if node_type == "SetUnionControlNetType":
                        if len(widgets) >= 1:
                            logger.info(f"SetUnionControlNetType node {node_id}: Setting type = '{widgets[0]}'")
                            converted_node["inputs"]["type"] = widgets[0]
                    
                    elif node_type == "ControlNetLoader":
                        if len(widgets) >= 1:
                            logger.info(f"ControlNetLoader node {node_id}: Setting control_net_name = '{widgets[0]}'")
                            converted_node["inputs"]["control_net_name"] = widgets[0]
                    
                    elif node_type == "CheckpointLoaderSimple":
                        if len(widgets) >= 1:
                            logger.info(f"CheckpointLoaderSimple node {node_id}: Setting ckpt_name = '{widgets[0]}'")
                            converted_node["inputs"]["ckpt_name"] = widgets[0]
                    
                    elif node_type == "VAELoader":
                        if len(widgets) >= 1:
                            logger.info(f"VAELoader node {node_id}: Setting vae_name = '{widgets[0]}'")
                            converted_node["inputs"]["vae_name"] = widgets[0]
                    
                    elif node_type == "EmptyLatentImage":
                        if len(widgets) >= 3:
                            converted_node["inputs"]["width"] = widgets[0]
                            converted_node["inputs"]["height"] = widgets[1]
                            converted_node["inputs"]["batch_size"] = widgets[2]
                    
                    elif node_type == "ImageScaleToTotalPixels":
                        if len(widgets) >= 2:
                            converted_node["inputs"]["upscale_method"] = widgets[0]
                            converted_node["inputs"]["megapixels"] = widgets[1]
                    
                    elif "ControlNetApply" in node_type:
                        if len(widgets) >= 3:
                            converted_node["inputs"]["start_percent"] = widgets[1]
                            converted_node["inputs"]["end_percent"] = widgets[2]
                    
                    elif node_type == "LoraLoader":
                        if len(widgets) >= 3:
                            logger.info(f"LoraLoader node {node_id}: Setting lora_name = '{widgets[0]}', strength_model = {widgets[1]}, strength_clip = {widgets[2]}")
                            converted_node["inputs"]["lora_name"] = widgets[0]
                            converted_node["inputs"]["strength_model"] = widgets[1]
                            converted_node["inputs"]["strength_clip"] = widgets[2]
                    
                    elif node_type == "easy imageSizeByLongerSide":
                        if len(widgets) >= 1:
                            converted_node["inputs"]["resolution"] = widgets[0]
                    
                    elif node_type == "easy float":
                        if len(widgets) >= 1:
                            logger.info(f"easy float node {node_id}: USING DEFAULT value={widgets[0]}")
                            converted_node["inputs"]["value"] = widgets[0]
                    
                    elif node_type == "LayerFilter: GaussianBlurV2":
                        if len(widgets) >= 1:
                            logger.info(f"GaussianBlurV2 node {node_id}: USING DEFAULT blur={widgets[0]}")
                            converted_node["inputs"]["blur"] = widgets[0]
                    
                    elif node_type == "LayerFilter: AddGrain":
                        if len(widgets) >= 3:
                            logger.info(f"AddGrain node {node_id}: USING DEFAULTS power={widgets[0]}, scale={widgets[1]}, sat={widgets[2]}")
                            converted_node["inputs"]["grain_power"] = widgets[0]
                            converted_node["inputs"]["grain_scale"] = widgets[1]
                            converted_node["inputs"]["grain_sat"] = widgets[2]
                    
                    elif node_type == "FluxGuidance":
                        if len(widgets) >= 1:
                            logger.info(f"FluxGuidance node {node_id}: USING DEFAULT guidance={widgets[0]}")
                            converted_node["inputs"]["guidance"] = widgets[0]
                    
                    elif node_type == "ImageQuantize":
                        if len(widgets) >= 2:
                            converted_node["inputs"]["colors"] = widgets[0]
                            converted_node["inputs"]["dither"] = widgets[1]
                    
                    elif node_type == "LineArtPreprocessor":
                        if len(widgets) >= 2:
                            converted_node["inputs"]["coarse"] = widgets[0]
                            converted_node["inputs"]["resolution"] = widgets[1]
                    
                    elif node_type == "DepthAnythingV2Preprocessor":
                        if len(widgets) >= 2:
                            converted_node["inputs"]["ckpt_name"] = widgets[0]
                            converted_node["inputs"]["resolution"] = widgets[1]
                    
                    elif node_type == "LoraLoader":
                        if len(widgets) >= 5:
                            logger.info(f"LoraLoader node {node_id}: USING DEFAULTS lora={widgets[0]}, sm={widgets[1]}, sc={widgets[2]}")
                            converted_node["inputs"]["lora_name"] = widgets[0]
                            converted_node["inputs"]["strength_model"] = widgets[1]
                            converted_node["inputs"]["strength_clip"] = widgets[2]
                    
                    elif node_type == "NunchakuTextEncoderLoaderV2":
                        if len(widgets) >= 4:
                            logger.info(f"NunchakuTextEncoderLoaderV2 node {node_id}: Setting model_type = '{widgets[0]}', text_encoder1 = '{widgets[1]}', text_encoder2 = '{widgets[2]}', t5_min_length = {widgets[3]}")
                            converted_node["inputs"]["model_type"] = widgets[0]
                            converted_node["inputs"]["text_encoder1"] = widgets[1]
                            converted_node["inputs"]["text_encoder2"] = widgets[2]
                            converted_node["inputs"]["t5_min_length"] = widgets[3]
                    
                    elif node_type == "UNETLoader":
                        if len(widgets) >= 2:
                            logger.info(f"UNETLoader node {node_id}: USING DEFAULTS unet={widgets[0]}, dtype={widgets[1]}")
                            converted_node["inputs"]["unet_name"] = widgets[0]
                            converted_node["inputs"]["weight_dtype"] = widgets[1]
                
                # Thêm các inputs khác từ links
                converted_workflow[node_id] = converted_node
            
            # Xử lý links để thêm connections
            if "links" in workflow:
                for link in workflow["links"]:
                    if len(link) >= 6:
                        source_node_id = str(link[1])
                        source_slot = link[2]
                        target_node_id = str(link[3])
                        target_slot = link[4]
                        link_type = link[5]
                        
                        if target_node_id in converted_workflow:
                            # Tìm tên input thực tế từ target node
                            target_node = next((n for n in workflow["nodes"] if str(n["id"]) == target_node_id), None)
                            if target_node and "inputs" in target_node and target_slot < len(target_node["inputs"]):
                                input_name = target_node["inputs"][target_slot]["name"]
                                converted_workflow[target_node_id]["inputs"][input_name] = [source_node_id, source_slot]
            
            return converted_workflow
        else:

            # Format cũ: {"1": {...}, "2": {...}} - đã đúng format rồi
            for node_id, node_data in workflow.items():

                if node_data.get("class_type") == "LoadImage":

                    # Cập nhật đường dẫn ảnh input

                    node_data["inputs"]["image"] = input_image_path

                

                elif node_data.get("class_type") == "CLIPTextEncode":

                    # Giữ nguyên prompt mặc định trong workflow
                    pass
                

                elif node_data.get("class_type") == "KSampler":

                    # Giữ nguyên thông số sampler mặc định
                    pass
                

                elif node_data.get("class_type") == "ControlNetApply":

                    # Giữ nguyên strength mặc định
                    pass
                
                elif node_type == "VAEDecode":
                    # Giữ nguyên mặc định; mọi kết nối sẽ được map từ links phía dưới
                    logger.info(f"VAEDecode node {node_id}: KEEPING DEFAULTS (no widget values)")
                    pass

                elif node_type == "VAEEncode":
                    # Giữ nguyên mặc định; mọi kết nối sẽ được map từ links phía dưới
                    logger.info(f"VAEEncode node {node_id}: KEEPING DEFAULTS (no widget values)")
                    pass

                elif node_type == "VAELoader":
                    # Đã có xử lý lấy vae_name từ widgets_values ở phần dưới; không sửa gì thêm
                    logger.info(f"VAELoader node {node_id}: USING DEFAULTS FROM WORKFLOW")
                    pass
            
            return workflow

