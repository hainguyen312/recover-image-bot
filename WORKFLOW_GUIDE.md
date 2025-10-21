# Hướng Dẫn Sử Dụng Workflow Restore.json

## Tổng Quan

Workflow `Restore.json` đã được sửa để hoạt động chính xác giống như khi chạy trên ComfyUI GUI local. Thay vì convert workflow sang format API phức tạp, code hiện tại sử dụng trực tiếp workflow ở format export gốc.

## Những Thay Đổi Chính

### 1. Sửa Lại Workflow Conversion
- **Trước**: Convert workflow không đúng cách, thiếu inputs cho KSampler
- **Sau**: Convert workflow đúng cách từ format export sang format API với đầy đủ inputs

### 2. Convert Workflow Đúng Cách
- **Trước**: Convert không đầy đủ, thiếu inputs cho KSampler
- **Sau**: Convert đầy đủ tất cả nodes với đúng inputs:
  - KSampler có đầy đủ 10 inputs (seed, steps, cfg, sampler_name, scheduler, denoise, model, positive, negative, latent_image)
  - Tất cả connections được map đúng từ links
  - Ghi đè 2 tham số: `filename` trong LoadImage và `text_b` trong StringFunction

### 3. Sử Dụng API Đúng Cách
- Convert workflow từ format export sang format API chuẩn
- Đảm bảo tất cả nodes có đủ inputs cần thiết

## Cách Sử Dụng

### 1. Sử Dụng Trong Code

```python
from comfyui_client import ComfyUIClient

# Khởi tạo client
client = ComfyUIClient()

# Chạy workflow với ảnh và prompt
result_filename = client.process_image_recovery_exact(
    input_image_path="input_images/your_image.jpg",
    prompt="a Vietnamese man wearing a black suit, white shirt, and light gray tie"
)

# Tải ảnh kết quả
image_data = client.get_image(result_filename)
with open("output.jpg", "wb") as f:
    f.write(image_data)
```

### 2. Sử Dụng Script Demo

```bash
# Thêm ảnh vào thư mục input_images/
python demo_workflow.py
```

### 3. Test Workflow

```bash
# Kiểm tra workflow có hoạt động đúng không
python test_workflow.py
```

## Cấu Trúc Workflow

Workflow `Restore.json` bao gồm:

- **41 nodes** với các chức năng khác nhau
- **62 links** kết nối các nodes
- **Node 75**: LoadImage - Load ảnh input
- **Node 60**: StringFunction|pysssss - Xử lý prompt text
- **Node 18**: PreviewImage (RESULT) - Ảnh kết quả cuối cùng
- **Node 19**: PreviewImage (ORIGINAL IMAGE) - Ảnh gốc

## Lưu Ý Quan Trọng

1. **Giữ Nguyên Workflow**: Tất cả các tham số khác trong workflow được giữ nguyên như trong file gốc
2. **Chỉ Ghi Đè 2 Tham Số**: 
   - Filename ảnh input
   - Prompt text_b của node StringFunction
3. **Format Export**: Workflow được sử dụng ở format export gốc, không convert
4. **Tương Thích**: Hoạt động giống hệt như khi chạy trên ComfyUI GUI

## Troubleshooting

### Lỗi "Không tìm thấy ảnh output"
- Kiểm tra ComfyUI server có chạy không
- Kiểm tra workflow có lỗi không
- Xem log để debug

### Lỗi Upload ảnh
- Kiểm tra đường dẫn ảnh input
- Kiểm tra quyền truy cập file
- Kiểm tra kết nối đến ComfyUI server

### Lỗi Workflow
- Kiểm tra file `workflows/Restore.json` có tồn tại không
- Kiểm tra cấu trúc JSON có đúng không
- Chạy `python test_workflow.py` để test

## So Sánh Với Phiên Bản Cũ

| Tính Năng | Phiên Bản Cũ | Phiên Bản Mới |
|-----------|--------------|---------------|
| Workflow Conversion | Không đúng, thiếu inputs | Convert đúng cách, đầy đủ inputs |
| KSampler Inputs | Thiếu seed, steps, cfg, etc. | Đầy đủ 10 inputs |
| Override Logic | Convert toàn bộ workflow | Convert đúng + ghi đè 2 tham số |
| Tương Thích | Chỉ chạy một phần nodes | Chạy đầy đủ tất cả nodes như GUI |
| Debug | Khó debug | Dễ debug |
| Bảo Trì | Phức tạp | Đơn giản |

## Kết Luận

Phiên bản mới đã sửa lại workflow conversion để hoạt động chính xác giống như ComfyUI GUI. Việc convert đúng cách từ format export sang format API đảm bảo tất cả nodes chạy đầy đủ với đúng inputs, giúp workflow hoạt động ổn định và dễ bảo trì hơn.
