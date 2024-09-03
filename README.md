# Transcription App

This project is a transcription application that uses Streamlit for the web interface and OpenAI for transcription services.

## Prerequisites

- Python 3.x
- `pip` (Python package installer)
- `virtualenv` (optional but recommended)

## Setup

1. **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2. **Create a virtual environment (optional but recommended):**

    ```bash
    python -m venv .venv
    ```

3. **Activate the virtual environment:**

    - On macOS and Linux:

        ```bash
        source .venv/bin/activate
        ```

    - On Windows:

        ```bash
        .venv\Scripts\activate
        ```

4. **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1. **Run the application using the provided script:**

    ```bash
    ./run_app.sh
    ```

    This script will activate the virtual environment and start the Streamlit application.

2. **Access the application:**

    Open your web browser and go to `http://localhost:8501` to access the Streamlit application.

## File Descriptions

- `transcriber.py`: Main application file that contains the Streamlit app code.
- `requirements.txt`: Lists all the Python dependencies required for the project.
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `run_app.sh`: Shell script to activate the virtual environment and run the Streamlit app.

## Additional Notes

- Ensure that you have the necessary API keys and configurations set up for OpenAI in your environment.
- The `.gitignore` file is configured to ignore certain files and directories, including virtual environment directories and output files.