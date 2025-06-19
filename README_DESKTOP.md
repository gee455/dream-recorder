# Dream Recorder Desktop Edition

A desktop-friendly version of the Dream Recorder that runs on your computer instead of a Raspberry Pi.

## Features

- 🎤 **Voice Recording**: Record your dreams using your computer's microphone
- 🤖 **AI Processing**: Uses OpenAI Whisper for transcription and GPT for prompt generation
- 🎬 **Video Generation**: Creates dream videos using Luma Labs AI
- 🎨 **Dreamy Effects**: Applies cinematic filters to create dreamy, low-res videos
- 📚 **Dream Library**: Browse and manage all your generated dreams

## Quick Start

### 1. Prerequisites

- **Python 3.8+** installed on your system
- **FFmpeg** installed on your system
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 2. Setup

```bash
# Run the setup script
./setup_desktop.sh
```

### 3. Configure API Keys

Edit `config.json` and add your API keys:

```json
{
  "OPENAI_API_KEY": "your-openai-api-key-here",
  "LUMALABS_API_KEY": "your-luma-labs-api-key-here"
}
```

**Get API Keys:**
- **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Luma Labs**: [lumalabs.ai/api/dashboard](https://lumalabs.ai/api/dashboard)

### 4. Run the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
python dream_recorder_desktop.py
```

### 5. Open in Browser

Navigate to: http://127.0.0.1:5000

## Usage

### Recording Dreams

1. Click **"Start Recording"** to begin recording your dream
2. Speak your dream description into your microphone
3. Click **"Stop Recording"** when finished
4. Wait for processing (transcription → prompt generation → video creation)
5. Your dream video will automatically play when ready

### Playing Dreams

- **"Play Latest Dream"**: Play your most recent dream
- **"Previous Dream"**: Cycle through your dream history
- **"Dream Library"**: Browse all your dreams in a grid view

## Cost

The app uses external APIs with the following approximate costs:

- **OpenAI**: < $0.01 per dream (Whisper + GPT)
- **Luma Labs**: $0.14 per dream (540p, 5 seconds)

## File Structure

```
dream-recorder/
├── dream_recorder_desktop.py    # Main desktop application
├── config_desktop.json          # Desktop configuration
├── requirements_desktop.txt     # Python dependencies
├── setup_desktop.sh            # Setup script
├── templates/
│   └── index_desktop.html      # Desktop web interface
├── functions/                   # Core functionality
├── media/                       # Generated videos and audio
│   ├── video/                  # Generated dream videos
│   ├── audio/                  # Recorded audio
│   └── thumbs/                 # Video thumbnails
└── db/                         # SQLite database
```

## Troubleshooting

### Microphone Issues
- Make sure your browser has permission to access your microphone
- Try refreshing the page and allowing microphone access when prompted

### FFmpeg Issues
- Ensure FFmpeg is installed and accessible from command line
- Test with: `ffmpeg -version`

### API Key Issues
- Verify your API keys are correct in `config.json`
- Check that you have sufficient credits in your API accounts

### Port Issues
- If port 5000 is in use, change the port in `config.json`
- Or kill the process using port 5000: `lsof -ti:5000 | xargs kill -9`

## Development

To run in development mode:

```bash
export FLASK_ENV=development
python dream_recorder_desktop.py
```

## Differences from Raspberry Pi Version

- **No GPIO**: Removed Raspberry Pi specific touch sensor controls
- **Web Interface**: Added desktop-friendly web controls
- **Local Host**: Runs on 127.0.0.1 instead of 0.0.0.0
- **Microphone Access**: Uses browser's MediaRecorder API
- **No Docker**: Runs directly with Python instead of containerized

## License

Same as the original project. See LICENSE.md for details. 