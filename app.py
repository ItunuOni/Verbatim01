import streamlit as st
import speech_recognition as sr
import io
import pydub
from datetime import timedelta
import time
import requests
import base64
import re # Import the regex module for extracting sample rate

# --- Thread Safety Mock (Required for Streamlit background jobs) ---
try:
    from streamlit.runtime.scriptrunner.script_run_context import get_script_run_context
except ImportError:
    def get_script_run_context():
        return None

# --- LANGUAGE & CONFIGURATION DICTIONARIES (Global for clarity/efficiency) ---
# Expanded languages for transcription
TRANSCRIPTION_LANGUAGES = {
    "English (US)": "en-US",
    "Spanish (Spain)": "es-ES",
    "French (France)": "fr-FR",
    "German (Germany)": "de-DE",
    "Italian (Italy)": "it-IT",
    "Russian (Russia)": "ru-RU",
    "Mandarin (China)": "zh-CN",
    "Japanese (Japan)": "ja-JP",
    "Korean (South Korea)": "ko-KR", 
    "Turkish (Turkey)": "tr-TR", 
    "Thai (Thailand)": "th-TH", 
    "Portuguese (Brazil)": "pt-BR",
    "Nigerian English": "en-NG",
    "Yoruba (Nigeria)": "yo-NG",
    "Hindi (India)": "hi-IN",
    "Swahili (Tanzania)": "sw-TZ",
    "Arabic (Saudi Arabia)": "ar-SA"
}

# Expanded languages for translation (Gemini API)
TRANSLATION_LANGUAGES = {
    "None (Show Original)": "original",
    "Spanish (es)": "es",
    "French (fr)": "fr",
    "German (de)": "de",
    "Italian (it)": "it",
    "Russian (ru)": "ru",
    "Portuguese (pt)": "pt",
    "Hindi (hi)": "hi",
    "Arabic (ar)": "ar",
    "Yoruba (yo)": "yo",
    "Hausa (ha)": "ha",
    "Korean (ko)": "ko", 
    "Turkish (tr)": "tr", 
    "Japanese (ja)": "ja", 
    "Mandarin (zh)": "zh", 
}

# Expanded voices for TTS (Text-to-Speech)
TTS_VOICES = {
    "Kore (Firm/Standard)": "Kore",      # Voice: Kore (Firm)
    "Puck (Upbeat)": "Puck",            # Voice: Puck (Upbeat)
    "Zephyr (Bright)": "Zephyr",        # Voice: Zephyr (Bright)
    "Charon (Informative)": "Charon",   # Voice: Charon (Informative)
    "Orus (Authoritative)": "Orus",     
    "Aoede (Breezy)": "Aoede",          
    "Iapetus (Clear)": "Iapetus",       
    "Algieba (Smooth)": "Algieba",      
    "Leda (Youthful)": "Leda",
    "Fenrir (Excitable)": "Fenrir",
    "Achernar (Soft)": "Achernar"
}
TTS_SAMPLE_TEXT = "Hello! This is a voice sample from the ManDem's Text-to-Speech model. I should sound natural."
# -----------------------------------------------------------

# --- Custom Styling for an Amazing GUI ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* 1. Page Background and Typography (LIGHT MODE DEFAULTS) */
        .stApp {
            background-color: #f0f2f6; /* Light gray background */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #1a1a1a; /* Default dark text */
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
            background-color: #ffffff; /* White background in light mode */
            min-height: 200px; /* Adjusted height */
        }
        
        /* Container Styling */
        .stContainer {
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 10px;
            background-color: #ffffff; /* White background in light mode */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
        }

        /* ------------------------------------------------------------------- */
        /* --- DARK MODE OVERRIDES (FIX FOR READABILITY) --------------------- */
        /* ------------------------------------------------------------------- */
        @media (prefers-color-scheme: dark) {
            /* Global App background and text in Dark Mode */
            .stApp {
                background-color: #1e1e1e; /* Dark app background */
                color: #f0f0f0 !important; /* Light text color */
            }

            /* Headers need color update to be visible against dark background */
            h1 {
                color: #6daae3 !important; /* Lighter blue for dark mode header */
                border-bottom-color: #6daae3 !important; 
            }
            
            /* Containers and Text Areas in Dark Mode */
            .stContainer, .stTextArea textarea {
                background-color: #2c2c2c !important; /* Slightly lighter dark background for card/elements */
                border-color: #555555 !important; /* Visible border */
                color: #f0f0f0 !important; /* Ensure content text is light */
            }
        }
        /* ------------------------------------------------------------------- */

        </style>
        """, unsafe_allow_html=True)

# --- Helper Function for SRT Format ---

def format_timedelta(td):
    """Converts timedelta object to SRT time format: HH:MM:SS,mmm"""
    total_seconds = int(td.total_seconds())
    milliseconds = td.microseconds // 1000
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def format_to_srt(transcribed_chunks):
    """
    Takes a list of (start_time, end_time, text) tuples and formats them into an SRT string.
    """
    srt_content = ""
    for i, (start_ms, end_ms, text) in enumerate(transcribed_chunks):
        start_time = timedelta(milliseconds=start_ms)
        end_time = timedelta(milliseconds=end_ms)
        
        srt_content += f"{i + 1}\n"
        srt_content += f"{format_timedelta(start_time)} --> {format_timedelta(end_time)}\n"
        srt_content += f"{text}\n\n"
        
    return srt_content


# --- API FUNCTIONS ---

def get_api_config():
    """Retrieves API key and model name from Streamlit secrets."""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        model_name = st.secrets.get("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-09-2025")
        
        if not api_key:
            # If the key is not in st.secrets (either local or cloud), return an error message
            return "ERROR: Gemini API Key not found in Streamlit secrets.", model_name
            
        return api_key, model_name
    except Exception as e:
        # Catch any unexpected errors during secrets access
        return f"ERROR: Gemini API Key configuration failed: {e}", ""

def translate_text(text, target_code):
    """
    Translates text using the Gemini API with retries and a final Google Search grounding fallback
    in case of persistent server errors (503/429).
    """
    if not text or target_code == "original":
        return text

    api_key, model_name = get_api_config()
    if api_key.startswith("ERROR"):
        return api_key

    # --- 1. PRIMARY ATTEMPTS (DIRECT API CALL with Backoff) ---
    system_prompt = f"You are a professional translator. Translate the following text into the language code '{target_code}'. Only return the translated text."
    user_query = f"Translate the following: {text}"
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    MAX_ATTEMPTS = 5
    last_error_status = None
    
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(apiUrl, headers={'Content-Type': 'application/json'}, json=payload, timeout=30)
            
            if response.status_code == 403:
                return "ERROR 403: Forbidden. The provided Gemini API Key is invalid or restricted."
            
            # Check for server-side issues (5xx) or rate limiting (429)
            if response.status_code >= 500 or response.status_code == 429:
                last_error_status = response.status_code
                if attempt < MAX_ATTEMPTS - 1: # Retry condition
                    # Exponential backoff: 2, 4, 8, 16 seconds
                    wait_time = 2 * (2 ** attempt)
                    time.sleep(wait_time)
                    continue 
                else:
                    # Last attempt failed, break loop to go to fallback
                    break 
            
            response.raise_for_status() # Raise for other unhandled 4xx errors
            
            result = response.json()
            translated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Translation not found.')
            return translated_text

        except requests.exceptions.RequestException as e:
            last_error_status = str(e)
            if attempt < MAX_ATTEMPTS - 1: 
                 wait_time = 2 * (2 ** attempt)
                 time.sleep(wait_time)
                 continue 
            # Last attempt failed due to request error, break loop to go to fallback
            break
        except Exception as e:
            return f"Translation API Call Failed: {e}"
    
    # --- 2. FALLBACK ATTEMPT (Using Google Search Grounding) ---
    # This might hit a different internal endpoint and bypass the rate limit/503.
    if last_error_status in [429, 503, 500] or "Service Unavailable" in str(last_error_status):
        st.warning(f"Primary Translation failed after {MAX_ATTEMPTS} attempts due to **{last_error_status}**. Attempting final fallback via Google Search grounding...")
        
        fallback_prompt = f"Translate the following text into the language code '{target_code}'. Only return the translated text: {text}"
        
        fallback_payload = {
            "contents": [{"parts": [{"text": fallback_prompt}]}],
            "tools": [{"google_search": {}}], # Adding the search tool
            "systemInstruction": {"parts": [{"text": "You are a professional translator. Use your internal knowledge and the grounding tool to translate the user's text accurately."}]},
        }

        try:
            # Single attempt for the fallback
            response = requests.post(apiUrl, headers={'Content-Type': 'application/json'}, json=fallback_payload, timeout=45) 
            response.raise_for_status() 

            fallback_result = response.json()
            fallback_text = fallback_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Translation not found in fallback.')
            
            if fallback_text and fallback_text != 'Translation not found in fallback.':
                st.success("Fallback translation successful!")
                return fallback_text
            
        except requests.exceptions.RequestException as e:
            return f"Translation API Call Failed after fallback attempt (Status: {last_error_status} -> Fallback Error: {e})"
        except Exception as e:
            return f"Translation API Call Failed after fallback attempt (Status: {last_error_status} -> Fallback Error: {e})"

    # If the function reaches here, all attempts failed
    return f"Translation API Call Failed after multiple attempts (Status: {last_error_status}). Please wait and try again."


def generate_tts_audio(text, voice_name, emotion_prompt=""):
    """
    Generates a voice-over audio file from text using the Gemini TTS API, then 
    uses pydub to safely convert the raw PCM data to WAV bytes.
    """
    if not text:
        return "ERROR: Please provide text to synthesize."
    
    api_key, _ = get_api_config()
    if api_key.startswith("ERROR"):
        return api_key

    model_name = "gemini-2.5-flash-preview-tts"
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    # Use emotion prompt if provided, otherwise use a neutral instruction
    if emotion_prompt:
        # Ensure the prompt is safe and clear for the model
        prompt = f"Say with a tone of '{emotion_prompt}': {text}"
    else:
        prompt = f"Say clearly and confidently: {text}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": { "voiceName": voice_name } 
                }
            }
        },
        "model": model_name
    }

    # Increased to 5 attempts for better resilience against 503 errors
    MAX_ATTEMPTS = 5
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(apiUrl, headers={'Content-Type': 'application/json'}, json=payload, timeout=60)
            
            if response.status_code == 403:
                return "ERROR 403: Forbidden. Check your Gemini API Key."
            
            # Check for server-side issues (500s) or rate limiting (429)
            if response.status_code >= 500 or response.status_code == 429:
                 if attempt < MAX_ATTEMPTS - 1: # Retry condition
                    wait_time = 2 * (2 ** attempt)
                    time.sleep(wait_time)
                    continue # Retry
            
            response.raise_for_status() 
            result = response.json()
            
            audio_part = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0]
            base64_data = audio_part.get('inlineData', {}).get('data')
            mime_type = audio_part.get('inlineData', {}).get('mimeType') # Get the full MIME type

            if base64_data and mime_type:
                
                # Extract sample rate from MIME type (e.g., 'audio/L16;rate=16000')
                rate_match = re.search(r'rate=(\d+)', mime_type)
                
                if not rate_match:
                    return f"ERROR: Could not determine sample rate from MIME type: {mime_type}"

                sample_rate = int(rate_match.group(1))
                
                # 1. Decode base64 to raw PCM bytes
                raw_pcm_data = base64.b64decode(base64_data)
                
                # 2. Use pydub to reliably create a WAV file from the raw 16-bit PCM
                # The API returns 16-bit signed PCM (sample_width=2), mono (channels=1).
                audio_segment = pydub.AudioSegment.from_raw(
                    io.BytesIO(raw_pcm_data), 
                    sample_width=2, 
                    frame_rate=sample_rate, # Use extracted sample rate
                    channels=1, 
                    format='raw'
                )
                
                # 3. Export the pydub segment to a byte array in WAV format
                wav_io = io.BytesIO()
                audio_segment.export(wav_io, format="wav")
                return wav_io.getvalue()

            else:
                return "ERROR: TTS API returned no audio data or MIME type."

        except requests.exceptions.RequestException as e:
            if attempt < MAX_ATTEMPTS - 1: # Retry condition
                wait_time = 2 * (2 ** attempt) 
                time.sleep(wait_time) 
                continue
            return f"TTS API Call Failed after multiple attempts: {e}"
        except Exception as e:
            # Handle pydub or other conversion errors here
            return f"Audio conversion or API Call Failed: {e}"
    
    return "TTS generation failed due to unknown error after all retries."


# --- Core Logic Function: Transcribe and Generate Subtitles ---

def process_media_for_subtitles(uploaded_file, language_code):
    """
    Handles file loading, audio extraction (if video), chunking, and transcription
    to generate text and SRT data with timestamps.
    """
    
    r = sr.Recognizer()
    chunk_size_ms = 8000  # 8 seconds per chunk for better accuracy and timestamp granularity
    
    # 1. Load the media file and extract the audio stream
    try:
        st.info("Step 1/3: Processing media file and extracting audio...")
        uploaded_file.seek(0) 
        # Note: We must read the file fully into memory for pydub to handle seekable IO
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
    
    for i, start_ms in enumerate(range(0, total_duration_ms, chunk_size_ms)):
        end_ms = min(start_ms + chunk_size_ms, total_duration_ms)
        chunk = audio_segment[start_ms:end_ms]
        
        wav_io = io.BytesIO()
        # Exporting to raw WAV format for speech_recognition library compatibility
        chunk.export(wav_io, format="wav")
        wav_io.seek(0)
        
        try:
            with sr.AudioFile(wav_io) as source:
                audio_data = r.record(source)
                
            chunk_text = r.recognize_google(audio_data, language=language_code)
            
            if chunk_text:
                transcribed_chunks.append((start_ms, end_ms, chunk_text))
                full_transcript.append(chunk_text)
                
        except sr.UnknownValueError:
            # Ignore chunks where no speech was detected
            pass
        except sr.RequestError as e:
            return None, None, f"ERROR: Google Speech Recognition failed on chunk {i+1}. Details: {e}"
        
        progress = (end_ms / total_duration_ms)
        progress_bar.progress(progress)


    progress_bar.empty()
    st.success("Step 3/3: Transcription completed for all chunks.")
    
    # 3. Compile final outputs
    final_text = " ".join(full_transcript)
    srt_content = format_to_srt(transcribed_chunks)
    
    return final_text, srt_content, None 

# --- Streamlit User Interface ---

def main():
    
    inject_custom_css()
    
    st.set_page_config(
        page_title="VERBATIM Speech-to-Text & Subtitle Generator",
        page_icon="👑"
    )

    if 'tts_text_area' not in st.session_state:
        st.session_state['tts_text_area'] = "Enter custom text here or run a transcription above to load the result automatically."
    
    # Check for API key presence globally
    api_key_set = st.secrets.get("GEMINI_API_KEY") is not None
        
    if not st.secrets.get("GEMINI_API_KEY"):
        st.warning("⚠️ **Gemini API Key Required:** Please set your `GEMINI_API_KEY` in the Streamlit secrets file (`.streamlit/secrets.toml`) or via the cloud settings to enable **Translation** and **Voice-Over Generation** features.")


    # 1. Title and Description
    st.title("🎤 MANDEM's Speech-to-Text, Subtitle & Voice-Over Generator")
    st.markdown("---")
    
    # --- TRANSCRIPTION AND UPLOADER SECTION (TOP PRIORITY) ---
    st.subheader("📁 Media Transcription & Subtitling")
    st.markdown("""
        Upload an **Audio** or **Video** file to generate a full transcript and time-coded SRT subtitles.
        """)

    with st.container(border=True):
        
        # --- Language Selection Widget ---
        language_options = TRANSCRIPTION_LANGUAGES
        
        selected_language_name = st.selectbox(
            "Select the Source Language Spoken in the Media:",
            options=list(language_options.keys()),
            index=0 # Default to English (US)
        )
        selected_language_code = language_options[selected_language_name]
        st.caption(f"Using Google Speech Recognition for **{selected_language_name}**.")
        
        # --- File Uploader ---
        uploaded_file = st.file_uploader(
            "Choose a media file...", 
            type=['wav', 'mp3', 'mp4', 'mov', 'avi'], 
            help="Supported file types: Audio (WAV, MP3) and Video (MP4, MOV, AVI). Max 800MB." 
        )

        if uploaded_file is not None:
            
            st.markdown(f"**File Name:** `{uploaded_file.name}` | **File Type:** `{uploaded_file.type}`")
            try:
                uploaded_file.seek(0)
                audio_bytes = uploaded_file.read()
                st.audio(audio_bytes, format=uploaded_file.type, start_time=0)
            except Exception:
                st.warning("Could not display media preview.")
                
            uploaded_file.seek(0)
            
            if st.button("🚀 Generate Transcript and Subtitles", use_container_width=True):
                
                with st.spinner("Starting media processing... (Requires FFmpeg for video/MP3)"):
                    final_text, srt_content, error_message = process_media_for_subtitles(uploaded_file, selected_language_code)
                
                if error_message:
                    st.error(error_message)
                else:
                    st.success("Transcription and Subtitle Generation Complete!")
                    
                    # Store results in session state
                    st.session_state['final_text'] = final_text
                    st.session_state['srt_content'] = srt_content
                    
                    # Update the text area content directly using the widget's key.
                    st.session_state['tts_text_area'] = final_text 
                    st.rerun() 
    
    st.markdown("---")

    # --- RESULTS, TRANSLATION & DOWNLOADS SECTION (MIDDLE PRIORITY) ---
    if 'final_text' in st.session_state and 'srt_content' in st.session_state:
        final_text = st.session_state['final_text']
        srt_content = st.session_state['srt_content']

        st.subheader("📝 Results, Translation & Downloads")

        col_text, col_srt = st.columns(2)
        
        with col_text:
            st.markdown("##### Full Transcribed Text")
            st.text_area("Full Transcript", final_text, height=350, disabled=True)
            
        with col_srt:
            st.markdown("##### SRT Subtitle File Content")
            st.text_area("SRT Output", srt_content, height=350)
        
        st.markdown("#### 🌐 Translation Options")
        
        target_lang_name = st.selectbox(
            "Select Target Language for Translation (via Gemini API):",
            options=list(TRANSLATION_LANGUAGES.keys()),
            index=0,
            key='translate_select',
            disabled=not api_key_set
        )
        
        target_code = TRANSLATION_LANGUAGES[target_lang_name]
        
        if target_code != "original" and api_key_set:
            if st.button(f"Translate to {target_lang_name}", key='translate_btn', disabled=not api_key_set):
                with st.spinner(f"Translating to {target_lang_name} via Gemini API (max 5 retries + fallback)..."):
                    translated_text = translate_text(final_text, target_code)
                        
                st.markdown("##### Translated Text")
                if translated_text.startswith("ERROR") or "Failed" in translated_text:
                    st.error(translated_text)
                    if "API Key not found" in translated_text:
                        st.markdown(f"To fix the API issue, please ensure you have set your Gemini API key in **`.streamlit/secrets.toml`**.")
                else:
                    st.info(translated_text)
                    # Update the text area content directly using the widget's key.
                    st.session_state['tts_text_area'] = translated_text
                    st.rerun()
        elif target_code != "original" and not api_key_set:
            st.warning("Translation disabled. Please set the Gemini API Key.")

        # --- DOWNLOAD BUTTONS SUB-SECTION ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_srt_dl, col_txt_dl = st.columns(2)
        
        col_srt_dl.download_button(
            label="⬇️ Download SRT Subtitles",
            data=srt_content,
            file_name=f"{uploaded_file.name.split('.')[0]}.srt",
            mime="text/plain",
            key='srt_download'
        )
        
        col_txt_dl.download_button(
            label="⬇️ Download Full Transcript (TXT)",
            data=final_text,
            file_name=f"{uploaded_file.name.split('.')[0]}_transcript.txt",
            mime="text/plain",
            key='txt_download'
        )
        
        st.caption("SRT and TXT files ready to download.")

    st.markdown("---") 

    # --- VOICE-OVER GENERATION SECTION (NEW BOTTOM LOCATION) ---
    st.subheader("🎙️ Voice-Over Generation (Text-to-Speech)")
    
    with st.container(border=True):
        st.caption("Use this to generate a high-quality voice-over from the transcribed or custom text.")
        
        tts_input_text = st.text_area(
            "Text to Synthesize:",
            height=150,
            key='tts_text_area',
            disabled=not api_key_set
        )

        col_voice, col_emotion = st.columns([0.6, 0.4])

        with col_voice:
            tts_voice_name = st.selectbox(
                "Select Voice:",
                options=list(TTS_VOICES.keys()),
                index=0,
                disabled=not api_key_set
            )
            selected_voice_code = TTS_VOICES.get(tts_voice_name, list(TTS_VOICES.values())[0])
        
        with col_emotion:
            emotion_prompt = st.text_input(
                "Add Emotion/Style (e.g., 'cheerful whisper'):",
                value="",
                disabled=not api_key_set
            )

        # --- VOICE PREVIEW AND GENERATE LOGIC ---
        preview_col, generate_col = st.columns(2)

        if not api_key_set:
            preview_col.button("▶️ Preview Selected Voice", key='preview_btn_disabled', use_container_width=True, disabled=True)
            generate_col.button("Generate Voice-Over", key='generate_tts_btn_disabled', use_container_width=True, disabled=True)
            
        else:
            # --- VOICE PREVIEW LOGIC ---
            with preview_col:
                if st.button("▶️ Preview Selected Voice", key='preview_btn', use_container_width=True):
                    # Check session state cache first
                    sample_key = f"tts_sample_{selected_voice_code}"
                    if sample_key not in st.session_state:
                        with st.spinner(f"Generating sample for {tts_voice_name}..."):
                            sample_audio = generate_tts_audio(TTS_SAMPLE_TEXT, selected_voice_code)
                            if isinstance(sample_audio, bytes):
                                st.session_state[sample_key] = sample_audio
                            else:
                                st.session_state[sample_key] = sample_audio # Store error message
                    
                    # Display result
                    if isinstance(st.session_state[sample_key], bytes):
                        st.audio(st.session_state[sample_key], format='audio/wav')
                    else:
                        st.error(st.session_state[sample_key])
            
            # --- GENERATE FULL VOICE-OVER ---
            with generate_col:
                if st.button("Generate Voice-Over", key='generate_tts_btn', use_container_width=True):
                    # Ensure we use the current, potentially user-edited, text from the text area
                    current_tts_text = st.session_state['tts_text_area'] 
                    
                    if not current_tts_text or current_tts_text.startswith("Enter custom text here"):
                        st.error("Please enter text before generating a voice-over.")
                    else:
                        with st.spinner(f"Synthesizing full voice-over with {tts_voice_name} and tone '{emotion_prompt}'..."):
                            audio_output = generate_tts_audio(current_tts_text, selected_voice_code, emotion_prompt)
                        
                        if isinstance(audio_output, bytes):
                            st.success(f"Voice-over generated successfully!")
                            st.audio(audio_output, format='audio/wav')
                            
                            st.download_button(
                                label="⬇️ Download Generated Voice-Over (WAV)",
                                data=audio_output,
                                file_name=f"voiceover_{selected_voice_code}_{int(time.time())}.wav",
                                mime="audio/wav",
                                key='tts_download_final'
                            )
                        else:
                            st.error(audio_output)
                            st.caption("Note: Check your API key and permissions.")

    # Show general instructions if the user hasn't uploaded a file yet
    if 'final_text' not in st.session_state and uploaded_file is None:
        st.info("Upload your media file using the controls above to start the process.")


if __name__ == "__main__":
    main()
