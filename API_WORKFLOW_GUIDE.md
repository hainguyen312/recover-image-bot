# Hướng dẫn sử dụng ComfyUI API Workflow System

## Tổng quan

Hệ thống mới sử dụng **ComfyUI API JSON format** thay vì GUI export format, cho phép can thiệp trực tiếp vào workflow mà không cần giao diện người dùng.

## Cách hoạt động

### 1. Template System

Hệ thống sử dụng **template với placeholder** để dễ dàng thay đổi parameters:

```python
# Tạo template từ file JSON
template = client.create_workflow_template("workflows/Restore_template.json")

# Áp dụng giá trị thực tế
workflow = client.apply_template_values(
    template=template,
    image_filename="input.jpg",
    user_prompt="restore this photo",
    seed=12345,
    steps=8,
    cfg=1.5,
    guidance=1.8
)
```

### 2. Placeholder System

File `workflows/Restore_template.json` chứa các placeholder:

- `__IMAGE_FILENAME__`: Tên file ảnh input
- `__USER_PROMPT__`: Prompt từ user
- `__SEED__`: Seed cho KSampler đầu tiên
- `__STEPS__`: Số bước sampling
- `__CFG__`: CFG scale
- `__GUIDANCE__`: Guidance scale
- `__SEED_2__`, `__STEPS_2__`, `__CFG_2__`: Parameters cho KSampler thứ hai

### 3. String Replacement

Hệ thống sử dụng **string replacement** để thay thế placeholder:

```python
replacements = {
    "__IMAGE_FILENAME__": image_filename,
    "__USER_PROMPT__": user_prompt,
    "__SEED__": str(kwargs.get("seed", 60747213359817)),
    "__STEPS__": str(kwargs.get("steps", 8)),
    "__CFG__": str(kwargs.get("cfg", 1.5)),
    # ... các placeholder khác
}

# Thực hiện replacement
workflow_str = json.dumps(workflow)
for placeholder, value in replacements.items():
    workflow_str = workflow_str.replace(placeholder, value)
workflow = json.loads(workflow_str)
```

## Cách sử dụng

### 1. Xử lý ảnh cơ bản

```python
from comfyui_client import ComfyUIClient

client = ComfyUIClient()

# Xử lý ảnh với prompt
result_filename = client.process_image_recovery(
    input_image_path="path/to/image.jpg",
    prompt="restore this damaged photo, fix scratches",
    steps=8,
    guidance_scale=1.8,
    seed=12345
)

# Tải ảnh kết quả
img_bytes = client.get_image(result_filename)
```

### 2. Sử dụng template trực tiếp

```python
# Tạo template
template = client.create_workflow_template()

# Áp dụng giá trị
workflow = client.apply_template_values(
    template=template,
    image_filename="input.jpg",
    user_prompt="restore photo",
    seed=12345,
    steps=10,
    cfg=2.0,
    guidance=2.5
)

# Gửi workflow
prompt_id = client.queue_prompt(workflow)
result = client.wait_for_completion(prompt_id)
```

### 3. Tùy chỉnh parameters

```python
# Có thể thay đổi nhiều parameters
workflow = client.apply_template_values(
    template=template,
    image_filename="input.jpg",
    user_prompt="restore this photo",
    seed=99999,           # Seed khác
    steps=15,             # Nhiều bước hơn
    cfg=2.5,              # CFG cao hơn
    guidance=3.0          # Guidance cao hơn
)
```

## Ưu điểm của hệ thống mới

### 1. **Dễ dàng can thiệp**
- Chỉ cần thay đổi placeholder trong template
- Không cần hiểu cấu trúc phức tạp của workflow

### 2. **Linh hoạt**
- Có thể thay đổi bất kỳ parameter nào
- Dễ dàng thêm placeholder mới

### 3. **Hiệu quả**
- Sử dụng trực tiếp API JSON format
- Không cần convert từ GUI format

### 4. **Dễ bảo trì**
- Template tách biệt với code
- Dễ dàng cập nhật workflow

## Cấu trúc file

```
workflows/
├── Restore.json              # Workflow gốc (API format)
├── Restore_template.json     # Template với placeholder
└── ...

comfyui_client.py             # Client với template system
test_new_system.py           # Script test hệ thống
```

## Test hệ thống

Chạy script test để kiểm tra:

```bash
python test_new_system.py
```

Script sẽ:
1. Test tạo template
2. Test áp dụng giá trị
3. Test xử lý ảnh thực tế
4. Lưu ảnh kết quả

## Lưu ý quan trọng

### 1. **Node IDs**
- Node 75: LoadImage (ảnh input)
- Node 60: StringFunction|pysssss (prompt)
- Node 3: KSampler đầu tiên
- Node 72: KSampler thứ hai
- Node 80: FluxGuidance

### 2. **Placeholder naming**
- Sử dụng format `__PLACEHOLDER_NAME__`
- Tất cả placeholder phải được thay thế trước khi gửi

### 3. **Error handling**
- Kiểm tra kết nối ComfyUI trước khi xử lý
- Xử lý lỗi upload ảnh và download kết quả

## Ví dụ thực tế

```python
# Bot Telegram sử dụng hệ thống mới
result_filename = client.process_image_recovery(
    input_image_path=local_path,
    prompt=prompt,
    steps=8,
    guidance_scale=1.8
)

# Tải và gửi ảnh kết quả
img_bytes = client.get_image(result_filename)
await update.message.reply_photo(
    photo=BytesIO(img_bytes),
    caption=f"🎨 Ảnh đã được phục hồi!\n\nPrompt: {prompt}"
)
```

Hệ thống mới này cho phép can thiệp vào workflow ComfyUI một cách linh hoạt và hiệu quả, hoàn toàn không cần sử dụng GUI.
