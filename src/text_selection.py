#!/usr/bin/env python3
import pyperclip
import time
from AppKit import NSPasteboard, NSStringPboardType
from pynput.keyboard import Key, Controller
from logger_config import setup_logging

logger = setup_logging()


class TextSelection:
    def __init__(self):
        self.keyboard_controller = Controller()
    
    def get_selected_text(self):
        """
        Get currently selected text using clipboard manipulation.
        Returns the selected text or None if no text is selected.
        """
        try:
            # Save current clipboard content
            original_clipboard = pyperclip.paste()

            # Clear clipboard with a unique marker to detect if copy operation succeeds
            marker = "___WHISPER_DICTATION_MARKER___"
            pyperclip.copy(marker)
            time.sleep(0.15)

            # Copy selected text to clipboard
            with self.keyboard_controller.pressed(Key.cmd):
                self.keyboard_controller.press('c')
                self.keyboard_controller.release('c')

            # Longer delay to ensure copy operation completes
            time.sleep(0.3)

            # Get the copied text
            selected_text = pyperclip.paste()
            logger.debug(f"Clipboard after copy: '{selected_text[:100] if selected_text else 'None'}...'")

            # Restore original clipboard content
            pyperclip.copy(original_clipboard)

            # Return selected text if it changed from the marker (meaning copy succeeded)
            if selected_text and selected_text != marker:
                logger.info(f"✓ Selected text captured ({len(selected_text)} chars)")
                return selected_text.strip()

            logger.debug("No text was selected (clipboard unchanged)")
            return None

        except Exception as e:
            logger.error(f"Error getting selected text: {e}")
            return None
    
    def replace_selected_text(self, new_text, original_text=None):
        """
        Replace currently selected text with new text.
        If original_text is provided, will find and replace it.
        """
        try:
            if original_text:
                # Save current clipboard
                original_clipboard = pyperclip.paste()

                # Use Find & Replace approach (reliable timing)
                # 1. Open Find (Cmd+F)
                with self.keyboard_controller.pressed(Key.cmd):
                    self.keyboard_controller.press('f')
                    self.keyboard_controller.release('f')

                time.sleep(0.3)

                # 2. Type the original text to search for
                self.keyboard_controller.type(original_text)
                time.sleep(0.2)

                # 3. Press Enter to find it
                self.keyboard_controller.press(Key.enter)
                self.keyboard_controller.release(Key.enter)
                time.sleep(0.2)

                # 4. Close Find dialog (Escape)
                self.keyboard_controller.press(Key.esc)
                self.keyboard_controller.release(Key.esc)
                time.sleep(0.2)

                # 5. Now the text should be selected, type replacement
                self.keyboard_controller.type(new_text)

                # Restore original clipboard
                pyperclip.copy(original_clipboard)

                logger.info(f"✓ Replaced: '{original_text[:30]}...' → '{new_text[:30]}...'")
            else:
                # Simple approach - just type (works if text is still selected)
                self.keyboard_controller.type(new_text)
                logger.info(f"✓ Inserted: {new_text[:50]}...")

            return True

        except Exception as e:
            logger.error(f"Error replacing text: {e}")
            # Try to restore clipboard on error
            try:
                if 'original_clipboard' in locals():
                    pyperclip.copy(original_clipboard)
            except:
                pass
            return False
    
    def select_all_and_replace(self, new_text):
        """
        Select all text in current field and replace with new text.
        Fallback method when specific text selection fails.
        """
        try:
            # Select all text
            with self.keyboard_controller.pressed(Key.cmd):
                self.keyboard_controller.press('a')
                self.keyboard_controller.release('a')
            
            time.sleep(0.1)
            
            # Type replacement text
            self.keyboard_controller.type(new_text)
            return True
            
        except Exception as e:
            logger.error(f"Error in select all and replace: {e}")
            return False
    
    def get_selected_text_native(self):
        """
        Alternative method using NSPasteboard directly.
        This is a backup method that might work better in some scenarios.
        """
        try:
            # Get the general pasteboard
            pasteboard = NSPasteboard.generalPasteboard()
            
            # Save current pasteboard content
            original_content = pasteboard.stringForType_(NSStringPboardType)
            
            # Clear pasteboard
            pasteboard.clearContents()
            
            # Copy selected text
            with self.keyboard_controller.pressed(Key.cmd):
                self.keyboard_controller.press('c')
                self.keyboard_controller.release('c')
            
            time.sleep(0.2)
            
            # Get copied text
            selected_text = pasteboard.stringForType_(NSStringPboardType)
            
            # Restore original content
            if original_content:
                pasteboard.clearContents()
                pasteboard.setString_forType_(original_content, NSStringPboardType)
            
            return selected_text.strip() if selected_text else None
            
        except Exception as e:
            logger.error(f"Error with native text selection: {e}")
            return None