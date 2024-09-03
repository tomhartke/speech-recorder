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
import queue
import logging
import time

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.style.configure("Record.TButton", background="green", foreground="white", font=('Helvetica', 12, 'bold'))
        self.style.configure("Stop.TButton", background="red", foreground="white", font=('Helvetica', 12, 'bold'))

        self.main_frame = ttk.Frame(master, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.cost_label = ttk.Label(self.main_frame, text="Total Time: 0.00 min | Total Cost: $0.00")
        self.cost_label.pack(anchor='ne', pady=(0, 20))

        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.toggle_button = ttk.Button(self.button_frame, text="Record", command=self.toggle_recording,
                                        style="Record.TButton")
        self.toggle_button.pack(expand=True, padx=5)

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
        self.is_recording = False
        self.state = "ready"
        self.client = None
        self.update_queue = queue.Queue()
        self.api_call_count = 0
        self.last_click_time = 0
        self.click_cooldown = 0.5  # 500ms cooldown between clicks

        # Bind focus events
        self.master.bind("<FocusIn>", self.on_focus_in)
        self.master.bind("<FocusOut>", self.on_focus_out)

        # Initialize in a separate thread
        threading.Thread(target=self.initialize, daemon=True).start()

        # Start the update loop
        self.update_loop()

    def initialize(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.update_queue.put(("update_history_display", ()))
        self.update_queue.put(("update_cost_display", ()))
        self.update_queue.put(("update_status", ("Ready",)))

    def update_loop(self):
        try:
            while True:
                method, args = self.update_queue.get_nowait()
                logging.debug(f"Executing: {method} with args: {args}")
                getattr(self, method)(*args)
                self.update_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error in update_loop: {e}")
        finally:
            self.master.after(50, self.update_loop)

    def on_focus_in(self, event):
        logging.info("Application regained focus")
        self.update_queue.put(("check_state", ()))

    def on_focus_out(self, event):
        logging.info("Application lost focus")

    def check_state(self):
        logging.info(f"Checking state: {self.state}")
        if self.state == "ready":
            self.enable_button()
        elif self.state == "recording":
            self.update_button("Stop", "Stop.TButton")
        else:
            self.update_button("Record", "Record.TButton", tk.DISABLED)

    def toggle_recording(self):
        current_time = time.time()
        if current_time - self.last_click_time < self.click_cooldown:
            logging.debug("Click ignored due to cooldown")
            return
        self.last_click_time = current_time

        logging.debug(f"Toggle recording called. Current state: {self.state}")
        if self.state == "recording":
            self.stop_recording()
        elif self.state == "ready":
            self.start_recording()
        else:
            logging.warning(f"Toggle recording called in unexpected state: {self.state}")

    def start_recording(self):
        logging.info("Starting recording")
        self.audio_data = []
        self.recording = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=self.audio_callback)
        self.recording.start()
        self.update_queue.put(("update_status", ("Recording...",)))
        self.update_queue.put(("update_button", ("Stop", "Stop.TButton")))
        self.state = "recording"

    def audio_callback(self, indata, frames, time, status):
        self.audio_data.append(indata.copy())

    def stop_recording(self):
        logging.info("Stopping recording")
        if self.recording:
            self.recording.stop()
            self.recording.close()
        self.update_queue.put(("update_status", ("Processing...",)))
        self.update_queue.put(("update_button", ("Record", "Record.TButton", tk.DISABLED)))
        self.state = "processing"
        threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        logging.info("Processing audio")
        audio = np.concatenate(self.audio_data, axis=0)
        duration = len(audio) / SAMPLE_RATE / 60  # duration in minutes
        sf.write(AUDIO_FILE, audio, SAMPLE_RATE)
        self.transcribe_audio(duration)

    def transcribe_audio(self, duration):
        try:
            logging.info("Starting transcription")
            with open(AUDIO_FILE, "rb") as audio_file:
                self.api_call_count += 1
                logging.info(f"Making API call #{self.api_call_count}")
                transcription = self.client.audio.transcriptions.create(model="whisper-1", file=audio_file)

            transcription_text = transcription.text
            self.update_queue.put(("update_transcription", (transcription_text,)))
            pyperclip.copy(transcription_text)

            self.save_to_history(transcription_text, duration)
            self.save_transaction(duration)
            self.update_queue.put(("update_history_display", ()))
            self.update_queue.put(("update_cost_display", ()))

            self.update_queue.put(("update_status", ("Transcription complete",)))

            # Delay re-enabling the button
            self.master.after(1000, lambda: self.update_queue.put(("enable_button", ())))

            logging.info("Transcription complete")
        except Exception as e:
            logging.error(f"Error in transcribe_audio: {e}")
            self.update_queue.put(("show_error", ("Transcription Error", f"An error occurred: {e}")))
            self.update_queue.put(("update_status", ("Transcription failed",)))
            self.update_queue.put(("enable_button", ()))

    def update_status(self, text):
        self.status_label.config(text=text)

    def update_button(self, text, style, state=tk.NORMAL):
        self.toggle_button.config(text=text, style=style, state=state)

    def enable_button(self):
        logging.info("Enabling record button")
        self.toggle_button.config(text="Record", style="Record.TButton", state=tk.NORMAL)
        self.state = "ready"

    def update_transcription(self, text):
        self.transcription_box.delete(1.0, tk.END)
        self.transcription_box.insert(tk.END, text)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

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
        logging.info(f"Transaction saved: duration={duration}, cost=${cost:.4f}")

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