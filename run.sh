#!/bin/bash

echo "Starting Whisper Dictation..."
echo ""

# Activate virtual environment first
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
source venv/bin/activate

# Check accessibility permissions programmatically
ACCESSIBILITY_CHECK=$(python3 -c "from ApplicationServices import AXIsProcessTrusted; print('yes' if AXIsProcessTrusted() else 'no')" 2>/dev/null)

# Check microphone permissions programmatically
MICROPHONE_CHECK=$(python3 -c "
try:
    from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
    status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
    print('yes' if status == 3 else 'no')
except:
    print('unknown')
" 2>/dev/null)

PERMISSIONS_OK=true

echo "=== Permission Check ==="
if [ "$ACCESSIBILITY_CHECK" = "yes" ]; then
    echo "✓ Accessibility: Granted"
else
    echo "✗ Accessibility: Not Granted"
    PERMISSIONS_OK=false
fi

if [ "$MICROPHONE_CHECK" = "yes" ]; then
    echo "✓ Microphone: Granted"
elif [ "$MICROPHONE_CHECK" = "unknown" ]; then
    echo "? Microphone: Status unknown (will prompt when recording)"
else
    echo "✗ Microphone: Not Granted"
    PERMISSIONS_OK=false
fi
echo "========================"
echo ""

if [ "$PERMISSIONS_OK" = "false" ]; then
    echo "⚠️  PERMISSIONS REQUIRED"
    echo ""
    
    if [ "$ACCESSIBILITY_CHECK" != "yes" ]; then
        echo "Accessibility (for keyboard shortcuts):"
        echo "  → System Settings → Privacy & Security → Accessibility"
        echo "  → Add and enable: Terminal"
        echo "  → IMPORTANT: After enabling, you must:"
        echo "     1. Remove Terminal from the list (click '-' button)"
        echo "     2. Add it back (click '+' button, select Terminal.app)"
        echo "     3. Quit Terminal completely (Cmd+Q)"
        echo "     4. Reopen Terminal and run this script again"
        echo ""
    fi
    
    if [ "$MICROPHONE_CHECK" != "yes" ]; then
        echo "Microphone (for audio recording):"
        echo "  → System Settings → Privacy & Security → Microphone"
        echo "  → Add and enable: Terminal"
        echo ""
        echo "Note: When you start the app, macOS will prompt you to allow microphone access."
        echo ""
    fi
    
    read -p "Press Enter to continue, or Ctrl+C to exit and grant permissions..."
    echo ""
fi

echo ""
echo "📋 REQUIRED PERMISSIONS (verify in System Settings):"
echo "   ✓ Privacy & Security → Accessibility → Terminal (enabled)"
echo "   ✓ Privacy & Security → Microphone → Terminal (enabled)"
echo ""
echo "   If keyboard shortcuts don't work after enabling:"
echo "   1. Remove Terminal from Accessibility list (- button)"
echo "   2. Add it back (+ button)"
echo "   3. Quit Terminal completely (Cmd+Q) and reopen"
echo ""

echo "The app will now open. Look for the microphone icon (🎙️) in your menu bar."
if [ "$ACCESSIBILITY_CHECK" = "yes" ] && [ "$MICROPHONE_CHECK" = "yes" ]; then
    echo "Press the Globe/Fn key (bottom right corner) to start/stop recording."
    echo "Or hold Right Shift to record instantly (release after 1.5s to process)."
elif [ "$MICROPHONE_CHECK" = "yes" ]; then
    echo "Use menu bar: Click 🎙️ → Start Recording to record manually."
else
    echo "Grant microphone permission when prompted to enable recording."
fi
echo ""
echo "Press Ctrl+C to quit the app."
echo ""

# Check for Zscaler certificate and set absolute path for SSL verification
if [ -f "$SCRIPT_DIR/zscaler_root.pem" ]; then
    export SSL_CERT_FILE="$SCRIPT_DIR/zscaler_root.pem"
    export REQUESTS_CA_BUNDLE="$SCRIPT_DIR/zscaler_root.pem"
fi

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