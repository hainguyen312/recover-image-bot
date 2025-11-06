import json
import os
import requests
import time
import uuid
import logging
from typing import Dict, Any, Optional
from config import config

# websocket-client may not be installed in all environments; import safely
try:
    import websocket
except Exception:
    websocket = None

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
        """Xóa cache và giải phóng VRAM trên ComfyUI server.
        
        Thử các endpoint để:
        1. Free memory (/free)
        2. Unload models nếu có endpoint
        
        Returns:
            True nếu thành công, False nếu không
        """
        success = False
        
        # 1. Thử endpoint /free để giải phóng memory
        try:
            url = f"{self.server_url.rstrip('/')}/free"
            response = requests.post(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Successfully called /free endpoint to free memory")
                success = True
            else:
                logger.warning(f"⚠️ /free endpoint returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ /free endpoint not available or failed: {e}")
        
        # 2. Thử endpoint /system_stats để trigger cache clear (nếu có)
        # Lưu ý: endpoint này có thể có side effects nhưng có thể giúp clear cache
        try:
            url = f"{self.server_url.rstrip('/')}/system_stats"
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Successfully called /system_stats endpoint")
                success = True
        except requests.exceptions.RequestException as e:
            logger.debug(f"/system_stats endpoint not available: {e}")
        
        # 3. Thử unload models nếu có endpoint (một số custom API có thể có)
        try:
            url = f"{self.server_url.rstrip('/')}/unload"
            response = requests.post(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Successfully called /unload endpoint")
                success = True
        except requests.exceptions.RequestException:
            # Endpoint này có thể không tồn tại, không cần log warning
            pass
        
        if success:
            logger.info("Cache clearing completed successfully")
        else:
            logger.warning("Cache clearing attempted but no endpoints responded successfully")
        
        return success
        
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
                try:
                    return response.json()
                except Exception as e:
                    logger.warning(f"Progress endpoint returned non-JSON body: {e}; raw={response.text}")
                    return {}
            else:
                # Do not raise here; return empty dict and log details so callers can retry gracefully
                logger.warning(f"Failed to get progress: HTTP {response.status_code}; body={response.text}")
                return {}

        except requests.exceptions.RequestException as e:
            # Network level errors (timeout, connection error) should be logged and returned as empty progress
            logger.warning(f"Network error getting progress from {self.server_url}/progress: {e}")
            return {}
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 600) -> Dict[str, Any]:
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
    
    def wait_for_completion_with_progress(self, prompt_id: str, progress_callback=None, timeout: int = 600) -> Dict[str, Any]:
        """Đợi cho đến khi xử lý hoàn tất với callback để hiển thị progress"""
        # First, try to use WebSocket to receive live progress messages from ComfyUI.
        # If websocket-client is not available or WS connection fails, fall back to HTTP polling.
        start_time = time.time()

        def _http_polling():
            # Fallback polling: /progress may not exist on ComfyUI; only poll /history for completion.
            while time.time() - start_time < timeout:
                try:
                    # Check history - tolerate failures here too (log and continue)
                    try:
                        history = self.get_history(prompt_id)
                    except Exception as hist_e:
                        logger.warning(f"Failed to fetch history during polling: {hist_e}")
                        history = {}

                    if prompt_id in history:
                        prompt_data = history[prompt_id]
                        if 'status' in prompt_data:
                            status = prompt_data['status']
                            if status.get('status_str') == 'success':
                                return prompt_data
                            elif status.get('status_str') == 'error':
                                error_message = status.get('messages', ['Unknown error'])
                                raise Exception(f"ComfyUI processing failed: {error_message}")

                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error waiting for completion (HTTP fallback): {str(e)}")
                    raise

            raise Exception(f"Timeout waiting for ComfyUI completion after {timeout} seconds")

        # If websocket-client is available, try using it to listen to /ws
        if websocket is None:
            logger.info("websocket-client not installed; using HTTP polling for progress")
            return _http_polling()

        # Build WS URL from server_url, converting http->ws and https->wss when needed
        base = self.server_url.rstrip('/')
        if base.startswith('https://'):
            ws_base = 'wss://' + base[len('https://'):]
        elif base.startswith('http://'):
            ws_base = 'ws://' + base[len('http://'):]
        else:
            ws_base = base

        ws_url = f"{ws_base}/ws?clientId={self.client_id}"

        try:
            # create a blocking WebSocket connection with a small recv timeout
            ws = websocket.create_connection(ws_url, timeout=5)
        except Exception as e:
            logger.warning(f"Could not open WebSocket to ComfyUI ({ws_url}): {e}; falling back to HTTP polling")
            return _http_polling()

        # set a short socket timeout to allow timeout checks
        try:
            ws.settimeout(2)
        except Exception:
            pass

        try:
            while time.time() - start_time < timeout:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    # no message in this interval; continue and check time
                    continue
                except Exception as e:
                    logger.warning(f"WebSocket recv error: {e}")
                    break

                if not raw:
                    continue

                try:
                    msg = json.loads(raw)
                except Exception:
                    # not JSON — ignore
                    continue

                mtype = msg.get('type')

                # progress messages: {type: 'progress', data: {value, max}}
                if mtype == 'progress':
                    data = msg.get('data', {})
                    if progress_callback:
                        try:
                            progress_callback(data)
                        except Exception as cb_e:
                            logger.warning(f"progress_callback raised: {cb_e}")

                # executing messages indicate when nodes/prompt start/finish
                elif mtype == 'executing':
                    data = msg.get('data', {})
                    # When data['node'] is null and prompt_id matches, execution finished
                    if data.get('prompt_id') == prompt_id and data.get('node') is None:
                        # Fetch final history to return detailed result
                        try:
                            history = self.get_history(prompt_id)
                            if prompt_id in history:
                                return history[prompt_id]
                        except Exception as e:
                            logger.warning(f"Failed to fetch history after WS executing message: {e}")
                        # if history fetch failed, still return a success marker
                        return {"status": {"status_str": "success"}}

                # other message types can be logged/debugged
                else:
                    # ignore other messages or add debug logging
                    continue

            # loop finished without receiving completion
            raise Exception(f"Timeout waiting for ComfyUI completion after {timeout} seconds")

        finally:
            try:
                ws.close()
            except Exception:
                pass


    def queue_prompt_with_progress(self, prompt: Dict[str, Any], progress_callback=None, timeout: int = 600) -> Dict[str, Any]:
        """Queue a prompt and listen for progress via WebSocket (preferred).

        If WebSocket isn't available or fails, falls back to queue + HTTP polling.
        Returns the final prompt history dict on success.
        """
        start_time = time.time()

        # If websocket-client not available, fall back
        if websocket is None:
            logger.info("websocket-client not installed; falling back to queue + polling")
            prompt_id = self.queue_prompt(prompt)
            return self.wait_for_completion_with_progress(prompt_id, progress_callback=progress_callback, timeout=timeout)

        ws_url = f"{self.server_url.rstrip('/')}/ws?clientId={self.client_id}"

        try:
            ws = websocket.create_connection(ws_url, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to open WebSocket ({ws_url}): {e}; falling back to queue + polling")
            prompt_id = self.queue_prompt(prompt)
            return self.wait_for_completion_with_progress(prompt_id, progress_callback=progress_callback, timeout=timeout)

        try:
            # Ensure quick recv timeout for the listen loop
            try:
                ws.settimeout(2)
            except Exception:
                pass

            # Now send the prompt to the server
            p = {"prompt": prompt, "client_id": self.client_id}
            try:
                resp = requests.post(f"{self.server_url}/prompt", json=p, timeout=self.timeout)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to queue prompt via HTTP after WS opened: {e}")
                raise

            try:
                resp_json = resp.json()
                prompt_id = resp_json.get('prompt_id')
            except Exception as e:
                logger.error(f"Failed to parse prompt response: {e}; text={resp.text}")
                raise

            logger.info(f"Queued prompt {prompt_id}, listening for progress via WebSocket")

            # Listen for messages until completion or timeout
            while time.time() - start_time < timeout:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    logger.warning(f"WebSocket recv error: {e}")
                    break

                if not raw:
                    continue

                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                mtype = msg.get('type')

                if mtype == 'progress':
                    data = msg.get('data', {})
                    if progress_callback:
                        try:
                            progress_callback(data)
                        except Exception as cb_e:
                            logger.warning(f"progress_callback raised: {cb_e}")

                elif mtype == 'executing':
                    data = msg.get('data', {})
                    if data.get('prompt_id') == prompt_id and data.get('node') is None:
                        # Completed
                        try:
                            history = self.get_history(prompt_id)
                            if prompt_id in history:
                                return history[prompt_id]
                        except Exception as e:
                            logger.warning(f"Failed to fetch history after executing WS msg: {e}")
                        return {"status": {"status_str": "success"}}

                else:
                    continue

            raise Exception(f"Timeout waiting for prompt {prompt_id} completion after {timeout} seconds")

        finally:
            try:
                ws.close()
            except Exception:
                pass
    

    def process_image_recovery(self, input_image_path: str, prompt: str, 
                             strength: float = 0.8, steps: int = 20, 
                             guidance_scale: float = 7.5, seed: Optional[int] = None,
                             progress_callback=None) -> str:
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

            # 5) Gửi workflow và đợi kết quả (kèm progress qua WebSocket nếu có)
            try:
                result = self.queue_prompt_with_progress(workflow, progress_callback=progress_callback, timeout=600)
                logger.info("Workflow completed successfully (via WS)")
            except Exception as e:
                # Fallback: queue + polling
                logger.warning(f"WS progress flow failed: {e}; falling back to queue + polling")
                prompt_id = self.queue_prompt(workflow)
                logger.info(f"Queued prompt {prompt_id}, waiting for completion via polling...")
                result = self.wait_for_completion(prompt_id, timeout=600)

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

            result_filename = None
            if preferred:
                logger.info(f"Using RESULT from node {preferred[0]}: {preferred[1]}")
                result_filename = preferred[1]
            elif fallback:
                logger.info(f"Using non-ORIGINAL image from node {fallback[0]}: {fallback[1]}")
                result_filename = fallback[1]
            elif any_image:
                logger.info(f"Using first available image from node {any_image[0]}: {any_image[1]}")
                result_filename = any_image[1]
            else:
                raise Exception("Không tìm thấy ảnh output trong kết quả.")
            
            # 7) Clear cache để giải phóng VRAM cho lần xử lý tiếp theo
            try:
                logger.info("Clearing cache to free VRAM...")
                self.clear_cache()
            except Exception as e:
                logger.warning(f"Failed to clear cache (non-critical): {e}")
            
            return result_filename

        except Exception as e:
            logger.error(f"Error processing image recovery: {str(e)}")
            raise

    def process_inpainting(self, input_image_path: str, prompt: str,
                           ref_image2_path: Optional[str] = None,
                           ref_image3_path: Optional[str] = None,
                           progress_callback=None) -> str:
        """Xử lý inpainting với ComfyUI sử dụng workflows/Inpainting.json.

        Thay đổi tối thiểu:
        - Node "78" (LoadImage): ảnh chính (image)
        - Node "111" (TextEncodeQwenImageEditPlus): prompt tích cực
        - Tùy chọn: Node "106" và "108" (LoadImage) nếu cung cấp ref_image2/3

        Args:
            input_image_path: Ảnh cần inpaint/chỉnh sửa
            prompt: Mô tả chỉnh sửa
            ref_image2_path: Ảnh tham chiếu 2 (tùy chọn)
            ref_image3_path: Ảnh tham chiếu 3 (tùy chọn)
            progress_callback: Callback đồng bộ nhận dict tiến độ

        Returns:
            Tên file ảnh kết quả trên ComfyUI server
        """
        try:
            logger.info("=== PROCESSING INPAINTING WORKFLOW ===")
            logger.info(f"Input image path: {input_image_path}")
            logger.info(f"User prompt: '{prompt}'")

            if not input_image_path:
                raise Exception("input_image_path is required")

            # Helper: upload a local image to ComfyUI and return unique filename
            def _upload_image(local_path: str) -> str:
                timestamp = int(time.time())
                uid = uuid.uuid4().hex[:8]
                base, ext = os.path.splitext(os.path.basename(local_path))
                unique_name = f"{base}_{timestamp}_{uid}{ext}"
                url = f"{self.server_url.rstrip('/')}/upload/image"
                with open(local_path, "rb") as f:
                    files = {"image": (unique_name, f, "application/octet-stream")}
                    resp = requests.post(url, files=files)
                    resp.raise_for_status()
                return unique_name

            # 1) Upload ảnh chính và các ảnh tham chiếu (nếu có)
            image1_filename = _upload_image(input_image_path)
            image2_filename = _upload_image(ref_image2_path) if ref_image2_path else None
            image3_filename = _upload_image(ref_image3_path) if ref_image3_path else None

            logger.info(f"Uploaded image1: {image1_filename}")
            if image2_filename:
                logger.info(f"Uploaded image2: {image2_filename}")
            if image3_filename:
                logger.info(f"Uploaded image3: {image3_filename}")

            # 2) Đọc workflow Inpainting.json
            with open("workflows/Inpainting.json", "r", encoding="utf-8") as f:
                workflow = json.loads(f.read())

            # 3) Gán ảnh vào các node tương ứng
            # Node 78: ảnh chính (LoadImage)
            if "78" in workflow and "inputs" in workflow["78"]:
                workflow["78"]["inputs"]["image"] = image1_filename
            else:
                logger.warning("Workflow Inpainting.json không có node '78' như kỳ vọng")

            # Node 106 và 108: ảnh tham chiếu (nếu cung cấp)
            if image2_filename and "106" in workflow and "inputs" in workflow["106"]:
                workflow["106"]["inputs"]["image"] = image2_filename
            if image3_filename and "108" in workflow and "inputs" in workflow["108"]:
                workflow["108"]["inputs"]["image"] = image3_filename

            # 4) Cập nhật prompt cho node 111 (positive prompt)
            if "111" in workflow and "inputs" in workflow["111"]:
                workflow["111"]["inputs"]["prompt"] = prompt
            else:
                logger.warning("Workflow Inpainting.json không có node '111' như kỳ vọng để set prompt")

            logger.info(f"Prepared Inpainting workflow with {len(workflow)} nodes")

            # 5) Gửi workflow và theo dõi tiến độ
            try:
                result = self.queue_prompt_with_progress(workflow, progress_callback=progress_callback, timeout=600)
                logger.info("Inpainting completed successfully (via WS)")
            except Exception as e:
                logger.warning(f"WS progress flow failed: {e}; falling back to queue + polling")
                prompt_id = self.queue_prompt(workflow)
                result = self.wait_for_completion(prompt_id, timeout=600)

            # 6) Trích ảnh kết quả
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

                # ưu tiên node 8 (VAEDecode) nếu có, kế đến Preview 116
                if str(node_id) == "8" and preferred is None:
                    preferred = (node_id, filename)
                if str(node_id) == "116" and not preferred:
                    preferred = (node_id, filename)
                if fallback is None:
                    fallback = (node_id, filename)
                if any_image is None:
                    any_image = (node_id, filename)

            if preferred:
                return preferred[1]
            if fallback:
                return fallback[1]
            if any_image:
                return any_image[1]

            raise Exception("Không tìm thấy ảnh output trong kết quả Inpainting.")

        except Exception as e:
            logger.error(f"Error processing inpainting: {str(e)}")
            raise
