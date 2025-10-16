#!/usr/bin/env python3
"""
Script để test kết nối ComfyUI
"""

import requests
import json
import sys
import os

# Add parent directory to path để import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

def test_comfyui_connection():
    """Test kết nối ComfyUI"""
    print("🔌 Test kết nối ComfyUI")
    print("=" * 50)
    
    # Test system stats
    try:
        response = requests.get(f"{config.COMFYUI_SERVER_URL}/system_stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print("✅ ComfyUI đang chạy!")
            print(f"   - CPU: {stats.get('system', {}).get('cpu_percent', 'N/A')}%")
            print(f"   - RAM: {stats.get('system', {}).get('memory_percent', 'N/A')}%")
            print(f"   - GPU: {stats.get('system', {}).get('gpu_percent', 'N/A')}%")
        else:
            print(f"❌ ComfyUI trả về status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Không thể kết nối ComfyUI")
        print("💡 Đảm bảo ComfyUI đang chạy:")
        print("   cd /path/to/ComfyUI")
        print("   python main.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout khi kết nối ComfyUI")
        return False
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return False
    
    # Test history
    try:
        response = requests.get(f"{config.COMFYUI_SERVER_URL}/history", timeout=10)
        if response.status_code == 200:
            history = response.json()
            print("✅ Có thể truy cập history")
            print(f"   - Số job đã chạy: {len(history)}")
        else:
            print(f"⚠️ Không thể truy cập history: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Lỗi khi truy cập history: {e}")
    
    # Test queue info
    try:
        response = requests.get(f"{config.COMFYUI_SERVER_URL}/queue", timeout=10)
        if response.status_code == 200:
            queue = response.json()
            print("✅ Có thể truy cập queue")
            print(f"   - Job đang chờ: {len(queue.get('queue_pending', []))}")
            print(f"   - Job đang chạy: {len(queue.get('queue_running', []))}")
        else:
            print(f"⚠️ Không thể truy cập queue: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Lỗi khi truy cập queue: {e}")
    
    return True

def test_workflow_file():
    """Test workflow file"""
    print("\n📋 Test workflow file")
    print("=" * 50)
    
    workflow_file = "workflows/image_recovery_workflow.json"
    
    if not os.path.exists(workflow_file):
        print(f"❌ Không tìm thấy workflow file: {workflow_file}")
        print("💡 Chạy script setup workflow:")
        print("   python scripts/setup_workflow.py")
        return False
    
    try:
        with open(workflow_file, 'r') as f:
            workflow = json.load(f)
        
        print(f"✅ Workflow file hợp lệ: {workflow_file}")
        print(f"   - Số nodes: {len(workflow)}")
        
        # Kiểm tra các node quan trọng
        node_types = {}
        for node_id, node_data in workflow.items():
            class_type = node_data.get("class_type", "Unknown")
            node_types[class_type] = node_types.get(class_type, 0) + 1
        
        print("   - Các node types:")
        for class_type, count in node_types.items():
            print(f"     * {class_type}: {count}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Workflow file không hợp lệ JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi đọc workflow file: {e}")
        return False

def main():
    """Main function"""
    print("🧪 Test ComfyUI Setup")
    print("=" * 50)
    
    # Test connection
    connection_ok = test_comfyui_connection()
    
    # Test workflow file
    workflow_ok = test_workflow_file()
    
    print("\n📊 Kết quả test:")
    print("=" * 50)
    print(f"ComfyUI Connection: {'✅ OK' if connection_ok else '❌ FAIL'}")
    print(f"Workflow File: {'✅ OK' if workflow_ok else '❌ FAIL'}")
    
    if connection_ok and workflow_ok:
        print("\n🎉 Tất cả đều OK! Bạn có thể chạy API.")
        print("\n🚀 Chạy API:")
        print("   python main.py")
        print("\n🤖 Chạy Telegram Bot:")
        print("   python run_bot.py")
        print("\n🔄 Chạy cả hai:")
        print("   python run_all.py")
    else:
        print("\n⚠️ Cần sửa lỗi trước khi chạy API.")
        
        if not connection_ok:
            print("\n🔧 Sửa lỗi ComfyUI:")
            print("1. Đảm bảo ComfyUI đang chạy")
            print("2. Kiểm tra port 8188")
            print("3. Kiểm tra firewall")
        
        if not workflow_ok:
            print("\n🔧 Sửa lỗi Workflow:")
            print("1. Chạy: python scripts/setup_workflow.py")
            print("2. Tạo workflow trong ComfyUI")
            print("3. Export và lưu JSON")

if __name__ == "__main__":
    main()
