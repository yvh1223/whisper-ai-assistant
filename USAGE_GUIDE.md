# Whisper Dictation - Usage Guide

## Quick Start

```bash
# Run the app
python src/main.py

# Or run in background
nohup ./run.sh >/dev/null 2>&1 & disown
```

## 🎤 Keyboard Shortcuts

### Recording Triggers (Choose One)

#### Option 1: Globe/Fn Key (Recommended)
- **Press** Globe/Fn key (bottom left) → **Start recording** 🔴
- **Press again** → **Stop & transcribe** ✅
- **Location**: Next to left Cmd key on Mac keyboards

#### Option 2: Right Shift Key (Quick & Smart)
- **Hold** Right Shift → **Starts recording immediately**
- **Release <0.75s** → **Discards recording** (too short, probably accident)
- **Release >0.75s** → **Processes & transcribes** ✅
- **Press another key while holding** → **Cancels recording** (you're typing)

### Stop Background Process

```bash
# Find the process
ps aux | grep 'src/main.py'

# Kill it
kill -9 <PID>
```

---

## 📊 Menu Bar Interface

Look for **🎙️** icon in your menu bar (top right of screen).

### Menu Options

1. **Start/Stop Recording**
   - Click to manually start/stop recording
   - Same as using keyboard shortcuts

2. **Microphone** (submenu)
   - Lists all available input devices
   - Default microphone marked with "(Default)"
   - Click to switch between microphones
   - Useful for external mics, AirPods, etc.

3. **Status**
   - Shows current app state:
     - "Ready" - waiting for input
     - "Recording..." - actively recording
     - "Transcribing..." - processing audio
     - "Transcribed: [text]" - last transcription

4. **Quit**
   - Stops the app completely

---

## 🎯 Two Modes of Operation

### Mode 1: Simple Dictation (Default)

**When**: No text is selected

**What happens**:
1. Press Globe/Fn or hold Right Shift
2. Speak clearly
3. Release/press again
4. Text appears at cursor position ✨

**Example**:
```
You: [Press Globe] "Hello world, this is a test" [Press Globe]
Result: Hello world, this is a test █
```

---

### Mode 2: AI Text Enhancement (NEW!)

**When**: Text is selected (highlighted)

**What happens**:
1. **Select text** you want to modify (highlight it)
2. Press Globe/Fn or hold Right Shift
3. **Give voice instruction** (not the text itself!)
4. Release/press again
5. Selected text is **replaced** with AI-enhanced version ✨

**Examples**:

```
Selected: "hey whats up"
Voice: "Make this more professional"
Result: "Good morning, how are you doing?"
```

```
Selected: "The quick brown fox"
Voice: "Translate to Spanish"
Result: "El rápido zorro marrón"
```

```
Selected: "this is a long paragraph with many words..."
Voice: "Summarize in one sentence"
Result: "Brief summary of the paragraph."
```

```
Selected: "my email is bad grammer and spelling"
Voice: "Fix grammar and spelling"
Result: "My email has bad grammar and spelling"
```

---

## 🎨 Visual Feedback

### Menu Bar Icon Changes

- **🎙️** - Ready / Idle
- **🔴 REC** - Recording (loud audio)
- **🟡 REC** - Recording (medium audio)
- **🟢 REC** - Recording (quiet audio)
- **⚪ REC** - Recording (silence)
- **🎙️ (Recording)** - In recording mode
- **🎙️ (Transcribing)** - Processing audio
- **🎙️ (Loading...)** - Starting up

### Status Messages

Check the menu bar → Status to see:
- What the app is doing
- Last transcribed text (truncated to 30 chars)
- Error messages if something fails

---

## ⚙️ Configuration

### Environment Variables (`.env` file)

```bash
# Required
OPENAI_API_KEY=sk-proj-your_key_here

# Models (current configuration)
OPENAI_MODEL=gpt-5-nano              # Text enhancement
OPENAI_WHISPER_MODEL=gpt-4o-mini-transcribe  # Speech-to-text
USE_OPENAI_WHISPER=true              # Use cloud (true) or local (false)

# Optional
OPENAI_TTS_MODEL=gpt-4o-mini-tts     # TTS model (cheaper than tts-1)
OPENAI_TTS_VOICE=alloy               # Voice for TTS (alloy, echo, fable, onyx, nova, shimmer)
LOG_LEVEL=INFO                       # DEBUG for troubleshooting
OPENAI_DISABLE_SSL_VERIFY=true       # Temporary SSL workaround
```

### Switching Between Cloud & Local Whisper

**Cloud (OpenAI API)** - Faster, costs $0.003/min:
```bash
USE_OPENAI_WHISPER=true
```

**Local (Free)** - Slower, but free:
```bash
USE_OPENAI_WHISPER=false
```

---

## 💰 Costs

### Transcription (Speech-to-Text)
- **Cloud (OpenAI)**: $0.003/min ($3 per 1,000 min)
- **Local**: FREE (uses local Whisper model)

### Text Enhancement
- **GPT-5 Nano**: $0.05/1M input tokens, $0.40/1M output tokens
- Typical enhancement: ~$0.0001 per request (very cheap!)

### Example Monthly Cost
If you use:
- 1 hour/day of transcription (cloud): ~$5.40/month
- 100 text enhancements/day: ~$0.30/month
- **Total**: ~$6/month

---

## 🔧 Troubleshooting

### "No audio recorded"
- Check microphone permissions
- Select correct microphone from menu bar
- Speak louder or closer to mic

### "Model not loaded"
- Wait 10-30 seconds on first launch
- Local Whisper model takes time to load
- Icon changes from "🎙️ (Loading...)" to "🎙️"

### "Connection error" / "API error"
- Check your `.env` file has valid `OPENAI_API_KEY`
- Verify internet connection
- Check OpenAI API status

### Text enhancement not working
- Make sure text is actually selected (highlighted)
- Check `OPENAI_API_KEY` is set
- Look at logs: `LOG_LEVEL=DEBUG` in `.env`

### Background process won't die
```bash
# Force kill all Python processes (careful!)
pkill -9 -f "src/main.py"
```

---

## 🚀 Pro Tips

1. **Use Right Shift for speed**: Hold → speak → release. No second press needed!

2. **Test microphone first**: Click menu bar → Microphone → try different ones

3. **Check audio levels**: Watch the colored dots (🔴🟡🟢) to know it's recording

4. **Select carefully**: For text enhancement, select ONLY the text you want modified

5. **Be specific**: Voice instructions work better when clear
   - Good: "Make this sound friendlier"
   - Bad: "Change it"

6. **Monitor costs**: Set `LOG_LEVEL=DEBUG` to see API calls in terminal

7. **Local first**: Use `USE_OPENAI_WHISPER=false` for free transcription, only upgrade if you need speed

---

## 📱 macOS Permissions

### Required Permissions

1. **Microphone Access**
   - System Preferences → Security & Privacy → Privacy → Microphone
   - Add Terminal (or the app)

2. **Accessibility Access**
   - System Preferences → Security & Privacy → Privacy → Accessibility
   - Add Terminal (or the app)
   - Needed for keyboard simulation (paste text)

### How to Grant

1. Run the app: `python src/main.py`
2. macOS will prompt for permissions
3. Click "Open System Preferences"
4. Enable checkboxes for Terminal
5. Restart the app

---

## 🐛 Debug Mode

```bash
# Enable detailed logging
echo "LOG_LEVEL=DEBUG" >> .env

# Run and watch logs
python src/main.py

# You'll see:
# - API calls
# - Transcription results
# - Selected text
# - Model responses
# - Errors with full stack traces
```

---

## 📝 Notes

- **Only works on macOS** (uses AppKit, rumps)
- **Globe/Fn key** = vk=63 in keyboard codes
- **Audio files** are temporary and auto-deleted after transcription
- **Clipboard** is temporarily used for text selection but restored immediately
- **Thread-safe** - can handle rapid key presses without issues

---

**Need help?** Check the logs, enable DEBUG mode, or review error messages in the menu bar status.
