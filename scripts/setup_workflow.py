#!/usr/bin/env python3
"""
Script để setup workflow cho ComfyUI
"""

import json
import os
from pathlib import Path

def create_workflow_directory():
    """Tạo thư mục workflows"""
    workflows_dir = Path("workflows")
    workflows_dir.mkdir(exist_ok=True)
    print(f"✅ Đã tạo thư mục: {workflows_dir}")
    return workflows_dir

def create_sample_workflow():
    """Tạo workflow mẫu"""
    workflow = {
        "1": {
            "inputs": {
                "image": "input_image.jpg",
                "upload": "image"
            },
            "class_type": "LoadImage",
            "_meta": {
                "title": "Load Image"
            }
        },
        "2": {
            "inputs": {
                "text": "your prompt here",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Prompt)"
            }
        },
        "3": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Negative)"
            }
        },
        "4": {
            "inputs": {
                "ckpt_name": "your_model.safetensors"
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            }
        },
        "5": {
            "inputs": {
                "seed": 123456789,
                "steps": 20,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["6", 0]
            },
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "6": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
                "title": "Empty Latent Image"
            }
        },
        "7": {
            "inputs": {
                "samples": ["5", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "8": {
            "inputs": {
                "filename_prefix": "recovered_image",
                "images": ["7", 0]
            },
            "class_type": "SaveImage",
            "_meta": {
                "title": "Save Image"
            }
        }
    }
    
    return workflow

def save_workflow(workflow, filepath):
    """Lưu workflow vào file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã lưu workflow: {filepath}")

def main():
    """Main function"""
    print("🔧 Setup ComfyUI Workflow")
    print("=" * 50)
    
    # Tạo thư mục workflows
    workflows_dir = create_workflow_directory()
    
    print("\n📋 Hướng dẫn setup workflow:")
    print("=" * 50)
    print()
    print("1️⃣ Chạy ComfyUI:")
    print("   cd /path/to/ComfyUI")
    print("   python main.py")
    print()
    print("2️⃣ Vào ComfyUI Web UI:")
    print("   http://localhost:8188")
    print()
    print("3️⃣ Load workflow có sẵn:")
    print("   - Load workflow từ file .json")
    print("   - Hoặc tạo workflow mới")
    print()
    print("4️⃣ Export workflow:")
    print("   - Nhấn 'Save' trong ComfyUI")
    print("   - Copy JSON content")
    print()
    print("5️⃣ Lưu workflow:")
    print("   - Paste JSON vào file workflows/image_recovery_workflow.json")
    print("   - Hoặc sử dụng script này")
    print()
    
    # Tạo workflow mẫu
    choice = input("Bạn có muốn tạo workflow mẫu không? (y/N): ").strip().lower()
    
    if choice == 'y':
        workflow = create_sample_workflow()
        filepath = workflows_dir / "image_recovery_workflow.json"
        save_workflow(workflow, filepath)
        
        print("\n📝 Workflow mẫu đã được tạo!")
        print("⚠️ Bạn cần cập nhật:")
        print("   - Model name trong node 4")
        print("   - Node structure theo workflow thực tế")
        print("   - Parameters phù hợp với model")
    
    print("\n🎯 Bước tiếp theo:")
    print("1. Chạy ComfyUI: python main.py")
    print("2. Test workflow trong ComfyUI")
    print("3. Export workflow JSON")
    print("4. Lưu vào workflows/image_recovery_workflow.json")
    print("5. Test API với workflow thật")

if __name__ == "__main__":
    main()
