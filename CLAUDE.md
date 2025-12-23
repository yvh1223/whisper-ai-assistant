# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisper Dictation is a macOS-only menu bar application for voice-to-text transcription using OpenAI's Whisper model (locally or via API). It supports four modes:
1. **Standard dictation**: Press Globe/Fn key to record → release to transcribe → paste at cursor
2. **AI-enhanced text editing**: Select text → press Globe/Fn → speak instruction → AI modifies selected text using OpenAI GPT models
3. **Text-to-Speech (TTS)**: Select text → say "read this" OR click menu bar option → text is read aloud with natural voice
4. **Task Management**: Add/manage tasks via voice or typing from menu bar

**Multi-language Support**: Speak in any language → get English text automatically. Uses `gpt-4o-mini-transcribe` to transcribe, then auto-detects non-English and translates using GPT. Cost-optimized: English-only costs $0.003/min, other languages cost $0.003/min + small GPT translation fee (still cheaper than whisper-1's $0.006/min).

**Task Management**:
- Add tasks by **typing** (menu → Tasks → Add Task (type)) - just type "buy milk tomorrow"
- Add tasks by **voice** (menu → Tasks → Add Task (voice)) - say "task add buy milk tomorrow"
- View/complete tasks from menu bar
- Natural language parsing: "high priority", "tomorrow", "by friday", etc.

## Architecture

### Core Components

- **`src/main.py`**: Main application entry point
  - `WhisperDictationApp`: rumps-based menu bar app managing lifecycle, UI, recording, and transcription
  - Global key listeners for Globe/Fn key (vk=63) and Right Shift key
  - Right Shift has optimistic recording: starts immediately, discards if released <0.75s, processes if held longer
  - Threading model: separate threads for model loading, keyboard monitoring, recording, and transcription

- **`src/openai_client.py`**: OpenAI API integration for STT, text enhancement, and TTS
  - `OpenAIClient.transcribe_audio()`: transcribes audio using OpenAI Whisper API → auto-detects language → transcribes with gpt-4o-mini-transcribe → auto-translates to English if needed using GPT
  - `OpenAIClient.is_english()`: detects non-Latin scripts (Hindi/Devanagari, Arabic, Chinese, Japanese, Korean)
  - `OpenAIClient.translate_to_english()`: translates non-English text to English using GPT
  - `OpenAIClient.enhance_text()`: sends voice instruction + selected text to GPT for enhancement
  - `OpenAIClient.text_to_speech()`: converts text to speech using OpenAI TTS API, plays with afplay
  - Uses openai Python library
  - Configurable via `.env` (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_WHISPER_MODEL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE, USE_OPENAI_WHISPER, etc.)

- **`src/text_selection.py`**: Clipboard-based text selection handling
  - `get_selected_text()`: Cmd+C to clipboard → read → restore original clipboard
  - `replace_selected_text()`: Types replacement text (overwrites selection)

- **`src/recording_indicator.py`**: Visual feedback via menu bar icon
  - Updates icon based on audio RMS levels: 🔴 (loud) → 🟡 (medium) → 🟢 (quiet) → ⚪ (silence)

- **`src/logger_config.py`**: Colored logging setup with LOG_LEVEL support

### Key Workflow

1. Globe/Fn key pressed → `start_recording()` → spawns `record_audio()` thread → fills `self.frames` buffer
2. Globe/Fn key released → `stop_recording()` → captures selected text → spawns `process_recording()` thread
3. `transcribe_audio()`: saves frames to temp WAV → Whisper auto-detects language & transcribes (local model uses task="translate" for English, OpenAI API uses transcriptions endpoint) → if non-English detected, auto-translates to English using GPT
4. **If selected text + voice contains TTS keywords** (read/speak/say): `openai_client.text_to_speech()` → generates MP3 → plays with afplay
5. **If selected text + OpenAI available** (non-TTS): `openai_client.enhance_text()` → replace selection with enhanced text
6. **If no selection**: `insert_text()` → types transcribed text at cursor (always in English)

**TTS Keywords**: "read", "speak", "say" - triggers text-to-speech instead of AI enhancement

**Selection Size Limit**: Maximum 1000 characters to prevent accidental huge selections

### Recording Triggers

- **Globe/Fn key (vk=63)**: Toggle recording on release (must press twice: once to start, once to stop)
- **Right Shift**: Hold to record immediately, release >0.75s to process, <0.75s to discard

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install PortAudio (required for PyAudio)
brew install portaudio

# Optional: Configure OpenAI API for AI enhancement and/or cloud transcription
cp .env.example .env
# Edit .env with OpenAI API key from https://platform.openai.com/api-keys
```

### Running

```bash
# Development mode
python src/main.py

# Background mode
nohup ./run.sh >/dev/null 2>&1 & disown
```

### Testing

**Before making changes**: Verify all imports work. This app uses macOS-specific libraries (rumps, AppKit, pynput) that require macOS + accessibility permissions.

### Debugging

Kill background processes:
```bash
ps aux | grep 'src/main.py'
kill -9 <PID>
```

## macOS Permissions Required

- **Microphone**: System Preferences → Security & Privacy → Privacy → Microphone
- **Accessibility**: System Preferences → Security & Privacy → Privacy → Accessibility

## Dependencies

- **Audio**: pyaudio, faster-whisper (local Whisper model), openai (optional cloud transcription)
- **UI**: rumps (menu bar), pyobjc (macOS APIs)
- **Input**: pynput (keyboard monitoring)
- **Cloud**: openai (GPT text enhancement, Whisper API, TTS), python-dotenv
- **Clipboard**: pyperclip, AppKit.NSPasteboard

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required for AI features)
- `OPENAI_MODEL`: Text enhancement and translation model, default 'gpt-5-nano' (also used for auto-translating non-English to English)
- `OPENAI_WHISPER_MODEL`: Whisper model for transcription, default 'gpt-4o-mini-transcribe' at $0.003/min (auto-translates to English via GPT if non-English detected)
- `OPENAI_TTS_MODEL`: Text-to-speech model, default 'gpt-4o-mini-tts' at $12/1M chars (cheaper than 'tts-1' at $15/1M)
- `OPENAI_TTS_VOICE`: TTS voice, default 'alloy' (options: alloy, echo, fable, onyx, nova, shimmer)
- `USE_OPENAI_WHISPER`: Set to 'true' to use OpenAI Whisper API instead of local model, default 'false'
- `LOG_LEVEL`: Default 'INFO'
- `NO_COLOR`: Set to 'true' to disable colored logs

## Known Limitations

- macOS only (uses AppKit, pynput macOS features)
- Local Whisper model loads on startup (medium.en) - can take several seconds
- Clipboard-based text selection may be unreliable in some apps
- Globe/Fn key detection requires accessibility permissions
- OpenAI Whisper API has a 25 MB file size limit for audio transcription