from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Union
import uuid

class ImageRecoveryRequest(BaseModel):
    prompt: str = Field(..., description="Mô tả chi tiết về việc phục hồi ảnh")
    strength: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Độ mạnh của việc phục hồi (0.0-1.0)")
    steps: Optional[int] = Field(20, ge=1, le=100, description="Số bước xử lý")
    guidance_scale: Optional[float] = Field(7.5, ge=1.0, le=20.0, description="Tỷ lệ hướng dẫn")
    seed: Optional[int] = Field(None, description="Seed để tạo ảnh (để tái tạo kết quả)")

class ImageRecoveryFromURLRequest(BaseModel):
    image_url: HttpUrl = Field(..., description="URL của ảnh cần phục hồi")
    prompt: str = Field(..., description="Mô tả chi tiết về việc phục hồi ảnh")
    strength: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Độ mạnh của việc phục hồi (0.0-1.0)")
    steps: Optional[int] = Field(20, ge=1, le=100, description="Số bước xử lý")
    guidance_scale: Optional[float] = Field(7.5, ge=1.0, le=20.0, description="Tỷ lệ hướng dẫn")
    seed: Optional[int] = Field(None, description="Seed để tạo ảnh (để tái tạo kết quả)")

class ImageRecoveryResponse(BaseModel):
    success: bool
    message: str
    result_image_url: Optional[str] = None
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    processing_time: Optional[float] = None
    error_details: Optional[str] = None

class ComfyUIWorkflowRequest(BaseModel):
    prompt: str
    input_image_path: str
    strength: float = 0.8
    steps: int = 20
    guidance_scale: float = 7.5
    seed: Optional[int] = None
