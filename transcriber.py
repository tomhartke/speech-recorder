import os
import sounddevice as sd
import wave
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
from pathlib import Path
from openai import OpenAI
import json
import datetime
import pyperclip
import threading

# Constants
AUDIO_FILE = "output.wav"
SAMPLERATE = 44100
HISTORY_FILE = "transcription_history.json"
TRANSACTIONS_FILE = "transactions.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
COST_PER_MINUTE = 0.006

# Check if the API key is available
if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

recording = None
audio_frames = []
recording_start_time = None


# Function to callback and store the audio data during recording
def audio_callback(indata, frames, time, status):
    audio_frames.append(indata.copy())


# Function to start recording
def start_recording():
    global recording, audio_frames, recording_start_time
    print("Recording started...")
    status_label.config(text="Recording...", foreground="red")
    audio_frames = []  # Clear the previous audio data
    recording_start_time = datetime.datetime.now()

    recording = sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', callback=audio_callback)
    recording.start()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


# Function to stop recording and automatically transcribe
def stop_recording():
    global recording, recording_start_time
    print("Recording stopped.")
    recording.stop()
    recording.close()

    recording_end_time = datetime.datetime.now()
    duration = (recording_end_time - recording_start_time).total_seconds() / 60  # Duration in minutes

    # Convert the audio frames to a numpy array and save as WAV file
    audio_data = np.concatenate(audio_frames, axis=0)

    with wave.open(AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLERATE)
        wf.writeframes((audio_data * 32767).astype('int16').tobytes())

    file_size = os.path.getsize(AUDIO_FILE) / 1024  # in KB
    status_label.config(text=f"Recording stopped. File size: {file_size:.2f} KB", foreground="green")

    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

    # Automatically transcribe the audio in a separate thread
    threading.Thread(target=transcribe_audio, args=(duration,), daemon=True).start()


# Function to transcribe the recorded audio
def transcribe_audio(duration):
    try:
        root.after(0, lambda: status_label.config(text="Transcription in progress...", foreground="blue"))

        file_path = Path(AUDIO_FILE)
        with open(file_path, "rb") as audio_file_obj:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_obj
            )
        transcription_text = transcription.text

        root.after(0, lambda: transcription_box.delete(1.0, tk.END))
        root.after(0, lambda: transcription_box.insert(tk.END, transcription_text))

        # Copy to clipboard
        pyperclip.copy(transcription_text)

        # Save to history
        save_to_history(transcription_text, duration)

        # Save transaction and update cost
        save_transaction(duration)
        root.after(0, update_cost_display)

        # Update history display
        root.after(0, update_history_display)

        root.after(0, lambda: status_label.config(text="Transcription complete and copied to clipboard",
                                                  foreground="green"))
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Transcription Error", f"An error occurred: {e}"))
        root.after(0, lambda: status_label.config(text="Transcription failed", foreground="red"))


# Function to save transcription to history
def save_to_history(transcription, duration):
    history = load_history()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.append({
        "timestamp": timestamp,
        "duration": duration,
        "transcription": transcription
    })

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
        timestamp = entry['timestamp']
        transcription = entry['transcription']

        # Check if duration is available
        if 'duration' in entry:
            duration_str = f"(Duration: {entry['duration']:.2f} min)"
        else:
            duration_str = "(Duration: N/A)"

        history_box.insert(tk.END, f"{timestamp} {duration_str}:\n{transcription}\n\n")


# Function to save transaction
def save_transaction(duration):
    transactions = load_transactions()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cost = duration * COST_PER_MINUTE
    transactions.append({"timestamp": timestamp, "duration": duration, "cost": cost})

    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)


# Function to load transactions
def load_transactions():
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, 'r') as f:
            return json.load(f)
    return []


# Function to calculate total cost and time
def calculate_totals():
    transactions = load_transactions()
    total_cost = sum(transaction['cost'] for transaction in transactions)
    total_time = sum(transaction['duration'] for transaction in transactions)
    return total_cost, total_time


# Function to update cost display
def update_cost_display():
    total_cost, total_time = calculate_totals()
    cost_label.config(text=f"Total Time: {total_time:.2f} min | Total Cost: ${total_cost:.2f}")


# Create the main window
root = tk.Tk()
root.title("Audio Recorder with Transcription")
root.geometry("600x800")

style = ttk.Style()
style.theme_use('clam')

# Configure styles
style.configure("TButton", padding=10, font=('Helvetica', 12))
style.configure("TLabel", font=('Helvetica', 12))

# Create a main frame
main_frame = ttk.Frame(root, padding="20 20 20 20")
main_frame.pack(fill=tk.BOTH, expand=True)

# Add cost display label in the upper right corner
cost_label = ttk.Label(main_frame, text="Total Time: 0.00 min | Total Cost: $0.00", foreground="blue")
cost_label.pack(anchor='ne', pady=(0, 20))

# Add start/stop recording buttons
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)

start_button = ttk.Button(button_frame, text="Start Recording", command=start_recording)
start_button.pack(side=tk.LEFT, expand=True, padx=5)

stop_button = ttk.Button(button_frame, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, expand=True, padx=5)

# Add status label
status_label = ttk.Label(main_frame, text="Not recording", foreground="black")
status_label.pack(pady=10)

# Add transcription display box
transcription_label = ttk.Label(main_frame, text="Transcription:")
transcription_label.pack(anchor='w', pady=(20, 5))
transcription_box = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10, font=('Helvetica', 10))
transcription_box.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

# Add history display box
history_label = ttk.Label(main_frame, text="Transcription History:")
history_label.pack(anchor='w', pady=(0, 5))
history_box = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10, font=('Helvetica', 10))
history_box.pack(fill=tk.BOTH, expand=True)

# Initialize history display and cost display
update_history_display()
update_cost_display()

# Run the application
root.mainloop()