# Speech to Text Typer

A speech recognition application that converts your speech to text and types it directly at your cursor position in any application.

## Features

- Real-time speech-to-text conversion using Faster Whisper
- Modern PyQt5 user interface
- Auto-typing at the cursor position
- Adjustable model settings (size, device, precision)
- Pause/Resume functionality
- Shows last recognized text in the UI
- Automatic detection of local models

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
pip install -r requirements.txt
```

3. Set up speech recognition models:

### Option 1: Use Automatic Download (Default)
- The application can automatically download models from HuggingFace
- Select your preferred model size in the UI (tiny, base, small, medium, etc.)
- Note: This requires internet connection when first using a model

### Option 2: Install Models Locally (Recommended)
- Download a Whisper model from HuggingFace
- Create a directory in the `models/` folder
- Place the model files in this directory
- The application will automatically detect and use local models

**Example for downloading the distil-large-v3 model**:
```bash
# Create model directory
mkdir -p models/en_fasterwhisper_distil_large_v3

# Download model files (example using Hugging Face CLI tool)
cd models/en_fasterwhisper_distil_large_v3
huggingface-cli download distil-whisper/distil-large-v3 --include="*.bin" --include="*.json"
```

Alternatively, you can download the files manually from: https://huggingface.co/distil-whisper/distil-large-v3

Required model files:
- model.bin (main model weights - large file)
- config.json
- tokenizer.json 
- vocabulary.json
- preprocessor_config.json

4. If you want to use GPU acceleration (recommended for better performance):
   - Install CUDA and cuDNN if not already installed
   - Make sure PyTorch is installed with CUDA support

## Usage

1. Run the application:

```bash
python whisper_typing.py
```

2. If using a downloaded model, it will be automatically detected
   
3. Otherwise, select your preferred model settings:
   - Model Size: smaller models are faster but less accurate, larger models are slower but more accurate
   - Device: "cuda" for GPU, "cpu" for CPU, or "auto" to automatically select the best option
   - Precision: "int8" for faster but potentially less accurate, "float16" for slower but more accurate

4. Choose your language or use "Auto Detect"

5. Click "Apply Settings" to load the model

6. Click "Start Listening" to begin speech recognition

7. Speak clearly and the text will be:
   - Displayed in the application UI
   - Typed at your current cursor position (if Auto Type is enabled)

8. You can toggle Auto Type on/off while the application is running

9. Use "Pause"/"Resume" to temporarily stop/restart speech recognition

10. Click "Stop Listening" when you're done

## Troubleshooting

- **No audio input detected**: Make sure your microphone is properly connected and allowed in your system settings
- **Slow transcription**: Try a smaller model size or use GPU acceleration if available
- **Inaccurate transcription**: Try a larger model or speak more clearly
- **Text not appearing at cursor**: Make sure the application has accessibility permissions

## License

This project is open source and available under the MIT License. 