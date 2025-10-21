#!/usr/bin/env python3
"""
Script test hệ thống ComfyUI mới với template system
"""

import os
import sys
import logging
from comfyui_client import ComfyUIClient

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_template_system():
    """Test template system với file ảnh test"""
    try:
        # Khởi tạo client
        client = ComfyUIClient()
        
        # Kiểm tra kết nối ComfyUI
        if not client.health_check():
            logger.error("❌ Không thể kết nối ComfyUI server")
            return False
        
        logger.info("✅ Kết nối ComfyUI thành công")
        
        # Test với ảnh có sẵn
        test_image_path = "input_images/test_image.jpg"
        if not os.path.exists(test_image_path):
            logger.error(f"❌ Không tìm thấy file test: {test_image_path}")
            return False
        
        logger.info(f"📸 Sử dụng ảnh test: {test_image_path}")
        
        # Test prompt
        test_prompt = "restore this photo, fix any damage, improve quality and colors"
        logger.info(f"📝 Prompt test: {test_prompt}")
        
        # Chạy xử lý
        logger.info("🚀 Bắt đầu xử lý ảnh...")
        result_filename = client.process_image_recovery(
            input_image_path=test_image_path,
            prompt=test_prompt,
            steps=8,
            guidance_scale=1.8,
            seed=12345
        )
        
        logger.info(f"✅ Xử lý hoàn tất! Kết quả: {result_filename}")
        
        # Test tải ảnh kết quả
        try:
            img_bytes = client.get_image(result_filename)
            logger.info(f"✅ Tải ảnh kết quả thành công ({len(img_bytes)} bytes)")
            
            # Lưu ảnh kết quả
            output_path = f"output_images/test_result_new_system.png"
            os.makedirs("output_images", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            logger.info(f"💾 Đã lưu ảnh kết quả: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi tải ảnh kết quả: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong quá trình test: {str(e)}")
        return False

def test_template_creation():
    """Test tạo template"""
    try:
        client = ComfyUIClient()
        
        # Test tạo template
        template = client.create_workflow_template()
        logger.info(f"✅ Tạo template thành công với {len(template)} nodes")
        
        # Test áp dụng giá trị
        workflow = client.apply_template_values(
            template=template,
            image_filename="test.jpg",
            user_prompt="test prompt",
            seed=12345,
            steps=10,
            cfg=2.0,
            guidance=2.5
        )
        
        logger.info("✅ Áp dụng giá trị template thành công")
        
        # Kiểm tra một số giá trị đã được thay thế
        if "75" in workflow and workflow["75"]["inputs"]["image"] == "test.jpg":
            logger.info("✅ Image filename đã được thay thế")
        else:
            logger.warning("⚠️ Image filename chưa được thay thế đúng")
        
        if "60" in workflow and workflow["60"]["inputs"]["text_b"] == "test prompt":
            logger.info("✅ User prompt đã được thay thế")
        else:
            logger.warning("⚠️ User prompt chưa được thay thế đúng")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi test template: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Bắt đầu test hệ thống ComfyUI mới...")
    
    # Test 1: Template system
    logger.info("\n📋 Test 1: Template system")
    if test_template_creation():
        logger.info("✅ Template system hoạt động tốt")
    else:
        logger.error("❌ Template system có lỗi")
        sys.exit(1)
    
    # Test 2: Xử lý ảnh thực tế
    logger.info("\n🖼️ Test 2: Xử lý ảnh thực tế")
    if test_template_system():
        logger.info("✅ Xử lý ảnh thành công")
    else:
        logger.error("❌ Xử lý ảnh thất bại")
        sys.exit(1)
    
    logger.info("\n🎉 Tất cả test đều thành công!")
    logger.info("🚀 Hệ thống mới đã sẵn sàng sử dụng!")
