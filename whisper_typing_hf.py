import sys
import sounddevice as sd
import numpy as np
import queue
import threading
import time
import os
from faster_whisper import WhisperModel
from pynput.keyboard import Controller
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QSlider, 
                            QCheckBox, QProgressBar, QStyle, QFileDialog, QRadioButton,
                            QButtonGroup, QLineEdit, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
# Import for Hugging Face integration
try:
    from huggingface_whisper import HuggingFaceWhisperModel
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    print("HuggingFace integration not available. Install required packages with:")
    print("pip install requests soundfile")

# All valid Whisper language codes
VALID_LANGUAGE_CODES = [
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy",
    "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw",
    "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn",
    "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
    "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si",
    "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl",
    "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "zh", "yue"
]

def find_local_model():
    """Search the models directory for valid model directories."""
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    if not os.path.exists(models_dir):
        return None
    
    # Look for directories that might contain Whisper models
    for dir_name in os.listdir(models_dir):
        dir_path = os.path.join(models_dir, dir_name)
        if os.path.isdir(dir_path):
            # Check if this directory contains model.bin and config.json
            if os.path.exists(os.path.join(dir_path, "model.bin")) and \
               os.path.exists(os.path.join(dir_path, "config.json")):
                return dir_path
    
    return None

class AudioTranscriptionThread(QThread):
    transcription_done = pyqtSignal(str)
    status_update = pyqtSignal(str)
    audio_level_update = pyqtSignal(float)
    
    def __init__(self, model_size="distil-large-v3", device="auto", compute_type="int8", model_path=None, parent=None):
        super().__init__(parent)
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_path = model_path
        self.running = False
        self.paused = False
        self.audio_queue = queue.Queue()
        self.keyboard = Controller()
        self.auto_type = True
        self.sample_rate = 16000
        self.model = None
        self.debug = True
        self.use_api = False  # Flag to indicate if using Hugging Face API
        
        # Audio processing parameters
        self.chunk_size = 8000  # Increased from default 4000
        self.audio_buffer = []  # Store audio chunks for processing
        self.buffer_max_size = 5  # Number of chunks to buffer before processing
        self.trigger_level = 0.01  # Minimum audio level to start processing
        self.language = "en"  # Default language
        self.auto_detect_language = False  # Whether to use language detection
        self.initial_prompt = ""  # Optional prompt to guide transcription
        
    def update_model(self, model_size, device, compute_type, model_path=None, use_api=False, api_key=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_path = model_path
        self.use_api = use_api
        
        if use_api:
            model_info = f"Hugging Face API model: openai/whisper-{model_size}"
        else:
            model_info = self.model_path if self.model_path else model_size
            
        self.status_update.emit(f"Loading model: {model_info}...")
        
        # Load model in a separate thread to prevent UI freezing
        def load_model():
            try:
                if use_api:
                    # Use Hugging Face API model
                    from huggingface_whisper import HuggingFaceWhisperModel
                    model_id = f"openai/whisper-{model_size}"
                    self.model = HuggingFaceWhisperModel(model_id=model_id, api_key=api_key)
                    self.status_update.emit(f"Connected to API model: {model_id}")
                else:
                    # Use local or downloadable model
                    self.model = WhisperModel(
                        model_path if model_path else model_size, 
                        device=device, 
                        compute_type=compute_type
                    )
                    self.status_update.emit("Model loaded successfully!")
            except Exception as e:
                self.status_update.emit(f"Error loading model: {str(e)}")
                
        threading.Thread(target=load_model).start()
    
    def set_language(self, language):
        """Set the language for transcription"""
        if language == "auto":
            self.auto_detect_language = True
            self.language = None  # None will let Whisper auto-detect
            print("Language set to: auto-detect")
        else:
            self.auto_detect_language = False
            self.language = language
            print(f"Language set to: {language}")
    
    def set_initial_prompt(self, prompt):
        """Set initial prompt to guide transcription"""
        self.initial_prompt = prompt
        print(f"Initial prompt set to: '{prompt}'")
        
    def callback(self, indata, frames, time, status):
        """Callback function to put audio data into the queue."""
        if status:
            print(f"Audio callback status: {status}")
        
        # Calculate audio level and emit signal
        audio_level = np.abs(indata).mean()
        self.audio_level_update.emit(audio_level)
        
        # Debug audio levels to check if microphone is working
        if self.debug and audio_level > 0.01:  # Only print if there's significant audio
            print(f"Audio level: {audio_level:.4f}")
                
        if not self.paused and self.running:
            self.audio_queue.put(indata.copy())
    
    def run(self):
        self.running = True
        self.status_update.emit("Loading model...")
        
        try:
            # Only load the model if it's not already loaded
            if self.model is None:
                self.status_update.emit("Creating new model instance...")
                if self.use_api:
                    # Use Hugging Face API model
                    from huggingface_whisper import HuggingFaceWhisperModel
                    model_id = f"openai/whisper-{self.model_size}"
                    self.model = HuggingFaceWhisperModel(model_id=model_id)
                    if self.debug:
                        print(f"Using Hugging Face API model: {model_id}")
                else:
                    # Use local or downloadable model
                    self.model = WhisperModel(
                        self.model_path if self.model_path else self.model_size, 
                        device=self.device, 
                        compute_type=self.compute_type
                    )
            
            self.status_update.emit("Model loaded. Starting audio stream...")
            
            # Clear the audio buffer
            self.audio_buffer = []
            
            with sd.InputStream(samplerate=self.sample_rate, channels=1, blocksize=self.chunk_size, callback=self.callback):
                self.status_update.emit("Listening... Speak now!")
                
                while self.running:
                    try:
                        # Use a timeout to allow checking the running flag periodically
                        audio_chunk = self.audio_queue.get(timeout=0.5)
                        if not self.paused:
                            # Add the chunk to our buffer
                            self.audio_buffer.append(audio_chunk)
                            
                            # Process audio when we have enough chunks or high audio level
                            audio_level = np.abs(audio_chunk).mean()
                            buffer_full = len(self.audio_buffer) >= self.buffer_max_size
                            
                            if buffer_full or audio_level > self.trigger_level * 3:  # Trigger on loud sounds immediately
                                # Combine all buffered chunks
                                combined_chunks = np.vstack(self.audio_buffer) if len(self.audio_buffer) > 1 else self.audio_buffer[0]
                                audio_data = np.squeeze(combined_chunks)
                                
                                # Reset buffer
                                self.audio_buffer = []
                                
                                # Debug: Print audio data shape and values
                                if self.debug:
                                    print(f"Processing audio chunk: shape={audio_data.shape}, min={audio_data.min():.4f}, max={audio_data.max():.4f}, mean={audio_data.mean():.4f}")
                                
                                # Transcribe speech
                                transcription_kwargs = {
                                    'beam_size': 5,
                                    'vad_filter': True,
                                    'vad_parameters': dict(min_silence_duration_ms=500)
                                }
                                
                                # Add language if not auto-detecting
                                if not self.auto_detect_language and self.language:
                                    transcription_kwargs['language'] = self.language
                                    
                                # Add initial prompt if provided
                                if self.initial_prompt:
                                    transcription_kwargs['initial_prompt'] = self.initial_prompt
                                
                                segments, info = self.model.transcribe(audio_data, **transcription_kwargs)
                                
                                if self.debug:
                                    print(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
                                
                                # Process the transcribed text
                                transcribed_text = ""
                                for segment in segments:
                                    text = segment.text.strip()
                                    if text:
                                        transcribed_text += text + " "
                                        self.transcription_done.emit(text)
                                        
                                        # Type out the recognized text if auto-type is enabled
                                        if self.auto_type:
                                            if self.debug:
                                                print(f"Typing text: '{text}'")
                                            try:
                                                # Try using a small delay before typing
                                                time.sleep(0.1)
                                                self.keyboard.type(text + " ")
                                            except Exception as e:
                                                print(f"Error typing text: {e}")
                                
                                # Print if no text was transcribed
                                if not transcribed_text and self.debug:
                                    print("No text transcribed from audio chunk")
                                    # Check if audio level was too low
                                    if audio_data.mean() < 0.01:
                                        print("Audio level may be too low - speak louder or adjust microphone")
                                
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"Error in transcription loop: {e}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            self.status_update.emit(error_msg)
        finally:
            self.status_update.emit("Transcription stopped")
            self.running = False
    
    def stop(self):
        self.running = False
        self.wait()
    
    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused
    
    def set_auto_type(self, enabled):
        self.auto_type = enabled
        print(f"Auto-type {'enabled' if enabled else 'disabled'}") 