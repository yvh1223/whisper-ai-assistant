# Whisper Dictation

**Note: This application is for macOS only.**

A macOS application that converts speech to text using OpenAI's Whisper model running locally. Press the Globe/Function key to start recording, press it again to stop recording, transcribe, and paste text at your current cursor position.

## Features

- System tray (menu bar) application that runs in the background
- Global hotkey (Globe/Function key) to trigger dictation
- Transcribes speech to text using OpenAI's Whisper model locally
- Automatically pastes transcribed text at your cursor position
- **AI-powered text enhancement** - when you have text selected, your voice becomes an instruction to modify that text using OpenAI GPT models
- **Text-to-Speech (TTS)** - Select text and have it read aloud with natural voice
  - Use menu bar "Read Selected Text Aloud" option
  - Or say "read this", "read aloud", or "speak" when text is selected
- Visual feedback with menu bar icon status (🎙️ for dictation, 🔊 for reading)

## Setup and Installation

### Development Setup

1. Install Python dependencies:

```
pip install -r requirements.txt
```

2. Install PortAudio (required for PyAudio):

```
brew install portaudio
```

3. Set up OpenAI API (optional - for AI text enhancement and/or cloud-based transcription):

```
cp .env.example .env
# Edit .env and add your OpenAI API key
# Get your API key from: https://platform.openai.com/api-keys
```

4. Run the application in development mode:

```
python src/main.py
```

### Running the App (System-Wide)

**Recommended - using the start script:**

```bash
./start_background.sh
```

This will:
- Activate the virtual environment
- Start the app with menu bar icon 🎙️
- Show clear instructions

**⚠️ IMPORTANT:** The terminal window must stay open (you can minimize it). Closing the terminal will stop the app.

**To stop:**
```bash
# In the terminal where it's running: Press Ctrl+C
# Or from another terminal:
./stop_background.sh
```

**Alternative - direct run:**
```bash
./run.sh
```

## Usage

1. Launch the Whisper Dictation app. You'll see a microphone icon (🎙️) in your menu bar.
2. Press the Globe key or Function key on your keyboard to start recording.
3. Speak clearly into your microphone.
4. Press the Globe/Function key again to stop recording.
5. The app will transcribe your speech and automatically paste it at your current cursor position.

### AI Text Enhancement (New Feature)

When you have OpenAI API configured, you can use voice commands to modify selected text:

1. **Select text** in any application (highlight the text you want to modify)
2. **Press the Globe/Function key** to start recording
3. **Give a voice instruction** like:
   - "Make this more professional"
   - "Translate this to Spanish"
   - "Summarize this paragraph"
   - "Fix the grammar"
   - "Make this sound friendlier"
4. **Press the Globe/Function key again** to stop recording
5. The selected text will be **automatically replaced** with the AI-enhanced version

**Note**: If no text is selected, the app behaves normally and just inserts the transcribed text.

### Text-to-Speech (TTS)

Have selected text read aloud with natural voice:

**Method 1: Voice Command**
1. **Select text** in any application
2. **Press Globe/Function key** to start recording
3. **Say**: "read this" or "read aloud" or "speak"
4. **Press Globe/Function key** to stop
5. The text will be **read aloud** automatically

**Method 2: Menu Bar**
1. **Select text** in any application
2. Click the 🎙️ icon in your menu bar
3. Click **"Read Selected Text Aloud"**
4. The text will be read aloud

**Note**: TTS requires OpenAI API to be configured in `.env`

You can also interact with the app through the menu bar icon:

- Click "Start Recording" / "Stop Recording" to toggle recording
- Click "Read Selected Text Aloud" for TTS
- Select microphone from the "Microphone" submenu
- View status in the menu
- Click "Quit" to exit the application

## Permissions

The app requires the following permissions:

- Microphone access (to record your speech).  
  Go to System Preferences → Security & Privacy → Privacy → Microphone and add your Terminal or the app.
- Accessibility access (to simulate keyboard presses for pasting).  
  Go to System Preferences → Security & Privacy → Privacy → Accessibility and add your Terminal or the app.

## Requirements

- macOS 10.14 or later
- Microphone
- OpenAI API key (optional - for AI text enhancement and/or cloud-based transcription)

## Troubleshooting

### Stopping the Background Process

**Easy way:**
```bash
./stop_background.sh
```

**Manual way:**
1. List the running process(es):
```bash
ps aux | grep 'src/main.py'
```

2. Kill the process by its PID:
```bash
kill -9 <PID>
```

### Common Issues

**"The terminal has no selection to copy"** - This is normal when using Terminal. Use the app in TextEdit, Notes, or other apps to avoid this message.

**Text not being replaced** - Make sure you:
1. Have text selected before pressing Globe/Fn
2. Keep the text editor window focused
3. Have OPENAI_API_KEY set in .env
4. Have OPENAI_DISABLE_SSL_VERIFY=true in .env

**Recording not working** - Check:
1. Microphone permissions granted
2. Accessibility permissions granted
3. Correct microphone selected in menu bar
