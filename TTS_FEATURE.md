# Text-to-Speech (TTS) Feature

## ✅ What I Added

### 1. Menu Bar Option
- **"Read Selected Text Aloud"** option in menu bar
- Click 🎙️ icon → Select this option
- Reads any selected text using OpenAI TTS

### 2. Voice-Activated TTS
- Say **"read this"**, **"read aloud"**, or **"speak"** when text is selected
- App automatically detects TTS keywords and reads text instead of enhancing it

### 3. Visual Feedback
- Icon changes to 🔊 while reading
- Status shows "Reading text aloud..."
- Returns to 🎙️ when done

## 🎯 How To Use

### Method 1: Menu Bar (Easiest)
1. **Select text** in Notes, TextEdit, or browser
2. **Click 🎙️** icon in menu bar
3. **Click "Read Selected Text Aloud"**
4. ✓ Text is read aloud!

### Method 2: Voice Command
1. **Select text** in any app
2. **Press Globe/Fn key**
3. **Say**: "read this" or "read aloud"
4. **Release Globe/Fn key**
5. ✓ Text is read aloud automatically!

## ⚙️ Configuration

Uses your `.env` settings:
- `OPENAI_TTS_MODEL=gpt-4o-mini-tts` (default, cheaper option - or use `tts-1`, `tts-1-hd` for higher quality)
- `OPENAI_TTS_VOICE=alloy` (options: alloy, echo, fable, onyx, nova, shimmer)

**Available Voices:**
- **alloy**: Neutral, balanced
- **echo**: Masculine, clear
- **fable**: British, expressive
- **onyx**: Deep, authoritative
- **nova**: Feminine, energetic
- **shimmer**: Soft, warm

## 🧪 Test It Now

**Quick test:**
1. Open Notes app
2. Type: "Hello, this is a test of the text to speech feature"
3. Select that sentence (highlight it)
4. Click 🎙️ → "Read Selected Text Aloud"
5. Listen!

**Or with voice:**
1. Select the same text
2. Press Globe/Fn
3. Say: "read this"
4. Release Globe/Fn
5. Listen!

## 📊 How It Works

1. **Selection captured** (max 1000 chars)
2. **Voice transcribed** → checks for TTS keywords
3. **If keywords found** ("read", "speak", "say"):
   - Sends text to OpenAI TTS API
   - Generates MP3 audio file
   - Plays with macOS `afplay` command
   - Cleans up temp file
4. **If no TTS keywords** → normal AI enhancement

## 🎛️ Voice Selection

To change the voice, edit `.env`:
```bash
OPENAI_TTS_VOICE=nova  # Try different voices!
```

Restart the app to apply changes.

## 💡 Pro Tips

- **Best for short text**: Under 1000 characters (automatic limit)
- **Works offline**: No! Requires OpenAI API (uses their TTS service)
- **Natural sounding**: Uses OpenAI's advanced TTS models
- **Fast**: Typical response 1-2 seconds
- **Clear**: Use TextEdit or Notes for best experience

## 🔍 Troubleshooting

**No sound?**
- Check system volume
- Ensure OPENAI_API_KEY is set in `.env`
- Check logs for errors

**Wrong voice?**
- Edit OPENAI_TTS_VOICE in `.env`
- Restart app

**Text not reading?**
- Ensure text is selected before clicking menu
- Try with a small amount of text first
- Check that you have OpenAI API credits

## 📝 Related Features

The app now has 3 modes:

1. **Dictation** (no selection): Speaks → types text
2. **AI Enhancement** (selection + instruction): "make uppercase" → TRANSFORMS TEXT
3. **TTS** (selection + read command): "read this" → 🔊 READS ALOUD

All work seamlessly with the same Globe/Fn key!
