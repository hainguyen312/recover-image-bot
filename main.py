import os
import time
import uuid
import shutil
import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

import requests

from config import config
from comfyui_client import ComfyUIClient
from storage_service import get_storage_service

logger = logging.getLogger("main")

app = FastAPI(title="Image Recovery Bot API")


@app.get("/health")
async def health_check():
    services = {"comfyui": "unknown", "storage": "unknown"}

    # Check ComfyUI
    try:
        comfy_url = f"{config.COMFYUI_SERVER_URL.rstrip('/')}/history/0"
        r = requests.get(comfy_url, timeout=5)
        services["comfyui"] = "running" if r.status_code == 200 else f"error_http_{r.status_code}"
    except Exception as e:
        services["comfyui"] = f"error: {e}"

    # Check storage
    try:
        svc = get_storage_service()
        services["storage"] = "initialized"
    except Exception as e:
        services["storage"] = f"error: {e}"

    return {"status": "ok", "services": services}


async def _save_upload_to_temp(upload: UploadFile) -> str:
    tmpdir = os.path.join(os.getcwd(), "temp")
    os.makedirs(tmpdir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{upload.filename}"
    path = os.path.join(tmpdir, filename)

    with open(path, "wb") as out_file:
        shutil.copyfileobj(upload.file, out_file)

    return path


@app.post("/recover-image")
async def recover_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    strength: float = Form(0.8),
    steps: int = Form(20),
    guidance_scale: float = Form(7.5),
):
    start_time = time.time()

    # Save uploaded image to temp
    try:
        input_path = await _save_upload_to_temp(image)
    except Exception as e:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    client = ComfyUIClient()

    try:
        # process_image_recovery is CPU/blocking — run in thread
        result_filename = await asyncio.to_thread(
            client.process_image_recovery,
            input_path,
            prompt,
            strength,
            steps,
            guidance_scale,
        )
    except Exception as e:
        logger.exception("ComfyUI processing failed")
        raise HTTPException(status_code=500, detail=f"ComfyUI processing failed: {e}")

    try:
        # get_image is blocking — run in thread
        image_bytes = await asyncio.to_thread(client.get_image, result_filename, "", "output")
    except Exception as e:
        logger.exception("Failed to retrieve result image from ComfyUI")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve result image: {e}")

    try:
        storage = get_storage_service()
    except Exception as e:
        logger.exception("Failed to initialize storage service")
        raise HTTPException(status_code=500, detail=f"Failed to initialize storage service: {e}")

    try:
        public_url = await storage.upload_image(image_bytes, result_filename, content_type="image/png")
    except Exception as e:
        logger.exception("Failed to upload result image to storage")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {e}")

    elapsed = time.time() - start_time
    job_id = uuid.uuid4().hex

    return {
        "success": True,
        "job_id": job_id,
        "processing_time": elapsed,
        "result_image_url": public_url,
    }


@app.post("/recover-image-from-url")
async def recover_image_from_url(
    image_url: str = Form(...),
    prompt: str = Form(...),
    strength: float = Form(0.8),
    steps: int = Form(20),
    guidance_scale: float = Form(7.5),
):
    # Download image
    try:
        r = requests.get(image_url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {e}")

    # Save to temp
    tmpname = f"{uuid.uuid4().hex}.jpg"
    tmpdir = os.path.join(os.getcwd(), "temp")
    os.makedirs(tmpdir, exist_ok=True)
    tmp_path = os.path.join(tmpdir, tmpname)
    with open(tmp_path, "wb") as f:
        f.write(r.content)

    # Reuse recover_image flow by calling client directly
    client = ComfyUIClient()
    try:
        result_filename = await asyncio.to_thread(
            client.process_image_recovery,
            tmp_path,
            prompt,
            strength,
            steps,
            guidance_scale,
        )

        image_bytes = await asyncio.to_thread(client.get_image, result_filename, "", "output")
    except Exception as e:
        logger.exception("ComfyUI processing failed for URL")
        raise HTTPException(status_code=500, detail=f"ComfyUI processing failed: {e}")

    try:
        storage = get_storage_service()
        public_url = await storage.upload_image(image_bytes, result_filename, content_type="image/png")
    except Exception as e:
        logger.exception("Failed to upload image to storage for URL flow")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {e}")

    return {"success": True, "result_image_url": public_url}


# ============== INPAINTING WORKFLOW APIs ==============

@app.post("/inpaint-image")
async def inpaint_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    ref_image2: UploadFile = File(None),
    ref_image3: UploadFile = File(None),
):
    """API inpainting sử dụng workflow Inpainting.json.

    - image: ảnh chính cần chỉnh sửa
    - prompt: mô tả chỉnh sửa
    - ref_image2/ref_image3: ảnh tham chiếu tùy chọn
    """
    start_time = time.time()

    # Lưu các file vào temp
    try:
        input_path = await _save_upload_to_temp(image)
        ref2_path = await _save_upload_to_temp(ref_image2) if ref_image2 else None
        ref3_path = await _save_upload_to_temp(ref_image3) if ref_image3 else None
    except Exception as e:
        logger.exception("Failed to save uploaded files for inpainting")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {e}")

    client = ComfyUIClient()

    try:
        # process_inpainting là blocking — chạy trong thread
        result_filename = await asyncio.to_thread(
            client.process_inpainting,
            input_path,
            prompt,
            ref2_path,
            ref3_path,
        )
    except Exception as e:
        logger.exception("ComfyUI inpainting failed")
        raise HTTPException(status_code=500, detail=f"ComfyUI inpainting failed: {e}")

    try:
        image_bytes = await asyncio.to_thread(client.get_image, result_filename, "", "output")
    except Exception as e:
        logger.exception("Failed to retrieve inpainting result image from ComfyUI")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve result image: {e}")

    try:
        storage = get_storage_service()
        public_url = await storage.upload_image(image_bytes, result_filename, content_type="image/png")
    except Exception as e:
        logger.exception("Failed to upload inpainting image to storage")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {e}")

    elapsed = time.time() - start_time
    job_id = uuid.uuid4().hex

    return {
        "success": True,
        "job_id": job_id,
        "processing_time": elapsed,
        "result_image_url": public_url,
    }


@app.post("/inpaint-image-from-url")
async def inpaint_image_from_url(
    image_url: str = Form(...),
    prompt: str = Form(...),
    ref_image2_url: str = Form(None),
    ref_image3_url: str = Form(None),
):
    """API inpainting từ URL sử dụng workflow Inpainting.json.
    Các ảnh tham chiếu có thể để trống.
    """
    def _download_to_temp(url: str) -> str:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        tmpname = f"{uuid.uuid4().hex}.jpg"
        tmpdir = os.path.join(os.getcwd(), "temp")
        os.makedirs(tmpdir, exist_ok=True)
        tmp_path = os.path.join(tmpdir, tmpname)
        with open(tmp_path, "wb") as f:
            f.write(r.content)
        return tmp_path

    try:
        input_path = _download_to_temp(image_url)
        ref2_path = _download_to_temp(ref_image2_url) if ref_image2_url else None
        ref3_path = _download_to_temp(ref_image3_url) if ref_image3_url else None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image(s): {e}")

    client = ComfyUIClient()
    try:
        result_filename = await asyncio.to_thread(
            client.process_inpainting,
            input_path,
            prompt,
            ref2_path,
            ref3_path,
        )
        image_bytes = await asyncio.to_thread(client.get_image, result_filename, "", "output")
    except Exception as e:
        logger.exception("ComfyUI inpainting failed for URL flow")
        raise HTTPException(status_code=500, detail=f"ComfyUI inpainting failed: {e}")

    try:
        storage = get_storage_service()
        public_url = await storage.upload_image(image_bytes, result_filename, content_type="image/png")
    except Exception as e:
        logger.exception("Failed to upload inpainting image (URL flow) to storage")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {e}")

    return {"success": True, "result_image_url": public_url}


# ============== AUTO WORKFLOW SELECTION ==============

def _classify_by_keywords(text: str) -> str:
    t = (text or "").lower()
    inpaint_keys = [
        "inpaint", "change", "replace", "switch", "background", "remove object", "add object",
        "doi", "thay", "thêm", "xóa", "đổi nền", "bãi biển", "beach", "blend lighting",
        "áo", "quần", "tóc", "ghép", "edit"
    ]
    restore_keys = [
        "restore", "recover", "enhance", "old photo", "fix scratch", "scratch", "stain",
        "remove noise", "grain", "sharpen", "color", "exposure", "discolor", "blur",
        "phục hồi", "phục chế", "khử nhiễu", "vết xước", "vết bẩn", "tăng chi tiết", "cân bằng màu"
    ]
    inpaint_score = sum(k in t for k in inpaint_keys)
    restore_score = sum(k in t for k in restore_keys)
    if inpaint_score > restore_score:
        return "inpaint"
    return "restore"


def _classify_with_local_llm(text: str) -> str:
    """Cố gắng phân loại qua LLM chạy local (ví dụ Ollama). Fallback sang keyword nếu lỗi.

    Cấu hình qua env:
    - OLLAMA_URL (mặc định http://localhost:11434)
    - OLLAMA_MODEL (ví dụ: qwen2.5:3b, llama3.1:8b, v.v.)
    - Nếu không có OLLAMA_MODEL, bỏ qua Ollama.
    """
    try:
        ollama_model = os.getenv("OLLAMA_MODEL")
        if not ollama_model:
            return _classify_by_keywords(text)

        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        url = f"{ollama_url}/api/generate"
        instruction = (
            "You are a classifier. Decide the best workflow for an image request. "
            "Return exactly one token: 'restore' or 'inpaint'.\n\n"
            "If the user asks to change content (background, clothes, remove/add objects), answer 'inpaint'. "
            "If the user asks to restore/enhance/fix quality (scratches, noise, colors), answer 'restore'.\n\n"
            f"User request: {text}\nAnswer:"
        )
        payload = {
            "model": ollama_model,
            "prompt": instruction,
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json() or {}
        resp = (data.get("response") or "").strip().lower()
        if "inpaint" in resp:
            return "inpaint"
        if "restore" in resp:
            return "restore"
        # Nếu không chắc, fallback keyword
        return _classify_by_keywords(text)
    except Exception:
        return _classify_by_keywords(text)


def classify_workflow(user_text: str) -> str:
    """Phân loại workflow: 'restore' hoặc 'inpaint' (LLM local -> keyword fallback)."""
    return _classify_with_local_llm(user_text)


@app.post("/process-image")
async def process_image_auto(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    ref_image2: UploadFile = File(None),
    ref_image3: UploadFile = File(None),
):
    """Endpoint tự động chọn workflow (Restore vs Inpainting) dựa trên yêu cầu người dùng.

    - Ưu tiên phân loại bằng LLM local (Ollama) nếu có OLLAMA_MODEL, nếu không fallback heuristic.
    - Nếu chọn 'restore' → chạy process_image_recovery
    - Nếu chọn 'inpaint' → chạy process_inpainting (dùng ref_image2/ref_image3 nếu có)
    """
    start_time = time.time()

    # Lưu file vào temp
    try:
        input_path = await _save_upload_to_temp(image)
        ref2_path = await _save_upload_to_temp(ref_image2) if ref_image2 else None
        ref3_path = await _save_upload_to_temp(ref_image3) if ref_image3 else None
    except Exception as e:
        logger.exception("Failed to save uploaded files for /process-image")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {e}")

    selected = classify_workflow(prompt)

    client = ComfyUIClient()
    try:
        if selected == "restore":
            result_filename = await asyncio.to_thread(
                client.process_image_recovery,
                input_path,
                prompt,
                0.8,
                20,
                7.5,
            )
        else:
            result_filename = await asyncio.to_thread(
                client.process_inpainting,
                input_path,
                prompt,
                ref2_path,
                ref3_path,
            )
    except Exception as e:
        logger.exception("ComfyUI processing failed for /process-image")
        raise HTTPException(status_code=500, detail=f"ComfyUI processing failed: {e}")

    try:
        image_bytes = await asyncio.to_thread(client.get_image, result_filename, "", "output")
    except Exception as e:
        logger.exception("Failed to retrieve result image from ComfyUI (/process-image)")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve result image: {e}")

    try:
        storage = get_storage_service()
        public_url = await storage.upload_image(image_bytes, result_filename, content_type="image/png")
    except Exception as e:
        logger.exception("Failed to upload image to storage (/process-image)")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {e}")

    elapsed = time.time() - start_time
    job_id = uuid.uuid4().hex

    return {
        "success": True,
        "job_id": job_id,
        "processing_time": elapsed,
        "used_workflow": selected,
        "result_image_url": public_url,
    }
