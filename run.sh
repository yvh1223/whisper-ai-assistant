#!/bin/bash

echo "Starting Whisper Dictation..."
echo "This app needs accessibility permissions to detect keyboard shortcuts"
echo "If this is your first time running the app, please allow Terminal in"
echo "System Preferences → Privacy & Security → Privacy → Accessibility"
echo ""
echo "The app will now open. Look for the microphone icon (🎙️) in your menu bar."
echo "Press the Globe/Fn key (bottom right corner of keyboard) to start/stop recording."
echo "Right Shift: Select text → Press once to play → Press again to stop TTS"
echo ""
echo "Press Ctrl+C to quit the app."

# Run the dictation app
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

# Activate virtual environment
source venv/bin/activate

# Check for Zscaler certificate and set absolute path for SSL verification
if [ -f "$SCRIPT_DIR/zscaler_root.pem" ]; then
    export SSL_CERT_FILE="$SCRIPT_DIR/zscaler_root.pem"
    export REQUESTS_CA_BUNDLE="$SCRIPT_DIR/zscaler_root.pem"
fi

# Parse command-line arguments
USE_LOCAL=false
LOCAL_MODEL="large-v3"
TTS_SPEED="1"

while [[ $# -gt 0 ]]; do
    case $1 in
        --use-local)
            USE_LOCAL=true
            # Only consume next arg as model if it doesn't start with --
            if [[ $# -gt 1 ]] && [[ "$2" != --* ]]; then
                LOCAL_MODEL="$2"
                shift 2
            else
                shift 1
            fi
            ;;
        --tts-speed)
            TTS_SPEED="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Enable MLX Whisper if requested
if [ "$USE_LOCAL" = true ]; then
    echo ""
    echo "MLX Whisper mode enabled (local transcription)"
    export USE_MLX_WHISPER=true
    export MLX_WHISPER_MODEL="$LOCAL_MODEL"
    echo "Using model: ${MLX_WHISPER_MODEL}"
    echo "First run will download model to ~/.cache/huggingface/hub/"
fi

# Set TTS playback speed
# Valid options: 1, 1.25, 1.5, 2 (default: 1)
export TTS_SPEED="$TTS_SPEED"
if [[ "$TTS_SPEED" =~ ^(1|1.25|1.5|2)$ ]]; then
    echo "TTS playback speed: ${TTS_SPEED}x"
else
    echo "Warning: Invalid TTS speed '$TTS_SPEED', using default 1x"
    export TTS_SPEED="1"
fi

# Run with venv Python
python src/main.py