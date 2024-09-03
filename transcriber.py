import streamlit as st
import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
import json
import datetime
import os
import time
import logging
import threading
import pyperclip

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
AUDIO_FILE = "output.wav"
SAMPLE_RATE = 44100
CHANNELS = 1
HISTORY_FILE = "transcription_history.json"
TRANSACTIONS_FILE = "transactions.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
COST_PER_MINUTE = 0.006

if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")


class AudioRecorder:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.is_recording = False
        self.audio_data = []

    def start_recording(self):
        self.audio_data = []
        self.is_recording = True
        threading.Thread(target=self._record).start()

    def _record(self):
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=self._audio_callback):
            while self.is_recording:
                sd.sleep(100)

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logging.warning(status)
        self.audio_data.append(indata.copy())

    def stop_recording(self):
        self.is_recording = False

    def save_audio(self):
        if not self.audio_data:
            raise ValueError("No audio data to save")
        audio = np.concatenate(self.audio_data, axis=0)
        sf.write(AUDIO_FILE, audio, SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE / 60  # duration in minutes
        return duration

    def transcribe_audio(self):
        with open(AUDIO_FILE, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcription.text

    @staticmethod
    def save_to_history(transcription, duration):
        history = AudioRecorder.load_history()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append({"timestamp": timestamp, "duration": duration, "transcription": transcription})
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []

    @staticmethod
    def save_transaction(duration):
        transactions = AudioRecorder.load_transactions()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cost = duration * COST_PER_MINUTE
        transactions.append({"timestamp": timestamp, "duration": duration, "cost": cost})
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)
        logging.info(f"Transaction saved: duration={duration}, cost=${cost:.4f}")

    @staticmethod
    def load_transactions():
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r') as f:
                return json.load(f)
        return []


def get_transcription_preview(transcription, max_length=50):
    """Generate a preview of the transcription."""
    if len(transcription) > max_length:
        return transcription[:max_length] + "..."
    return transcription


def main():
    st.set_page_config(page_title="Audio Recorder with Transcription", layout="wide")
    st.title("Audio Recorder with Transcription")

    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioRecorder()

    # Display total time and cost
    transactions = AudioRecorder.load_transactions()
    total_cost = sum(transaction.get('cost', 0) for transaction in transactions)
    total_time = sum(transaction.get('duration', 0) for transaction in transactions)
    st.sidebar.write(f"Total Time: {total_time:.2f} min | Total Cost: ${total_cost:.2f}")

    # Create two columns for layout
    col1, col2 = st.columns([1, 2])

    with col1:
        # Record button - made more prominent
        button_color = "red" if st.session_state.recorder.is_recording else "green"
        button_text = "Stop Recording" if st.session_state.recorder.is_recording else "Start Recording"
        if st.button(button_text, key="record_button", help="Click to start or stop recording",
                     use_container_width=True):
            try:
                if not st.session_state.recorder.is_recording:
                    st.session_state.recorder.start_recording()
                    st.session_state.recording_start_time = time.time()
                else:
                    st.session_state.recorder.stop_recording()
                    duration = st.session_state.recorder.save_audio()
                    st.session_state.audio_duration = duration
                    st.session_state.audio_saved = True

                    # Automatic transcription
                    with st.spinner("Transcribing..."):
                        transcription = st.session_state.recorder.transcribe_audio()
                        AudioRecorder.save_to_history(transcription, duration)
                        AudioRecorder.save_transaction(duration)
                        st.session_state.transcription = transcription

                        # Copy to clipboard
                        pyperclip.copy(transcription)
                        st.success("Transcription copied to clipboard!")
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logging.error(f"Recording error: {str(e)}")

        # Display recording status
        if st.session_state.recorder.is_recording:
            st.write("Recording in progress...")
        elif hasattr(st.session_state, 'audio_saved') and st.session_state.audio_saved:
            st.write("Recording saved and transcribed. Transcription copied to clipboard.")

    with col2:
        # Display latest transcription
        if hasattr(st.session_state, 'transcription'):
            st.subheader("Latest Transcription:")
            st.text_area("Latest transcription", value=st.session_state.transcription, height=200,
                         key="latest_transcription")

    # Display history in a more compact form with previews
    st.subheader("Transcription History:")
    history = AudioRecorder.load_history()
    for index, entry in enumerate(reversed(history)):
        timestamp = entry.get('timestamp', 'Unknown Date')
        transcription = entry.get('transcription', 'No transcription available')
        duration = entry.get('duration', 'Unknown')
        duration_str = f"{duration:.2f} min" if isinstance(duration, (int, float)) else str(duration)
        preview = get_transcription_preview(transcription)

        with st.expander(f"{timestamp} (Duration: {duration_str}): {preview}"):
            st.text_area(f"Transcription {index}", value=transcription, height=100, key=f"history_{index}")


if __name__ == "__main__":
    main()