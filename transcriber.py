import sounddevice as sd
import wave
import tkinter as tk
from tkinter import messagebox

# Constants
AUDIO_FILE = "output.wav"
SAMPLERATE = 44100

recording = None


# Function to start recording
def start_recording():
    global recording
    print("Recording started...")
    recording = sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32')
    recording.start()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


# Function to stop recording
def stop_recording():
    global recording
    print("Recording stopped.")
    audio_data = recording.read(int(SAMPLERATE * recording.latency))[0]
    recording.stop()

    # Save as WAV file
    with wave.open(AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLERATE)
        wf.writeframes((audio_data * 32767).astype('int16').tobytes())

    messagebox.showinfo("Recording Complete", f"Audio saved to {AUDIO_FILE}")
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
