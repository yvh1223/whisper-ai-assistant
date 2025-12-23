# Quick Start Guide

## ✅ Fixed Issues

1. **Selection size limit** - Max 1000 characters to prevent accidents
2. **Unicode keyboard errors** - Fixed crashes from special characters
3. **Reliable timing** - Back to working speeds

## 🎯 How To Use Correctly

### Simple Dictation (No Selection)
1. Click in any text field (Notes, TextEdit, browser, etc.)
2. Press **Globe/Fn key**
3. Speak your text
4. Release **Globe/Fn key**
5. ✓ Text appears at cursor!

### AI Text Enhancement (With Selection)
1. **IMPORTANT:** Use TextEdit or Notes (NOT Terminal or VS Code terminal pane)
2. Type some text: `hello world`
3. **SELECT ONLY the text you want to change** (drag to highlight)
   - ⚠️ Keep it under 1000 characters
   - ⚠️ Don't select entire files!
4. **Keep the text editor focused** (don't switch windows)
5. Press **Globe/Fn key**
6. Speak your instruction: `make this uppercase`
7. Release **Globe/Fn key**
8. Wait 2-3 seconds
9. ✓ Text transforms: `HELLO WORLD`

## ⚠️ Common Mistakes

**❌ DON'T:**
- Select huge amounts of text (you selected 5846 chars - way too much!)
- Use in Terminal window (causes "no selection" errors)
- Switch windows while recording
- Select text in code editors with special characters

**✅ DO:**
- Use in TextEdit, Notes, or web browsers
- Select small amounts of text (a few sentences max)
- Keep the window focused
- Test with simple text first

## 🧪 Test It Now

### Test 1: Simple Dictation
1. Open Notes app
2. Click in a blank note
3. Press Globe/Fn → Say "This is a test" → Release
4. Should appear instantly

### Test 2: AI Enhancement
1. In Notes, type: `test text here`
2. Select those 3 words (highlight them)
3. Press Globe/Fn → Say "make uppercase" → Release
4. Should become: `TEST TEXT HERE`

## 📊 What You Experienced

**Your log showed:**
```
✓ Selected text captured (5846 chars)
```

This means you accidentally selected 5846 characters (probably the whole start_background.sh file in VS Code). The app tried to:
1. Send 5846 chars to OpenAI
2. Search for that huge text
3. Replace it

**Now fixed:** Maximum 1000 characters, anything more gets ignored.

## 💡 Pro Tips

- **Smaller selections = Faster** (10-50 words is ideal)
- **Clear instructions work best**: "uppercase", "summarize", "translate to spanish"
- **Keep text editor focused** when using AI mode
- **Use Notes or TextEdit** for best results
- **Minimize Terminal** after starting with `./run.sh`
