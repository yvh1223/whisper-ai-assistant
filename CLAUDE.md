# CLAUDE.md

Technical documentation for Claude Code when working with this repository.

## Project Overview

**Whisper Dictation** - macOS menu bar app for voice-to-text transcription using OpenAI's Whisper model (local or cloud).

### Features

1. **Voice Dictation** - Press Globe/Fn key → record → transcribe → paste at cursor
2. **AI Text Enhancement** - Select text + voice instruction → AI modifies text using GPT
3. **Text-to-Speech (TTS)** - Select text → "read this" OR menu click → natural voice playback
4. **Task Management** - Voice-controlled task tracking with priorities, due dates, categories

### Multi-language Support

Speak in any language → get English text automatically:
- Uses `gpt-4o-mini-transcribe` ($0.003/min) for transcription
- Auto-detects non-English and translates using GPT
- Cost-optimized: cheaper than `whisper-1` ($0.006/min)

## Architecture

### Core Components

**`src/main.py`** - Main application entry point
- `WhisperDictationApp`: rumps-based menu bar app
- Global key listeners: Globe/Fn (vk=63) and Right Shift keys
- Threading: separate threads for model loading, keyboard monitoring, recording, transcription
- Audio playback: multi-fallback player system (afplay → mpg123 → ffplay)
- TTS controls: "Stop Reading" button, dynamic timeout based on text length

**`src/openai_client.py`** - OpenAI API integration
- `transcribe_audio()`: Whisper transcription with auto-translation to English
- `is_english()`: detects non-Latin scripts (Hindi, Arabic, Chinese, Japanese, Korean)
- `translate_to_english()`: GPT-based translation
- `enhance_text()`: voice instruction + selected text → GPT enhancement
- `text_to_speech()`: OpenAI TTS API → MP3 generation
- `parse_task_command()`: natural language task parsing via GPT
- SSL: Uses system certificates (`ssl.get_default_verify_paths().cafile`) for Zscaler compatibility
- Configuration: `.env` (API key, models, SSL settings)

**`src/text_selection.py`** - Clipboard-based text selection
- `get_selected_text()`: Cmd+C → clipboard → read → restore (uses unique marker for reliability)
- `get_selected_text_native()`: NSPasteboard fallback method
- `replace_selected_text()`: types replacement text to overwrite selection
- Improved timing: 0.15s pre-copy delay, 0.3s post-copy delay

**`src/task_manager.py`** - Task management system
- JSON-based storage (`~/.whisper_tasks.json`)
- Natural language parsing via GPT
- Fallback regex parser for offline use
- Priority levels: high, medium, low
- Due date parsing: "tomorrow", "next monday", "december 25"
- Category/tag support

**`src/recording_indicator.py`** - Visual feedback
- RMS-based audio level indicator: 🔴 (loud) → 🟡 (medium) → 🟢 (quiet) → ⚪ (silence)

**`src/logger_config.py`** - Logging configuration
- Colored logs with LOG_LEVEL support
- NO_COLOR environment variable support

### Key Workflow

1. **Recording Start**: Globe/Fn pressed → `start_recording()` → spawns recording thread → fills audio buffer
2. **Recording Stop**: Globe/Fn released → `stop_recording()` → captures selected text → spawns `process_recording()` thread
3. **Transcription**: Save frames to temp WAV → Whisper transcribes (local: `task="translate"`, cloud: API) → auto-translate if non-English
4. **Decision Tree**:
   - **Task command detected** ("task add..."): `task_manager.parse_command()` → save to JSON → voice feedback
   - **TTS request + selected text** ("read this"): `text_to_speech()` → generate MP3 → play audio (with stop button)
   - **Selected text + OpenAI available**: `enhance_text()` → replace selection
   - **No selection**: `insert_text()` → paste at cursor

### TTS Implementation Details

**Keywords**: "read", "speak", "say" trigger TTS mode

**Size Limits**:
- TTS: 4000 chars (truncated if exceeded)
- AI Enhancement: 1000 chars (falls back to dictation if exceeded)

**Audio Playback**:
- Multi-fallback: afplay → mpg123 → ffplay
- Dynamic timeout: `(char_count / 10.0) * 1.5` seconds (min 30s, max 300s)
- Process management: uses `Popen()` with thread-safe locking for stop control
- Stop button: shows during playback, terminates audio process

**Text Selection**:
- Uses unique marker (`___WHISPER_DICTATION_MARKER___`) to detect successful clipboard copy
- Fallback to native NSPasteboard method if regular method fails
- 0.2s delay after menu click to allow focus return

### Recording Triggers

- **Globe/Fn key (vk=63)**: Toggle recording (press to start, press again to stop)
- **Right Shift**: Hold to record, release >0.75s to process, <0.75s to discard

## Development

### Python Version Requirement

**Python 3.12 ONLY** - Do NOT use 3.13 or 3.14 (SSL certificate issues with corporate proxies like Zscaler)

### Setup

```bash
# Create venv with Python 3.12
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies
brew install portaudio  # Required for PyAudio
brew install mpg123     # Backup audio player for TTS (recommended)

# Configure OpenAI API (optional)
cp .env.example .env
# Edit .env with API key from https://platform.openai.com/api-keys
```

### SSL Certificates

Uses **system SSL certificates** instead of certifi for Zscaler proxy compatibility:
- Default: SSL verification enabled via `ssl.get_default_verify_paths().cafile`
- Testing only: Set `OPENAI_DISABLE_SSL_VERIFY=true` in `.env` (not recommended)

### Running

```bash
# Development mode
python src/main.py

# Background mode
./run.sh
# or
nohup ./run.sh >/dev/null 2>&1 & disown
```

### Testing

- Verify all imports work (macOS-specific: rumps, AppKit, pynput)
- Requires macOS with Microphone + Accessibility permissions
- Test audio players: `which afplay mpg123 ffplay`

### Debugging

```bash
# Kill background processes
ps aux | grep 'src/main.py'
kill -9 <PID>

# Enable debug logging
# Add to .env:
LOG_LEVEL=DEBUG
```

## Dependencies

**Core**:
- **Audio**: pyaudio, faster-whisper (local Whisper), openai (cloud)
- **UI**: rumps (menu bar), pyobjc (macOS APIs)
- **Input**: pynput (keyboard monitoring)
- **Cloud**: openai (GPT, Whisper API, TTS), python-dotenv
- **Clipboard**: pyperclip, AppKit.NSPasteboard

**System**:
- portaudio (brew)
- mpg123 (brew, optional but recommended for TTS)

## Environment Variables

```bash
# Required for AI features
OPENAI_API_KEY=sk-...

# Model configuration
OPENAI_MODEL=gpt-5-nano              # Text enhancement, translation
OPENAI_TASK_MODEL=gpt-5-mini         # Task parsing
OPENAI_WHISPER_MODEL=gpt-4o-mini-transcribe  # $0.003/min
OPENAI_TTS_MODEL=gpt-4o-mini-tts     # $12/1M chars
OPENAI_TTS_VOICE=alloy               # alloy/echo/fable/onyx/nova/shimmer

# Transcription
USE_OPENAI_WHISPER=false             # true = cloud, false = local

# SSL (Zscaler compatibility)
OPENAI_DISABLE_SSL_VERIFY=false      # true = disable (testing only)

# Logging
LOG_LEVEL=INFO                       # DEBUG/INFO/WARNING/ERROR
NO_COLOR=false                       # true = disable colored logs
```

## macOS Permissions

Grant in **System Preferences → Security & Privacy → Privacy**:
- **Microphone** - for audio recording
- **Accessibility** - for keyboard shortcuts and text pasting

## Known Limitations

- **macOS only** - uses AppKit, pynput macOS features
- **Model load time** - local Whisper medium.en takes several seconds on startup
- **Clipboard reliability** - may be unreliable in some apps (uses fallback methods)
- **Globe/Fn key** - requires Accessibility permissions
- **Audio file size** - OpenAI Whisper API: 25 MB limit
- **TTS character limit** - OpenAI TTS API: ~4096 chars

## File Organization

```
whisper-dictation/
├── src/                    # Source code
│   ├── main.py            # Main app entry point
│   ├── openai_client.py   # OpenAI API integration
│   ├── text_selection.py  # Clipboard handling
│   ├── task_manager.py    # Task management
│   ├── recording_indicator.py  # Visual feedback
│   └── logger_config.py   # Logging setup
├── test/                   # Unit tests
├── archive/               # Archived files (gitignored)
├── .env                   # API keys (gitignored)
├── .env.example           # Template
├── requirements.txt       # Python dependencies
├── run.sh                 # Run script
├── CLAUDE.md             # This file
└── README.md             # User-facing docs
```

## Development Tips

1. **SSL issues?** Check that you're using system certs, not certifi
2. **TTS not playing?** Install mpg123 (`brew install mpg123`)
3. **Selection not working?** Enable DEBUG logging to see clipboard operations
4. **Task parsing failing?** Check OpenAI API key and model settings
5. **Audio timeout?** Dynamic timeout should handle long text, check logs for timeout value

## Cost Optimization

- **Whisper**: Use `gpt-4o-mini-transcribe` ($0.003/min) instead of `whisper-1` ($0.006/min)
- **TTS**: Use `gpt-4o-mini-tts` ($12/1M chars) instead of `tts-1` ($15/1M)
- **Translation**: Only translates if non-English detected (saves API calls)
- **Local Whisper**: Set `USE_OPENAI_WHISPER=false` for $0 transcription (slower)
