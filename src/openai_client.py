#!/usr/bin/env python3
# ABOUTME: OpenAI client for AI-powered text enhancement, STT, and TTS using GPT models
import os
import ssl
import certifi
from dotenv import load_dotenv
from logger_config import setup_logging

# Load environment variables
load_dotenv()
logger = setup_logging()

class OpenAIClient:
    def __init__(self):
        """Initialize OpenAI client"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.whisper_model = os.getenv('OPENAI_WHISPER_MODEL', 'gpt-4o-mini-transcribe')
        self.tts_model = os.getenv('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
        self.tts_voice = os.getenv('OPENAI_TTS_VOICE', 'alloy')
        self.use_openai_whisper = os.getenv('USE_OPENAI_WHISPER', 'false').lower() == 'true'

        # Initialize OpenAI client
        try:
            if self.api_key:
                from openai import OpenAI
                import httpx

                # Check if SSL verification should be disabled (for local testing only)
                disable_ssl = os.getenv('OPENAI_DISABLE_SSL_VERIFY', 'false').lower() == 'true'

                if disable_ssl:
                    logger.warning("⚠️  SSL VERIFICATION DISABLED - for local testing only!")
                    # Configure httpx client with disabled SSL and longer timeout
                    http_client = httpx.Client(
                        verify=False,
                        timeout=30.0,
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )
                else:
                    # Use certifi's CA bundle for SSL verification
                    http_client = httpx.Client(
                        verify=certifi.where(),
                        timeout=30.0,
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )

                self.client = OpenAI(
                    api_key=self.api_key,
                    http_client=http_client,
                    max_retries=2  # Reduce retries to fail faster
                )
                logger.info(f"OpenAI client initialized")
                logger.info(f"  - Text model: {self.model}")
                logger.info(f"  - Whisper model: {self.whisper_model} (enabled: {self.use_openai_whisper})")
                logger.info(f"  - TTS model: {self.tts_model}")
                if not disable_ssl:
                    logger.info(f"  - SSL certs: {certifi.where()}")
            else:
                logger.warning("OPENAI_API_KEY not found in environment variables")
                self.client = None
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            self.client = None

    def is_available(self):
        """Check if OpenAI client is available and initialized"""
        return self.client is not None

    def enhance_text(self, transcribed_text, selected_text):
        """
        Send transcribed instruction and selected text to OpenAI.
        Returns the enhanced/modified text.
        """
        if not self.client:
            raise Exception("OpenAI client not initialized")

        # Construct the prompt for GPT
        prompt = f"""You are helping a user edit text based on voice commands. The user has selected some text and given a voice instruction for how to modify it.

Selected text: "{selected_text}"
Voice instruction: "{transcribed_text}"

Please modify the selected text according to the voice instruction. Return only the modified text without any explanation or additional formatting."""

        try:
            # Use Chat Completions API
            kwargs = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful text editing assistant. Follow user instructions precisely and return only the modified text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # GPT-5 specific settings
            if self.model.startswith('gpt-5'):
                kwargs['max_completion_tokens'] = 1000
                # GPT-5 Nano only supports temperature=1 (default)
                if 'nano' not in self.model.lower():
                    kwargs['temperature'] = 0.7
            else:
                kwargs['max_tokens'] = 1000
                kwargs['temperature'] = 0.7

            response = self.client.chat.completions.create(**kwargs)

            # Extract the generated text
            if response.choices and len(response.choices) > 0:
                enhanced_text = response.choices[0].message.content.strip()
                logger.debug(f"OpenAI response: {enhanced_text}")
                return enhanced_text
            else:
                raise Exception("No content in OpenAI response")

        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            raise

    def test_connection(self):
        """Test if OpenAI client is working properly"""
        if not self.client:
            return False, "Client not initialized"

        try:
            # Simple test with a basic prompt
            # GPT-5 models use max_completion_tokens, older models use max_tokens
            kwargs = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Say 'Hello, OpenAI connection successful!'"
                    }
                ]
            }

            # Use max_completion_tokens for GPT-5 models
            if self.model.startswith('gpt-5'):
                kwargs['max_completion_tokens'] = 50
            else:
                kwargs['max_tokens'] = 50

            response = self.client.chat.completions.create(**kwargs)

            if response.choices and len(response.choices) > 0:
                return True, response.choices[0].message.content.strip()
            else:
                return False, "No content in response"

        except Exception as e:
            return False, str(e)

    def is_available(self):
        """Check if OpenAI client is available and configured"""
        return self.client is not None

    def transcribe_audio(self, audio_file_path):
        """
        Transcribe audio file using OpenAI Whisper API.
        Returns transcribed text.
        """
        if not self.client:
            raise Exception("OpenAI client not initialized")

        try:
            with open(audio_file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    response_format="text"
                )

            logger.debug(f"OpenAI Whisper transcription: {response}")
            return response.strip() if isinstance(response, str) else response.text.strip()

        except Exception as e:
            logger.error(f"Error transcribing audio with OpenAI: {e}")
            raise

    def text_to_speech(self, text, output_path=None):
        """
        Convert text to speech using OpenAI TTS.
        If output_path is provided, saves to file. Otherwise returns audio data.
        """
        if not self.client:
            raise Exception("OpenAI client not initialized")

        try:
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text
            )

            if output_path:
                response.stream_to_file(output_path)
                logger.info(f"TTS audio saved to: {output_path}")
                return output_path
            else:
                return response.content

        except Exception as e:
            logger.error(f"Error generating speech with OpenAI: {e}")
            raise

    def get_model_info(self):
        """Get information about the current model configuration"""
        return {
            'text_model': self.model,
            'whisper_model': self.whisper_model,
            'use_openai_whisper': self.use_openai_whisper,
            'tts_model': self.tts_model,
            'tts_voice': self.tts_voice,
            'api_key_set': bool(self.api_key),
            'available': self.is_available()
        }