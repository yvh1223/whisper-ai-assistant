#!/bin/bash
# ABOUTME: Start Whisper Dictation - Keep this terminal open!

cd "$(dirname "$0")"

# Check if already running
if pgrep -f "python.*src/main.py" > /dev/null; then
    echo "⚠️  Whisper Dictation is already running!"
    echo ""
    echo "To stop it, run: ./stop_background.sh"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          Whisper Dictation - Starting...                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check for --use-local flag to enable MLX Whisper
if [[ "$1" == "--use-local" ]]; then
    echo "✓ MLX Whisper mode enabled (local transcription)"
    export USE_MLX_WHISPER=true
    export MLX_WHISPER_MODEL="${2:-large-v3}"
    echo "  Model: ${MLX_WHISPER_MODEL}"
fi

echo "✓ Starting app with menu bar icon 🎙️"
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  IMPORTANT: Keep this terminal window open!                ║"
echo "║                                                                 ║"
echo "║  Minimize it, but DON'T close it.                              ║"
echo "║  The app will stop if you close this window.                   ║"
echo "║                                                                 ║"
echo "║  To stop: Press Ctrl+C or run ./stop_background.sh             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting in 2 seconds..."
sleep 2

# Run the app (will block here until stopped)
python src/main.py
