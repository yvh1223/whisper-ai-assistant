#!/bin/bash
# ABOUTME: Stop Whisper Dictation running in background

echo "Stopping Whisper Dictation..."

# Find and kill the process
pkill -f "python.*src/main.py"

# Wait a moment
sleep 1

# Check if stopped
if pgrep -f "python.*src/main.py" > /dev/null; then
    echo "⚠️  Process still running. Forcing shutdown..."
    pkill -9 -f "python.*src/main.py"
    sleep 1
fi

if ! pgrep -f "python.*src/main.py" > /dev/null; then
    echo "✓ Whisper Dictation stopped"
else
    echo "❌ Failed to stop. Try manually:"
    echo "   ps aux | grep 'src/main.py'"
    echo "   kill -9 <PID>"
fi
