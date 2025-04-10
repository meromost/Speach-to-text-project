import sys
import sounddevice as sd
import numpy as np
import queue
import threading
import time
import os
import math
from faster_whisper import WhisperModel
from pynput.keyboard import Controller
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QSlider, 
                            QCheckBox, QProgressBar, QStyle, QFileDialog, QRadioButton,
                            QButtonGroup, QLineEdit, QGroupBox, QTextEdit,
                            QFrame, QSizePolicy, QStackedWidget, QToolButton,
                            QLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPainter, QPen, QPainterPath, QTextCursor

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

# Color scheme
class DarkTheme:
    # Main colors
    BG_DARK = "#1E2124"  # Dark background
    BG_PANEL = "#2C2F33"  # Slightly lighter panels
    TEXT_PRIMARY = "#FFFFFF"  # White text
    TEXT_SECONDARY = "#B9BBBE"  # Light gray text
    ACCENT_PRIMARY = "#FF5722"  # Orange for primary buttons
    ACCENT_SECONDARY = "#3B82F6"  # Blue for visualizations and secondary elements
    
    # Button states
    BUTTON_HOVER = "#FF7043"  # Lighter orange for button hover
    BUTTON_PRESSED = "#E64A19"  # Darker orange for button press
    BUTTON_SECONDARY = "#2C3E50"  # Dark blue-gray for secondary buttons
    BUTTON_SECONDARY_HOVER = "#34495E"  # Lighter blue-gray
    
    # Borders and shadows
    BORDER_RADIUS = 12
    PANEL_RADIUS = 8

# Audio visualization class
class AudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 30) # Keep the smaller size
        self.bars = 8 # Fewer bars for compact UI
        self._levels = [0] * self.bars
        self.active = False
        
    def set_active(self, active):
        self.active = active
        if not active:
             self._levels = [0] * self.bars # Reset levels when inactive
        self.update()

    def update_levels(self, level):
        if not self.active:
            return
        
        # Scale the input level (0 to 1) to affect the visualization
        # Add some randomness based on level to make it dynamic
        import random
        for i in range(self.bars):
            base = level * (0.5 + 0.5 * abs(math.sin(time.time() * 5 + i * 0.8)))
            variation = random.uniform(-0.1, 0.1) * level
            self._levels[i] = max(0.05, min(0.95, base + variation))
        self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = width / (self.bars * 2)
        spacing = bar_width
        
        painter.setPen(Qt.NoPen)
        
        for i, level in enumerate(self._levels):
            if self.active:
                color = QColor(DarkTheme.ACCENT_SECONDARY)
            else:
                color = QColor(DarkTheme.ACCENT_SECONDARY).darker(150)
                
            painter.setBrush(color)
            
            x = i * (bar_width + spacing) + spacing
            bar_height = height * (level if self.active else 0.05) # Min height when inactive
            y = (height - bar_height) / 2 # Center vertically
            
            path = QPainterPath()
            path.addRoundedRect(x, y, bar_width, bar_height, 2, 2)
            painter.drawPath(path)

# Custom rounded button
class RoundedButton(QPushButton):
    def __init__(self, text, parent=None, primary=True):
        super().__init__(text, parent)
        self.primary = primary
        self.setFixedHeight(40)
        self.setMinimumWidth(80)
        
        if primary:
            # Use standard string formatting for clarity with CSS
            style = f'''
                QPushButton {{
                    background-color: {DarkTheme.ACCENT_PRIMARY};
                    color: {DarkTheme.TEXT_PRIMARY};
                    border: none;
                    border-radius: {DarkTheme.BORDER_RADIUS}px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DarkTheme.BUTTON_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {DarkTheme.BUTTON_PRESSED};
                }}
            '''
            self.setStyleSheet(style)
        else:
            style = f'''
                QPushButton {{
                    background-color: {DarkTheme.BUTTON_SECONDARY};
                    color: {DarkTheme.TEXT_PRIMARY};
                    border: none;
                    border-radius: {DarkTheme.BORDER_RADIUS}px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DarkTheme.BUTTON_SECONDARY_HOVER};
                }}
            '''
            self.setStyleSheet(style)

# Custom rounded panel
class RoundedPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkTheme.BG_PANEL};
                border-radius: {DarkTheme.PANEL_RADIUS}px;
                border: none;
            }}
        """)

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
        self.setWindowTitle("Speech-to-Text Writer")
        # Set initial size for normal mode, store minimized size
        self.normal_size = QSize(800, 600) # Default normal size
        self.minimized_size = QSize(250, 150) # Compact size
        self.resize(self.normal_size)
        self.is_minimized_ui = False # Start with normal UI

        # --- Start: Apply DarkTheme Styles (Keep existing styles) ---
        self.setStyleSheet(f"""
            QMainWindow {{ /* ... existing styles ... */ }}
            QLabel {{ /* ... existing styles ... */ }}
            QComboBox {{ /* ... existing styles ... */ }}
            /* ... other existing styles ... */
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ /* ... existing styles ... */ }}
        """)
        # --- End: Apply DarkTheme Styles ---

        # --- Central Widget and Stacked Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout(self.central_widget)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget()
        self.base_layout.addWidget(self.stacked_widget)
        # --- End Central Widget Setup ---

        # Initialize transcription thread (SINGLE instance)
        self.transcription_thread = AudioTranscriptionThread()
        self.transcription_thread.transcription_done.connect(self.update_transcription)
        self.transcription_thread.status_update.connect(self.update_status)
        self.transcription_thread.audio_level_update.connect(self.update_audio_level)
        
        self.is_listening = False
        self.is_paused = False

        # --- Setup both UI states and add to StackedWidget ---
        self.normal_ui_widget = QWidget() # Create container widget for normal UI
        self.setup_dark_ui() # Populate the normal_ui_widget (will also create main_layout now)
        self.stacked_widget.addWidget(self.normal_ui_widget)
        
        self.minimized_ui_widget = QWidget() # Create container widget for minimized UI
        self.setup_minimized_ui() # Populate the minimized_ui_widget
        self.stacked_widget.addWidget(self.minimized_ui_widget)
        # --- End UI Setup ---
        
        self.stacked_widget.setCurrentIndex(0)
        self.initialize_model()
        print("__init__ completed.")


    def setup_dark_ui(self):
        # --- Create and assign main layout for normal_ui_widget HERE ---
        self.main_layout = QVBoxLayout(self.normal_ui_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20) # Normal margins
        self.main_layout.setSpacing(15)
        # --- End Layout Creation ---

        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("Speech-to-Text Writer")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        header_layout.addWidget(title_label, 0, Qt.AlignVCenter) # Align title vertically
        header_layout.addStretch()

        # --- Add UI Toggle Button --- 
        self.toggle_ui_button = QToolButton()
        # Using a different standard icon that might be more visible
        self.toggle_ui_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown)) 
        self.toggle_ui_button.setIconSize(QSize(18, 18))
        self.toggle_ui_button.setFixedSize(30, 30)
        # Add some styling to make it stand out
        self.toggle_ui_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {DarkTheme.BUTTON_SECONDARY};
                border: none;
                padding: 5px;
                border-radius: {DarkTheme.BORDER_RADIUS // 2}px; /* Half main radius */
            }}
            QToolButton:hover {{
                 background-color: {DarkTheme.BUTTON_SECONDARY_HOVER};
            }}
        """)
        self.toggle_ui_button.setToolTip("Toggle Compact/Full UI")
        self.toggle_ui_button.clicked.connect(self.toggle_ui_mode)
        
        # Add Spacing before button and align vertically
        header_layout.addSpacing(10) # Add 10px space before the button
        header_layout.addWidget(self.toggle_ui_button, 0, Qt.AlignVCenter) # Add button, align vertically center
        # --- End Add UI Toggle Button ---

        # Note: self.main_layout is now the layout for normal_ui_widget
        self.main_layout.addLayout(header_layout)

        # --- Main Content Area (Split Layout) ---
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)

        # --- Left Panel (Controls) ---
        left_panel = RoundedPanel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(15, 15, 15, 15)

        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-style: italic;")
        self.status_label.setWordWrap(True)
        left_layout.addWidget(self.status_label)

        model_group = QGroupBox("Model Configuration")
        model_group.setObjectName("Model Configuration")
        model_layout = QVBoxLayout(model_group)
        self.model_layout = model_layout # Store layout directly
        model_layout.setSpacing(10)

        self.model_source_group = QButtonGroup(self)
        self.huggingface_rb = QRadioButton("Hugging Face Model")
        self.local_model_rb = QRadioButton("Local Model")
        self.model_source_group.addButton(self.huggingface_rb, 1)
        self.model_source_group.addButton(self.local_model_rb, 2)
        self.huggingface_rb.setChecked(True)
        self.huggingface_rb.toggled.connect(self.toggle_model_source)
        model_source_layout = QHBoxLayout()
        model_source_layout.addWidget(self.huggingface_rb)
        model_source_layout.addWidget(self.local_model_rb)
        model_layout.addLayout(model_source_layout)

        self.hf_model_layout = QHBoxLayout()
        self.model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["distil-large-v3", "large-v3", "large-v2", "medium.en", "small.en", "base.en", "tiny.en"])
        self.hf_model_layout.addWidget(self.model_label)
        self.hf_model_layout.addWidget(self.model_combo)
        model_layout.addLayout(self.hf_model_layout)

        self.local_model_layout = QHBoxLayout()
        self.local_model_label = QLabel("Path:")
        self.local_model_path_edit = QLineEdit()
        self.local_model_path_edit.setPlaceholderText("Path to local model directory")
        self.local_model_path_edit.setReadOnly(True)
        self.browse_button = RoundedButton("...", primary=False)
        self.browse_button.setFixedSize(40, 30)
        # Corrected stylesheet application for browse button
        browse_base_style = self.browse_button.styleSheet()
        self.browse_button.setStyleSheet(f'QPushButton {{ padding: 5px; }} {browse_base_style}')
        self.browse_button.clicked.connect(self.browse_local_model)
        self.local_model_layout.addWidget(self.local_model_label)
        self.local_model_layout.addWidget(self.local_model_path_edit)
        self.local_model_layout.addWidget(self.browse_button)
        # This layout is added/removed dynamically by toggle_model_source

        device_layout = QHBoxLayout()
        self.device_label = QLabel("Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        device_layout.addWidget(self.device_label)
        device_layout.addWidget(self.device_combo)
        model_layout.addLayout(device_layout)

        compute_layout = QHBoxLayout()
        self.compute_label = QLabel("Compute Type:")
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "float16", "float32"])
        compute_layout.addWidget(self.compute_label)
        compute_layout.addWidget(self.compute_combo)
        model_layout.addLayout(compute_layout)

        self.apply_button = RoundedButton("Apply Settings", primary=False)
        self.apply_button.clicked.connect(self.apply_model_settings)
        model_layout.addWidget(self.apply_button, alignment=Qt.AlignCenter)

        left_layout.addWidget(model_group)

        lang_group = QGroupBox("Transcription Settings")
        lang_group.setObjectName("Transcription Settings")
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(10)

        lang_select_layout = QHBoxLayout()
        self.language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Auto Detect", None) # User data is None for auto
        for code in VALID_LANGUAGE_CODES:
            self.language_combo.addItem(code, code) # User data is the language code
        self.language_combo.setCurrentText("en")
        lang_select_layout.addWidget(self.language_label)
        lang_select_layout.addWidget(self.language_combo)
        lang_layout.addLayout(lang_select_layout)

        prompt_layout = QHBoxLayout()
        self.prompt_label = QLabel("Prompt:")
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("Optional initial prompt...")
        prompt_layout.addWidget(self.prompt_label)
        prompt_layout.addWidget(self.prompt_edit)
        lang_layout.addLayout(prompt_layout)

        self.apply_lang_button = RoundedButton("Apply Language/Prompt", primary=False)
        self.apply_lang_button.clicked.connect(self.apply_language_and_prompt)
        lang_layout.addWidget(self.apply_lang_button, alignment=Qt.AlignCenter)

        left_layout.addWidget(lang_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)

        self.auto_type_checkbox = QCheckBox("Auto-type recognized text")
        self.auto_type_checkbox.setChecked(True)
        self.auto_type_checkbox.stateChanged.connect(self.toggle_auto_type)
        options_layout.addWidget(self.auto_type_checkbox)

        self.debug_checkbox = QCheckBox("Enable Debug Logging")
        self.debug_checkbox.setChecked(False) # Default to off
        self.debug_checkbox.stateChanged.connect(self.toggle_debug)
        options_layout.addWidget(self.debug_checkbox)

        left_layout.addWidget(options_group)

        self.test_button = RoundedButton("Test Typing", primary=False)
        self.test_button.clicked.connect(self.test_typing)
        left_layout.addWidget(self.test_button)

        left_layout.addStretch()
        main_content_layout.addWidget(left_panel, 1)

        # --- Right Panel (Transcription & Controls) ---
        right_panel = RoundedPanel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(15, 15, 15, 15)

        self.transcription_display = QTextEdit()
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setFont(QFont("Arial", 11))
        self.transcription_display.setPlaceholderText("Recognized text will appear here...")
        right_layout.addWidget(self.transcription_display, 1)

        viz_layout = QHBoxLayout()
        viz_layout.addWidget(QLabel("Mic Level:"))
        self.audio_visualizer = AudioVisualizer()
        viz_layout.addWidget(self.audio_visualizer, 1)
        right_layout.addLayout(viz_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.start_button = RoundedButton("Start Listening", primary=True)
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.toggle_listening)

        self.pause_button = RoundedButton("Pause", primary=False)
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        right_layout.addLayout(button_layout)

        main_content_layout.addWidget(right_panel, 2)

        self.main_layout.addLayout(main_content_layout, 1)

        self.toggle_model_source() # Initial setup of model source display
        print("setup_dark_ui completed.")


    def toggle_model_source(self):
        # --- Keep the NEW logic added previously for handling layouts ---
        use_huggingface = self.huggingface_rb.isChecked()

        def safe_remove_layout(layout):
            # If layout is not None and has a parent widget/layout
            if layout is not None and layout.parent() is not None:
                # Remove widgets first
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                    else:
                        # If item is a layout, recursively remove it
                        sub_layout = item.layout()
                        if sub_layout is not None:
                            safe_remove_layout(sub_layout)
                # After removing items, remove the layout itself from its parent
                parent = layout.parent()
                if parent is not None:
                     # Check if parent is a layout or widget before removing
                     if isinstance(parent, QLayout): 
                         parent.removeItem(layout)
                     elif isinstance(parent, QWidget):
                         # Widgets don't directly remove layouts, often just deleting is enough
                         # Or assume the layout was added to the widget's own layout
                         if parent.layout() is layout: # If it's the widget's main layout
                             # Should not typically remove the main layout this way
                             print("Warning: Attempting to remove widget's main layout in safe_remove_layout")
                         elif parent.layout() is not None: # If widget has a layout, remove item from it
                              parent.layout().removeItem(layout)
                     else: 
                         print(f"Warning: Unknown parent type {type(parent)} in safe_remove_layout")

                # Setting parent to None might not be needed after removeItem/deletion
            elif layout is not None:
                print("Warning: safe_remove_layout called on layout with no parent.")

        # Use the stored layout reference
        model_group_layout = self.model_layout 

        if use_huggingface:
            safe_remove_layout(self.local_model_layout)
            if self.hf_model_layout.parent() is None:
                 model_group_layout.insertLayout(1, self.hf_model_layout) # Insert HF layout

            self.local_model_path_edit.clear()
            if self.transcription_thread: # Update thread path correctly
                 self.transcription_thread.model_path = None
        else:
            safe_remove_layout(self.hf_model_layout)
            if self.local_model_layout.parent() is None:
                 model_group_layout.insertLayout(1, self.local_model_layout) # Insert Local layout

            found_path = find_local_model() # Use helper function
            if found_path:
                self.local_model_path_edit.setText(found_path)
                if self.transcription_thread:
                    self.transcription_thread.model_path = found_path
            else:
                 self.local_model_path_edit.setPlaceholderText("No local model found, please browse.")


    def browse_local_model(self):
        # --- Keep the NEW logic added previously ---
        dir_path = QFileDialog.getExistingDirectory(self, "Select Local Model Directory", ".")
        if dir_path:
            # ... (keep existing validation and path setting logic) ...
            if os.path.exists(os.path.join(dir_path, "model.bin")) and \
               os.path.exists(os.path.join(dir_path, "config.json")):
                 self.local_model_path_edit.setText(dir_path)
                 if self.transcription_thread:
                    self.transcription_thread.model_path = dir_path
                    print(f"Set local model path: {dir_path}") # Debug
            else:
                self.status_label.setText("Error: Selected directory doesn't look like a valid model folder.")
                print("Selected directory missing model.bin or config.json") # Debug


    def update_audio_level(self, level):
        # Update BOTH visualizers
        scaled_level_for_viz = level * 5
        if hasattr(self, 'audio_visualizer'):
            self.audio_visualizer.update_levels(scaled_level_for_viz)
        if hasattr(self, 'min_audio_visualizer'): # Update minimized one too
            self.min_audio_visualizer.update_levels(scaled_level_for_viz)


    def initialize_model(self):
        # --- CORRECTED: Use self.transcription_thread and new UI names ---
        self.status_label.setText("Status: Initializing model...")
        print("Initializing model (via initialize_model)...") # Debug

        # Stop existing thread if running (shouldn't be on first init, but good practice)
        if self.transcription_thread.isRunning():
             print("Stopping existing thread before initializing...") # Debug
             self.transcription_thread.stop()

        # Apply settings from UI to the existing thread instance
        self.apply_model_settings(initialize=True) # Pass flag to indicate initialization
        self.apply_language_and_prompt() # Apply language/prompt settings

        self.status_label.setText("Status: Model initialized. Ready.")
        print("Model initialization complete.") # Debug


    def apply_model_settings(self, initialize=False):
        # --- CORRECTED: Update self.transcription_thread, use new UI names ---
        if not initialize and self.transcription_thread.isRunning():
            print("Stopping running thread before applying settings...") # Debug
            self.toggle_listening() # Stop listening cleanly

        # Determine model source and path/size
        if self.huggingface_rb.isChecked():
            model_size = self.model_combo.currentText()
            model_path = None
            print(f"Applying settings: HF Model={model_size}") # Debug
        else:
            model_size = None
            model_path = self.local_model_path_edit.text()
            if not model_path or not os.path.isdir(model_path):
                self.status_label.setText("Error: Invalid or missing local model path.")
                print("Error: Invalid local model path.") # Debug
                return
            print(f"Applying settings: Local Model Path={model_path}") # Debug

        device = self.device_combo.currentText()
        compute_type = self.compute_combo.currentText() # Use compute_combo

        print(f"Applying settings: Device={device}, Compute Type={compute_type}") # Debug

        # Update the *existing* thread instance
        self.transcription_thread.update_model(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            model_path=model_path
        )
        
        if not initialize: # Don't show this during initial setup
            self.status_label.setText("Status: Model settings applied. Reloading model...")
            print("Model settings applied, reload triggered in thread.") # Debug


    def apply_language_and_prompt(self):
         # --- CORRECTED: Update self.transcription_thread ---
         language = self.language_combo.currentData() if self.language_combo.currentData() else self.language_combo.currentText() # Handle "Auto Detect"
         prompt = self.prompt_edit.text()
         
         lang_display = language if language else "auto-detect" # For status message
         print(f"Applying language: {lang_display}, Prompt: '{prompt}'") # Debug
         
         self.transcription_thread.set_language(language) # Pass the actual code or None
         self.transcription_thread.set_initial_prompt(prompt)
         
         self.status_label.setText(f"Status: Language set to '{lang_display}'. Prompt updated.")


    def toggle_listening(self):
        # --- CORRECTED: Use self.transcription_thread and manage state ---
        if not self.is_listening:
            # Start listening
            self.is_listening = True
            self.is_paused = False
            # --- Update BOTH sets of buttons --- 
            # Normal UI buttons
            self.start_button.setText("Stop Listening")
            self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
            self.start_button.setToolTip("Stop Listening")
            self.pause_button.setEnabled(True)
            self.pause_button.setText("Pause")
            self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.pause_button.setToolTip("Pause")
            # Minimized UI buttons
            self.min_start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
            self.min_start_button.setToolTip("Stop Listening")
            self.min_pause_button.setEnabled(True)
            self.min_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.min_pause_button.setToolTip("Pause")
            # --- End Button Updates ---
            # Disable settings groups (only exist in normal UI)
            self.findChild(QGroupBox, "Model Configuration").setEnabled(False)
            self.findChild(QGroupBox, "Transcription Settings").setEnabled(False)
            self.status_label.setText("Status: Starting transcription...")
            self.min_status_label.setText("Listening...") # Update minimized status
            print("Starting transcription thread...") # Debug
            self.transcription_thread.start()
            # --- Update BOTH visualizers ---
            self.audio_visualizer.set_active(True)
            self.min_audio_visualizer.set_active(True)
            # --- End Visualizer Updates ---
        else:
            # Stop listening
            self.is_listening = False
            print("Stopping transcription thread...") # Debug
            self.transcription_thread.stop()
            # --- Update BOTH sets of buttons --- 
            # Normal UI buttons
            self.start_button.setText("Start Listening")
            self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.start_button.setToolTip("Start Listening")
            self.pause_button.setEnabled(False)
            self.pause_button.setText("Pause")
            self.pause_button.setToolTip("Pause")
            # Minimized UI buttons
            self.min_start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.min_start_button.setToolTip("Start Listening")
            self.min_pause_button.setEnabled(False)
            self.min_pause_button.setToolTip("Pause")
            # --- End Button Updates ---
            # Re-enable settings groups
            self.findChild(QGroupBox, "Model Configuration").setEnabled(True)
            self.findChild(QGroupBox, "Transcription Settings").setEnabled(True)
            self.status_label.setText("Status: Stopped.")
            self.min_status_label.setText("Stopped") # Update minimized status
            # --- Update BOTH visualizers ---
            self.audio_visualizer.set_active(False)
            self.min_audio_visualizer.set_active(False)
            # --- End Visualizer Updates ---


    def toggle_pause(self):
        # --- CORRECTED: Use self.transcription_thread and manage state ---
        if not self.is_listening: # Can only pause if listening
            return

        self.is_paused = self.transcription_thread.toggle_pause() # Call method on the correct thread
        
        if self.is_paused:
            # --- Update BOTH sets of buttons --- 
            self.pause_button.setText("Resume")
            self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.pause_button.setToolTip("Resume")
            self.min_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.min_pause_button.setToolTip("Resume")
            # --- End Button Updates ---
            self.status_label.setText("Status: Paused.")
            self.min_status_label.setText("Paused") # Update minimized status
            # --- Update BOTH visualizers ---
            self.audio_visualizer.set_active(False)
            self.min_audio_visualizer.set_active(False)
            # --- End Visualizer Updates ---
            print("Transcription paused.") # Debug
        else:
            # --- Update BOTH sets of buttons --- 
            self.pause_button.setText("Pause")
            self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.pause_button.setToolTip("Pause")
            self.min_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.min_pause_button.setToolTip("Pause")
            # --- End Button Updates ---
            self.status_label.setText("Status: Resumed Listening...")
            self.min_status_label.setText("Listening...") # Update minimized status
            # --- Update BOTH visualizers ---
            self.audio_visualizer.set_active(True)
            self.min_audio_visualizer.set_active(True)
            # --- End Visualizer Updates ---
            print("Transcription resumed.") # Debug


    def toggle_auto_type(self, state):
        # --- CORRECTED: Update self.transcription_thread ---
        enabled = state == Qt.Checked
        self.transcription_thread.set_auto_type(enabled)
        print(f"Auto-type {'enabled' if enabled else 'disabled'}") # Debug


    def toggle_debug(self, state):
         # --- CORRECTED: Update self.transcription_thread ---
        enabled = state == Qt.Checked
        self.transcription_thread.debug = enabled
        print(f"Debug logging {'enabled' if enabled else 'disabled'}") # Debug


    def test_typing(self):
        # --- CORRECTED: Use self.transcription_thread.keyboard ---
        self.status_label.setText("Status: Testing keyboard typing...")
        test_text = " The quick brown fox jumps over the lazy dog. 1234567890 !@#$%^&*()_+ "
        try:
            print("Testing keyboard input...") # Debug
            time.sleep(1) 
            # Use the keyboard controller from the thread instance
            self.transcription_thread.keyboard.type(test_text) 
            self.status_label.setText("Status: Typing test complete.")
            print("Typing test complete.") # Debug
        except Exception as e:
            error_msg = f"Status: Error during typing test: {e}"
            self.status_label.setText(error_msg)
            print(error_msg) # Debug


    def update_transcription(self, text):
        # --- CORRECTED: Use self.transcription_display and QTextCursor ---
        # Append text to the QTextEdit display
        cursor = self.transcription_display.textCursor() # Get cursor
        cursor.movePosition(QTextCursor.End) # Move to end
        self.transcription_display.setTextCursor(cursor) # Set cursor
        self.transcription_display.insertPlainText(text + " ") # Insert text
        self.transcription_display.ensureCursorVisible() # Scroll to end
        # print(f"UI Updated: '{text}'") # Debug (can be noisy)


    def update_status(self, status):
        # Update BOTH status labels
        self.status_label.setText(f"Status: {status}")
        if hasattr(self, 'min_status_label'): # Check if minimized UI is setup
             # Keep minimized status brief
             if "Error" in status:
                 self.min_status_label.setText("Error")
             elif "Loading model" in status:
                 self.min_status_label.setText("Loading...")
             elif "successfully" in status:
                 self.min_status_label.setText("Ready")
             elif "Listening" in status or "Resumed" in status:
                 self.min_status_label.setText("Listening...")
             elif "Paused" in status:
                 self.min_status_label.setText("Paused")
             elif "Stopped" in status:
                  self.min_status_label.setText("Stopped")
             else:
                 # Fallback for other statuses
                 short_status = status.split('.')[0] # Take first part
                 self.min_status_label.setText(short_status[:15]) # Limit length
        print(f"Status Update: {status}") # Also print for clarity


    def closeEvent(self, event):
        # --- CORRECTED: Stop self.transcription_thread ---
        print("Close event triggered.") # Debug
        if self.transcription_thread.isRunning():
            print("Stopping transcription thread on close...") # Debug
            self.transcription_thread.stop()
        event.accept()
        print("Application closing.") # Debug

    # --- ADDED: setup_minimized_ui method --- 
    def setup_minimized_ui(self):
        minimized_layout = QVBoxLayout(self.minimized_ui_widget) # Layout for minimized_ui_widget
        minimized_layout.setContentsMargins(10, 10, 10, 10) # Tighter margins
        minimized_layout.setSpacing(8)

        # Panel for background
        min_panel = RoundedPanel(self.minimized_ui_widget)
        min_panel_layout = QVBoxLayout(min_panel)
        min_panel_layout.setContentsMargins(10, 10, 10, 10)
        min_panel_layout.setSpacing(8)
        minimized_layout.addWidget(min_panel)

        # Header Row (Visualizer and Toggle Button)
        min_header_layout = QHBoxLayout()
        
        # Use a *separate* visualizer instance for the minimized UI
        self.min_audio_visualizer = AudioVisualizer()
        min_header_layout.addWidget(self.min_audio_visualizer, 1)
        
        min_header_layout.addSpacing(8) # Add 8px space here

        # --- Update Minimized Toggle Button ---
        self.min_toggle_ui_button = QToolButton() # Store reference
        self.min_toggle_ui_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.min_toggle_ui_button.setIconSize(QSize(18, 18))
        self.min_toggle_ui_button.setFixedSize(30, 30)
        self.min_toggle_ui_button.setStyleSheet(f"""
            QToolButton {{
                 background-color: {DarkTheme.BUTTON_SECONDARY};
                 border: none;
                 padding: 5px;
                 border-radius: {DarkTheme.BORDER_RADIUS // 2}px;
            }}
             QToolButton:hover {{
                 background-color: {DarkTheme.BUTTON_SECONDARY_HOVER};
            }}
        """)
        self.min_toggle_ui_button.setToolTip("Toggle Compact/Full UI")
        self.min_toggle_ui_button.clicked.connect(self.toggle_ui_mode)
        min_header_layout.addWidget(self.min_toggle_ui_button)
        # --- End Update Minimized Toggle Button ---
        min_panel_layout.addLayout(min_header_layout)

        # Control Buttons Row (Start/Stop and Pause)
        min_button_layout = QHBoxLayout()
        min_button_layout.setSpacing(8)
        
        # Use *separate* button instances for the minimized UI
        # Link them to the SAME toggle_listening/toggle_pause methods
        self.min_start_button = RoundedButton("", primary=True) # Text set dynamically
        self.min_start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.min_start_button.setFixedSize(40, 40) # Make buttons square-ish
        self.min_start_button.setIconSize(QSize(20, 20))
        self.min_start_button.setToolTip("Start Listening")
        self.min_start_button.clicked.connect(self.toggle_listening) # Connect to logic
        
        self.min_pause_button = RoundedButton("", primary=False)
        self.min_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.min_pause_button.setFixedSize(40, 40)
        self.min_pause_button.setIconSize(QSize(20, 20))
        self.min_pause_button.setEnabled(False)
        self.min_pause_button.setToolTip("Pause")
        self.min_pause_button.clicked.connect(self.toggle_pause) # Connect to logic
        
        min_button_layout.addStretch()
        min_button_layout.addWidget(self.min_start_button)
        min_button_layout.addWidget(self.min_pause_button)
        min_button_layout.addStretch()
        min_panel_layout.addLayout(min_button_layout)
        
        # Minimized status label (Optional, maybe remove for space)
        self.min_status_label = QLabel("Ready")
        self.min_status_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 9pt;")
        self.min_status_label.setAlignment(Qt.AlignCenter)
        min_panel_layout.addWidget(self.min_status_label)
        
        print("setup_minimized_ui completed.") # Debug
    # --- END ADDED: setup_minimized_ui ---

    # --- ADDED: toggle_ui_mode method --- 
    def toggle_ui_mode(self):
        if self.is_minimized_ui:
            # Switch to normal UI
            self.stacked_widget.setCurrentIndex(0)
            self.is_minimized_ui = False
            # Change button icon for the now visible button
            self.toggle_ui_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
            # --- Restore Resizing Logic --- 
            self.setFixedSize(QSize()) # Remove fixed size constraint
            self.setMinimumSize(self.normal_size) # Restore minimum size
            self.resize(self.normal_size) # Resize to stored normal size
            self.normal_ui_widget.layout().setContentsMargins(20, 20, 20, 20) # Restore normal margins
            self.base_layout.setContentsMargins(0,0,0,0) # Ensure base has no margins
            # --- End Resizing Logic --- 
            print("Switched to Normal UI")
        else:
            # Switch to minimized UI
            self.stacked_widget.setCurrentIndex(1)
            self.is_minimized_ui = True
            # Change button icon for the now visible button
            self.min_toggle_ui_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
            # --- Restore Resizing Logic --- 
            self.normal_size = self.size() # Store current size before minimizing
            self.setMinimumSize(QSize(0,0)) # Allow shrinking
            self.resize(self.minimized_size) # Resize to compact dimensions
            self.setFixedSize(self.minimized_size) # Fix the size
            self.minimized_ui_widget.layout().setContentsMargins(10, 10, 10, 10) # Apply minimized margins
            self.base_layout.setContentsMargins(0,0,0,0) # Ensure base has no margins
            # --- End Resizing Logic --- 
            print("Switched to Minimized UI")
    # --- END ADDED: toggle_ui_mode ---

# --- Main execution block (remains the same) ---
if __name__ == '__main__':
    app = QApplication(sys.argv) # Added missing QApplication instance
    # ... (keep existing __main__ block) ...
    main_win = SpeechToTextApp()
    main_win.show()
    sys.exit(app.exec_()) 