#!/usr/bin/env python3
# ABOUTME: MLX Whisper client for local speech-to-text on Apple Silicon Macs
# ABOUTME: Optimized for M1/M2/M3 with auto-detection and English translation
import os
import tempfile
import ssl
from logger_config import setup_logging

logger = setup_logging()

class MLXWhisperClient:
    """MLX Whisper transcription client - optimized for Apple Silicon"""

    def __init__(self, model_size="large-v3"):
        """
        Initialize MLX Whisper model

        Args:
            model_size: Model size to use (tiny, base, small, medium, large-v3)
                       Default: large-v3 (highest accuracy)
        """
        self.model_size = model_size
        self.model = None
        self.processor = None

        # Map common names to MLX model paths
        self.model_map = {
            "tiny": "mlx-community/whisper-tiny-mlx",
            "base": "mlx-community/whisper-base-mlx",
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large": "mlx-community/whisper-large-v3-mlx",
            "large-v3": "mlx-community/whisper-large-v3-mlx",
        }

        self._load_model()

    def _load_model(self):
        """Load MLX Whisper model from Hugging Face"""
        try:
            import mlx_whisper
            import os

            model_name = self.model_map.get(self.model_size, "mlx-community/whisper-large-v3-mlx")
            logger.info(f"Loading MLX Whisper model: {self.model_size} ({model_name})")

            # Set HuggingFace cache dir
            cache_dir = os.path.expanduser('~/.cache/huggingface/hub')
            os.environ['HF_HOME'] = os.path.expanduser('~/.cache/huggingface')
            os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

            # Set SSL certs for Zscaler compatibility
            self._setup_ssl_for_huggingface()

            # Check if model is already cached
            model_repo = self.model_map.get(self.model_size, "mlx-community/whisper-large-v3-mlx")
            cache_path = os.path.join(cache_dir, f"models--{model_repo.replace('/', '--')}")

            if os.path.exists(cache_path):
                logger.info(f"✓ Model already cached at: {cache_path}")
            else:
                logger.info(f"📥 Downloading model (~{self._get_model_size()} MB)...")
                logger.info(f"   Cache location: {cache_dir}")
                logger.info("   This may take 5-15 minutes on first run depending on internet speed")

            # MLX Whisper will auto-download and cache the model with progress
            self.mlx_whisper = mlx_whisper
            logger.info(f"✓ MLX Whisper loaded successfully")

        except ImportError as e:
            logger.error(f"mlx-whisper not installed. Install with: pip install mlx-whisper. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading MLX Whisper model: {e}")
            raise

    def _setup_ssl_for_huggingface(self):
        """Configure SSL certificates for HuggingFace downloads (Zscaler compatibility)"""
        import os
        import ssl

        # Check for Zscaler certificate in .env or use system defaults
        ssl_cert_file = os.getenv('SSL_CERT_FILE')
        requests_ca_bundle = os.getenv('REQUESTS_CA_BUNDLE')

        if ssl_cert_file:
            os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
            logger.debug(f"Using SSL_CERT_FILE for HuggingFace: {ssl_cert_file}")
        elif requests_ca_bundle:
            os.environ['REQUESTS_CA_BUNDLE'] = requests_ca_bundle
            logger.debug(f"Using REQUESTS_CA_BUNDLE for HuggingFace: {requests_ca_bundle}")
        else:
            # Use system default
            try:
                cert_path = ssl.get_default_verify_paths().cafile
                if cert_path and os.path.exists(cert_path):
                    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                    logger.debug(f"Using system SSL certs for HuggingFace: {cert_path}")
            except:
                logger.debug("No SSL cert path found, using defaults")

    def _get_model_size(self):
        """Get approximate model size in MB"""
        sizes = {
            "tiny": 39,
            "base": 140,
            "small": 244,
            "medium": 769,
            "large": 2900,
            "large-v3": 2900,
        }
        return sizes.get(self.model_size, 2900)

    def transcribe_audio(self, audio_file_path):
        """
        Transcribe audio file using MLX Whisper

        Auto-detects language and translates to English using local models if needed.

        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc)

        Returns:
            Transcribed text in English
        """
        try:
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            logger.info(f"🎙️ TRANSCRIPTION: Using LOCAL model - MLX Whisper ({self.model_size})")

            # Ensure SSL certificates are configured for HuggingFace API calls (even for cached models, MLX checks metadata)
            ssl_cert_file = os.getenv('SSL_CERT_FILE')
            requests_ca_bundle = os.getenv('REQUESTS_CA_BUNDLE')

            old_ssl_cert = os.environ.get('SSL_CERT_FILE')
            old_ca_bundle = os.environ.get('REQUESTS_CA_BUNDLE')

            try:
                # Set SSL certs if available
                if ssl_cert_file and os.path.exists(ssl_cert_file):
                    os.environ['SSL_CERT_FILE'] = ssl_cert_file
                    os.environ['REQUESTS_CA_BUNDLE'] = ssl_cert_file
                    logger.debug(f"Using SSL cert for HuggingFace: {ssl_cert_file}")

                # Transcribe with language auto-detection
                result = self.mlx_whisper.transcribe(
                    audio_file_path,
                    path_or_hf_repo=self.model_map.get(self.model_size, "mlx-community/whisper-large-v3-mlx")
                )
            finally:
                # Restore original environment variables
                if old_ssl_cert is None:
                    os.environ.pop('SSL_CERT_FILE', None)
                else:
                    os.environ['SSL_CERT_FILE'] = old_ssl_cert

                if old_ca_bundle is None:
                    os.environ.pop('REQUESTS_CA_BUNDLE', None)
                else:
                    os.environ['REQUESTS_CA_BUNDLE'] = old_ca_bundle

            # Extract transcribed text
            text = result.get("text", "").strip()

            if not text:
                logger.warning("No speech detected in audio")
                return ""

            # Check if transcription is in English
            detected_language = result.get("language", "en")
            logger.debug(f"Detected language: {detected_language}")

            # If non-English, translate to English locally
            if detected_language != "en" and not self._is_english_text(text):
                logger.debug(f"Non-English text detected ({detected_language}), translating to English...")
                text = self._translate_locally(text, detected_language)

            logger.debug(f"MLX Whisper transcription: {text}")
            return text

        except Exception as e:
            logger.error(f"Error transcribing audio with MLX Whisper: {e}")
            raise

    def _is_english_text(self, text):
        """
        Check if text appears to be in English

        Returns True if text contains primarily English characters
        """
        try:
            # Try to detect non-Latin scripts (Hindi, Arabic, Chinese, Japanese, Korean)
            non_latin_ranges = [
                (0x0900, 0x097F),    # Devanagari (Hindi)
                (0x0600, 0x06FF),    # Arabic
                (0x4E00, 0x9FFF),    # CJK Unified Ideographs (Chinese)
                (0x3040, 0x309F),    # Hiragana (Japanese)
                (0x30A0, 0x30FF),    # Katakana (Japanese)
                (0xAC00, 0xD7AF),    # Hangul (Korean)
            ]

            for char in text:
                char_code = ord(char)
                for start, end in non_latin_ranges:
                    if start <= char_code <= end:
                        return False

            return True
        except Exception as e:
            logger.debug(f"Error checking if text is English: {e}")
            return True  # Default to True on error

    def _is_translation_model_cached(self, model_name):
        """
        Check if a translation model is actually cached and has required files

        Returns True only if model cache exists with config.json, False otherwise
        """
        try:
            cache_dir = os.path.expanduser('~/.cache/huggingface/hub')
            # Convert model name (e.g., "Helsinki-NLP/opus-mt-ur-en") to cache directory name
            cache_model_dir = model_name.replace('/', '--')
            cache_path = os.path.join(cache_dir, f"models--{cache_model_dir}")

            logger.debug(f"Checking cache for {model_name} at {cache_path}")

            # Check if cache directory exists
            if not os.path.exists(cache_path):
                logger.debug(f"Model cache directory not found: {cache_path}")
                return False

            # Verify critical model files exist (config.json is required)
            snapshots_path = os.path.join(cache_path, "snapshots")
            if not os.path.exists(snapshots_path):
                logger.debug(f"Model cache incomplete (no snapshots directory): {cache_path}")
                return False

            # Check if there are snapshot directories with config.json
            try:
                snapshots = os.listdir(snapshots_path)
                if not snapshots:
                    logger.debug(f"Model snapshots directory is empty: {snapshots_path}")
                    return False

                for snapshot in snapshots:
                    snapshot_path = os.path.join(snapshots_path, snapshot)
                    if os.path.isdir(snapshot_path):
                        config_file = os.path.join(snapshot_path, "config.json")
                        if os.path.exists(config_file):
                            logger.debug(f"✓ Model cache valid for {model_name}")
                            return True
                        else:
                            logger.debug(f"  Snapshot {snapshot} missing config.json")
            except Exception as e:
                logger.debug(f"Error checking snapshots: {e}")
                return False

            logger.debug(f"✗ Model cache incomplete (no valid snapshots with config.json): {cache_path}")
            return False

        except Exception as e:
            logger.debug(f"Error checking model cache: {e}")
            return False

    def _translate_locally(self, text, source_lang):
        """
        Translate non-English text to English using local models

        Supports: Hindi (hi), Urdu (ur), Chinese (zh) via Helsinki-NLP opus-mt models
        Falls back to OpenAI if local translation fails and internet is available.

        Args:
            text: Text to translate
            source_lang: ISO 639-1 language code (e.g., 'hi' for Hindi, 'ur' for Urdu, 'zh' for Chinese)

        Returns:
            Translated text in English
        """
        try:
            import torch
            import signal

            # Map language codes to Helsinki-NLP model names
            model_map = {
                "hi": "Helsinki-NLP/opus-mt-hi-en",    # Hindi to English
                "ur": "Helsinki-NLP/opus-mt-ur-en",    # Urdu to English
                "zh": "Helsinki-NLP/opus-mt-zh-en",    # Chinese to English
            }

            model_name = model_map.get(source_lang)
            if not model_name:
                logger.debug(f"No local translation model for {source_lang}, trying OpenAI...")
                return self._translate_with_openai(text)

            # Check if model is cached before trying to load it
            if not self._is_translation_model_cached(model_name):
                logger.debug(f"Translation model not cached ({model_name}), trying OpenAI...")
                return self._translate_with_openai(text)

            logger.info(f"🌐 TRANSLATION: Using LOCAL model - {model_name} ({source_lang}→en)")
            try:
                # Save original environment variables
                old_offline = os.environ.get('HF_HUB_OFFLINE')
                old_transformers_offline = os.environ.get('TRANSFORMERS_OFFLINE')
                old_huggingface_offline = os.environ.get('HUGGINGFACE_CO_OFFLINE')

                try:
                    # Set offline BEFORE any transformers imports
                    os.environ['HF_HUB_OFFLINE'] = '1'
                    os.environ['TRANSFORMERS_OFFLINE'] = '1'
                    os.environ['HUGGINGFACE_CO_OFFLINE'] = '1'

                    # Import transformers AFTER setting offline mode
                    from transformers import pipeline

                    def timeout_handler(signum, frame):
                        raise TimeoutError("Translation model loading timeout - falling back to OpenAI")

                    # Set a 10 second timeout to prevent hanging on network retries
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(10)

                    try:
                        # Use CPU for compatibility, local_files_only=True prevents any network access
                        translator = pipeline("translation", model=model_name, device=-1 if torch.cuda.is_available() else -1, local_files_only=True)

                        logger.debug(f"Translating {source_lang} text to English...")
                        result = translator(text, max_length=512)
                        translated_text = result[0]["translation_text"]

                        logger.info(f"✓ Local translation successful: {translated_text}")
                        return translated_text
                    finally:
                        # Cancel the timeout alarm
                        signal.alarm(0)

                finally:
                    # Restore original environment variables
                    if old_offline is None:
                        os.environ.pop('HF_HUB_OFFLINE', None)
                    else:
                        os.environ['HF_HUB_OFFLINE'] = old_offline

                    if old_transformers_offline is None:
                        os.environ.pop('TRANSFORMERS_OFFLINE', None)
                    else:
                        os.environ['TRANSFORMERS_OFFLINE'] = old_transformers_offline

                    if old_huggingface_offline is None:
                        os.environ.pop('HUGGINGFACE_CO_OFFLINE', None)
                    else:
                        os.environ['HUGGINGFACE_CO_OFFLINE'] = old_huggingface_offline

            except (TimeoutError, Exception) as pipeline_error:
                # If pipeline fails (timeout, SSL, missing files, etc), fall back immediately
                logger.debug(f"Failed to load translation pipeline ({source_lang}): {pipeline_error}")
                logger.debug("Falling back to OpenAI translation...")
                return self._translate_with_openai(text)

        except Exception as e:
            logger.warning(f"Local translation error ({source_lang}): {e}")
            logger.debug("Falling back to OpenAI translation...")
            return self._translate_with_openai(text)

    def _translate_with_openai(self, text):
        """
        Translate text to English using OpenAI API (fallback)

        Only used if local translation fails and internet is available.
        """
        try:
            from openai_client import OpenAIClient

            client = OpenAIClient()
            if client.is_available():
                logger.info(f"🌐 TRANSLATION: Using CLOUD model - OpenAI gpt-4o-mini")
                result = client.translate_to_english(text)
                logger.info(f"✓ OpenAI translation successful: {result}")
                return result
            else:
                logger.warning("OpenAI client not available and no local translation available, returning text as-is")
                return text

        except Exception as e:
            logger.warning(f"OpenAI translation failed: {e}, returning original text")
            return text

    def is_available(self):
        """Check if MLX Whisper is available and ready"""
        try:
            import mlx_whisper
            return True
        except ImportError:
            return False
