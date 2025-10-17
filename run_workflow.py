import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests


def post_prompt(server_url: str, workflow: Dict[str, Any]) -> str:
    """Gửi workflow (định dạng export chuẩn của ComfyUI) lên API /prompt và trả về prompt_id."""
    url = f"{server_url.rstrip('/')}/prompt"
    resp = requests.post(url, json={"prompt": workflow})
    resp.raise_for_status()
    data = resp.json()
    return data.get("prompt_id")


def wait_for_completion(server_url: str, prompt_id: str, timeout: int = 600) -> Dict[str, Any]:
    """Poll /history đến khi hoàn tất hoặc hết thời gian."""
    url = f"{server_url.rstrip('/')}/history/{prompt_id}"
    start = time.time()
    while True:
        if time.time() - start > timeout:
            raise TimeoutError(f"Hết thời gian chờ sau {timeout}s cho prompt_id={prompt_id}")
        resp = requests.get(url)
        resp.raise_for_status()
        hist = resp.json()
        if prompt_id in hist:
            entry = hist[prompt_id]
            status = (entry.get("status") or {}).get("status_str")
            if status == "success":
                return entry
            if status == "error":
                raise RuntimeError(entry.get("status", {}).get("messages", ["Unknown error"]))
        time.sleep(2)


def select_result_filename(result: Dict[str, Any]) -> Optional[str]:
    """Ưu tiên node 18 (RESULT), loại node 19 (ORIGINAL IMAGE), nếu không có thì lấy node ảnh hợp lệ đầu tiên."""
    outputs = result.get("outputs", {}) or {}
    candidate: Optional[str] = None
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
        if nid == 18 and filename:
            return filename
        if candidate is None and nid != 19 and filename:
            candidate = filename
    return candidate


def download_image(server_url: str, filename: str, save_path: str) -> None:
    """Tải ảnh từ API /view theo filename và lưu ra đường dẫn save_path."""
    url = f"{server_url.rstrip('/')}/view"
    params = {"filename": filename, "subfolder": "", "type": "output"}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(resp.content)


def upload_image(server_url: str, image_path: str) -> str:
    """Upload ảnh lên ComfyUI (/upload/image). Trả về tên file đã lưu trên server (basename)."""
    url = f"{server_url.rstrip('/')}/upload/image"
    filename = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        files = {"image": (filename, f, "application/octet-stream")}
        resp = requests.post(url, files=files)
        resp.raise_for_status()
    return filename


def download_image_to_tmp(image_url: str, tmp_dir: str = "temp") -> str:
    """Tải ảnh từ URL về thư mục tạm và trả về đường dẫn file cục bộ."""
    os.makedirs(tmp_dir, exist_ok=True)
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()
    # cố gắng lấy tên file từ URL, fallback tên ngẫu nhiên
    base = os.path.basename(image_url.split("?")[0]) or f"image_{int(time.time())}.jpg"
    local_path = os.path.join(tmp_dir, base)
    with open(local_path, "wb") as f:
        f.write(resp.content)
    return local_path


def apply_overrides_to_workflow(workflow: Dict[str, Any], image_filename: Optional[str], prompt_text: Optional[str]) -> Dict[str, Any]:
    """Chỉ ghi đè 2 chỗ: filename của LoadImage và text_b của StringFunction|pysssss."""
    if not isinstance(workflow, dict) or "nodes" not in workflow:
        return workflow
    for node in workflow["nodes"]:
        ntype = node.get("type")
        widgets = node.get("widgets_values")
        if ntype == "LoadImage" and image_filename and isinstance(widgets, list) and len(widgets) >= 1:
            widgets[0] = image_filename  # giữ widget thứ 2 ("image") nguyên vẹn
        if ntype == "StringFunction|pysssss" and prompt_text and isinstance(widgets, list) and len(widgets) >= 4:
            # widgets: [action, tidy_tags, text_a, text_b, text_c]
            widgets[3] = prompt_text
    return workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ComfyUI workflow JSON via API")
    parser.add_argument("--server", default=os.environ.get("COMFYUI_SERVER_URL", "http://127.0.0.1:8188"), help="ComfyUI server URL (mặc định: http://127.0.0.1:8188)")
    parser.add_argument("--workflow", default="workflows/Restore.json", help="Đường dẫn file workflow JSON (mặc định: workflows/Restore.json)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout chờ hoàn tất (giây)")
    parser.add_argument("--output", default="output_images/result.png", help="Đường dẫn lưu file ảnh tải về (tùy chọn). Nếu để trống sẽ không tải.")
    parser.add_argument("--no-download", action="store_true", help="Không tải ảnh về, chỉ in filename")
    parser.add_argument("--image", help="Đường dẫn ảnh input trên máy bạn. Dùng kèm --upload để tự upload.")
    parser.add_argument("--image-url", help="URL ảnh input. Script sẽ tải về tạm và upload lên ComfyUI.")
    parser.add_argument("--prompt", help="Text để điền vào text_b của node StringFunction|pysssss (node 60)")
    parser.add_argument("--upload", action="store_true", help="Upload ảnh --image lên ComfyUI trước khi chạy workflow")

    args = parser.parse_args()

    # Đọc workflow JSON gốc (giữ nguyên mặc định)
    try:
        with open(args.workflow, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except Exception as e:
        print(f"Lỗi đọc workflow: {e}")
        sys.exit(1)

    # Upload ảnh nếu được yêu cầu hoặc nếu có URL ảnh
    image_filename: Optional[str] = None
    if args.image_url:
        try:
            local_path = download_image_to_tmp(args.image_url)
            image_filename = upload_image(args.server, local_path)
            print(f"Đã tải từ URL và upload ảnh lên server: {image_filename}")
        except Exception as e:
            print(f"Không thể dùng --image-url: {e}")
            sys.exit(1)
    elif args.image:
        if args.upload:
            if not os.path.isfile(args.image):
                print("Lỗi: --image không tồn tại.")
                sys.exit(1)
            try:
                image_filename = upload_image(args.server, args.image)
                print(f"Đã upload ảnh lên server: {image_filename}")
            except Exception as e:
                print(f"Upload thất bại: {e}")
                sys.exit(1)
        else:
            # Không upload: giả định file đã nằm trong thư mục input của ComfyUI
            image_filename = os.path.basename(args.image)

    # Chỉ ghi đè đúng 2 chỗ theo yêu cầu
    workflow = apply_overrides_to_workflow(workflow, image_filename=image_filename, prompt_text=args.prompt)

    print(f"Gửi workflow '{args.workflow}' lên {args.server}...")
    prompt_id = post_prompt(args.server, workflow)
    print(f"Prompt ID: {prompt_id}")

    print("Đang chờ hoàn tất...")
    result = wait_for_completion(args.server, prompt_id, timeout=args.timeout)

    filename = select_result_filename(result)
    if not filename:
        print("Không tìm thấy ảnh output trong kết quả.")
        sys.exit(2)

    print(f"Ảnh output trên server: {filename}")

    if not args.no_download:
        save_path = args.output
        try:
            download_image(args.server, filename, save_path)
            print(f"Đã tải ảnh về: {save_path}")
        except Exception as e:
            print(f"Không thể tải ảnh: {e}")


if __name__ == "__main__":
    main()


