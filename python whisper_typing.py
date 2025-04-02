import sounddevice as sd
import numpy as np
import queue
from faster_whisper import WhisperModel
from pynput.keyboard import Controller

# Load the Faster Whisper model
model = WhisperModel("distil-large-v3", device="cuda" or "cpu", compute_type="int8")

# Keyboard controller to simulate typing
keyboard = Controller()
audio_queue = queue.Queue()

# Audio settings
SAMPLE_RATE = 16000  # Whisper model sample rate
BLOCKSIZE = 4000     # Smaller blocks reduce latency

def callback(indata, frames, time, status):
    """Callback function to put audio data into the queue."""
    if status:
        print(status)
    audio_queue.put(indata.copy())

# Start recording
with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
    print("Listening... Speak now!")

    while True:
        audio_chunk = audio_queue.get()
        audio_data = np.squeeze(audio_chunk)

        # Transcribe speech
        segments, _ = model.transcribe(audio_data, beam_size=5)

        # Type out the recognized text
        for segment in segments:
            keyboard.type(segment.text + " ")
