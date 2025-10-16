import os
import tempfile
import time
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from PIL import Image
import io
import httpx

from models import ImageRecoveryRequest, ImageRecoveryFromURLRequest, ImageRecoveryResponse
from comfyui_client import ComfyUIClient
from storage_service import get_storage_service
from config import config

# Thiết lập logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Image Recovery API",
    description="API để phục hồi ảnh sử dụng ComfyUI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên hạn chế domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo clients
comfyui_client = ComfyUIClient()
storage_service = get_storage_service()

# In-memory job tracking (trong production nên dùng Redis hoặc database)
active_jobs = {}

async def download_image_from_url(url: str, max_size_mb: int = 10) -> tuple[bytes, str]:
    """Download ảnh từ URL và trả về bytes và content type"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Kiểm tra content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="URL không phải là ảnh")
            
            # Kiểm tra kích thước
            content_length = int(response.headers.get('content-length', 0))
            if content_length > max_size_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"Ảnh quá lớn. Kích thước tối đa: {max_size_mb}MB"
                )
            
            # Lấy extension từ content type hoặc URL
            if 'jpeg' in content_type or 'jpg' in content_type:
                extension = 'jpg'
            elif 'png' in content_type:
                extension = 'png'
            elif 'webp' in content_type:
                extension = 'webp'
            else:
                # Fallback: lấy từ URL
                extension = url.split('.')[-1].lower()
                if extension not in config.ALLOWED_EXTENSIONS:
                    extension = 'jpg'  # Default
            
            return response.content, extension
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Timeout khi download ảnh")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Lỗi khi download ảnh: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khi xử lý URL ảnh: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Image Recovery API đang hoạt động", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Kiểm tra sức khỏe của các service"""
    try:
        # Kiểm tra ComfyUI server
        import requests
        response = requests.get(f"{config.COMFYUI_SERVER_URL}/system_stats", timeout=5)
        comfyui_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        comfyui_status = "unhealthy"
    
    return {
        "status": "healthy",
        "services": {
            "comfyui": comfyui_status,
            "storage": "healthy"  # Storage service sẽ được kiểm tra khi upload
        }
    }

@app.post("/recover-image", response_model=ImageRecoveryResponse)
async def recover_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Ảnh cần phục hồi"),
    prompt: str = Form(..., description="Mô tả chi tiết về việc phục hồi ảnh"),
    strength: float = Form(0.8, description="Độ mạnh của việc phục hồi (0.0-1.0)"),
    steps: int = Form(20, description="Số bước xử lý"),
    guidance_scale: float = Form(7.5, description="Tỷ lệ hướng dẫn"),
    seed: Optional[int] = Form(None, description="Seed để tạo ảnh")
):
    """
    API endpoint để phục hồi ảnh
    
    - **image**: File ảnh cần phục hồi (jpg, jpeg, png, webp)
    - **prompt**: Mô tả chi tiết về việc phục hồi ảnh
    - **strength**: Độ mạnh của việc phục hồi (0.0-1.0)
    - **steps**: Số bước xử lý (1-100)
    - **guidance_scale**: Tỷ lệ hướng dẫn (1.0-20.0)
    - **seed**: Seed để tạo ảnh (tùy chọn)
    """
    
    job_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Validate input
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File phải là ảnh")
        
        # Kiểm tra kích thước file
        file_size = 0
        content = await image.read()
        file_size = len(content)
        
        if file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File quá lớn. Kích thước tối đa: {config.MAX_FILE_SIZE_MB}MB"
            )
        
        # Validate extension
        file_extension = image.filename.split('.')[-1].lower() if image.filename else ''
        if file_extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng file không được hỗ trợ. Chỉ chấp nhận: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # Validate prompt
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt không được để trống")
        
        # Validate parameters
        if not 0.0 <= strength <= 1.0:
            raise HTTPException(status_code=400, detail="Strength phải trong khoảng 0.0-1.0")
        
        if not 1 <= steps <= 100:
            raise HTTPException(status_code=400, detail="Steps phải trong khoảng 1-100")
        
        if not 1.0 <= guidance_scale <= 20.0:
            raise HTTPException(status_code=400, detail="Guidance scale phải trong khoảng 1.0-20.0")
        
        # Tạo job entry
        active_jobs[job_id] = {
            "status": "processing",
            "start_time": start_time,
            "message": "Đang xử lý ảnh..."
        }
        
        # Lưu ảnh tạm thời
        temp_input_path = None
        try:
            # Tạo file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file.write(content)
                temp_input_path = temp_file.name
            
            # Xử lý ảnh với ComfyUI
            logger.info(f"Bắt đầu xử lý ảnh với job_id: {job_id}")
            result_filename = comfyui_client.process_image_recovery(
                input_image_path=temp_input_path,
                prompt=prompt,
                strength=strength,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=seed
            )
            
            # Lấy ảnh kết quả từ ComfyUI (sử dụng type="temp" vì ảnh được lưu tạm thời)
            result_image_bytes = comfyui_client.get_image(result_filename, folder_type="temp")
            
            # Upload lên cloud storage
            final_filename = f"recovered_{job_id}.{file_extension}"
            image_url = await storage_service.upload_image(
                image_bytes=result_image_bytes,
                filename=final_filename,
                content_type=image.content_type
            )
            
            processing_time = time.time() - start_time
            
            # Cập nhật job status
            active_jobs[job_id] = {
                "status": "completed",
                "start_time": start_time,
                "end_time": time.time(),
                "processing_time": processing_time,
                "result_url": image_url
            }
            
            logger.info(f"Hoàn thành xử lý ảnh với job_id: {job_id}, thời gian: {processing_time:.2f}s")
            
            return ImageRecoveryResponse(
                success=True,
                message="Phục hồi ảnh thành công",
                result_image_url=image_url,
                job_id=job_id,
                processing_time=processing_time
            )
            
        finally:
            # Cleanup temp files
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    os.unlink(temp_input_path)
                except:
                    pass
    
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Lỗi khi xử lý ảnh: {str(e)}"
        logger.error(f"Error in recover_image: {error_msg}")
        
        # Cập nhật job status
        active_jobs[job_id] = {
            "status": "failed",
            "start_time": start_time,
            "end_time": time.time(),
            "processing_time": processing_time,
            "error": error_msg
        }
        
        return ImageRecoveryResponse(
            success=False,
            message=error_msg,
            job_id=job_id,
            processing_time=processing_time,
            error_details=str(e)
        )

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Lấy trạng thái của job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    return active_jobs[job_id]

@app.get("/jobs")
async def list_jobs():
    """Lấy danh sách tất cả jobs"""
    return {
        "total_jobs": len(active_jobs),
        "jobs": active_jobs
    }

@app.post("/recover-image-from-url", response_model=ImageRecoveryResponse)
async def recover_image_from_url(request: ImageRecoveryFromURLRequest):
    """
    API endpoint để phục hồi ảnh từ URL
    
    - **image_url**: URL của ảnh cần phục hồi
    - **prompt**: Mô tả chi tiết về việc phục hồi ảnh
    - **strength**: Độ mạnh của việc phục hồi (0.0-1.0)
    - **steps**: Số bước xử lý (1-100)
    - **guidance_scale**: Tỷ lệ hướng dẫn (1.0-20.0)
    - **seed**: Seed để tạo ảnh (tùy chọn)
    """
    
    job_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Validate prompt
        if not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt không được để trống")
        
        # Validate parameters
        if not 0.0 <= request.strength <= 1.0:
            raise HTTPException(status_code=400, detail="Strength phải trong khoảng 0.0-1.0")
        
        if not 1 <= request.steps <= 100:
            raise HTTPException(status_code=400, detail="Steps phải trong khoảng 1-100")
        
        if not 1.0 <= request.guidance_scale <= 20.0:
            raise HTTPException(status_code=400, detail="Guidance scale phải trong khoảng 1.0-20.0")
        
        # Tạo job entry
        active_jobs[job_id] = {
            "status": "processing",
            "start_time": start_time,
            "message": "Đang download và xử lý ảnh..."
        }
        
        # Download ảnh từ URL
        logger.info(f"Downloading image from URL: {request.image_url}")
        image_content, extension = await download_image_from_url(str(request.image_url))
        
        # Validate extension
        if extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng ảnh không được hỗ trợ. Chỉ chấp nhận: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # Lưu ảnh tạm thời
        temp_input_path = None
        try:
            # Tạo file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
                temp_file.write(image_content)
                temp_input_path = temp_file.name
            
            # Cập nhật job status
            active_jobs[job_id]["message"] = "Đang xử lý ảnh với ComfyUI..."
            
            # Xử lý ảnh với ComfyUI
            logger.info(f"Bắt đầu xử lý ảnh với job_id: {job_id}")
            result_filename = comfyui_client.process_image_recovery(
                input_image_path=temp_input_path,
                prompt=request.prompt,
                strength=request.strength,
                steps=request.steps,
                guidance_scale=request.guidance_scale,
                seed=request.seed
            )
            
            # Lấy ảnh kết quả từ ComfyUI (sử dụng type="temp" vì ảnh được lưu tạm thời)
            result_image_bytes = comfyui_client.get_image(result_filename, folder_type="temp")
            
            # Upload lên cloud storage
            final_filename = f"recovered_{job_id}.{extension}"
            content_type = f"image/{extension}" if extension != 'jpg' else "image/jpeg"
            
            active_jobs[job_id]["message"] = "Đang upload kết quả..."
            image_url = await storage_service.upload_image(
                image_bytes=result_image_bytes,
                filename=final_filename,
                content_type=content_type
            )
            
            processing_time = time.time() - start_time
            
            # Cập nhật job status
            active_jobs[job_id] = {
                "status": "completed",
                "start_time": start_time,
                "end_time": time.time(),
                "processing_time": processing_time,
                "result_url": image_url
            }
            
            logger.info(f"Hoàn thành xử lý ảnh với job_id: {job_id}, thời gian: {processing_time:.2f}s")
            
            return ImageRecoveryResponse(
                success=True,
                message="Phục hồi ảnh thành công",
                result_image_url=image_url,
                job_id=job_id,
                processing_time=processing_time
            )
            
        finally:
            # Cleanup temp files
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    os.unlink(temp_input_path)
                except:
                    pass
    
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Lỗi khi xử lý ảnh: {str(e)}"
        logger.error(f"Error in recover_image_from_url: {error_msg}")
        
        # Cập nhật job status
        active_jobs[job_id] = {
            "status": "failed",
            "start_time": start_time,
            "end_time": time.time(),
            "processing_time": processing_time,
            "error": error_msg
        }
        
        return ImageRecoveryResponse(
            success=False,
            message=error_msg,
            job_id=job_id,
            processing_time=processing_time,
            error_details=str(e)
        )

@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Xóa job khỏi memory"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    del active_jobs[job_id]
    return {"message": f"Job {job_id} đã được xóa"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )
