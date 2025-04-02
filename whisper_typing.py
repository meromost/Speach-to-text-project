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
        
        # Audio processing parameters
        self.chunk_size = 8000  # Increased from default 4000
        self.audio_buffer = []  # Store audio chunks for processing
        self.buffer_max_size = 5  # Number of chunks to buffer before processing
        self.trigger_level = 0.01  # Minimum audio level to start processing
        self.language = "en"  # Default language
        self.auto_detect_language = False  # Whether to use language detection
        self.initial_prompt = ""  # Optional prompt to guide transcription
        
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


class SpeechToTextApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech to Text Typer")
        self.setMinimumSize(500, 550)
        
        # Initialize the audio thread
        self.audio_thread = None
        self.model_path = None
        
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
        self.download_radio.setChecked(True)
        self.model_source_buttons.addButton(self.download_radio, 1)
        self.model_source_buttons.addButton(self.local_radio, 2)
        model_source_layout.addWidget(self.download_radio)
        model_source_layout.addWidget(self.local_radio)
        
        # Local model path selection
        local_path_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setEnabled(False)
        self.local_path_edit.setPlaceholderText("Select local model directory...")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setEnabled(False)
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
        
        main_layout.addWidget(self.download_model_group)
        
        # Language and voice settings
        voice_settings_group = QGroupBox("Language Settings")
        voice_settings_layout = QVBoxLayout()
        voice_settings_group.setLayout(voice_settings_layout)
        
        # Language selection
        language_layout = QHBoxLayout()
        language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        
        # Add "Auto Detect" option
        self.language_combo.addItem("Auto Detect", "auto")
        
        # Add all supported languages with their codes
        language_names = {
            "en": "English", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
            "ja": "Japanese", "zh": "Chinese", "ru": "Russian", "ko": "Korean", "ar": "Arabic",
            "hi": "Hindi", "pt": "Portuguese", "tr": "Turkish", "pl": "Polish", "ca": "Catalan",
            "nl": "Dutch", "sv": "Swedish", "id": "Indonesian", "vi": "Vietnamese", "uk": "Ukrainian",
            "he": "Hebrew", "fa": "Persian", "el": "Greek", "th": "Thai", "hu": "Hungarian",
            "fi": "Finnish", "cs": "Czech", "da": "Danish", "ro": "Romanian", "no": "Norwegian",
            "sk": "Slovak", "bg": "Bulgarian", "hr": "Croatian", "lt": "Lithuanian", "sl": "Slovenian",
            "sr": "Serbian", "et": "Estonian", "lv": "Latvian"
        }
        
        # Add common languages first with friendly names
        for code, name in language_names.items():
            self.language_combo.addItem(name, code)
            
        # Add remaining languages with just their codes
        for code in [c for c in VALID_LANGUAGE_CODES if c not in language_names]:
            self.language_combo.addItem(code, code)
            
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        voice_settings_layout.addLayout(language_layout)
        
        # Initial prompt for better context
        prompt_layout = QHBoxLayout()
        prompt_label = QLabel("Initial Prompt:")
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("Optional: Provide context to guide transcription...")
        prompt_layout.addWidget(prompt_label)
        prompt_layout.addWidget(self.prompt_edit)
        voice_settings_layout.addLayout(prompt_layout)
        
        main_layout.addWidget(voice_settings_group)
        
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
        
        # Get selected language code
        language_code = self.language_combo.currentData()
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
        
        # Set language and prompt
        self.audio_thread.set_language(language_code)
        if initial_prompt:
            self.audio_thread.set_initial_prompt(initial_prompt)
        
        # Connect signals
        self.audio_thread.transcription_done.connect(self.update_transcription)
        self.audio_thread.status_update.connect(self.update_status)
        self.audio_thread.audio_level_update.connect(self.update_audio_level)
        
        # Set debug state
        self.audio_thread.debug = self.debug_checkbox.isChecked()
    
    def apply_model_settings(self):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
            self.start_button.setText("Start Listening")
            self.pause_button.setEnabled(False)
        
        self.initialize_model()
        self.status_label.setText("Settings applied. Ready to start.")
    
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
    
    def closeEvent(self, event):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechToTextApp()
    window.show()
    sys.exit(app.exec_()) 