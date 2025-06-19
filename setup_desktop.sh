#!/bin/bash

echo "🌙 Setting up Dream Recorder for Desktop"
echo "========================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed. Please install FFmpeg:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu/Debian: sudo apt install ffmpeg"
    echo "   Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing Python dependencies..."
pip install -r requirements_desktop.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p media/video media/audio media/thumbs db

# Copy config file
echo "⚙️  Setting up configuration..."
cp config_desktop.json config.json

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.json and add your API keys:"
echo "   - OPENAI_API_KEY"
echo "   - LUMALABS_API_KEY"
echo ""
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python dream_recorder_desktop.py"
echo ""
echo "3. Open your browser to: http://127.0.0.1:5000"
echo "" 