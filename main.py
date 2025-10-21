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
