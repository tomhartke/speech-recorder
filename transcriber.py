import os
import sounddevice as sd
import wave
import tkinter as tk
from tkinter import messagebox, scrolledtext
import numpy as np
from pathlib import Path
from openai import OpenAI
import json
import datetime
import pyperclip

# Constants
AUDIO_FILE = "output.wav"
SAMPLERATE = 44100
HISTORY_FILE = "transcription_history.json"
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
    status_label.config(text="Recording...", fg="red")
    audio_frames = []  # Clear the previous audio data

    recording = sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', callback=audio_callback)
    recording.start()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


# Function to stop recording and automatically transcribe
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

    file_size = os.path.getsize(AUDIO_FILE) / 1024  # in KB
    status_label.config(text=f"Recording stopped. File size: {file_size:.2f} KB", fg="green")

    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

    # Automatically transcribe the audio
    transcribe_audio()


# Function to transcribe the recorded audio
def transcribe_audio():
    try:
        status_label.config(text="Transcription in progress...", fg="blue")
        root.update_idletasks()  # Force update the label

        file_path = Path(AUDIO_FILE)
        with open(file_path, "rb") as audio_file_obj:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_obj
            )
        transcription_text = transcription.text

        # Update the transcription box
        transcription_box.delete(1.0, tk.END)
        transcription_box.insert(tk.END, transcription_text)

        # Copy to clipboard
        pyperclip.copy(transcription_text)

        # Save to history
        save_to_history(transcription_text)

        # Update history display
        update_history_display()

        status_label.config(text="Transcription complete and copied to clipboard", fg="green")
    except Exception as e:
        messagebox.showerror("Transcription Error", f"An error occurred: {e}")
        status_label.config(text="Transcription failed", fg="red")


# Function to save transcription to history
def save_to_history(transcription):
    history = load_history()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.append({"timestamp": timestamp, "transcription": transcription})

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


# Function to load history
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []


# Function to update history display
def update_history_display():
    history = load_history()
    history_box.delete(1.0, tk.END)
    for entry in reversed(history):
        history_box.insert(tk.END, f"{entry['timestamp']}:\n{entry['transcription']}\n\n")


# Create the main window
root = tk.Tk()
root.title("Audio Recorder with Transcription and History")

# Add start/stop recording buttons
start_button = tk.Button(root, text="Start Recording", command=start_recording)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
stop_button.pack(pady=10)

# Add transcription display box
transcription_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10)
transcription_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Add status label
status_label = tk.Label(root, text="Not recording", fg="black")
status_label.pack(pady=5)

# Add history display box
history_label = tk.Label(root, text="Transcription History:")
history_label.pack(pady=5)
history_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10)
history_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Initialize history display
update_history_display()

# Run the application
root.mainloop()