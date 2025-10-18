# app.py

import streamlit as st
import speech_recognition as sr
import io
import pydub
from datetime import timedelta

# --- CRITICAL FIX: Removed Live Transcription Imports as the feature is disabled ---

# --- Custom Styling for an Amazing GUI ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* 1. Page Background and Typography */
        .stApp {
            background-color: #f0f2f6; /* Light gray background */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* 2. Custom Header Styling */
        h1 {
            color: #1f77b4; /* A vibrant blue color */
            border-bottom: 2px solid #1f77b4;
            padding-bottom: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        
        /* 3. Button Styling (Primary/Start Transcription) */
        .stButton>button {
            background-color: #0c9955; /* A strong green */
            color: white !important;
            font-weight: bold;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            font-size: 16px;
        }
        .stButton>button:hover {
            background-color: #097d44; /* Darker green on hover */
            box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
        }
        
        /* 5. Text Area Styling (Result Box) */
        .stTextArea textarea {
            border: 2px solid #1f77b4;
            border-radius: 8px;
            padding: 15px;
            font-size: 16px;
            background-color: #ffffff;
            min-height: 250px;
        }
        
        /* Container Styling */
        .stContainer {
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 10px;
            background-color: #ffffff;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
        }
        </style>
        """, unsafe_allow_html=True)

# --- Configuration and Setup ---
st.set_page_config(
    page_title="MANDEM's Speech-to-Text & Subtitle Generator",
    page_icon="👑"
)

# --- Helper Function for SRT Format ---

def format_timedelta(td):
    """Converts timedelta object to SRT time format: HH:MM:SS,mmm"""
    # Calculate hours, minutes, seconds, and milliseconds
    total_seconds = int(td.total_seconds())
    milliseconds = td.microseconds // 1000
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Format to "HH:MM:SS,mmm"
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def format_to_srt(transcribed_chunks):
    """
    Takes a list of (start_time, end_time, text) tuples and formats them into an SRT string.
    """
    srt_content = ""
    for i, (start_ms, end_ms, text) in enumerate(transcribed_chunks):
        # Convert milliseconds to timedelta objects
        start_time = timedelta(milliseconds=start_ms)
        end_time = timedelta(milliseconds=end_ms)
        
        # Format the SRT block
        srt_content += f"{i + 1}\n"
        srt_content += f"{format_timedelta(start_time)} --> {format_timedelta(end_time)}\n"
        srt_content += f"{text}\n\n"
        
    return srt_content

# --- Core Logic Function: Transcribe and Generate Subtitles ---

def process_media_for_subtitles(uploaded_file, language_code):
    """
    Handles file loading, audio extraction (if video), chunking, and transcription
    to generate text and SRT data with timestamps.
    
    The 'language_code' parameter is now required for accurate transcription.
    """
    
    r = sr.Recognizer()
    # language_code is now passed in as an argument
    chunk_size_ms = 8000  # 8 seconds per chunk for better accuracy and timestamp granularity
    
    # 1. Load the media file and extract the audio stream
    try:
        st.info("Step 1/3: Processing media file and extracting audio...")
        # pydub can automatically read audio from many video containers (MP4, MOV, etc.) 
        # as long as FFmpeg is available on the system.
        audio_segment = pydub.AudioSegment.from_file(io.BytesIO(uploaded_file.read()))
        total_duration_ms = len(audio_segment)
        st.success(f"Audio loaded. Total duration: {total_duration_ms / 1000:.1f} seconds.")
        
    except pydub.exceptions.CouldntDecodeError:
        return None, None, "ERROR: Could not decode the file. Ensure it is a valid audio/video format and that FFmpeg is installed."
    except Exception as e:
        return None, None, f"An unexpected error occurred during audio processing: {e}"

    
    transcribed_chunks = []
    full_transcript = []
    
    # 2. Chunk the audio and transcribe sequentially
    st.info(f"Step 2/3: Starting transcription in {chunk_size_ms/1000:.0f} second chunks...")
    progress_bar = st.progress(0)
    
    # Iterate through the audio in fixed chunks
    for i, start_ms in enumerate(range(0, total_duration_ms, chunk_size_ms)):
        end_ms = min(start_ms + chunk_size_ms, total_duration_ms)
        chunk = audio_segment[start_ms:end_ms]
        
        # Convert the pydub chunk to a format speech_recognition can use (WAV)
        wav_io = io.BytesIO()
        chunk.export(wav_io, format="wav")
        wav_io.seek(0)
        
        try:
            with sr.AudioFile(wav_io) as source:
                audio_data = r.record(source)
                
            # Perform the Recognition, using the selected language code
            chunk_text = r.recognize_google(audio_data, language=language_code)
            
            # Store the chunk data for SRT and full transcript
            if chunk_text:
                transcribed_chunks.append((start_ms, end_ms, chunk_text))
                full_transcript.append(chunk_text)
                
        except sr.UnknownValueError:
            # If a chunk is silent or unclear, skip it but still update the progress
            pass
        except sr.RequestError as e:
            return None, None, f"ERROR: Google Speech Recognition failed on chunk {i+1}. Details: {e}"
        
        # Update progress bar
        progress = (end_ms / total_duration_ms)
        progress_bar.progress(progress)


    progress_bar.empty()
    st.success("Step 3/3: Transcription completed for all chunks.")
    
    # 3. Compile final outputs
    final_text = " ".join(full_transcript)
    srt_content = format_to_srt(transcribed_chunks)
    
    return final_text, srt_content, None # Return transcript, srt, and no error

# --- Streamlit User Interface ---

def main():
    """
    Sets up the Streamlit user interface elements.
    """
    
    # Inject CSS at the start
    inject_custom_css()
    
    # 1. Title and Description
    st.title("🎤 MANDEM's Speech-to-Text & Subtitle Generator")
    st.markdown("---")
    st.markdown("""
        Upload an **Audio** (WAV, MP3) or **Video** (MP4, MOV, AVI) file below. 
        The app will generate both a full transcript and a downloadable SRT subtitle file.
        """, unsafe_allow_html=False)
    
    # --- File Uploader Widget ---
    
    st.subheader("📁 Audio/Video File Uploader")
    with st.container(border=True):
        
        # --- Language Selection Widget (NEW) ---
        language_options = {
            "English (US)": "en-US",
            "Spanish (Spain)": "es-ES",
            "French (France)": "fr-FR",
            "German (Germany)": "de-DE",
            "Mandarin (China)": "zh-CN",
            "Japanese (Japan)": "ja-JP",
            "Portuguese (Brazil)": "pt-BR",
            "Nigerian English": "en-NG", # Added regional English variant for fun
            "Yoruba (Nigeria)": "yo-NG"  # Added a local Nigerian language
        }
        
        selected_language_name = st.selectbox(
            "Select the Language Spoken in the Media:",
            options=list(language_options.keys()),
            index=0 # Default to English (US)
        )
        selected_language_code = language_options[selected_language_name]
        st.info(f"Using Google Speech Recognition for **{selected_language_name}**.")
        # --- End Language Selection Widget ---

        uploaded_file = st.file_uploader(
            "Choose a media file...", 
            type=['wav', 'mp3', 'mp4', 'mov', 'avi'], # Added video formats
            help="Supported file types: Audio (WAV, MP3) and Video (MP4, MOV, AVI)."
        )

        if uploaded_file is not None:
            
            # Display the uploaded file information
            st.markdown(f"**File Name:** `{uploaded_file.name}`")
            st.markdown(f"**File Type:** `{uploaded_file.type}`")
            
            # Display media player
            try:
                # Reset file pointer for the audio player
                uploaded_file.seek(0)
                audio_bytes = uploaded_file.read()
                st.audio(audio_bytes, format=uploaded_file.type, start_time=0)
            except Exception:
                st.warning("Could not display media preview.")
                
            # Reset file pointer for processing
            uploaded_file.seek(0)
            
            # 4. Transcription Button
            if st.button("🚀 Generate Transcript and Subtitles"):
                
                with st.spinner("Starting media processing... (Requires FFmpeg for video/MP3)"):
                    # Call the core logic function, passing the selected language code (UPDATED CALL)
                    final_text, srt_content, error_message = process_media_for_subtitles(uploaded_file, selected_language_code)
                
                # 5. Display Results
                st.subheader("📝 Results")
                
                if error_message:
                    st.error(error_message)
                else:
                    st.success("Transcription and Subtitle Generation Complete!")
                    
                    col_text, col_srt = st.columns(2)
                    
                    with col_text:
                        st.markdown("##### Full Transcribed Text")
                        st.text_area(
                            "Full Transcript", 
                            final_text, 
                            height=350, 
                            help="The complete text generated from the media."
                        )
                        
                    with col_srt:
                        st.markdown("##### SRT Subtitle File Content")
                        st.text_area(
                            "SRT Output", 
                            srt_content, 
                            height=350,
                            help="The SubRip Subtitle file format, ready for download."
                        )
                        
                        # Provide Download Button for SRT file
                        st.download_button(
                            label="⬇️ Download SRT Subtitle File",
                            data=srt_content,
                            file_name=f"{uploaded_file.name.split('.')[0]}.srt",
                            mime="text/plain"
                        )
                    
        else:
            st.info("Upload your media file above to begin the transcription and subtitling process.")

# Execute the main function when the script is run
if __name__ == "__main__":
    main()
