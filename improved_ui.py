import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QSlider, 
                            QCheckBox, QProgressBar, QStyle, QFileDialog, QRadioButton,
                            QButtonGroup, QLineEdit, QGroupBox, QTextEdit, QScrollArea,
                            QSplitter, QFrame, QListWidget, QListWidgetItem, QToolButton)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap

# Custom styles and colors
class StyleSheet:
    # Color scheme
    PRIMARY = "#1976D2"
    PRIMARY_HOVER = "#1565C0"
    PRIMARY_ACTIVE = "#0D47A1"
    SECONDARY = "#00ACC1"
    SECONDARY_HOVER = "#0097A7"
    SECONDARY_ACTIVE = "#00838F"
    
    BG_LIGHT = "#F5F7FA"
    PANEL_BG = "#FFFFFF"
    PANEL_BG_ALT = "#F1F3F5"
    
    TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#6B7280"
    TEXT_INACTIVE = "#9CA3AF"
    
    SUCCESS = "#10B981"
    WARNING = "#F59E0B" 
    ERROR = "#EF4444"
    INFO = "#3B82F6"
    
    BORDER = "#D1D5DB"
    FOCUS_BORDER = "#3B82F6"
    
    # Main application stylesheet
    MAIN_STYLE = f"""
        QMainWindow {{
            background-color: {BG_LIGHT};
        }}
        QLabel {{
            color: {TEXT_PRIMARY};
        }}
        QLabel[heading=true] {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 5px;
            padding-bottom: 2px;
            border-bottom: 1px solid {BORDER};
        }}
        QPushButton {{
            background-color: {PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_ACTIVE};
        }}
        QPushButton[secondary=true] {{
            background-color: {SECONDARY};
        }}
        QPushButton[secondary=true]:hover {{
            background-color: {SECONDARY_HOVER};
        }}
        QPushButton[secondary=true]:pressed {{
            background-color: {SECONDARY_ACTIVE};
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INACTIVE};
        }}
        QGroupBox {{
            background-color: {PANEL_BG};
            border-radius: 6px;
            border: 1px solid {BORDER};
            margin-top: 16px;
            font-weight: bold;
            padding-top: 22px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            color: {TEXT_PRIMARY};
        }}
        QLineEdit, QComboBox, QTextEdit {{
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 6px;
            background-color: {PANEL_BG};
        }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
            border: 1px solid {FOCUS_BORDER};
        }}
        QProgressBar {{
            border: 1px solid {BORDER};
            border-radius: 4px;
            text-align: center;
            background-color: {PANEL_BG_ALT};
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY};
            border-radius: 3px;
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {BORDER};
            height: 6px;
            background: {PANEL_BG_ALT};
            margin: 0px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {PRIMARY};
            border: none;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::sub-page:horizontal {{
            background: {PRIMARY};
            border-radius: 3px;
        }}
        QCheckBox {{
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {BORDER};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {PRIMARY};
            border: 1px solid {PRIMARY};
            image: url(check.png);
        }}
        QRadioButton {{
            spacing: 5px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {BORDER};
            border-radius: 9px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {PRIMARY};
            border: 1px solid {PRIMARY};
            width: 10px;
            height: 10px;
            border-radius: 5px;
        }}
        QListWidget {{
            border: 1px solid {BORDER};
            border-radius: 4px;
            background-color: {PANEL_BG};
        }}
        QListWidget::item {{
            padding: 5px;
            border-bottom: 1px solid {PANEL_BG_ALT};
        }}
        QListWidget::item:selected {{
            background-color: {PRIMARY};
            color: white;
        }}
    """

class ImprovedSpeechToTextApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech to Text Typer")
        self.setMinimumSize(900, 700)
        
        # Apply stylesheet
        self.setStyleSheet(StyleSheet.MAIN_STYLE)
        
        # Initialize central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create header
        self.setup_header()
        
        # Create splitter for top and bottom sections
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.main_splitter)
        
        # Create top and bottom containers
        self.top_container = QWidget()
        self.bottom_container = QWidget()
        self.main_splitter.addWidget(self.top_container)
        self.main_splitter.addWidget(self.bottom_container)
        
        # Set up layouts
        self.top_layout = QHBoxLayout(self.top_container)
        self.bottom_layout = QHBoxLayout(self.bottom_container)
        
        # Create the four main panels
        self.setup_transcription_panel()
        self.setup_controls_panel()
        self.setup_model_settings_panel()
        self.setup_language_panel()
        self.setup_status_panel()
        self.setup_options_panel()
        
        # Create status bar
        self.statusBar().showMessage("Ready to transcribe. Click START or press Alt+S to begin")
        
        # Set up timer for audio level simulation (will be replaced with actual audio data)
        self.audio_timer = QTimer()
        self.audio_timer.timeout.connect(self.update_audio_level)
        self.audio_timer.start(100)
        
    def setup_header(self):
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("SPEECH-TO-TEXT TYPER")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title_label)
        self.main_layout.addLayout(header_layout)
    
    def setup_transcription_panel(self):
        # Create transcription group
        transcription_group = QGroupBox("📝 TRANSCRIPTION")
        transcription_layout = QVBoxLayout()
        transcription_group.setLayout(transcription_layout)
        
        # Transcription text area
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setPlaceholderText("Transcribed text will appear here...")
        self.transcription_text.setMinimumHeight(150)
        
        transcription_layout.addWidget(self.transcription_text)
        
        # Add to top layout
        self.top_layout.addWidget(transcription_group)
    
    def setup_controls_panel(self):
        # Create controls group
        controls_group = QGroupBox("🎛️ CONTROLS")
        controls_layout = QVBoxLayout()
        controls_group.setLayout(controls_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Start button
        self.start_button = QPushButton("START")
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.toggle_listening)
        
        # Pause button
        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        
        # Stop button
        self.stop_button = QPushButton("STOP")
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_listening)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        controls_layout.addLayout(button_layout)
        
        # Audio level
        audio_level_layout = QVBoxLayout()
        audio_level_label = QLabel("Audio Level:")
        self.audio_level_progress = QProgressBar()
        self.audio_level_progress.setRange(0, 100)
        self.audio_level_progress.setValue(0)
        
        audio_level_layout.addWidget(audio_level_label)
        audio_level_layout.addWidget(self.audio_level_progress)
        controls_layout.addLayout(audio_level_layout)
        
        # Status indicators
        model_status_layout = QHBoxLayout()
        model_status_label = QLabel("Model Status:")
        self.model_status_value = QLabel("Not Loaded")
        model_status_layout.addWidget(model_status_label)
        model_status_layout.addWidget(self.model_status_value)
        
        # CPU and Memory usage
        resource_layout = QHBoxLayout()
        cpu_label = QLabel("CPU:")
        self.cpu_value = QLabel("0%")
        memory_label = QLabel("Memory:")
        self.memory_value = QLabel("0 MB")
        
        resource_layout.addWidget(cpu_label)
        resource_layout.addWidget(self.cpu_value)
        resource_layout.addWidget(memory_label)
        resource_layout.addWidget(self.memory_value)
        
        controls_layout.addLayout(model_status_layout)
        controls_layout.addLayout(resource_layout)
        
        # Add to top layout
        self.top_layout.addWidget(controls_group)
    
    def setup_model_settings_panel(self):
        # Create model settings group
        model_settings_group = QGroupBox("⚡ MODEL SETTINGS")
        model_settings_layout = QVBoxLayout()
        model_settings_group.setLayout(model_settings_layout)
        
        # Radio buttons for model source
        model_source_label = QLabel("📡 Model Source:")
        self.model_source_buttons = QButtonGroup()
        self.download_radio = QRadioButton("Download from HuggingFace")
        self.local_radio = QRadioButton("Use local model")
        self.model_source_buttons.addButton(self.download_radio, 1)
        self.model_source_buttons.addButton(self.local_radio, 2)
        self.download_radio.setChecked(True)
        
        model_settings_layout.addWidget(model_source_label)
        model_settings_layout.addWidget(self.download_radio)
        model_settings_layout.addWidget(self.local_radio)
        
        # Local model path
        path_layout = QHBoxLayout()
        path_label = QLabel("📂 Model Path:")
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select local model directory...")
        self.path_edit.setEnabled(False)
        self.browse_button = QPushButton("...")
        self.browse_button.setMaximumWidth(40)
        self.browse_button.setEnabled(False)
        
        path_layout.addWidget(path_label)
        model_settings_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        model_settings_layout.addLayout(path_layout)
        
        # Model size
        model_layout = QHBoxLayout()
        model_label = QLabel("🧠 Model Size:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"])
        self.model_combo.setCurrentText("small")
        
        model_settings_layout.addWidget(model_label)
        model_settings_layout.addWidget(self.model_combo)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("💻 Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda", "auto"])
        self.device_combo.setCurrentText("auto")
        
        model_settings_layout.addWidget(device_label)
        model_settings_layout.addWidget(self.device_combo)
        
        # Connect signals
        self.download_radio.toggled.connect(self.toggle_model_source)
        self.local_radio.toggled.connect(self.toggle_model_source)
        self.browse_button.clicked.connect(self.browse_local_model)
        
        # Add to bottom layout
        self.bottom_layout.addWidget(model_settings_group)
    
    def setup_language_panel(self):
        # Create language group
        language_group = QGroupBox("🌐 LANGUAGE & INPUT")
        language_layout = QVBoxLayout()
        language_group.setLayout(language_layout)
        
        # Language selection
        language_label = QLabel("🗣️ Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Auto Detect", "auto")
        
        # Add common languages
        language_names = {
            "en": "English", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
            "ja": "Japanese", "zh": "Chinese", "ru": "Russian", "ko": "Korean"
        }
        
        for code, name in language_names.items():
            self.language_combo.addItem(f"{name} ({code})", code)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        
        # Microphone sensitivity
        sensitivity_label = QLabel("🎤 Microphone Sensitivity:")
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 20)
        self.sensitivity_slider.setValue(10)
        
        # Sensitivity labels
        sensitivity_labels_layout = QHBoxLayout()
        low_label = QLabel("Low")
        medium_label = QLabel("Medium")
        high_label = QLabel("High")
        medium_label.setAlignment(Qt.AlignCenter)
        high_label.setAlignment(Qt.AlignRight)
        
        sensitivity_labels_layout.addWidget(low_label)
        sensitivity_labels_layout.addWidget(medium_label)
        sensitivity_labels_layout.addWidget(high_label)
        
        language_layout.addWidget(sensitivity_label)
        language_layout.addWidget(self.sensitivity_slider)
        language_layout.addLayout(sensitivity_labels_layout)
        
        # Initial prompt
        prompt_label = QLabel("💡 Initial Prompt:")
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("Optional: Provide context to guide transcription...")
        
        language_layout.addWidget(prompt_label)
        language_layout.addWidget(self.prompt_edit)
        
        # Add to bottom layout
        self.bottom_layout.addWidget(language_group)
    
    def setup_status_panel(self):
        # Create status group
        status_group = QGroupBox("📊 STATUS & HISTORY")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        # Status message
        self.status_message = QLabel("Status: Ready")
        status_layout.addWidget(self.status_message)
        
        # Session history
        history_label = QLabel("🕒 Last Session:")
        self.history_list = QListWidget()
        dummy_sessions = ["14:22 - Meeting notes", "13:05 - Email draft", "09:30 - Code comments"]
        self.history_list.addItems(dummy_sessions)
        
        status_layout.addWidget(history_label)
        status_layout.addWidget(self.history_list)
        
        # History buttons
        history_buttons_layout = QHBoxLayout()
        self.clear_button = QPushButton("🗑️ Clear")
        self.export_button = QPushButton("💾 Export")
        
        history_buttons_layout.addWidget(self.clear_button)
        history_buttons_layout.addWidget(self.export_button)
        status_layout.addLayout(history_buttons_layout)
        
        # Add to bottom layout
        self.bottom_layout.addWidget(status_group)
    
    def setup_options_panel(self):
        # Create options group
        options_group = QGroupBox("⚙️ OPTIONS")
        options_layout = QVBoxLayout()
        options_group.setLayout(options_layout)
        
        # Checkboxes
        self.auto_type_checkbox = QCheckBox("Auto-Type Text")
        self.auto_type_checkbox.setChecked(True)
        
        self.debug_checkbox = QCheckBox("Show Debug Info")
        self.debug_checkbox.setChecked(True)
        
        self.continuous_checkbox = QCheckBox("Continuous Mode")
        self.continuous_checkbox.setChecked(False)
        
        self.punctuate_checkbox = QCheckBox("Auto-punctuate")
        self.punctuate_checkbox.setChecked(False)
        
        options_layout.addWidget(self.auto_type_checkbox)
        options_layout.addWidget(self.debug_checkbox)
        options_layout.addWidget(self.continuous_checkbox)
        options_layout.addWidget(self.punctuate_checkbox)
        
        # Buttons
        options_buttons_layout = QHBoxLayout()
        self.test_button = QPushButton("⌨️ Test Typing")
        self.settings_button = QPushButton("⚙️ Settings")
        
        options_buttons_layout.addWidget(self.test_button)
        options_buttons_layout.addWidget(self.settings_button)
        options_layout.addLayout(options_buttons_layout)
        
        # Keyboard shortcut info
        shortcut_label = QLabel("Keyboard Shortcut: Alt+S")
        options_layout.addWidget(shortcut_label)
        
        # Connect signals
        self.auto_type_checkbox.stateChanged.connect(self.toggle_auto_type)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug)
        self.test_button.clicked.connect(self.test_typing)
        
        # Add to bottom layout
        self.bottom_layout.addWidget(options_group)
    
    # Functionality methods
    def toggle_model_source(self):
        """Handle toggling between download and local model sources"""
        if self.download_radio.isChecked():
            self.path_edit.setEnabled(False)
            self.browse_button.setEnabled(False)
        else:
            self.path_edit.setEnabled(True)
            self.browse_button.setEnabled(True)
    
    def browse_local_model(self):
        """Open file dialog to select local model directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Model Directory", os.path.expanduser("~"))
        if directory:
            self.path_edit.setText(directory)
            print(f"Selected local model directory: {directory}")
    
    def update_audio_level(self):
        """Simulate audio level updates (will be replaced with actual levels)"""
        import random
        level = random.randint(0, 100)
        self.audio_level_progress.setValue(level)
        
        # Update color based on level
        if level < 30:
            self.audio_level_progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {StyleSheet.SUCCESS}; }}")
        elif level < 70:
            self.audio_level_progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {StyleSheet.WARNING}; }}")
        else:
            self.audio_level_progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {StyleSheet.ERROR}; }}")
        
        # Update CPU and memory (simulation)
        cpu = random.randint(20, 40)
        memory = random.randint(300, 500)
        
        self.cpu_value.setText(f"{cpu}%")
        self.memory_value.setText(f"{memory} MB")
    
    def toggle_listening(self):
        """Start or stop listening"""
        if self.start_button.text() == "START":
            # Start listening
            self.start_button.setText("LISTENING...")
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.model_status_value.setText("Loaded")
            self.status_message.setText("✅ Status: Listening...")
            self.statusBar().showMessage("Listening... Speak now!")
            
            # Add demo text (will be replaced with actual transcription)
            self.transcription_text.append("I'm currently listening to what you're saying and transcribing it in real-time.")
        else:
            self.stop_listening()
    
    def toggle_pause(self):
        """Pause or resume listening"""
        if self.pause_button.text() == "PAUSE":
            self.pause_button.setText("RESUME")
            self.status_message.setText("⏸️ Status: Paused")
            self.statusBar().showMessage("Transcription paused")
        else:
            self.pause_button.setText("PAUSE")
            self.status_message.setText("✅ Status: Listening...")
            self.statusBar().showMessage("Listening... Speak now!")
    
    def stop_listening(self):
        """Stop listening and reset UI"""
        self.start_button.setText("START")
        self.start_button.setEnabled(True)
        self.pause_button.setText("PAUSE")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.status_message.setText("Status: Ready")
        self.statusBar().showMessage("Ready to transcribe. Click START or press Alt+S to begin")
    
    def toggle_auto_type(self, state):
        """Toggle auto-typing functionality"""
        print(f"Auto-type {'enabled' if state == Qt.Checked else 'disabled'}")
    
    def toggle_debug(self, state):
        """Toggle debug mode"""
        print(f"Debug mode {'enabled' if state == Qt.Checked else 'disabled'}")
    
    def test_typing(self):
        """Test keyboard input functionality"""
        self.statusBar().showMessage("Testing typing functionality...")
        print("Testing keyboard input...")
        self.transcription_text.append("This is a test of the typing functionality.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImprovedSpeechToTextApp()
    window.show()
    sys.exit(app.exec_()) 