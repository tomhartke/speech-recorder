import os
import sounddevice as sd
import soundfile as sf
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from openai import OpenAI
import json
import datetime
import pyperclip
import threading

# Constants
AUDIO_FILE = "output.wav"
SAMPLE_RATE = 44100
HISTORY_FILE = "transcription_history.json"
TRANSACTIONS_FILE = "transactions.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
COST_PER_MINUTE = 0.006

if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")


class AudioRecorderApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Recorder with Transcription")
        master.geometry("600x800")

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure button styles
        self.style.configure("Record.TButton", background="red", foreground="white")
        self.style.configure("Stop.TButton", background="gray", foreground="white")

        self.main_frame = ttk.Frame(master, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.cost_label = ttk.Label(self.main_frame, text="Total Time: 0.00 min | Total Cost: $0.00")
        self.cost_label.pack(anchor='ne', pady=(0, 20))

        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.start_button = ttk.Button(self.button_frame, text="Record", command=self.start_recording,
                                       style="Record.TButton")
        self.start_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.stop_button = ttk.Button(self.button_frame, text="Stop", command=self.stop_recording, state=tk.DISABLED,
                                      style="Stop.TButton")
        self.stop_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.status_label = ttk.Label(self.main_frame, text="Not recording")
        self.status_label.pack(pady=10)

        self.transcription_label = ttk.Label(self.main_frame, text="Transcription:")
        self.transcription_label.pack(anchor='w', pady=(20, 5))
        self.transcription_box = tk.Text(self.main_frame, wrap=tk.WORD, height=10)
        self.transcription_box.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        self.history_label = ttk.Label(self.main_frame, text="Transcription History:")
        self.history_label.pack(anchor='w', pady=(0, 5))
        self.history_box = tk.Text(self.main_frame, wrap=tk.WORD, height=10)
        self.history_box.pack(fill=tk.BOTH, expand=True)

        self.recording = None
        self.audio_data = []

        # Initialize in a separate thread
        threading.Thread(target=self.initialize, daemon=True).start()

    def initialize(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.update_history_display()
        self.update_cost_display()
        self.master.after(0, lambda: self.status_label.config(text="Ready"))

    def start_recording(self):
        self.audio_data = []
        self.recording = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=self.audio_callback)
        self.recording.start()
        self.status_label.config(text="Recording...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def audio_callback(self, indata, frames, time, status):
        self.audio_data.append(indata.copy())

    def stop_recording(self):
        if self.recording:
            self.recording.stop()
            self.recording.close()
        self.status_label.config(text="Processing...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        audio = np.concatenate(self.audio_data, axis=0)
        duration = len(audio) / SAMPLE_RATE / 60  # duration in minutes
        sf.write(AUDIO_FILE, audio, SAMPLE_RATE)
        self.transcribe_audio(duration)

    def transcribe_audio(self, duration):
        try:
            with open(AUDIO_FILE, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(model="whisper-1", file=audio_file)

            transcription_text = transcription.text
            self.master.after(0, lambda: self.transcription_box.delete(1.0, tk.END))
            self.master.after(0, lambda: self.transcription_box.insert(tk.END, transcription_text))
            pyperclip.copy(transcription_text)

            self.save_to_history(transcription_text, duration)
            self.save_transaction(duration)
            self.master.after(0, self.update_history_display)
            self.master.after(0, self.update_cost_display)

            self.master.after(0, lambda: self.status_label.config(text="Transcription complete"))
            self.master.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Transcription Error", f"An error occurred: {e}"))
            self.master.after(0, lambda: self.status_label.config(text="Transcription failed"))
            self.master.after(0, lambda: self.start_button.config(state=tk.NORMAL))

    def save_to_history(self, transcription, duration):
        history = self.load_history()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append({"timestamp": timestamp, "duration": duration, "transcription": transcription})
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []

    def update_history_display(self):
        history = self.load_history()
        self.history_box.delete(1.0, tk.END)
        for entry in reversed(history):
            timestamp = entry['timestamp']
            transcription = entry['transcription']
            duration = entry.get('duration', 'N/A')
            duration_str = f"(Duration: {duration:.2f} min)" if isinstance(duration,
                                                                           (int, float)) else f"(Duration: {duration})"
            self.history_box.insert(tk.END, f"{timestamp} {duration_str}:\n{transcription}\n\n")

    def save_transaction(self, duration):
        transactions = self.load_transactions()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cost = duration * COST_PER_MINUTE
        transactions.append({"timestamp": timestamp, "duration": duration, "cost": cost})
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)

    def load_transactions(self):
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r') as f:
                return json.load(f)
        return []

    def update_cost_display(self):
        transactions = self.load_transactions()
        total_cost = sum(transaction['cost'] for transaction in transactions)
        total_time = sum(transaction['duration'] for transaction in transactions)
        self.cost_label.config(text=f"Total Time: {total_time:.2f} min | Total Cost: ${total_cost:.2f}")


root = tk.Tk()
app = AudioRecorderApp(root)
root.mainloop()