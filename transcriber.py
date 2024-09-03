import sounddevice as sd
import wave
import tkinter as tk
from tkinter import messagebox
import numpy as np

# Constants
AUDIO_FILE = "output.wav"
SAMPLERATE = 44100

recording = None
audio_frames = []


# Function to callback and store the audio data during recording
def audio_callback(indata, frames, time, status):
    audio_frames.append(indata.copy())


# Function to start recording
def start_recording():
    global recording, audio_frames
    print("Recording started...")
    audio_frames = []  # Clear the previous audio data

    recording = sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', callback=audio_callback)
    recording.start()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


# Function to stop recording
def stop_recording():
    global recording
    print("Recording stopped.")
    recording.stop()
    recording.close()

    # Convert the audio frames to a numpy array and save as WAV file
    audio_data = np.concatenate(audio_frames, axis=0)

    with wave.open(AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLERATE)
        wf.writeframes((audio_data * 32767).astype('int16').tobytes())

    # messagebox.showinfo("Recording Complete", f"Audio saved to {AUDIO_FILE}")
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


# Create the main window
root = tk.Tk()
root.title("Simple Audio Recorder")

# Add start/stop recording buttons
start_button = tk.Button(root, text="Start Recording", command=start_recording)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
stop_button.pack(pady=10)

# Run the application
root.mainloop()
