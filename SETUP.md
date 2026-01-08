# Setup Instructions - Whisper Dictation

## Required Permissions

Whisper Dictation requires **3 permissions** to work properly on macOS.

---

## Step-by-Step Setup

### 1. Open System Settings

Click the **Apple menu** (top-left) → **System Settings**

### 2. Navigate to Privacy & Security

Scroll down in the **left sidebar** → Click **"Privacy & Security"**

### 3. Enable Three Permissions

You need to enable your terminal app (Terminal, iTerm2, VS Code, etc.) in **THREE** different sections:

---

#### A) ✅ ACCESSIBILITY

**Purpose:** Allows keyboard shortcuts (Globe/Fn, Right Shift) and text pasting

1. Click **"Accessibility"** in the right panel
2. Find your terminal app in the list
3. Toggle the switch **ON** (should turn blue)
4. If already ON, toggle it **OFF then ON** to refresh

---

#### B) 🎤 MICROPHONE

**Purpose:** Allows audio recording for voice dictation

1. Go back to Privacy & Security
2. Click **"Microphone"**
3. Find your terminal app
4. Toggle the switch **ON**

---

#### C) ⌨️ INPUT MONITORING ⚠️ **CRITICAL**

**Purpose:** Detects keyboard events (Globe/Fn key, Right Shift)

**This is the most commonly missed permission!**

1. Go back to Privacy & Security
2. Click **"Input Monitoring"**
3. Find your terminal app
4. Toggle the switch **ON**

**Without this permission, keyboard shortcuts will NOT work!**

---

### 4. Restart Your Terminal

**IMPORTANT:** You must fully quit and restart your terminal:

1. Press **Cmd+Q** to quit (don't just close the window)
2. Reopen your terminal
3. Navigate to the project directory
4. Run: `./run.sh`

---

## Verification

When you start the app, you should see:

```
======================================================================
                    PERMISSION STATUS CHECK
======================================================================

1️⃣  ACCESSIBILITY (required for keyboard shortcuts)
   ✓ Granted - Globe/Fn and Right Shift shortcuts will work

2️⃣  MICROPHONE (required for voice recording)
   ✓ Granted - Audio recording will work

3️⃣  INPUT MONITORING (required for keyboard event detection)
   ⚠ Cannot verify automatically - will test during runtime
   If keyboard shortcuts don't work, this permission is likely missing

======================================================================
✓ All detectable permissions granted!
NOTE: If keyboard shortcuts don't work, enable Input Monitoring
======================================================================
```

---

## Troubleshooting

### Keyboard shortcuts not working after 30 seconds?

After 30 seconds, if no keyboard events are detected, you'll see a warning:

```
⚠️  KEYBOARD EVENTS NOT DETECTED!
MOST LIKELY CAUSE: Missing 'Input Monitoring' permission
```

**Solution:**
1. Check **Input Monitoring** is enabled for your terminal
2. Check **Accessibility** is enabled
3. Try toggling Accessibility **OFF then ON**
4. **Quit terminal completely** (Cmd+Q) and restart
5. Run `./run.sh` again

### Still not working?

1. Make sure you're enabling permissions for the **correct app**:
   - If running from Terminal → Enable "Terminal"
   - If running from iTerm2 → Enable "iTerm2"
   - If running from VS Code terminal → Enable "Visual Studio Code"

2. Check macOS version:
   - Older macOS: "System Preferences" instead of "System Settings"
   - Older macOS: May not have "Input Monitoring" (requires macOS Catalina 10.15+)

3. Try running with `sudo` (not recommended for regular use):
   ```bash
   sudo python src/main.py
   ```

---

## Why Can't This Be Automated?

macOS **does not allow** apps to programmatically grant themselves permissions for security reasons. This is a macOS security feature, not a limitation of Whisper Dictation.

The app will:
- ✅ Detect which permissions are missing
- ✅ Show clear instructions on how to enable them
- ✅ Display notifications when permissions are needed
- ❌ Cannot automatically enable permissions for you

---

## Need Help?

If you're still having issues:
1. Check the terminal output for detailed error messages
2. Enable debug logging: Add `LOG_LEVEL=DEBUG` to your `.env` file
3. Report issues at: https://github.com/anthropics/claude-code/issues
