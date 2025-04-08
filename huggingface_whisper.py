"""
Hugging Face Inference API support for Speech-to-Text application.
This module provides functionality to use Whisper models directly from Hugging Face's servers.
"""

import json
import requests
import io
import numpy as np
import os
import time
from typing import Dict, List, Union, Tuple, Optional, Any

# Default API endpoint
HF_API_URL = "https://api-inference.huggingface.co/models/"
DEFAULT_MODEL = "openai/whisper-medium"  # Default model to use

class WhisperSegment:
    """Compatible class with Faster Whisper's Segment class"""
    def __init__(self, text, start=0.0, end=0.0):
        self.text = text
        self.start = start
        self.end = end
        self.words = []

class WhisperInfo:
    """Compatible class with Faster Whisper's TranscriptionInfo class"""
    def __init__(self, language, language_probability=1.0):
        self.language = language
        self.language_probability = language_probability

class HuggingFaceWhisperModel:
    """
    A class that mimics the WhisperModel interface but uses Hugging Face's Inference API
    instead of running the model locally.
    """
    
    def __init__(self, model_id=DEFAULT_MODEL, api_key=None, api_url=HF_API_URL):
        """
        Initialize the HuggingFaceWhisperModel.
        
        Args:
            model_id (str): The model ID on Hugging Face (e.g., "openai/whisper-medium")
            api_key (str, optional): Hugging Face API key. If None, looks for HF_API_KEY environment variable.
            api_url (str, optional): The API URL. Defaults to Hugging Face's Inference API.
        """
        self.model_id = model_id
        self.api_key = api_key or os.environ.get("HF_API_KEY")
        self.api_url = api_url
        self.endpoint = f"{api_url}{model_id}"
        
        # Validate API key
        if not self.api_key:
            print("Warning: No Hugging Face API key provided. Using anonymous access which has rate limits.")
            print("Set your API key with: export HF_API_KEY='your_api_key'")
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare headers for API request."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def transcribe(self, audio_data: np.ndarray, language=None, initial_prompt=None, 
                   beam_size=5, vad_filter=True, vad_parameters=None, **kwargs) -> Tuple[List[WhisperSegment], WhisperInfo]:
        """
        Transcribe audio using Hugging Face's Inference API.
        
        Args:
            audio_data (np.ndarray): Audio data as numpy array
            language (str, optional): Language code (e.g., "en")
            initial_prompt (str, optional): Text to guide the transcription
            beam_size (int, optional): Not used in API but included for compatibility
            vad_filter (bool, optional): Not used in API but included for compatibility
            vad_parameters (dict, optional): Not used in API but included for compatibility
            **kwargs: Additional options for the API

        Returns:
            Tuple[List[WhisperSegment], WhisperInfo]: Transcription segments and info
        """
        # Convert audio to WAV bytes
        try:
            import soundfile as sf
            wav_bytes = io.BytesIO()
            sf.write(wav_bytes, audio_data, 16000, format='WAV')
            wav_bytes.seek(0)
            audio_bytes = wav_bytes.read()
        except ImportError:
            raise ImportError("Please install soundfile: pip install soundfile")
        
        # Prepare headers
        headers = self._prepare_headers()
        
        # Prepare parameters
        params = {}
        if language:
            params["language"] = language
        if initial_prompt:
            params["initial_prompt"] = initial_prompt
        
        # Send request
        try:
            # API requires either files or binary data
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                files=files,
                data={"options": json.dumps(params)} if params else None
            )
            
            # Check if successful
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                print(error_msg)
                # Return empty result
                return [], WhisperInfo("en", 0.0)
            
            # Parse result
            result = response.json()
            
            # Handle different API response formats
            if isinstance(result, dict) and "text" in result:
                # Simple format: just return the text
                segments = [WhisperSegment(result["text"])]
                language = result.get("language", "en")
                language_prob = 1.0
            elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
                # Format with segments
                segments = [WhisperSegment(item["text"], 
                                          item.get("start", 0.0), 
                                          item.get("end", 0.0)) for item in result]
                language = result[0].get("language", "en")
                language_prob = 1.0
            else:
                # Unknown format, return the raw text
                segments = [WhisperSegment(str(result))]
                language = "en"
                language_prob = 0.0
            
            info = WhisperInfo(language, language_prob)
            return segments, info
            
        except Exception as e:
            print(f"Error in API request: {e}")
            # Return empty result
            return [], WhisperInfo("en", 0.0)

# Function to test the API
def test_api(api_key=None, test_file=None):
    """Test the Hugging Face Whisper API with a sample audio."""
    import soundfile as sf
    
    model = HuggingFaceWhisperModel(api_key=api_key)
    
    if test_file and os.path.exists(test_file):
        # Load test audio file
        audio_data, sample_rate = sf.read(test_file)
        if sample_rate != 16000:
            print(f"Warning: Audio sample rate is {sample_rate}Hz, not 16000Hz")
    else:
        # Generate a silent audio sample
        print("No test file provided. Generating a silent sample.")
        audio_data = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    
    print(f"Transcribing audio with model: {model.model_id}...")
    start_time = time.time()
    segments, info = model.transcribe(audio_data)
    elapsed = time.time() - start_time
    
    print(f"Transcription completed in {elapsed:.2f} seconds.")
    print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
    print("Transcription results:")
    for i, segment in enumerate(segments):
        print(f"Segment {i+1}: {segment.text}")
    
    return segments, info

if __name__ == "__main__":
    # If run directly, test the API
    api_key = os.environ.get("HF_API_KEY")
    test_api(api_key) 