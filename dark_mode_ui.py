import sys
import os
import time
import math  # Make sure the import is at the top
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QTextEdit,
                            QFrame, QSizePolicy, QStackedWidget, QToolButton)
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
        
        # Header with title and mode selector
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Speech-to-Text Writer")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Online Mode", "Offline Mode"])
        header_layout.addWidget(self.mode_selector)
        
        normal_layout.addLayout(header_layout)
        
        # Main text area panel
        text_panel = RoundedPanel()
        text_panel_layout = QVBoxLayout(text_panel)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText("Transcribed text will appear here...")
        text_panel_layout.addWidget(self.text_edit)
        
        normal_layout.addWidget(text_panel)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Spacer to center buttons
        buttons_layout.addStretch()
        
        self.start_button = RoundedButton("Start", primary=True)
        self.stop_button = RoundedButton("Stop", primary=False)
        self.pause_button = RoundedButton("Pause", primary=False)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.pause_button)
        
        # Spacer to center buttons
        buttons_layout.addStretch()
        
        normal_layout.addLayout(buttons_layout)
        
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
            # Restore to normal size
            self.main_layout.setContentsMargins(20, 20, 20, 20)  # Restore original margins
            self.resize(800, 500)
            self.setMinimumSize(800, 500)
        else:
            # Switch to minimized UI
            self.stacked_widget.setCurrentIndex(1)
            self.is_minimized_ui = True
            # Set small margins
            self.main_layout.setContentsMargins(4, 4, 4, 4)
            # Resize to smaller window and set fixed size
            self.setMinimumSize(10, 10)  # Allow smaller minimum size
            self.resize(self.minimized_size)  # Use the stored minimized size
            
    def toggle_listening(self):
        if self.audio_visualizer.active:
            self.stop_listening()
            self.mini_start_button.setText("▶")
        else:
            self.start_listening()
            self.mini_start_button.setText("⏸")
            
    def start_listening(self):
        if not self.is_minimized_ui:
            self.text_edit.append("Listening started...")
            
        self.audio_visualizer.start_animation()
        self.status_indicator.setStyleSheet(f"color: {DarkTheme.ACCENT_PRIMARY};")
        self.status_text.setText("Listening")
        self.status_text.setStyleSheet(f"color: {DarkTheme.ACCENT_PRIMARY}; font-size: 10px;")
        
    def stop_listening(self):
        if not self.is_minimized_ui:
            self.text_edit.append("Listening stopped.")
            
        self.audio_visualizer.stop_animation()
        self.status_indicator.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.status_text.setText("Not listening")
        self.status_text.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 10px;")
        
    def pause_listening(self):
        if not self.is_minimized_ui:
            self.text_edit.append("Listening paused.")
            
        self.stop_listening()
        self.status_text.setText("Paused")

# For testing the UI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechToTextApp()
    window.show()
    sys.exit(app.exec_()) 