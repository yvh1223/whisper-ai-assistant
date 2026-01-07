#!/bin/bash
# ABOUTME: Start Whisper Dictation - Keep this terminal open!

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

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

# Check for Zscaler certificate and set absolute path for SSL verification
if [ -f "$SCRIPT_DIR/zscaler_root.pem" ]; then
    export SSL_CERT_FILE="$SCRIPT_DIR/zscaler_root.pem"
    export REQUESTS_CA_BUNDLE="$SCRIPT_DIR/zscaler_root.pem"
fi

# Parse command-line arguments
USE_LOCAL=false
LOCAL_MODEL="large-v3"
TTS_SPEED="1"
TTS_ENABLED=false

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
        --tts-on)
            TTS_ENABLED=true
            shift 1
            ;;
        *)
            shift
            ;;
    esac
done

# Enable MLX Whisper if requested
if [ "$USE_LOCAL" = true ]; then
    echo "✓ MLX Whisper mode enabled (local transcription)"
    export USE_MLX_WHISPER=true
    export MLX_WHISPER_MODEL="$LOCAL_MODEL"
    echo "  Model: ${MLX_WHISPER_MODEL}"
fi

# Set TTS enabled/disabled
export TTS_ENABLED="$TTS_ENABLED"
if [ "$TTS_ENABLED" = true ]; then
    echo "✓ TTS enabled"
    # Set TTS playback speed
    # Valid options: 1, 1.25, 1.5, 2 (default: 1)
    export TTS_SPEED="$TTS_SPEED"
    if [[ "$TTS_SPEED" =~ ^(1|1.25|1.5|2)$ ]]; then
        echo "  TTS playback speed: ${TTS_SPEED}x"
    else
        echo "⚠️  Warning: Invalid TTS speed '$TTS_SPEED', using default 1x"
        export TTS_SPEED="1"
    fi
else
    echo "✓ TTS disabled (use --tts-on to enable)"
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
