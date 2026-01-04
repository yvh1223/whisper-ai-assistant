#!/bin/bash

echo "Starting Whisper Dictation..."
echo "This app needs accessibility permissions to detect keyboard shortcuts"
echo "If this is your first time running the app, please allow Terminal in"
echo "System Preferences → Privacy & Security → Privacy → Accessibility"
echo ""
echo "The app will now open. Look for the microphone icon (🎙️) in your menu bar."
echo "Press the Globe/Fn key (bottom right corner of keyboard) to start/stop recording."
echo "Or hold Right Shift to record instantly (release after 0.75s to process, before to discard)."
echo ""
echo "Press Ctrl+C to quit the app."

# Run the dictation app
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Check for --use-local flag to enable MLX Whisper
if [[ "$1" == "--use-local" ]]; then
    echo ""
    echo "MLX Whisper mode enabled (local transcription)"
    export USE_MLX_WHISPER=true

    # Optionally set model size
    # Options: tiny (39MB), base (140MB), small (244MB), medium (769MB), large-v3 (2.9GB)
    # Default: large-v3
    # Usage: ./run.sh --use-local small
    export MLX_WHISPER_MODEL="${2:-large-v3}"
    echo "Using model: ${MLX_WHISPER_MODEL}"
    echo "First run will download model to ~/.cache/huggingface/hub/"
fi

# Run with venv Python
python src/main.py