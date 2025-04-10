import sys
import os
import time
import math  # Make sure the import is at the top
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QTextEdit,
                            QFrame, QSizePolicy, QStackedWidget, QToolButton,
                            QGroupBox, QRadioButton, QButtonGroup, QLineEdit, QFileDialog,
                            QCheckBox, QSlider, QProgressBar)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QPainterPath, QIcon

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
        self.setMinimumSize(180, 30)  # Even smaller minimum size for compact mode
        self.bars = 8  # Fewer bars for very compact UI
        self._levels = [0] * self.bars
        self.active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_levels)
        self.animations = []
        
    def start_animation(self):
        self.active = True
        self.timer.start(80)  # Update more frequently for smoother animation
        
    def stop_animation(self):
        self.active = False
        self.timer.stop()
        self._levels = [0] * self.bars
        self.update()
        
    def update_levels(self):
        if self.active:
            import random
            for i in range(self.bars):
                # Generate random heights to simulate audio activity
                # Using sin wave pattern for more realistic audio visualization
                base = 0.3 + 0.7 * abs(math.sin(time.time() * 3 + i * 0.5))
                variation = random.uniform(-0.2, 0.2)
                self._levels[i] = max(0.05, min(0.95, base + variation))
            self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate bar width and spacing
        width = self.width()
        height = self.height()
        bar_width = width / (self.bars * 2)
        spacing = bar_width
        
        # Draw the bars
        painter.setPen(Qt.NoPen)
        
        for i, level in enumerate(self._levels):
            if self.active:
                # Use a gradient from primary to secondary accent when active
                color = QColor(DarkTheme.ACCENT_SECONDARY)
            else:
                # Use a darker color when inactive
                color = QColor(DarkTheme.ACCENT_SECONDARY).darker(150)
                
            painter.setBrush(color)
            
            x = i * (bar_width + spacing) + spacing
            bar_height = height * (level if self.active else 0.1)  # Small fixed height when inactive
            y = (height - bar_height) / 2
            
            # Draw rounded bars
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
        
        # Style based on button type
        if primary:
            self.setStyleSheet(f"""
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
            """)
        else:
            self.setStyleSheet(f"""
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
            """)

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

# Main application window
class SpeechToTextApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech-to-Text Writer")
        self.setMinimumSize(800, 500)  # Start with full-size UI dimensions
        self.is_minimized_ui = False  # Start with normal UI
        
        # Set window background
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DarkTheme.BG_DARK};
            }}
            QLabel {{
                color: {DarkTheme.TEXT_PRIMARY};
            }}
            QComboBox {{
                background-color: {DarkTheme.BG_PANEL};
                color: {DarkTheme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DarkTheme.BG_PANEL};
                color: {DarkTheme.TEXT_PRIMARY};
                selection-background-color: {DarkTheme.ACCENT_SECONDARY};
                selection-color: {DarkTheme.TEXT_PRIMARY};
                border: none;
            }}
            QTextEdit {{
                background-color: {DarkTheme.BG_PANEL};
                color: {DarkTheme.TEXT_PRIMARY};
                border: none;
                border-radius: {DarkTheme.PANEL_RADIUS}px;
                padding: 10px;
                selection-background-color: {DarkTheme.ACCENT_SECONDARY};
            }}
            QScrollBar:vertical {{
                background: {DarkTheme.BG_PANEL};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {DarkTheme.BUTTON_SECONDARY};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {DarkTheme.BG_PANEL};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {DarkTheme.BUTTON_SECONDARY};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        
        # Create central widget with stacked layout for normal/minimized modes
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)  # Normal UI margins
        
        # Create stacked widget for different UI states
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Setup both UI states
        self.setup_normal_ui()
        self.setup_minimized_ui()
        
        # Store the minimized UI size for later
        self.minimized_size = QSize(226, 177)
        
        # Start with normal UI
        self.stacked_widget.setCurrentIndex(0)
        
    def setup_normal_ui(self):
        # Create widget for normal UI
        normal_ui = QWidget()
        normal_layout = QVBoxLayout(normal_ui)
        normal_layout.setSpacing(15)
        
        # Header with title (Removed old mode selector)
        header_layout = QHBoxLayout()
        title_label = QLabel("Speech-to-Text Writer")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        normal_layout.addLayout(header_layout)
        
        # --- Status & Audio Level ---
        status_audio_layout = QHBoxLayout()
        self.status_label = QLabel("Ready") # General Status Label
        self.status_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        status_audio_layout.addWidget(self.status_label)
        status_audio_layout.addStretch()
        
        audio_level_label = QLabel("Audio:")
        audio_level_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; margin-right: 5px;")
        self.audio_level_progress = QProgressBar() # Audio Level Bar
        self.audio_level_progress.setRange(0, 100)
        self.audio_level_progress.setValue(0)
        self.audio_level_progress.setTextVisible(False)
        self.audio_level_progress.setFixedSize(100, 10) # Make it compact
        self.audio_level_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: {DarkTheme.BG_DARK};
            }}
            QProgressBar::chunk {{
                background-color: {DarkTheme.ACCENT_SECONDARY};
                border-radius: 5px;
            }}
        """)
        status_audio_layout.addWidget(audio_level_label)
        status_audio_layout.addWidget(self.audio_level_progress)
        normal_layout.addLayout(status_audio_layout)

        # --- Model Configuration Panel ---
        model_config_panel = RoundedPanel() # Use the custom panel
        model_config_layout = QVBoxLayout(model_config_panel)
        model_config_layout.setSpacing(10)
        
        # Current Model Banner (Label)
        self.current_model_label = QLabel("Model: Offline (Default)")
        self.current_model_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; padding-bottom: 5px;")
        model_config_layout.addWidget(self.current_model_label)
        
        # Source Selection (Radio Buttons)
        source_radio_layout = QHBoxLayout()
        self.model_source_buttons = QButtonGroup()
        self.online_radio = QRadioButton("Online (HuggingFace)")
        self.offline_radio = QRadioButton("Offline (Local)")
        self.online_radio.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};") # Style radio buttons
        self.offline_radio.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        
        self.model_source_buttons.addButton(self.online_radio, 1)
        self.model_source_buttons.addButton(self.offline_radio, 2)
        source_radio_layout.addWidget(self.online_radio)
        source_radio_layout.addWidget(self.offline_radio)
        source_radio_layout.addStretch()
        model_config_layout.addLayout(source_radio_layout)
        
        # --- Online (HuggingFace) Model Widgets ---
        self.online_model_widget = QWidget() # Container to show/hide
        online_model_layout = QHBoxLayout()
        online_model_layout.setContentsMargins(0, 5, 0, 0) # Add some top margin
        self.online_model_widget.setLayout(online_model_layout)
        
        hf_model_label = QLabel("Model:")
        hf_model_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        self.hf_model_combo = QComboBox()
        self.hf_model_combo.addItems(["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"]) # Example models
        self.hf_model_combo.setCurrentText("small") # Default
        # Styling for QComboBox is handled globally in __init__
        
        # Device selection
        device_label = QLabel("Device:")
        device_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY}; margin-left: 15px;")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda", "auto"])
        self.device_combo.setCurrentText("auto")
        
        # Precision selection
        precision_label = QLabel("Precision:")
        precision_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY}; margin-left: 15px;")
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["float16", "int8"])
        self.precision_combo.setCurrentText("int8")

        online_model_layout.addWidget(hf_model_label)
        online_model_layout.addWidget(self.hf_model_combo)
        online_model_layout.addWidget(device_label)
        online_model_layout.addWidget(self.device_combo)
        online_model_layout.addWidget(precision_label)
        online_model_layout.addWidget(self.precision_combo)
        online_model_layout.addStretch()
        model_config_layout.addWidget(self.online_model_widget)
        
        # --- Offline (Local) Model Widgets ---
        self.offline_model_widget = QWidget() # Container to show/hide
        offline_model_layout = QHBoxLayout()
        offline_model_layout.setContentsMargins(0, 5, 0, 0) # Add some top margin
        self.offline_model_widget.setLayout(offline_model_layout)
        
        local_path_label = QLabel("Path:")
        local_path_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setPlaceholderText("Path to local model...")
        self.local_path_edit.setStyleSheet(f"""
            QLineEdit {{ 
                background-color: {DarkTheme.BG_DARK}; 
                color: {DarkTheme.TEXT_PRIMARY}; 
                border: 1px solid {DarkTheme.BG_PANEL}; 
                border-radius: 6px; 
                padding: 5px;
            }}
        """)
        self.browse_button = RoundedButton("Browse...", primary=False)
        # self.browse_button.clicked.connect(self.browse_local_model) # Placeholder connection
        
        offline_model_layout.addWidget(local_path_label)
        offline_model_layout.addWidget(self.local_path_edit, 1)
        offline_model_layout.addWidget(self.browse_button)
        model_config_layout.addWidget(self.offline_model_widget)
        
        normal_layout.addWidget(model_config_panel) # Add the panel to the main layout
        
        # --- Transcription Output Panel ---
        output_panel = RoundedPanel()
        output_layout = QVBoxLayout(output_panel)
        self.transcription_label = QLabel("Transcription output will appear here...")
        self.transcription_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; padding: 10px;")
        self.transcription_label.setWordWrap(True)
        output_layout.addWidget(self.transcription_label)
        normal_layout.addWidget(output_panel)

        # --- Quality & Context Settings Panel ---
        settings_panel = RoundedPanel()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setSpacing(10)

        # Quality Settings
        quality_label = QLabel("Quality Settings")
        quality_label.setStyleSheet("font-weight: bold;")
        settings_layout.addWidget(quality_label)

        quality_checkbox_layout = QHBoxLayout()
        self.high_quality_checkbox = QCheckBox("High Quality")
        self.noise_reduction_checkbox = QCheckBox("Noise Reduction")
        self.vad_checkbox = QCheckBox("VAD")
        for cb in [self.high_quality_checkbox, self.noise_reduction_checkbox, self.vad_checkbox]:
            cb.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
            quality_checkbox_layout.addWidget(cb)
        quality_checkbox_layout.addStretch()
        settings_layout.addLayout(quality_checkbox_layout)

        # Context Slider
        context_layout = QHBoxLayout()
        context_label = QLabel("Context Window:")
        context_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.context_slider = QSlider(Qt.Horizontal)
        self.context_slider.setRange(0, 5)
        self.context_slider.setValue(3)
        self.context_value_label = QLabel("3")
        self.context_value_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; min-width: 15px;")
        # self.context_slider.valueChanged.connect(lambda val: self.context_value_label.setText(str(val))) # Example connection
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_slider)
        context_layout.addWidget(self.context_value_label)
        settings_layout.addLayout(context_layout)

        # Sensitivity Slider & Calibration
        mic_sensitivity_layout = QHBoxLayout()
        mic_sensitivity_label = QLabel("Mic Sensitivity:")
        mic_sensitivity_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.mic_sensitivity_slider = QSlider(Qt.Horizontal)
        self.mic_sensitivity_slider.setRange(1, 20) 
        self.mic_sensitivity_slider.setValue(10)
        self.mic_sensitivity_value = QLabel("50%") # Placeholder label
        self.mic_sensitivity_value.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; min-width: 30px;")
        # self.mic_sensitivity_slider.valueChanged.connect(lambda val: self.mic_sensitivity_value.setText(f"{int(val/20*100)}%")) # Example connection
        self.calibrate_button = RoundedButton("Calibrate", primary=False)
        mic_sensitivity_layout.addWidget(mic_sensitivity_label)
        mic_sensitivity_layout.addWidget(self.mic_sensitivity_slider)
        mic_sensitivity_layout.addWidget(self.mic_sensitivity_value)
        mic_sensitivity_layout.addWidget(self.calibrate_button)
        settings_layout.addLayout(mic_sensitivity_layout)
        
        # Context/Prompt Settings
        context_settings_label = QLabel("Transcription Context")
        context_settings_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        settings_layout.addWidget(context_settings_label)

        prompt_layout = QHBoxLayout()
        prompt_label = QLabel("Initial Prompt:")
        prompt_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("Optional context...")
        self.prompt_edit.setStyleSheet(f"""
            QLineEdit {{ 
                background-color: {DarkTheme.BG_DARK}; 
                color: {DarkTheme.TEXT_PRIMARY}; 
                border: 1px solid {DarkTheme.BG_PANEL}; 
                border-radius: 6px; 
                padding: 5px;
            }}
        """)
        prompt_layout.addWidget(prompt_label)
        prompt_layout.addWidget(self.prompt_edit)
        settings_layout.addLayout(prompt_layout)

        normal_layout.addWidget(settings_panel)

        # --- Main Control Buttons ---
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch() # Center buttons
        self.start_button = RoundedButton("Start", primary=True)
        self.stop_button = RoundedButton("Stop", primary=False)
        self.pause_button = RoundedButton("Pause", primary=False)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.pause_button)
        buttons_layout.addStretch() # Center buttons
        normal_layout.addLayout(buttons_layout)

        # --- Other Controls & Apply Button ---
        controls_apply_layout = QHBoxLayout()
        
        # Checkboxes
        self.auto_type_checkbox = QCheckBox("Auto-type")
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.auto_type_checkbox.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.debug_checkbox.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        controls_apply_layout.addWidget(self.auto_type_checkbox)
        controls_apply_layout.addWidget(self.debug_checkbox)
        controls_apply_layout.addStretch()
        
        # Test Typing Button
        self.test_typing_button = RoundedButton("Test Typing", primary=False)
        controls_apply_layout.addWidget(self.test_typing_button)

        # Apply Button
        self.apply_button = RoundedButton("Apply Settings", primary=False)
        # self.apply_button.clicked.connect(self.apply_model_settings) # Placeholder connection
        controls_apply_layout.addWidget(self.apply_button)
        
        normal_layout.addLayout(controls_apply_layout)

        # Add stretch to push buttons down (MOVED to after other controls)
        # normal_layout.addStretch()
        
        # Add minimize UI button
        minimize_layout = QHBoxLayout()
        minimize_layout.addStretch()
        
        self.minimize_ui_button = QPushButton("Minimize UI")
        self.minimize_ui_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DarkTheme.TEXT_SECONDARY};
                border: none;
                padding: 5px;
            }}
            QPushButton:hover {{
                color: {DarkTheme.TEXT_PRIMARY};
            }}
        """)
        self.minimize_ui_button.clicked.connect(self.toggle_ui_mode)
        minimize_layout.addWidget(self.minimize_ui_button)
        
        normal_layout.addLayout(minimize_layout)
        
        # Set initial state (e.g., default to Online)
        self.online_radio.setChecked(True)
        self.online_model_widget.setVisible(True)
        self.offline_model_widget.setVisible(False)
        
        # Connect radio button signals AFTER setting initial state
        self.online_radio.toggled.connect(self.toggle_model_source)
        # self.offline_radio is implicitly handled by the button group
        
        # Add to stacked widget
        self.stacked_widget.addWidget(normal_ui)
        
        # Connect control buttons
        self.start_button.clicked.connect(self.start_listening)
        self.stop_button.clicked.connect(self.stop_listening)
        self.pause_button.clicked.connect(self.pause_listening)
        
    def setup_minimized_ui(self):
        # Create widget for minimized UI
        minimized_ui = QWidget()
        minimized_layout = QVBoxLayout(minimized_ui)
        minimized_layout.setContentsMargins(4, 4, 4, 4)
        minimized_layout.setSpacing(2)
        
        # Create compact visualizer panel
        visualizer_panel = RoundedPanel()
        visualizer_panel.setFixedHeight(169)  # Fixed height to match the target 177px window height
        visualizer_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkTheme.BG_PANEL};
                border-radius: {DarkTheme.PANEL_RADIUS}px;
                border: none;
            }}
        """)
        visualizer_layout = QVBoxLayout(visualizer_panel)
        visualizer_layout.setContentsMargins(6, 8, 6, 8)
        visualizer_layout.setSpacing(4)
        
        # Status indicator (listening/not listening)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 10))
        self.status_indicator.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        status_layout.addWidget(self.status_indicator)
        
        self.status_text = QLabel("Not listening")
        self.status_text.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 10px;")
        status_layout.addWidget(self.status_text)
        
        status_layout.addStretch()
        
        # Maximize button
        maximize_button = QToolButton()
        maximize_button.setText("⬆")
        maximize_button.setFont(QFont("Arial", 10))
        maximize_button.setFixedSize(18, 18)
        maximize_button.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {DarkTheme.TEXT_SECONDARY};
                border: none;
                padding: 0px;
            }}
            QToolButton:hover {{
                color: {DarkTheme.TEXT_PRIMARY};
            }}
        """)
        maximize_button.clicked.connect(self.toggle_ui_mode)
        status_layout.addWidget(maximize_button)
        
        visualizer_layout.addLayout(status_layout)
        
        # Audio visualizer - make it larger for the taller UI
        self.audio_visualizer = AudioVisualizer()
        self.audio_visualizer.setMinimumHeight(80)  # Taller for more pronounced visualization
        visualizer_layout.addWidget(self.audio_visualizer)
        
        # Simple controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)
        
        # Start/Pause toggle button
        self.mini_start_button = QToolButton()
        self.mini_start_button.setText("▶")
        self.mini_start_button.setFont(QFont("Arial", 12))
        self.mini_start_button.setFixedSize(32, 32)
        self.mini_start_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {DarkTheme.ACCENT_PRIMARY};
                color: {DarkTheme.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 0px;
            }}
            QToolButton:hover {{
                background-color: {DarkTheme.BUTTON_HOVER};
            }}
        """)
        self.mini_start_button.clicked.connect(self.toggle_listening)
        controls_layout.addWidget(self.mini_start_button)
        
        # Online/Offline toggle
        self.mini_mode_selector = QComboBox()
        self.mini_mode_selector.addItems(["Online", "Offline"])
        self.mini_mode_selector.setFixedHeight(24)
        self.mini_mode_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkTheme.BG_PANEL};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid #444;
                border-radius: 4px;
                padding: 2px 6px;
                min-width: 80px;
                max-width: 80px;
                font-size: 10px;
            }}
        """)
        controls_layout.addWidget(self.mini_mode_selector)
        
        controls_layout.addStretch()
        
        visualizer_layout.addLayout(controls_layout)
        
        minimized_layout.addWidget(visualizer_panel)
        
        # Add to stacked widget
        self.stacked_widget.addWidget(minimized_ui)
        
    def toggle_ui_mode(self):
        if self.is_minimized_ui:
            # Switch to normal UI
            self.stacked_widget.setCurrentIndex(0)
            self.is_minimized_ui = False
            self.main_layout.setContentsMargins(20, 20, 20, 20)
            self.resize(800, 500)
            self.setMinimumSize(800, 500)
        else:
            # Switch to minimized UI
            self.stacked_widget.setCurrentIndex(1)
            self.is_minimized_ui = True
            self.main_layout.setContentsMargins(4, 4, 4, 4)
            self.setMinimumSize(10, 10)
            self.resize(self.minimized_size)
            
    def toggle_model_source(self):
        is_online = self.online_radio.isChecked()
        self.online_model_widget.setVisible(is_online)
        self.offline_model_widget.setVisible(not is_online)
        
        # Update banner text (example)
        if is_online:
            current_hf_model = self.hf_model_combo.currentText()
            self.current_model_label.setText(f"Model: Online ({current_hf_model})")
        else:
            current_local_path = self.local_path_edit.text() or "Not selected"
            self.current_model_label.setText(f"Model: Offline ({current_local_path})")
            
    def toggle_listening(self):
        if self.audio_visualizer.active:
            self.stop_listening()
            self.mini_start_button.setText("▶")
        else:
            self.start_listening()
            self.mini_start_button.setText("⏸")
            
    def start_listening(self):
        self.audio_visualizer.start_animation()
        self.status_indicator.setStyleSheet(f"color: {DarkTheme.ACCENT_PRIMARY};")
        self.status_text.setText("Listening")
        self.status_text.setStyleSheet(f"color: {DarkTheme.ACCENT_PRIMARY}; font-size: 10px;")
        
    def stop_listening(self):
        self.audio_visualizer.stop_animation()
        self.status_indicator.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.status_text.setText("Not listening")
        self.status_text.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 10px;")
        
    def pause_listening(self):
        self.stop_listening()
        self.status_text.setText("Paused")

# For testing the UI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechToTextApp()
    window.show()
    sys.exit(app.exec_()) 