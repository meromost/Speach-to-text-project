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
import scipy.signal as signal

# English only - remove other language codes
ENGLISH_CODE = "en"

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
        
        # Improved Audio processing parameters
        self.chunk_size = 4000  # Reduced for more frequent processing
        self.audio_buffer = []  # Store audio chunks for processing
        self.buffer_max_size = 3  # Reduced for more responsive transcription
        self.trigger_level = 0.02  # Increased threshold for better signal-to-noise ratio
        self.silence_chunks = 0  # Count consecutive silent chunks
        self.max_silence_chunks = 5  # Maximum silent chunks before forcing processing
        self.vad_enabled = True  # Voice activity detection
        self.language = ENGLISH_CODE  # Fixed to English
        self.initial_prompt = ""  # Optional prompt to guide transcription
        
        # Enhanced parameters for better accuracy
        self.noise_reduction_enabled = True
        self.context_window = []  # Store previous transcriptions for context
        self.max_context_window = 3  # Max number of previous transcriptions to keep
        self.high_quality_mode = False  # Toggle for more accurate but slower processing
        
        # Advanced audio processing
        self.pre_emphasis = 0.97  # Pre-emphasis filter coefficient
        self.energy_threshold = 0.005  # Minimum energy for audio to be considered speech
        self.dynamic_energy = True  # Adjust energy threshold dynamically
        
    def update_model(self, model_size, device, compute_type, model_path=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_path = model_path
        
        model_info = self.model_path if self.model_path else model_size
        self.status_update.emit(f"Loading model: {model_info}...")
        
        # Load model in a separate thread to prevent UI freezing
        def load_model():
            try:
                self.model = WhisperModel(
                    model_path if model_path else model_size, 
                    device=device, 
                    compute_type=compute_type
                )
                self.status_update.emit("Model loaded successfully!")
            except Exception as e:
                self.status_update.emit(f"Error loading model: {str(e)}")
                
        threading.Thread(target=load_model).start()
    
    def set_initial_prompt(self, prompt):
        """Set initial prompt to guide transcription"""
        self.initial_prompt = prompt
        print(f"Initial prompt set to: '{prompt}'")
        
    def set_high_quality_mode(self, enabled):
        """Enable or disable high quality mode for better accuracy"""
        self.high_quality_mode = enabled
        print(f"High quality mode {'enabled' if enabled else 'disabled'}")
        
    def set_noise_reduction(self, enabled):
        """Enable or disable noise reduction preprocessing"""
        self.noise_reduction_enabled = enabled
        print(f"Noise reduction {'enabled' if enabled else 'disabled'}")
    
    def preprocess_audio(self, audio_data):
        """Apply preprocessing to improve audio quality before transcription"""
        if not self.noise_reduction_enabled:
            return audio_data.astype(np.float32)
        
        try:
            # Ensure audio is float32
            audio_data = audio_data.astype(np.float32)
            
            # Apply pre-emphasis to enhance high frequencies (improves speech clarity)
            emphasized_audio = np.append(
                audio_data[0], 
                audio_data[1:] - self.pre_emphasis * audio_data[:-1]
            )
            
            # Calculate energy of signal
            energy = np.sum(emphasized_audio ** 2) / len(emphasized_audio)
            
            # Dynamically adjust energy threshold if enabled
            if self.dynamic_energy and energy > self.energy_threshold:
                # Gradually adapt the threshold (slower adjustment = more stable)
                self.energy_threshold = 0.9 * self.energy_threshold + 0.1 * energy
            
            # Apply normalization (more controlled approach)
            if np.max(np.abs(emphasized_audio)) > 0:
                emphasized_audio = emphasized_audio / (np.max(np.abs(emphasized_audio)) + 1e-8)
                
            # Return processed audio
            return emphasized_audio.astype(np.float32)
            
        except Exception as e:
            print(f"Error in audio preprocessing: {e}")
            return audio_data.astype(np.float32)
    
    def is_speech(self, audio_data):
        """Better voice activity detection to filter out silence and background noise"""
        if not self.vad_enabled:
            return True
            
        try:
            # Calculate signal energy
            energy = np.sum(audio_data ** 2) / len(audio_data)
            
            # Check if energy is above threshold
            is_voice = energy > self.energy_threshold
            
            # Additional check for clipped/loud audio
            max_amplitude = np.max(np.abs(audio_data))
            is_too_loud = max_amplitude > 0.95  # Near clipping
            
            if is_too_loud:
                # If audio is very loud but fairly consistent, it might be background noise
                std_dev = np.std(audio_data)
                variation_coefficient = std_dev / max_amplitude
                
                # Genuine speech usually has high variation even when loud
                is_voice = variation_coefficient > 0.1
                
                if self.debug:
                    print(f"Loud audio detected: max={max_amplitude:.4f}, variation={variation_coefficient:.4f}, " +
                          f"considered {'speech' if is_voice else 'noise'}")
            
            if self.debug and is_voice:
                print(f"Voice detected with energy: {energy:.6f} (threshold: {self.energy_threshold:.6f})")
                
            return is_voice
            
        except Exception as e:
            print(f"Error in voice activity detection: {e}")
            return True  # Default to assuming it's speech if detection fails
    
    def get_context_prompt(self):
        """Create a context prompt from previous transcriptions"""
        # Special prompt to avoid "Thank you" hallucination, based on research
        base_prompt = "This is a speech-to-text system. Transcribe exactly what you hear. The words 'Thank you' are not being spoken. "
        
        if not self.context_window:
            return base_prompt + (self.initial_prompt or "")
            
        context = " ".join(self.context_window)
        if self.initial_prompt:
            return f"{base_prompt} {self.initial_prompt} Previous context: {context}"
        return f"{base_prompt} Previous context: {context}"
        
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
                self.model = WhisperModel(
                    self.model_path if self.model_path else self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type
                )
            
            self.status_update.emit("Model loaded. Starting audio stream...")
            
            # Clear the audio buffer and reset counters
            self.audio_buffer = []
            self.silence_chunks = 0
            
            with sd.InputStream(samplerate=self.sample_rate, channels=1, blocksize=self.chunk_size, callback=self.callback):
                self.status_update.emit("Listening... Speak now!")
                
                while self.running:
                    try:
                        # Use a timeout to allow checking the running flag periodically
                        audio_chunk = self.audio_queue.get(timeout=0.5)
                        if not self.paused:
                            # Add the chunk to our buffer
                            self.audio_buffer.append(audio_chunk)
                            
                            # Calculate audio level
                            audio_level = np.abs(audio_chunk).mean()
                            
                            # Determine if we should process now
                            process_now = False
                            
                            # 1. Check if we have enough chunks
                            buffer_full = len(self.audio_buffer) >= self.buffer_max_size
                            
                            # 2. Check if audio is loud enough to trigger immediate processing
                            loud_audio = audio_level > self.trigger_level * 3
                            
                            # 3. Check if we've had too many silent chunks (force processing)
                            if audio_level < self.trigger_level:
                                self.silence_chunks += 1
                            else:
                                self.silence_chunks = 0
                                
                            force_process = self.silence_chunks >= self.max_silence_chunks and len(self.audio_buffer) > 1
                            
                            # Decide whether to process now
                            process_now = buffer_full or loud_audio or force_process
                            
                            if process_now:
                                # Combine all buffered chunks
                                combined_chunks = np.vstack(self.audio_buffer) if len(self.audio_buffer) > 1 else self.audio_buffer[0]
                                audio_data = np.squeeze(combined_chunks)
                                
                                # Reset buffer and silence counter
                                self.audio_buffer = []
                                self.silence_chunks = 0
                                
                                # Debug: Print audio data shape and values
                                if self.debug:
                                    print(f"Processing audio chunk: shape={audio_data.shape}, min={audio_data.min():.4f}, max={audio_data.max():.4f}, mean={audio_data.mean():.4f}")
                                
                                # Check if this might be speech using VAD
                                if not self.is_speech(audio_data):
                                    if self.debug:
                                        print("Skipping chunk - no speech detected")
                                    continue
                                
                                # Keep a copy of the original audio for fallback
                                original_audio = audio_data.copy().astype(np.float32)
                                
                                # Preprocess audio for better quality
                                processed_audio = self.preprocess_audio(audio_data)
                                
                                # Transcribe speech with enhanced parameters for English only
                                transcription_kwargs = {
                                    'beam_size': 5 if not self.high_quality_mode else 8,
                                    'vad_filter': True,
                                    'vad_parameters': dict(min_silence_duration_ms=300),
                                    'language': ENGLISH_CODE,  # Always use English
                                    'temperature': 0.0,        # Use greedy decoding for more exact transcriptions
                                    'repetition_penalty': 1.5, # Penalize repeating the same phrases
                                    'no_speech_threshold': 0.6, # Higher threshold to avoid "no speech" false positives
                                    'suppress_tokens': [-1],   # Suppress blank tokens
                                    'suppress_blank': True,    # Suppress blank outputs
                                    'without_timestamps': True # Disable timestamps to reduce "thank you" hallucinations
                                }
                                
                                # Add more parameters only in high quality mode
                                if self.high_quality_mode:
                                    transcription_kwargs.update({
                                        'condition_on_previous_text': True,  # Use previous text as context
                                        'best_of': 3              # Generate multiple candidates and pick the best one
                                    })
                                    
                                # Add context from previous transcriptions
                                effective_prompt = self.get_context_prompt()
                                if effective_prompt:
                                    transcription_kwargs['initial_prompt'] = effective_prompt
                                
                                try:
                                    # First try with processed audio
                                    segments, info = self.model.transcribe(processed_audio, **transcription_kwargs)
                                    
                                    if self.debug:
                                        print(f"Transcribing with English language model")
                                    
                                except Exception as e:
                                    # If processing fails, try with original audio
                                    print(f"Transcription with processed audio failed: {e}")
                                    print("Falling back to original audio...")
                                    try:
                                        segments, info = self.model.transcribe(original_audio, **transcription_kwargs)
                                        
                                        if self.debug:
                                            print(f"Fallback succeeded. Detected language: {info.language} with probability {info.language_probability:.2f}")
                                    except Exception as e2:
                                        print(f"Fallback transcription also failed: {e2}")
                                        # Continue to next audio chunk
                                        continue
                                
                                # Process the transcribed text
                                transcribed_text = ""
                                for segment in segments:
                                    text = segment.text.strip()
                                    
                                    # Apply hallucination correction
                                    text = self.correct_hallucinations(text)
                                    
                                    if text:
                                        transcribed_text += text + " "
                                        self.transcription_done.emit(text)
                                        
                                        # Update context window for future transcriptions
                                        self.context_window.append(text)
                                        if len(self.context_window) > self.max_context_window:
                                            self.context_window.pop(0)  # Remove oldest context
                                        
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

    def correct_hallucinations(self, text):
        """Correct common hallucination patterns in Whisper output"""
        # Map of common hallucinations and their likely corrections based on research
        hallucination_patterns = {
            "Thank you.": "",
            "Thank you": "",
            "Thank you very much.": "",
            "Thanks for watching.": "",
            "Thanks for watching": "",
            "Please subscribe": "",
            "Like and subscribe": "",
            "Don't forget to subscribe": ""
        }
        
        # Check if the output matches any known hallucination patterns
        if text.strip() in hallucination_patterns:
            if self.debug:
                print(f"Detected hallucination: '{text}' - skipping")
            return ""
            
        # Check if the text is very short and contains only common words
        if len(text.split()) <= 3 and any(pattern in text.lower() for pattern in ["thank", "thanks", "please", "subscribe"]):
            if self.debug:
                print(f"Detected likely hallucination: '{text}' - skipping")
            return ""
            
        return text

class SpeechToTextApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech to Text Typer (English)")
        self.setMinimumSize(500, 550)
        
        # Initialize the audio thread
        self.audio_thread = None
        
        # Automatically find local model
        self.model_path = find_local_model()
        
        # Set up the UI
        self.setup_ui()
        
        # Initially load the model
        self.initialize_model()
    
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Title
        title = QLabel("Speech to Text Typer")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Audio level indicator
        audio_level_layout = QHBoxLayout()
        audio_level_label = QLabel("Audio Level:")
        self.audio_level_progress = QProgressBar()
        self.audio_level_progress.setRange(0, 100)
        self.audio_level_progress.setValue(0)
        audio_level_layout.addWidget(audio_level_label)
        audio_level_layout.addWidget(self.audio_level_progress)
        main_layout.addLayout(audio_level_layout)
        
        # Model source selection
        model_source_group = QGroupBox("Model Source")
        model_source_layout = QVBoxLayout()
        model_source_group.setLayout(model_source_layout)
        
        # Radio buttons for model source
        self.model_source_buttons = QButtonGroup()
        self.download_radio = QRadioButton("Download from HuggingFace")
        self.local_radio = QRadioButton("Use local model")
        
        # Auto-select local model if found
        if self.model_path:
            self.local_radio.setChecked(True)
        else:
            self.download_radio.setChecked(True)
            
        self.model_source_buttons.addButton(self.download_radio, 1)
        self.model_source_buttons.addButton(self.local_radio, 2)
        model_source_layout.addWidget(self.download_radio)
        model_source_layout.addWidget(self.local_radio)
        
        # Local model path selection
        local_path_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setEnabled(self.local_radio.isChecked())
        
        # Set path if model was found
        if self.model_path:
            self.local_path_edit.setText(self.model_path)
            
        self.local_path_edit.setPlaceholderText("Select local model directory...")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setEnabled(self.local_radio.isChecked())
        self.browse_button.clicked.connect(self.browse_local_model)
        local_path_layout.addWidget(self.local_path_edit, 3)
        local_path_layout.addWidget(self.browse_button, 1)
        model_source_layout.addLayout(local_path_layout)
        
        # Connect radio button signals
        self.download_radio.toggled.connect(self.toggle_model_source)
        self.local_radio.toggled.connect(self.toggle_model_source)
        
        main_layout.addWidget(model_source_group)
        
        # Model selection (for download option)
        self.download_model_group = QGroupBox("Model Selection")
        download_model_layout = QVBoxLayout()
        self.download_model_group.setLayout(download_model_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"])
        self.model_combo.setCurrentText("small")  # Changed default to small for faster loading
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        download_model_layout.addLayout(model_layout)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda", "auto"])
        self.device_combo.setCurrentText("auto")
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        download_model_layout.addLayout(device_layout)
        
        # Precision selection
        precision_layout = QHBoxLayout()
        precision_label = QLabel("Precision:")
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["float16", "int8"])
        self.precision_combo.setCurrentText("int8")
        precision_layout.addWidget(precision_label)
        precision_layout.addWidget(self.precision_combo)
        download_model_layout.addLayout(precision_layout)
        
        # Enable/disable based on selection
        self.download_model_group.setEnabled(self.download_radio.isChecked())
        
        main_layout.addWidget(self.download_model_group)
        
        # Transcription options
        transcription_options_group = QGroupBox("Transcription Quality")
        transcription_options_layout = QVBoxLayout()
        transcription_options_group.setLayout(transcription_options_layout)
        
        # High quality mode checkbox
        self.high_quality_checkbox = QCheckBox("High Quality Mode (slower)")
        self.high_quality_checkbox.setToolTip("Enables more accurate but slower transcription parameters")
        self.high_quality_checkbox.setChecked(False)
        self.high_quality_checkbox.stateChanged.connect(self.toggle_high_quality)
        transcription_options_layout.addWidget(self.high_quality_checkbox)
        
        # Noise reduction checkbox
        self.noise_reduction_checkbox = QCheckBox("Noise Reduction")
        self.noise_reduction_checkbox.setToolTip("Apply audio preprocessing to reduce background noise")
        self.noise_reduction_checkbox.setChecked(True)
        self.noise_reduction_checkbox.stateChanged.connect(self.toggle_noise_reduction)
        transcription_options_layout.addWidget(self.noise_reduction_checkbox)
        
        # Voice Activity Detection (VAD) checkbox
        self.vad_checkbox = QCheckBox("Voice Activity Detection")
        self.vad_checkbox.setToolTip("Only process audio that contains speech")
        self.vad_checkbox.setChecked(True)
        self.vad_checkbox.stateChanged.connect(self.toggle_vad)
        transcription_options_layout.addWidget(self.vad_checkbox)
        
        # Context window size
        context_layout = QHBoxLayout()
        context_label = QLabel("Context Window Size:")
        self.context_slider = QSlider(Qt.Horizontal)
        self.context_slider.setRange(0, 5)
        self.context_slider.setValue(3)
        self.context_slider.setToolTip("Number of previous transcriptions to use as context")
        self.context_slider.valueChanged.connect(self.update_context_window)
        self.context_value_label = QLabel("3")
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_slider)
        context_layout.addWidget(self.context_value_label)
        transcription_options_layout.addLayout(context_layout)
        
        # Microphone sensitivity
        mic_sensitivity_layout = QHBoxLayout()
        mic_sensitivity_label = QLabel("Microphone Sensitivity:")
        self.mic_sensitivity_slider = QSlider(Qt.Horizontal)
        self.mic_sensitivity_slider.setRange(1, 20)  # 0.005 to 0.1 (scaled by 200)
        self.mic_sensitivity_slider.setValue(10)  # Default 0.05
        self.mic_sensitivity_slider.setToolTip("Adjust microphone sensitivity (threshold for speech detection)")
        self.mic_sensitivity_slider.valueChanged.connect(self.update_mic_sensitivity)
        self.mic_sensitivity_value = QLabel("5%")
        mic_sensitivity_layout.addWidget(mic_sensitivity_label)
        mic_sensitivity_layout.addWidget(self.mic_sensitivity_slider)
        mic_sensitivity_layout.addWidget(self.mic_sensitivity_value)
        
        # Add calibration button to mic sensitivity layout
        calibrate_button = QPushButton("Calibrate")
        calibrate_button.setToolTip("Auto-calibrate microphone based on room noise")
        calibrate_button.clicked.connect(self.calibrate_microphone)
        mic_sensitivity_layout.addWidget(calibrate_button)
        
        transcription_options_layout.addLayout(mic_sensitivity_layout)
        
        # Add to main layout after model selection group
        main_layout.addWidget(transcription_options_group)
        
        # Initial prompt for better transcription (replacing language settings group)
        prompt_group = QGroupBox("Transcription Context")
        prompt_layout = QVBoxLayout()
        prompt_group.setLayout(prompt_layout)
        
        # Explain that the app is English-only
        english_label = QLabel("This application is optimized for English speech recognition only.")
        english_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        prompt_layout.addWidget(english_label)
        
        # Initial prompt for better context
        prompt_layout_row = QHBoxLayout()
        prompt_label = QLabel("Initial Prompt:")
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("Optional: Provide context to guide transcription...")
        # Set a default prompt to avoid the "Thank you" issue
        self.prompt_edit.setText("I am testing speech recognition. I will say phrases like: testing one two three, hello world, this is a test.")
        prompt_layout_row.addWidget(prompt_label)
        prompt_layout_row.addWidget(self.prompt_edit)
        prompt_layout.addLayout(prompt_layout_row)
        
        # Add help text for prompt
        prompt_help = QLabel("Adding a prompt related to your topic can improve transcription accuracy.")
        prompt_help.setWordWrap(True)
        prompt_help.setStyleSheet("font-style: italic; color: #666666;")
        prompt_layout.addWidget(prompt_help)
        
        main_layout.addWidget(prompt_group)
        
        # Apply model settings button
        self.apply_button = QPushButton("Apply Settings")
        self.apply_button.clicked.connect(self.apply_model_settings)
        main_layout.addWidget(self.apply_button)
        
        # Transcription area
        transcription_label = QLabel("Last Transcription:")
        main_layout.addWidget(transcription_label)
        
        self.transcription_text = QLabel("")
        self.transcription_text.setWordWrap(True)
        self.transcription_text.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        self.transcription_text.setMinimumHeight(60)
        main_layout.addWidget(self.transcription_text)
        
        # Control options
        options_layout = QHBoxLayout()
        
        self.auto_type_checkbox = QCheckBox("Auto Type")
        self.auto_type_checkbox.setChecked(True)
        self.auto_type_checkbox.stateChanged.connect(self.toggle_auto_type)
        options_layout.addWidget(self.auto_type_checkbox)
        
        # Add debug checkbox
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setChecked(True)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug)
        options_layout.addWidget(self.debug_checkbox)
        
        # Add options layout to main layout
        main_layout.addLayout(options_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Start button
        self.start_button = QPushButton("Start Listening")
        self.start_button.clicked.connect(self.toggle_listening)
        button_layout.addWidget(self.start_button)
        
        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        main_layout.addLayout(button_layout)
        
        # Test typing button
        self.test_button = QPushButton("Test Typing")
        self.test_button.clicked.connect(self.test_typing)
        main_layout.addWidget(self.test_button)
        
        # Styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QComboBox, QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 1px;
            }
        """)
    
    def toggle_model_source(self):
        """Handle toggling between download and local model sources"""
        if self.download_radio.isChecked():
            self.local_path_edit.setEnabled(False)
            self.browse_button.setEnabled(False)
            self.download_model_group.setEnabled(True)
            self.model_path = None
        else:
            self.local_path_edit.setEnabled(True)
            self.browse_button.setEnabled(True)
            self.download_model_group.setEnabled(False)
            # Restore detected local model path if available
            if not self.local_path_edit.text() and find_local_model():
                self.model_path = find_local_model()
                self.local_path_edit.setText(self.model_path)
    
    def browse_local_model(self):
        """Open file dialog to select local model directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Model Directory", os.path.expanduser("~"))
        if directory:
            self.local_path_edit.setText(directory)
            self.model_path = directory
            print(f"Selected local model directory: {directory}")
    
    def update_audio_level(self, level):
        """Update the audio level progress bar"""
        # Scale the audio level to the progress bar
        # Typical speech audio levels are between 0 and 0.5
        scaled_level = min(int(level * 200), 100)
        self.audio_level_progress.setValue(scaled_level)
    
    def initialize_model(self):
        self.status_label.setText("Initializing...")
        
        # Set initial prompt
        initial_prompt = self.prompt_edit.text()
        
        # Determine if using local or downloadable model
        if self.local_radio.isChecked() and self.local_path_edit.text():
            model_path = self.local_path_edit.text()
            print(f"Initializing with local model at: {model_path}")
            self.audio_thread = AudioTranscriptionThread(
                device=self.device_combo.currentText(),
                compute_type=self.precision_combo.currentText(),
                model_path=model_path
            )
        else:
            model_size = self.model_combo.currentText()
            print(f"Initializing with model={model_size}, device={self.device_combo.currentText()}")
            self.audio_thread = AudioTranscriptionThread(
                model_size=model_size,
                device=self.device_combo.currentText(),
                compute_type=self.precision_combo.currentText()
            )
        
        # Set initial prompt if provided
        if initial_prompt:
            self.audio_thread.set_initial_prompt(initial_prompt)
        
        # Connect signals
        self.audio_thread.transcription_done.connect(self.update_transcription)
        self.audio_thread.status_update.connect(self.update_status)
        self.audio_thread.audio_level_update.connect(self.update_audio_level)
        
        # Set debug state
        self.audio_thread.debug = self.debug_checkbox.isChecked()
        
        self.status_label.setText("English model initialized. Ready to start.")
    
    def apply_model_settings(self):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
            self.start_button.setText("Start Listening")
            self.pause_button.setEnabled(False)
        
        self.initialize_model()
        self.status_label.setText("Settings applied. Ready to start.")
        
        # Apply transcription quality settings
        if self.audio_thread:
            self.audio_thread.set_high_quality_mode(self.high_quality_checkbox.isChecked())
            self.audio_thread.set_noise_reduction(self.noise_reduction_checkbox.isChecked())
            self.audio_thread.vad_enabled = self.vad_checkbox.isChecked()
            self.audio_thread.max_context_window = self.context_slider.value()
            self.audio_thread.energy_threshold = self.mic_sensitivity_slider.value() / 200
            
    def calibrate_microphone(self):
        """Auto-calibrate microphone by measuring background noise"""
        if not self.audio_thread:
            self.initialize_model()
            
        self.status_label.setText("Calibrating microphone... Please stay silent.")
        
        # Start a short recording to measure background noise
        try:
            # Record 2 seconds of audio
            duration = 2  # seconds
            recording = sd.rec(int(duration * self.audio_thread.sample_rate), 
                              samplerate=self.audio_thread.sample_rate, 
                              channels=1, dtype=np.float32)
            sd.wait()  # Wait until recording is finished
            
            # Calculate energy of background noise
            energy = np.sum(recording ** 2) / len(recording)
            
            # Set threshold to 2x the background noise
            threshold = min(max(energy * 2, 0.005), 0.1)
            
            # Update slider and audio thread
            slider_value = int(threshold * 200)
            self.mic_sensitivity_slider.setValue(slider_value)
            self.audio_thread.energy_threshold = threshold
            
            self.status_label.setText(f"Microphone calibrated. Threshold set to {threshold:.4f}")
            print(f"Microphone calibrated. Background noise: {energy:.6f}, Threshold: {threshold:.6f}")
            
        except Exception as e:
            self.status_label.setText(f"Calibration failed: {str(e)}")
            print(f"Calibration error: {e}")
    
    def toggle_listening(self):
        if not self.audio_thread:
            self.initialize_model()
        
        if self.audio_thread.isRunning():
            print("Stopping audio thread")
            self.audio_thread.stop()
            self.start_button.setText("Start Listening")
            self.pause_button.setEnabled(False)
        else:
            print("Starting audio thread")
            self.audio_thread.start()
            self.start_button.setText("Stop Listening")
            self.pause_button.setEnabled(True)
            self.pause_button.setText("Pause")
    
    def toggle_pause(self):
        if self.audio_thread and self.audio_thread.isRunning():
            paused = self.audio_thread.toggle_pause()
            self.pause_button.setText("Resume" if paused else "Pause")
            print(f"Transcription {'paused' if paused else 'resumed'}")
    
    def toggle_auto_type(self, state):
        if self.audio_thread:
            self.audio_thread.set_auto_type(state == Qt.Checked)
    
    def toggle_debug(self, state):
        if self.audio_thread:
            self.audio_thread.debug = state == Qt.Checked
            print(f"Debug mode {'enabled' if state == Qt.Checked else 'disabled'}")
    
    def test_typing(self):
        """Test if keyboard input works."""
        try:
            print("Testing keyboard input...")
            keyboard = Controller()
            time.sleep(1)  # Give time to focus on a text field
            keyboard.type("Test typing from Speech-to-Text app")
            self.status_label.setText("Test typing performed")
        except Exception as e:
            error_msg = f"Typing test error: {str(e)}"
            print(error_msg)
            self.status_label.setText(error_msg)
    
    def update_transcription(self, text):
        print(f"Transcribed: '{text}'")
        self.transcription_text.setText(text)
    
    def update_status(self, status):
        print(f"Status: {status}")
        self.status_label.setText(status)
    
    def toggle_high_quality(self, state):
        """Toggle high quality transcription mode"""
        enabled = state == Qt.Checked
        if self.audio_thread:
            self.audio_thread.set_high_quality_mode(enabled)
        self.update_status(f"High quality mode {'enabled' if enabled else 'disabled'}")
    
    def toggle_noise_reduction(self, state):
        """Toggle noise reduction preprocessing"""
        enabled = state == Qt.Checked
        if self.audio_thread:
            self.audio_thread.set_noise_reduction(enabled)
        self.update_status(f"Noise reduction {'enabled' if enabled else 'disabled'}")
    
    def toggle_vad(self, state):
        """Toggle voice activity detection"""
        enabled = state == Qt.Checked
        if self.audio_thread:
            self.audio_thread.vad_enabled = enabled
        self.update_status(f"Voice Activity Detection {'enabled' if enabled else 'disabled'}")
    
    def update_context_window(self, value):
        """Update the size of the context window"""
        self.context_value_label.setText(str(value))
        if self.audio_thread:
            self.audio_thread.max_context_window = value
        self.update_status(f"Context window size set to {value}")
    
    def update_mic_sensitivity(self, value):
        """Update the microphone sensitivity"""
        sensitivity = value / 200  # Scale back to 0.005 to 0.1
        if self.audio_thread:
            self.audio_thread.energy_threshold = sensitivity
        
        # Update the label to show percentage
        percentage = int((value / 20) * 100)
        self.mic_sensitivity_value.setText(f"{percentage}%")
        
        self.update_status(f"Microphone sensitivity set to {sensitivity:.3f}")
    
    def closeEvent(self, event):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechToTextApp()
    window.show()
    sys.exit(app.exec_()) 