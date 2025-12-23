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

# Run with venv Python
python src/main.py