import os
import tempfile

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio(audio_file) -> str:
    """
    Converts Streamlit microphone audio into text using Groq Whisper.
    audio_file comes from st.audio_input().
    """
    if audio_file is None:
        return ""

    audio_bytes = audio_file.getvalue()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    with open(temp_audio_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3-turbo",
            response_format="text",
            language="en",
        )

    return transcription.strip()