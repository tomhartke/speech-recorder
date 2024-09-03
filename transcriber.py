import os
import sounddevice as sd
import wave
import tkinter as tk
from tkinter import messagebox, scrolledtext
import numpy as np
from pathlib import Path
from openai import OpenAI

# Constants
AUDIO_FILE = "output.wav"
SAMPLERATE = 44100
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Check if the API key is available
if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

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

    messagebox.showinfo("Recording Complete", f"Audio saved to {AUDIO_FILE}")
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


# Function to transcribe the recorded audio
def transcribe_audio():
    try:
        file_path = Path(AUDIO_FILE)
        with open(file_path, "rb") as audio_file_obj:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_obj
            )
        transcription_text = transcription.text
        transcription_box.delete(1.0, tk.END)
        transcription_box.insert(tk.END, transcription_text)
    except Exception as e:
        messagebox.showerror("Transcription Error", f"An error occurred: {e}")


# Create the main window
root = tk.Tk()
root.title("Simple Audio Recorder with Transcription")

# Add start/stop recording buttons
start_button = tk.Button(root, text="Start Recording", command=start_recording)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
stop_button.pack(pady=10)

# Add transcribe button
transcribe_button = tk.Button(root, text="Transcribe", command=transcribe_audio)
transcribe_button.pack(pady=10)

# Add transcription display box
transcription_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10)
transcription_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Run the application
root.mainloop()
