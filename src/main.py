#!/usr/bin/env python3
import os
import time
import tempfile
import threading
import subprocess
import pyaudio
import wave
import numpy as np
import rumps
from pynput import keyboard
from pynput.keyboard import Key, Controller
import faster_whisper
import signal
import warnings
from AppKit import NSAlert, NSAlertFirstButtonReturn, NSAlertSecondButtonReturn
from text_selection import TextSelection
from openai_client import OpenAIClient
from task_manager import TaskManager
from recording_indicator import RecordingIndicator
from logger_config import setup_logging
from mlx_whisper_client import MLXWhisperClient
from tts_speed_controller import TTSSpeedController

# Suppress multiprocessing resource tracker warnings on shutdown
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

logger = setup_logging()

# Set up a global flag for handling SIGINT
exit_flag = False
exit_event = threading.Event()

def signal_handler(sig, frame):
    """Global signal handler for graceful shutdown"""
    global exit_flag
    logger.info("\n--- Shutdown signal received (Ctrl+C) ---")
    exit_flag = True
    exit_event.set()
    # Force exit immediately - don't wait for cleanup
    logger.info("Exiting...")
    os._exit(0)

# Set up graceful shutdown handling for interrupt and termination signals
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class WhisperDictationApp(rumps.App):
    def __init__(self):
        super(WhisperDictationApp, self).__init__("🎙️", quit_button=rumps.MenuItem("Quit"))
        
        # Status item
        self.status_item = rumps.MenuItem("Status: Ready")
        
        # Add menu items - use a single menu item for toggling recording
        self.recording_menu_item = rumps.MenuItem("Start Recording")

        # Recording state
        self.recording = False
        self.recording_start_time = None  # Track when recording started
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.keyboard_controller = Controller()
        self.cached_selected_text = None  # Cache selected text when recording stops

        # App lifecycle tracking
        self.last_activity_time = time.time()
        self.max_inactivity_time = 4 * 60 * 60  # 4 hours of inactivity
        self.max_recording_duration = 15 * 60  # 15 minutes in seconds

        # Microphone selection (None = use default)
        self.selected_input_device = None

        # Create microphone selection submenu
        self.mic_menu = {}
        self.mic_menu_mapping = {}  # Maps menu title to device index
        self.setup_microphone_menu()

        # Add TTS menu items
        self.tts_menu_item = rumps.MenuItem("Read Selected Text Aloud")
        self.stop_tts_menu_item = rumps.MenuItem("Stop Reading")
        self.stop_tts_menu_item.set_callback(self.stop_tts)

        # Track current audio playback process
        self.current_audio_process = None
        self.audio_process_lock = threading.Lock()

        # Initialize text selection handler
        self.text_selector = TextSelection()

        # Initialize OpenAI client
        self.openai_client = OpenAIClient()

        # Initialize TaskManager
        self.task_manager = TaskManager(openai_client=self.openai_client)

        # Task submenu will be created in setup_task_menu() (must be after task_manager init)
        self.setup_task_menu()

        # Initially hide the stop button
        self.stop_tts_menu_item.title = None  # Hidden

        self.menu = [
            self.recording_menu_item,
            self.tts_menu_item,
            self.stop_tts_menu_item,
            self.task_submenu,
            None,
            self.status_item
        ]

        # Initialize recording indicator
        self.indicator = RecordingIndicator()
        self.indicator.set_app_reference(self)

        # Initialize transcription backend (MLX, faster-whisper, or OpenAI)
        self.model = None
        self.mlx_client = None
        self.use_mlx_whisper = os.getenv('USE_MLX_WHISPER', 'false').lower() == 'true'

        if self.use_mlx_whisper:
            # Load MLX Whisper model
            self.load_mlx_thread = threading.Thread(target=self.load_mlx_model)
            self.load_mlx_thread.start()
        elif not self.openai_client.use_openai_whisper:
            # Load local faster-whisper model
            self.load_model_thread = threading.Thread(target=self.load_model)
            self.load_model_thread.start()
        else:
            # Using cloud API - model not needed
            self.title = "🎙️"
            self.status_item.title = "Status: Ready (Cloud API)"
            logger.info("Using OpenAI Whisper API - skipping local model load")
        
        # Audio recording parameters
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
        # Hotkey configuration - we'll listen for globe/fn key (vk=63)
        self.trigger_key = 63  # Key code for globe/fn key

        # Right Shift trigger state for TTS on/off toggle
        self.shift_press_time = None
        self.shift_held = False

        # TTS speed controller - read speed from environment or use default
        tts_speed = float(os.getenv('TTS_SPEED', '1.0'))
        self.tts_controller = TTSSpeedController(tts_speed=tts_speed)

        self.setup_global_monitor()
        
        # Show initial message
        logger.info("Started WhisperDictation app. Look for 🎙️ in your menu bar.")
        logger.info("Press and hold the Globe/Fn key (vk=63) to record. Release to transcribe.")
        logger.info("Right Shift: Select text → Press once to play → Press again to stop")
        logger.info("  - Speed preset at startup (use --tts-speed flag: 1, 1.25, 1.5, 2)")
        logger.info("Multi-language support: Speak in any language (Hindi, English, etc.) → Output in English")
        logger.info("Press Ctrl+C to quit the application.")
        logger.info("You may need to grant this app accessibility permissions in System Preferences.")
        logger.info("Go to System Preferences → Security & Privacy → Privacy → Accessibility")
        logger.info("and add your terminal or the built app to the list.")
        
        # Test OpenAI connection
        if self.openai_client.is_available():
            logger.info("✓ OpenAI client initialized successfully")
            model_info = self.openai_client.get_model_info()
            if model_info['use_openai_whisper']:
                logger.info("  → Using OpenAI Whisper API for transcription")
            else:
                logger.info("  → Using local Whisper model for transcription")
        else:
            logger.warning("⚠ OpenAI client not available - text enhancement features disabled")
        
        # Start a watchdog thread to check for exit flag
        self.watchdog = threading.Thread(target=self.check_exit_flag, daemon=True)
        self.watchdog.start()
    
    def check_exit_flag(self):
        """Monitor the exit flag, app runtime, and recording duration"""
        while True:
            # Check for exit flag
            if exit_flag:
                logger.info("Watchdog detected exit flag, shutting down...")
                self.cleanup()
                rumps.quit_application()
                os._exit(0)
                break

            # Check if app has been inactive too long (4 hours)
            inactive_time = time.time() - self.last_activity_time
            if inactive_time > self.max_inactivity_time:
                logger.warning(f"⚠️  No activity for {inactive_time/3600:.1f} hours - auto-shutting down for safety")
                rumps.notification(
                    title="Whisper Dictation Auto-Shutdown",
                    subtitle="Inactive for 4+ hours",
                    message="Automatically shutting down due to inactivity. Restart when needed."
                )
                time.sleep(2)  # Give notification time to show
                self.cleanup()
                rumps.quit_application()
                os._exit(0)
                break

            # Check if recording has been running too long (15 minutes)
            if self.recording and self.recording_start_time:
                recording_duration = time.time() - self.recording_start_time
                if recording_duration > self.max_recording_duration:
                    logger.warning(f"⚠️  Recording has been running for {recording_duration/60:.1f} minutes - auto-stopping")
                    rumps.notification(
                        title="Recording Auto-Stopped",
                        subtitle="Recording exceeded 15 minutes",
                        message="Recording automatically stopped for safety. Please start a new recording if needed."
                    )
                    # Stop recording
                    self.stop_recording()

            time.sleep(0.5)
    
    def cleanup(self):
        """Clean up resources before exiting"""
        logger.info("Cleaning up resources...")
        try:
            # Stop recording if in progress
            if self.recording:
                self.recording = False
                if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
                    try:
                        self.recording_thread.join(timeout=1.0)
                    except:
                        pass

            # Stop any playing audio
            if hasattr(self, 'current_audio_process') and self.current_audio_process:
                try:
                    if self.current_audio_process.poll() is None:
                        self.current_audio_process.terminate()
                        self.current_audio_process.wait(timeout=1.0)
                except:
                    pass

            # Close recording indicator if active
            if hasattr(self, 'recording_indicator'):
                try:
                    if hasattr(self.recording_indicator, 'stop'):
                        self.recording_indicator.stop()
                except:
                    pass

            # Close PyAudio properly
            if hasattr(self, 'audio'):
                try:
                    self.audio.terminate()
                except:
                    pass

            logger.info("Resources cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def load_mlx_model(self):
        """Load MLX Whisper model (optimized for Apple Silicon)"""
        self.title = "🎙️ (Loading MLX...)"
        self.status_item.title = "Status: Loading MLX Whisper model..."
        try:
            model_size = os.getenv('MLX_WHISPER_MODEL', 'large-v3')
            self.mlx_client = MLXWhisperClient(model_size=model_size)
            self.title = "🎙️"
            self.status_item.title = "Status: Ready (MLX Local)"
            logger.info(f"MLX Whisper model ({model_size}) loaded successfully!")
        except Exception as e:
            self.title = "🎙️ (Error)"
            self.status_item.title = "Status: Error loading MLX model"
            logger.error(f"Error loading MLX Whisper model: {e}")
            # Fall back to faster-whisper
            logger.info("Falling back to faster-whisper...")
            self.load_model()

    def load_model(self):
        self.title = "🎙️ (Loading...)"
        self.status_item.title = "Status: Loading Whisper model..."
        try:
            self.model = faster_whisper.WhisperModel("medium.en", compute_type="float32")
            self.title = "🎙️"
            self.status_item.title = "Status: Ready"
            logger.info("Whisper model loaded successfully!")
        except Exception as e:
            self.title = "🎙️ (Error)"
            self.status_item.title = "Status: Error loading model"
            logger.error(f"Error loading model: {e}")

    def setup_microphone_menu(self):
        """Setup the microphone selection submenu"""
        self.mic_submenu = rumps.MenuItem("Microphone")
        devices = self.get_input_devices()

        for device in devices:
            title = device['name']
            if device['is_default']:
                title += " (Default)"

            menu_item = rumps.MenuItem(title, callback=self.select_microphone)
            # Mark the default device as selected initially
            if device['is_default']:
                menu_item.state = True

            self.mic_menu[title] = menu_item
            self.mic_menu_mapping[title] = device['index']
            self.mic_submenu.add(menu_item)

    def setup_global_monitor(self):
        # Create a separate thread to monitor for global key events
        self.key_monitor_thread = threading.Thread(target=self.monitor_keys)
        self.key_monitor_thread.daemon = True
        self.key_monitor_thread.start()

    def get_input_devices(self):
        """Get list of available audio input devices"""
        devices = []
        default_index = self.audio.get_default_input_device_info()['index']
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': info['index'],
                    'name': info['name'],
                    'is_default': info['index'] == default_index
                })
        return devices

    def select_microphone(self, sender):
        """Callback when a microphone is selected from the menu"""
        # Uncheck all items in the microphone menu
        for item in self.mic_menu.values():
            item.state = False
        # Check the selected item
        sender.state = True
        # Store the device index (stored in the menu item's title parsing or we use a mapping)
        device_index = self.mic_menu_mapping.get(sender.title)
        self.selected_input_device = device_index
        device_name = sender.title.replace(" (Default)", "")
        logger.info(f"Microphone changed to: {device_name}")

    def discard_recording(self):
        """Discard current recording without processing (held too short)"""
        self.recording = False
        self.recording_start_time = None  # Clear recording start time
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=0.5)
        self.frames = []
        self.indicator.stop()
        self.title = "🎙️"
        self.status_item.title = "Status: Recording discarded (too short)"
        logger.info("Recording discarded - held for less than threshold")

    def handle_shift_tts(self):
        """
        Handle Right Shift for text-to-speech:
        1. If text is selected and not currently playing → get selected text and play TTS
        2. If already playing → increase speed by 0.25x
        """
        logger.debug(f"[TTS-START] handle_shift_tts called - is_playing={self.tts_controller.is_playing}")

        # Check if already playing - if so, increase speed
        if self.tts_controller.is_playing:
            logger.info("[TTS-SPEED] Right Shift pressed while reading - increasing speed")
            logger.debug("[TTS-SPEED] Calling increase_speed()")
            speed_result = self.tts_controller.increase_speed()
            logger.debug(f"[TTS-SPEED] increase_speed result: {speed_result}")
            if speed_result:
                status = self.tts_controller.get_status()
                logger.info(f"✓ TTS speed increased to {status['current_speed']}x")
            else:
                logger.debug("[TTS-SPEED] Speed control disabled for now")
            return

        # Try to get selected text
        logger.debug("[TTS-SELECT] Attempting to get selected text...")
        text_selection = TextSelection()
        selected_text = text_selection.get_selected_text()

        logger.debug(f"[TTS-SELECT] Got text: {repr(selected_text[:30] if selected_text else 'None')}...")

        if not selected_text or selected_text.strip() == "":
            logger.info("[TTS-FALLBACK] No text selected - falling back to voice recording")
            # Fall back to recording behavior
            self.shift_press_time = time.time()
            self.shift_held = True
            logger.debug("[TTS-FALLBACK] Starting recording")
            self.start_recording()
            logger.debug("[TTS-FALLBACK] Recording started")
            return

        # We have selected text - generate and play TTS
        text_preview = selected_text[:50] + "..." if len(selected_text) > 50 else selected_text
        logger.info(f"[TTS-GEN] Selected text ({len(selected_text)} chars): {text_preview}")

        try:
            # Generate TTS audio
            logger.debug("[TTS-GEN] Calling openai_client.text_to_speech()...")
            audio_data = self.openai_client.text_to_speech(selected_text)
            logger.debug(f"[TTS-GEN] Got audio data: {len(audio_data)} bytes")

            # Save to temporary file
            logger.debug("[TTS-GEN] Writing audio to temp file...")
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_audio_path = temp_file.name

            logger.debug(f"[TTS-GEN] Temp file written: {temp_audio_path}")

            # Play with TTS controller
            logger.info("[TTS-PLAY] Starting TTS playback...")
            logger.debug("[TTS-PLAY] Calling tts_controller.play_with_speed()")
            playback_result = self.tts_controller.play_with_speed(temp_audio_path, speed=1.0)
            logger.debug(f"[TTS-PLAY] play_with_speed returned: {playback_result}")

            if not playback_result:
                logger.error("[TTS-ERROR] Failed to start TTS playback")
                raise Exception("TTS playback failed to start")

            logger.debug("[TTS-PLAY] Playback started successfully")

        except Exception as e:
            logger.error(f"[TTS-ERROR] Error with TTS: {e}")
            import traceback
            logger.debug(f"[TTS-ERROR] Traceback: {traceback.format_exc()}")
            logger.info("[TTS-FALLBACK] Falling back to voice recording")
            self.shift_press_time = time.time()
            self.shift_held = True
            self.start_recording()

        logger.debug("[TTS-END] handle_shift_tts completed")

    def monitor_keys(self):
        # Track state of key 63 (Globe/Fn key)
        self.is_recording_with_key63 = False

        def on_press(key):
            try:
                # If Right Shift is held and another key is pressed, cancel recording (user is typing)
                if self.shift_held and key != Key.shift_r:
                    logger.info("Other key pressed while Right Shift held - canceling recording")
                    self.shift_held = False
                    self.discard_recording()
                    return

                # Removed logging for every key press; log only when target key is pressed
                if hasattr(key, 'vk') and key.vk == self.trigger_key:
                    logger.debug(f"Target key (vk={key.vk}) pressed")

                # Right Shift handling - toggle TTS on/off
                if key == Key.shift_r:
                    if self.tts_controller.is_playing:
                        logger.info("⏹ Right Shift pressed - stopping TTS playback")
                        self.tts_controller.stop()
                    else:
                        logger.info("▶ Right Shift pressed - checking for selected text")
                        self.handle_shift_tts()
                    logger.debug("Right Shift handling completed")
            except UnicodeDecodeError:
                # Ignore unicode errors from special characters
                pass
            except Exception as e:
                logger.debug(f"Error in on_press: {e}")

        def on_release(key):
            try:
                if hasattr(key, 'vk'):
                    logger.debug(f"Key with vk={key.vk} released")
                    if key.vk == self.trigger_key:
                        if not self.recording and not self.is_recording_with_key63:
                            logger.debug(f"Globe/Fn key (vk={key.vk}) released - STARTING recording")
                            self.is_recording_with_key63 = True
                            self.start_recording()
                        elif self.recording and self.is_recording_with_key63:
                            logger.debug(f"Globe/Fn key (vk={key.vk}) released - STOPPING recording")
                            self.is_recording_with_key63 = False
                            self.stop_recording()

            except UnicodeDecodeError:
                # Ignore unicode errors from special characters
                pass
            except Exception as e:
                logger.debug(f"Error in on_release: {e}")

        try:
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                logger.debug(f"Keyboard listener started - listening for key events")
                logger.debug(f"Target key is Globe/Fn key (vk={self.trigger_key})")
                logger.debug(f"Press and release the target key to control recording")
                listener.join()
        except Exception as e:
            logger.error(f"Error with keyboard listener: {e}")
            logger.error("Please check accessibility permissions in System Preferences")
    
    @rumps.clicked("Start Recording")  # This will be matched by title
    def toggle_recording(self, sender):
        if not self.recording:
            self.start_recording()
            sender.title = "Stop Recording"
        else:
            # Run stop_recording in a background thread to avoid blocking the UI
            stop_thread = threading.Thread(target=self._stop_recording_from_menu, args=(sender,))
            stop_thread.start()

    def _stop_recording_from_menu(self, sender):
        """Helper to stop recording from menu and update title"""
        self.stop_recording()
        sender.title = "Start Recording"

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_time = time.time()

    @rumps.clicked("Read Selected Text Aloud")
    def read_selected_text(self, sender):
        """Read selected text using TTS"""
        self.update_activity()
        # Run in background thread to avoid blocking UI
        tts_thread = threading.Thread(target=self._read_selected_text_worker)
        tts_thread.start()

    def stop_tts(self, sender=None):
        """Stop current TTS playback"""
        with self.audio_process_lock:
            if self.current_audio_process and self.current_audio_process.poll() is None:
                logger.info("Stopping TTS playback...")
                try:
                    self.current_audio_process.terminate()
                    time.sleep(0.1)
                    if self.current_audio_process.poll() is None:
                        self.current_audio_process.kill()
                    logger.info("✓ TTS playback stopped")
                    self.title = "🎙️"
                    self.status_item.title = "Status: Playback stopped"
                except Exception as e:
                    logger.error(f"Error stopping TTS: {e}")
            else:
                logger.debug("No TTS playback to stop")

        # Hide stop button
        self.stop_tts_menu_item.title = None

    def _read_selected_text_worker(self):
        """Worker function to read selected text using TTS"""
        try:
            # Small delay to allow focus to return to the original app after clicking menu
            time.sleep(0.2)

            # Get selected text - try regular method first
            selected_text = self.text_selector.get_selected_text()

            # Fallback to native method if regular method fails
            if not selected_text:
                logger.debug("Regular method failed, trying native NSPasteboard method...")
                selected_text = self.text_selector.get_selected_text_native()

            if not selected_text:
                self.status_item.title = "Status: No text selected"
                logger.warning("No text selected for TTS")
                return

            # Limit to 4000 chars (OpenAI TTS API supports up to ~4096 chars)
            if len(selected_text) > 4000:
                logger.warning(f"Selected text too long ({len(selected_text)} chars) - trimming to 4000")
                selected_text = selected_text[:4000]

            char_count = len(selected_text)
            logger.info(f"Reading aloud ({char_count} chars): {selected_text[:50]}...")
            self.title = "🔊 (Reading...)"
            self.status_item.title = "Status: Reading text aloud..."

            # Use OpenAI TTS
            if self.openai_client.is_available():
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                    audio_file = temp_audio.name

                # Generate speech
                self.openai_client.text_to_speech(selected_text, audio_file)

                # Play the audio file with fallback options (pass char count for better timeout estimation)
                self._play_audio_file(audio_file, char_count=char_count)

                # Clean up
                try:
                    os.unlink(audio_file)
                except Exception as e:
                    logger.warning(f"Could not delete temp audio file: {e}")

                self.title = "🎙️"
                self.status_item.title = "Status: ✓ Finished reading"
                logger.info("✓ Finished reading text aloud")
            else:
                self.title = "🎙️"
                self.status_item.title = "Status: OpenAI not configured"
                logger.warning("OpenAI client not available for TTS")

        except Exception as e:
            logger.error(f"Error reading text aloud: {e}")
            self.title = "🎙️"
            self.status_item.title = f"Status: TTS error - {str(e)[:30]}"

    def _play_audio_file(self, audio_file, char_count=None):
        """
        Play audio file with multiple fallback options.
        Tries: afplay, mpg123, ffplay (in order)

        Args:
            audio_file: Path to MP3 file
            char_count: Number of characters in the text (for timeout estimation)
        """
        logger.info(f"Playing audio: {audio_file}")

        # Verify file exists and has content
        if not os.path.exists(audio_file):
            raise Exception(f"Audio file not found: {audio_file}")

        file_size = os.path.getsize(audio_file)
        if file_size == 0:
            raise Exception("Generated audio file is empty")

        logger.debug(f"Audio file size: {file_size} bytes")

        # Calculate timeout based on character count (more accurate than file size)
        # TTS speaks at ~150-200 words/min ≈ 750-1000 chars/min ≈ 12-17 chars/second
        # Use conservative 10 chars/sec, add 50% buffer, minimum 30s, max 300s (5 min)
        if char_count:
            estimated_duration = (char_count / 10.0) * 1.5
            timeout_seconds = int(max(30, min(300, estimated_duration)))
            logger.info(f"Estimated audio duration: ~{int(char_count/10)}s ({char_count} chars), timeout: {timeout_seconds}s")
        else:
            # Fallback: use file size
            estimated_duration = (file_size / 16000) * 1.5
            timeout_seconds = int(max(30, min(300, estimated_duration)))
            logger.debug(f"Timeout set to {timeout_seconds}s (based on file size)")

        # Try multiple audio players in order of preference
        players = [
            ('afplay', ['afplay', audio_file]),
            ('mpg123', ['mpg123', '-q', audio_file]),
            ('ffplay', ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', audio_file])
        ]

        last_error = None
        for player_name, command in players:
            try:
                # Check if player is available
                check_cmd = ['which', player_name]
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=2)

                if result.returncode != 0:
                    logger.debug(f"{player_name} not available, trying next...")
                    continue

                logger.info(f"Using {player_name} to play audio")

                # Show stop button
                self.stop_tts_menu_item.title = "⏹ Stop Reading"

                # Try to play the audio with dynamic timeout
                with self.audio_process_lock:
                    self.current_audio_process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                # Wait for playback to finish (with timeout)
                try:
                    stdout, stderr = self.current_audio_process.communicate(timeout=timeout_seconds)
                    exit_code = self.current_audio_process.returncode

                    if exit_code != 0:
                        raise subprocess.CalledProcessError(exit_code, command, stdout, stderr)

                    logger.info(f"✓ Audio played successfully with {player_name}")

                    # Hide stop button
                    self.stop_tts_menu_item.title = None
                    return  # Success!

                except subprocess.TimeoutExpired:
                    # Timeout - kill process and try next player
                    with self.audio_process_lock:
                        if self.current_audio_process:
                            self.current_audio_process.kill()
                            self.current_audio_process = None
                    raise

            except subprocess.TimeoutExpired:
                last_error = f"{player_name} timed out"
                logger.warning(f"{player_name} timed out, trying next player...")
                continue
            except subprocess.CalledProcessError as e:
                last_error = f"{player_name} failed: {e.stderr if e.stderr else e}"
                logger.warning(f"{player_name} failed (exit code {e.returncode})")
                if e.stderr:
                    logger.debug(f"  Error output: {e.stderr}")
                continue
            except Exception as e:
                last_error = f"{player_name} error: {e}"
                logger.warning(f"{player_name} error: {e}")
                continue

        # All players failed - hide stop button and raise error
        self.stop_tts_menu_item.title = None
        error_msg = f"All audio players failed. Last error: {last_error}"
        logger.error(error_msg)
        logger.error("Tip: Install mpg123 with: brew install mpg123")
        raise Exception(error_msg)

    def start_recording(self):
        # Check if model is needed and loaded
        if self.use_mlx_whisper:
            if self.mlx_client is None:
                logger.warning("MLX model not loaded. Please wait for the model to finish loading.")
                self.status_item.title = "Status: Waiting for MLX model to load"
                return
        elif not self.openai_client.use_openai_whisper:
            if not hasattr(self, 'model') or self.model is None:
                logger.warning("Model not loaded. Please wait for the model to finish loading.")
                self.status_item.title = "Status: Waiting for model to load"
                return

        self.update_activity()  # Update activity timestamp
        self.frames = []
        self.recording = True
        self.recording_start_time = time.time()  # Track when recording started
        self.cached_selected_text = None  # Clear any previous cached selection

        # Update UI
        self.title = "🎙️ (Recording)"
        self.status_item.title = "Status: Recording..."
        logger.info("Recording started. Speak now...")

        # Show recording indicator
        self.indicator.start()

        # Start recording thread
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()
    
    def stop_recording(self):
        self.update_activity()  # Update activity timestamp
        self.recording = False
        self.recording_start_time = None  # Clear recording start time
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join(timeout=2.0)  # Add timeout to prevent indefinite blocking

        # Hide recording indicator
        self.indicator.stop()

        # Check for selected text NOW (while focus might still be on the text editor)
        self.cached_selected_text = self.text_selector.get_selected_text()

        if self.cached_selected_text:
            logger.info(f"✓ Selected text captured ({len(self.cached_selected_text)} chars): '{self.cached_selected_text[:50]}...'")
            self.title = "🎙️ (AI Enhancing)"
            self.status_item.title = "Status: AI enhancing..."
        else:
            logger.debug("No text selected - will insert transcription normally")
            self.title = "🎙️ (Transcribing)"
            self.status_item.title = "Status: Transcribing..."

        logger.info("Recording stopped. Processing...")

        # Process in background
        transcribe_thread = threading.Thread(target=self.process_recording)
        transcribe_thread.start()
    
    def process_recording(self):
        # Transcribe and insert text
        try:
            self.transcribe_audio()
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            self.status_item.title = "Status: Error during transcription"
        finally:
            self.title = "🎙️"  # Reset title
    
    def record_audio(self):
        stream = None
        try:
            # Build kwargs for audio stream
            stream_kwargs = {
                'format': self.format,
                'channels': self.channels,
                'rate': self.rate,
                'input': True,
                'frames_per_buffer': self.chunk
            }
            # Use selected input device if specified
            if self.selected_input_device is not None:
                stream_kwargs['input_device_index'] = self.selected_input_device

            stream = self.audio.open(**stream_kwargs)

            while self.recording:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)

                    # Update indicator with audio level
                    self.indicator.update_audio_level(data)
                except Exception as e:
                    logger.error(f"Error reading audio chunk: {e}")
                    break

        except Exception as e:
            logger.error(f"Error in record_audio: {e}")
            self.recording = False
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")
    
    def transcribe_audio(self):
        if not self.frames:
            self.title = "🎙️"
            self.status_item.title = "Status: No audio recorded"
            logger.warning("No audio recorded")
            return

        # Save the recorded audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name

        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))

        logger.debug("Audio saved to temporary file. Transcribing...")

        # Transcribe with Whisper (MLX, faster-whisper, or OpenAI API)
        # All modes auto-detect language and translate to English
        try:
            # Check transcription backend priority
            if self.use_mlx_whisper and self.mlx_client:
                logger.debug("Using MLX Whisper (auto-detect → English)...")
                text = self.mlx_client.transcribe_audio(temp_filename)
            elif self.openai_client.is_available() and self.openai_client.use_openai_whisper:
                logger.debug("Using OpenAI Whisper API (auto-detect → English)...")
                text = self.openai_client.transcribe_audio(temp_filename)
            else:
                # Use local faster-whisper model with translation to English
                logger.debug("Using faster-whisper model (auto-detect → English)...")
                try:
                    # task="translate" auto-detects language and translates to English
                    segments, _ = self.model.transcribe(temp_filename, beam_size=5, task="translate")

                    text = ""
                    for segment in segments:
                        text += segment.text
                except Exception as model_error:
                    logger.error(f"Error with Whisper model transcription: {model_error}")
                    raise Exception(f"Whisper model error: {model_error}")
            
            if text:
                text_lower = text.strip().lower()

                # Check for task commands FIRST (before selected text)
                task_keywords = ['task', 'todo', 'to do']
                is_task_command = any(text_lower.startswith(keyword) for keyword in task_keywords)

                if is_task_command:
                    logger.info(f"Task command detected: {text}")
                    self.title = "🎙️ (Processing task...)"
                    self.status_item.title = "Status: Processing task command..."
                    self.process_task_command(text)
                    return  # Don't proceed to normal dictation

                # Use cached selected text (captured when recording stopped)
                selected_text = getattr(self, 'cached_selected_text', None)

                if selected_text and self.openai_client.is_available():
                    logger.info(f"Selected text detected: {selected_text[:50]}...")
                    logger.info(f"Voice instruction: {text}")

                    # Check if this is a TTS request
                    tts_keywords = ['read', 'speak', 'say']
                    instruction_lower = text.strip().lower()
                    is_tts_request = any(keyword in instruction_lower for keyword in tts_keywords)

                    if is_tts_request:
                        # TTS mode - read the selected text aloud
                        logger.info("Detected TTS request - reading text aloud")

                        # Check TTS text size limit (OpenAI TTS supports up to ~4096 chars)
                        if len(selected_text) > 4000:
                            logger.warning(f"⚠️  Selected text too large for TTS ({len(selected_text)} chars)")
                            logger.warning("   Maximum 4000 characters for TTS. Truncating...")
                            selected_text = selected_text[:4000]

                        char_count = len(selected_text)

                        try:
                            self.title = "🔊 (Reading...)"
                            self.status_item.title = "Status: Reading text aloud..."

                            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                                audio_file = temp_audio.name

                            # Generate speech
                            self.openai_client.text_to_speech(selected_text, audio_file)

                            # Play the audio file with fallback options (pass char count for better timeout estimation)
                            self._play_audio_file(audio_file, char_count=char_count)

                            # Clean up
                            try:
                                os.unlink(audio_file)
                            except Exception as e:
                                logger.warning(f"Could not delete temp audio file: {e}")

                            self.title = "🎙️"
                            self.status_item.title = "Status: ✓ Finished reading"
                            logger.info("✓ Finished reading text aloud")

                        except Exception as e:
                            logger.error(f"Error with TTS: {e}")
                            self.title = "🎙️"
                            self.status_item.title = f"Status: TTS error"

                    else:
                        # AI Enhancement mode - modify the text

                        # Check AI enhancement text size limit (to avoid huge API calls)
                        if len(selected_text) > 1000:
                            logger.warning(f"⚠️  Selected text too large for AI enhancement ({len(selected_text)} chars)")
                            logger.warning("   Maximum 1000 characters for AI enhancement. Using normal dictation mode instead.")
                            # Fall through to normal dictation
                            selected_text = None

                        if selected_text:
                            try:
                                # Use OpenAI to enhance the selected text
                                self.title = "🎙️ (Calling AI...)"
                                self.status_item.title = "Status: Calling AI..."
                                enhanced_text = self.openai_client.enhance_text(text, selected_text)

                                # Replace selected text with enhanced version
                                self.title = "🎙️ (Replacing...)"
                                self.status_item.title = "Status: Replacing text..."

                                # Pass original text so it can find and replace it
                                self.text_selector.replace_selected_text(enhanced_text, original_text=selected_text)

                                logger.info(f"✓ Enhanced: {enhanced_text}")
                                self.title = "🎙️"
                                self.status_item.title = f"Status: ✓ Enhanced"

                            except Exception as e:
                                logger.error(f"Error enhancing text: {e}")
                                self.title = "🎙️"
                                # Fallback to normal text insertion
                                self.insert_text(text)
                                logger.info(f"Transcription (fallback): {text}")
                                self.status_item.title = f"Status: Fallback - {text[:30]}..."
                        else:
                            # Selection was too large, fall back to normal dictation
                            self.insert_text(text)
                            logger.info(f"Transcription: {text}")
                            self.status_item.title = f"Status: Transcribed: {text[:30]}..."
                else:
                    # No selected text or Bedrock unavailable - normal insertion
                    self.insert_text(text)
                    logger.info(f"Transcription: {text}")
                    self.status_item.title = f"Status: Transcribed: {text[:30]}..."
            else:
                logger.warning("No speech detected")
                self.status_item.title = "Status: No speech detected"
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.status_item.title = "Status: Transcription error"
            raise
        finally:
            # Clean up the temporary file
            os.unlink(temp_filename)
    
    def insert_text(self, text):
        # Paste text using clipboard + Cmd+V (works in any focused app)
        logger.info(f"Inserting text at cursor: {text[:50]}...")
        try:
            import pyperclip

            # Save current clipboard
            original_clipboard = pyperclip.paste()

            # Copy text to clipboard
            pyperclip.copy(text)

            # Small delay to ensure clipboard is updated
            time.sleep(0.1)

            # Send Cmd+V to paste using pynput (requires accessibility permissions)
            self.keyboard_controller.press(Key.cmd)
            time.sleep(0.05)
            self.keyboard_controller.press('v')
            time.sleep(0.05)
            self.keyboard_controller.release('v')
            time.sleep(0.05)
            self.keyboard_controller.release(Key.cmd)

            # Restore original clipboard after a delay
            time.sleep(0.1)
            pyperclip.copy(original_clipboard)

            logger.info("✓ Text inserted successfully")
        except Exception as e:
            logger.error(f"Error inserting text: {e}")
            # Final fallback: just copy to clipboard
            logger.info("Falling back to clipboard copy")
            import pyperclip
            pyperclip.copy(text)
            logger.info("✓ Text copied to clipboard - paste with Cmd+V")

    def setup_task_menu(self):
        """Setup/refresh task submenu with current tasks"""
        # Create submenu if it doesn't exist, otherwise clear it
        if not hasattr(self, 'task_submenu'):
            self.task_submenu = rumps.MenuItem("Tasks")
        elif hasattr(self.task_submenu, '_menu') and self.task_submenu._menu is not None:
            self.task_submenu.clear()

        # Static items
        add_text_item = rumps.MenuItem("Add Task (type)", callback=self.prompt_task_typing)
        list_item = rumps.MenuItem("List All Tasks", callback=self.list_tasks_via_voice)

        self.task_submenu.add(add_text_item)
        self.task_submenu.add(list_item)
        self.task_submenu.add(rumps.separator)

        # Dynamic task items (top 10 pending only)
        tasks = self.task_manager.get_tasks(limit=10, status='pending')

        for task in tasks:
            icon = "[ ]" if task['status'] == 'pending' else "[✓]"
            priority_label = f"({task['priority'].title()})" if task['priority'] else ""
            due_label = f"- {self.format_friendly_date(task['due_date'])}" if task['due_date'] else ""

            title = f"{icon} {task['description'][:30]} {priority_label} {due_label}"
            menu_item = rumps.MenuItem(title, callback=lambda s, t=task: self.toggle_task_from_menu(t))
            self.task_submenu.add(menu_item)

        if tasks:
            self.task_submenu.add(rumps.separator)

        # View all tasks (opens JSON file)
        view_item = rumps.MenuItem("View All Tasks", callback=self.open_task_file)
        self.task_submenu.add(view_item)

        # Update menu title with count
        pending_count = self.task_manager.get_pending_count()
        self.task_submenu.title = f"Tasks ({pending_count} pending)"

    def process_task_command(self, text):
        """Process voice task command"""
        self.update_activity()  # Update activity timestamp
        try:
            # Parse command
            parsed = self.task_manager.parse_command(text)

            if not parsed or 'action' not in parsed:
                logger.warning("Could not parse task command")
                self.status_item.title = "Status: Could not understand task command"
                self.title = "🎙️"
                return

            # Execute action
            if parsed['action'] == 'add':
                task = self.task_manager.add_task(
                    description=parsed.get('description'),
                    priority=parsed.get('priority'),
                    due_date=parsed.get('due_date'),
                    category=parsed.get('category')
                )
                feedback = self.format_task_added_feedback(task)
                logger.info(f"✓ {feedback}")
                self.status_item.title = f"Status: ✓ Task added"

            elif parsed['action'] == 'complete':
                task = self.task_manager.complete_task(parsed.get('identifier'))
                if task:
                    logger.info(f"✓ Completed: {task['description']}")
                    self.status_item.title = f"Status: ✓ Completed task"
                else:
                    logger.warning("Task not found")
                    self.status_item.title = "Status: Task not found"

            elif parsed['action'] == 'list':
                tasks = self.task_manager.list_tasks(filter_type=parsed.get('filter') or 'pending')
                feedback = self.format_task_list_feedback(tasks)
                logger.info(feedback)
                self.status_item.title = f"Status: {len(tasks)} pending task(s)"

            elif parsed['action'] == 'archive':
                task = self.task_manager.archive_task(parsed.get('identifier'))
                if task:
                    logger.info(f"✓ Archived: {task['description']}")
                    self.status_item.title = f"Status: ✓ Archived task"
                else:
                    logger.warning("Task not found")
                    self.status_item.title = "Status: Task not found"

            # Refresh menu
            self.setup_task_menu()
            self.title = "🎙️"

        except Exception as e:
            logger.error(f"Error processing task command: {e}")
            self.status_item.title = f"Status: Task error"
            self.title = "🎙️"

    def speak_feedback(self, message):
        """Speak feedback using TTS"""
        if not self.openai_client.is_available():
            logger.warning("TTS not available - skipping voice feedback")
            return

        try:
            self.title = "🔊"
            logger.info(f"Speaking: {message}")

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                audio_file = temp_audio.name

            self.openai_client.text_to_speech(message, audio_file)
            self._play_audio_file(audio_file)

            try:
                os.unlink(audio_file)
            except Exception as e:
                logger.warning(f"Could not delete temp audio file: {e}")

            self.title = "🎙️"
        except Exception as e:
            logger.error(f"TTS feedback error: {e}")
            self.title = "🎙️"

    def format_task_added_feedback(self, task):
        """Format friendly feedback for added task"""
        feedback = f"Added task: {task['description']}"
        if task.get('priority'):
            feedback += f", {task['priority']} priority"
        if task.get('due_date'):
            feedback += f", due {self.format_friendly_date(task['due_date'])}"
        if task.get('category'):
            feedback += f", in {task['category']}"
        return feedback

    def format_task_list_feedback(self, tasks):
        """Format friendly feedback for task list"""
        if not tasks:
            return "You have no pending tasks"

        count = len(tasks)
        feedback = f"You have {count} pending task{'s' if count > 1 else ''}. "

        for i, task in enumerate(tasks[:5], 1):  # Limit to 5 for voice
            feedback += f"{i}. {task['description']}"
            if task.get('priority'):
                feedback += f", {task['priority']} priority"
            if task.get('due_date'):
                feedback += f", due {self.format_friendly_date(task['due_date'])}"
            feedback += ". "

        if count > 5:
            feedback += f"And {count - 5} more."

        return feedback

    def format_friendly_date(self, date_str):
        """Convert ISO date to friendly format (e.g., 'tomorrow', 'today')"""
        if not date_str:
            return ""

        try:
            from datetime import datetime, timedelta
            task_date = datetime.fromisoformat(date_str).date()
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            if task_date == today:
                return "today"
            elif task_date == tomorrow:
                return "tomorrow"
            elif task_date < today:
                days_ago = (today - task_date).days
                return f"{days_ago} day{'s' if days_ago > 1 else ''} ago"
            else:
                days_until = (task_date - today).days
                if days_until <= 7:
                    return f"in {days_until} day{'s' if days_until > 1 else ''}"
                else:
                    return task_date.strftime('%b %d')
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date_str

    def toggle_task_from_menu(self, task):
        """Toggle task completion from menu click"""
        self.update_activity()  # Update activity timestamp
        try:
            if task['status'] == 'pending':
                self.task_manager.complete_task(task['id'])
            else:
                self.task_manager.uncomplete_task(task['id'])
            self.setup_task_menu()
        except Exception as e:
            logger.error(f"Error toggling task: {e}")

    def prompt_task_typing(self, sender):
        """Open text input window for typing task using native AppKit dialog"""
        from AppKit import NSTextField, NSMakeRect

        # Create alert
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Add Task")
        alert.setInformativeText_("Type your task (e.g., 'buy milk tomorrow' or 'call dentist high priority')")
        alert.addButtonWithTitle_("Add Task")
        alert.addButtonWithTitle_("Cancel")

        # Create text field
        text_field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 24))
        text_field.setStringValue_("")
        alert.setAccessoryView_(text_field)

        # Make text field first responder
        alert.window().setInitialFirstResponder_(text_field)

        # Run alert
        response = alert.runModal()

        if response == NSAlertFirstButtonReturn:
            # User clicked "Add Task"
            task_text = str(text_field.stringValue()).strip()
            if task_text:
                # Auto-prepend "task add" if user didn't type it
                if not task_text.lower().startswith('task'):
                    task_text = f"task add {task_text}"
                logger.info(f"Processing typed task command: {task_text}")
                # Process the task command
                threading.Thread(target=self._process_typed_task, args=(task_text,)).start()
            else:
                logger.warning("Empty task text - ignoring")

    def _process_typed_task(self, task_text):
        """Process typed task command in background thread"""
        try:
            # Parse command
            parsed = self.task_manager.parse_command(task_text)

            if not parsed or 'action' not in parsed:
                self.status_item.title = "Status: Could not understand task"
                logger.warning(f"Could not parse task command: {task_text}")
                return

            # Execute action
            if parsed['action'] == 'add':
                task = self.task_manager.add_task(
                    description=parsed.get('description'),
                    priority=parsed.get('priority'),
                    due_date=parsed.get('due_date'),
                    category=parsed.get('category')
                )
                feedback = self.format_task_added_feedback(task)
                logger.info(f"✓ {feedback}")
                self.status_item.title = f"Status: ✓ Task added"

            elif parsed['action'] == 'complete':
                task = self.task_manager.complete_task(parsed.get('identifier'))
                if task:
                    logger.info(f"✓ Completed task: {task['description']}")
                    self.status_item.title = "Status: ✓ Task completed"
                else:
                    logger.warning("Could not find that task")
                    self.status_item.title = "Status: Task not found"

            elif parsed['action'] == 'list':
                tasks = self.task_manager.list_tasks(filter_type=parsed.get('filter') or 'pending')
                feedback = self.format_task_list_feedback(tasks)
                logger.info(feedback)
                self.status_item.title = f"Status: {len(tasks)} tasks listed"

            elif parsed['action'] == 'archive':
                task = self.task_manager.archive_task(parsed.get('identifier'))
                if task:
                    logger.info(f"✓ Archived task: {task['description']}")
                    self.status_item.title = "Status: ✓ Task archived"
                else:
                    logger.warning("Could not find that task")
                    self.status_item.title = "Status: Task not found"

            # Refresh menu
            self.setup_task_menu()

        except Exception as e:
            logger.error(f"Error processing typed task: {e}")
            self.status_item.title = "Status: Task error"

    def list_tasks_via_voice(self, sender):
        """List all tasks (show in status and log)"""
        try:
            tasks = self.task_manager.list_tasks(filter_type='pending')
            feedback = self.format_task_list_feedback(tasks)
            logger.info(feedback)
            self.status_item.title = f"Status: {len(tasks)} pending task(s)"
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            self.status_item.title = "Status: Error listing tasks"

    def open_task_file(self, sender):
        """Open task JSON file in default editor"""
        try:
            subprocess.run(['open', str(self.task_manager.task_file)])
        except Exception as e:
            logger.error(f"Error opening task file: {e}")

    def handle_shutdown(self, _signal, _frame):
        """This method is no longer used with the global handler approach"""
        pass

# Wrap the main execution in a try-except to ensure clean exit
if __name__ == "__main__":
    try:
        WhisperDictationApp().run()
    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received, exiting...")
        os._exit(0)