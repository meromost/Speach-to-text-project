# Speech to Text Typer

A speech recognition application that converts your speech to text and types it directly at your cursor position in any application.

## Features

- Real-time speech-to-text conversion using Faster Whisper
- Modern PyQt5 user interface
- Auto-typing at the cursor position
- Adjustable model settings (size, device, precision)
- Pause/Resume functionality
- Shows last recognized text in the UI

## Requirements

```
PyQt5>=5.15.0
faster-whisper>=0.9.0
sounddevice>=0.4.5
numpy>=1.20.0
pynput>=1.7.6
```

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install PyQt5 faster-whisper sounddevice numpy pynput
```

3. If you want to use GPU acceleration (recommended for better performance):
   - Install CUDA and cuDNN if not already installed
   - Make sure PyTorch is installed with CUDA support

## Usage

1. Run the application:

```bash
python whisper_typing.py
```

2. Select your preferred model settings:
   - Model Size: smaller models are faster but less accurate, larger models are slower but more accurate
   - Device: "cuda" for GPU, "cpu" for CPU, or "auto" to automatically select the best option
   - Precision: "int8" for faster but potentially less accurate, "float16" for slower but more accurate

3. Click "Apply Settings" to load the model

4. Click "Start Listening" to begin speech recognition

5. Speak clearly and the text will be:
   - Displayed in the application UI
   - Typed at your current cursor position (if Auto Type is enabled)

6. You can toggle Auto Type on/off while the application is running

7. Use "Pause"/"Resume" to temporarily stop/restart speech recognition

8. Click "Stop Listening" when you're done

## Troubleshooting

- **No audio input detected**: Make sure your microphone is properly connected and allowed in your system settings
- **Slow transcription**: Try a smaller model size or use GPU acceleration if available
- **Inaccurate transcription**: Try a larger model or speak more clearly
- **Text not appearing at cursor**: Make sure the application has accessibility permissions

## License

This project is open source and available under the MIT License. 