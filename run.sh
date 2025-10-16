#!/bin/bash

# Script để chạy Image Recovery Bot API

echo "🚀 Starting Image Recovery Bot API..."

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 không được cài đặt"
    exit 1
fi

# Kiểm tra file .env
if [ ! -f .env ]; then
    echo "⚠️ File .env không tồn tại"
    echo "💡 Chạy: python scripts/setup.py để thiết lập"
    exit 1
fi

# Kiểm tra ComfyUI
echo "🔍 Kiểm tra ComfyUI..."
if curl -s http://localhost:8188/system_stats > /dev/null; then
    echo "✅ ComfyUI đang chạy"
else
    echo "⚠️ ComfyUI không chạy tại http://localhost:8188"
    echo "💡 Vui lòng chạy ComfyUI trước"
    read -p "Bạn có muốn tiếp tục không? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Chạy API
echo "🎯 Starting API server..."
python main.py
