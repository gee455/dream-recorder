import wave
import os
import tempfile
import ffmpeg
import wave

from datetime import datetime
from functions.video import generate_video
from functions.config_loader import get_config
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(
    api_key=get_config()["OPENAI_API_KEY"],
    http_client=None
)

def create_wav_file(audio_buffer):
    """Create a new WAV file in the audio buffer with the correct format."""
    wav_file = wave.open(audio_buffer, 'wb')
    wav_file.setnchannels(int(get_config()['AUDIO_CHANNELS']))
    wav_file.setsampwidth(int(get_config()['AUDIO_SAMPLE_WIDTH']))
    wav_file.setframerate(int(get_config()['AUDIO_FRAME_RATE']))
    return wav_file

def save_wav_file(audio_data, filename=None, logger=None):
    """Save the WAV file locally for debugging. Converts WebM to WAV using ffmpeg."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
    
    # Ensure the recordings directory exists
    os.makedirs(get_config()['RECORDINGS_DIR'], exist_ok=True)
    filepath = os.path.join(get_config()['RECORDINGS_DIR'], filename)
    
    try:
        # Create a temporary file for the WebM data
        with tempfile.NamedTemporaryFile(suffix='.webm', mode='wb', delete=False) as temp_webm:
            # Write the audio data in chunks to avoid memory issues
            chunk_size = 8192
            for i in range(0, len(audio_data), chunk_size):
                temp_webm.write(audio_data[i:i + chunk_size])
            temp_webm.flush()
            temp_webm_path = temp_webm.name

        try:
            # Convert WebM to WAV using ffmpeg with explicit formats and parameters
            stream = ffmpeg.input(
                temp_webm_path,
                f='webm',  # Explicitly set input format
                acodec='opus'  # WebM typically uses Opus codec
            )
            
            # Configure output with explicit format and parameters
            stream = ffmpeg.output(
                stream, 
                filepath,
                acodec='pcm_s16le',  # Standard WAV codec
                ac=int(get_config()['AUDIO_CHANNELS']),
                ar=int(get_config()['AUDIO_FRAME_RATE']),
                format='wav',  # Explicit output format
                audio_bitrate='192k',  # Ensure good quality
                loglevel='warning'  # Capture meaningful errors
            )
            
            # Run FFmpeg with error capture
            try:
                ffmpeg.run(stream, capture_stderr=True, overwrite_output=True)
            except ffmpeg.Error as e:
                stderr = e.stderr.decode() if e.stderr else "Unknown FFmpeg error"
                if logger:
                    logger.error(f"FFmpeg conversion error: {stderr}")
                raise Exception(f"FFmpeg conversion failed: {stderr}")
            
            # Verify the output file exists and is not empty
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                raise Exception("FFmpeg produced an empty or missing output file")
            
            if logger:
                logger.info(f"Successfully saved WAV file to {filepath}")
            return filename
            
        except Exception as e:
            if logger:
                logger.error(f"Error during audio conversion: {str(e)}")
            raise
            
    except Exception as e:
        if logger:
            logger.error(f"Error saving audio: {str(e)}")
        raise
        
    finally:
        # Clean up temporary file
        try:
            if 'temp_webm_path' in locals():
                os.unlink(temp_webm_path)
        except Exception as e:
            if logger:
                logger.warning(f"Failed to clean up temp file: {str(e)}")

def generate_video_prompt(transcription, luma_extend=False, logger=None, config=None):
    """Generate an enhanced video prompt from the transcription using GPT."""
    try:
        system_prompt = get_config()['GPT_SYSTEM_PROMPT_EXTEND'] if luma_extend else get_config()['GPT_SYSTEM_PROMPT']
        response = client.chat.completions.create(
            model=get_config()['GPT_MODEL'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{transcription}"}
            ],
            temperature=float(get_config()['GPT_TEMPERATURE']),
            max_tokens=int(get_config()['GPT_MAX_TOKENS'])
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if logger:
            logger.error(f"Error generating video prompt: {str(e)}")
        return None

def process_audio(sid, socketio, dream_db, recording_state, audio_chunks, logger = None):
    """Process the recorded audio and generate video, then update state and emit events."""
    try:
        # Combine all audio chunks
        audio_data = b''.join(audio_chunks)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_filename = f"recording_{timestamp}.wav"
        
        # Save the audio file
        try:
            wav_filename = save_wav_file(audio_data, wav_filename, logger)
            if not wav_filename:
                raise Exception("Failed to save audio file")
        except Exception as e:
            if logger:
                logger.error(f"Error saving audio: {str(e)}")
            raise Exception(f"Failed to save audio: {str(e)}")

        # Get the full path to the saved WAV file
        wav_path = os.path.join(get_config()['RECORDINGS_DIR'], wav_filename)
        
        # Transcribe the audio using OpenAI's Whisper API
        try:
            with open(wav_path, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model=get_config()['WHISPER_MODEL'],
                    file=audio_file
                )
        except Exception as e:
            if logger:
                logger.error(f"Transcription error: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

        # Update the transcription in the global state
        recording_state['transcription'] = transcription.text
        
        # Emit the transcription
        if sid:
            socketio.emit('transcription_update', {'text': transcription.text}, room=sid)
        else:
            socketio.emit('transcription_update', {'text': transcription.text})

        # Check if LUMA_EXTEND is set
        luma_extend = str(get_config()['LUMA_EXTEND']).lower() in ('1', 'true', 'yes')
        
        # Generate video prompt
        video_prompt = generate_video_prompt(
            transcription=transcription.text,
            luma_extend=luma_extend,
            logger=logger,
            config=get_config()
        )
        
        if not video_prompt:
            raise Exception("Failed to generate video prompt")
            
        recording_state['video_prompt'] = video_prompt
        
        if sid:
            socketio.emit('video_prompt_update', {'text': video_prompt}, room=sid)
        else:
            socketio.emit('video_prompt_update', {'text': video_prompt})

        # Generate the video
        video_filename, thumb_filename = generate_video(
            prompt=video_prompt,
            luma_extend=luma_extend,
            logger=logger
        )

        # Save to database
        try:
            from functions.dream_db import DreamData
            dream_data = DreamData(
                user_prompt=recording_state['transcription'],
                generated_prompt=recording_state['video_prompt'],
                audio_filename=wav_filename,
                video_filename=video_filename,
                thumb_filename=thumb_filename,
                status='completed',
            )
            dream_db.save_dream(dream_data.model_dump())
        except Exception as e:
            if logger:
                logger.error(f"Database error: {str(e)}")
            raise Exception(f"Failed to save to database: {str(e)}")

        # Update state and emit video ready event
        recording_state['status'] = 'complete'
        recording_state['video_url'] = f"/media/video/{video_filename}"
        
        if sid:
            socketio.emit('video_ready', {'url': recording_state['video_url']}, room=sid)
        else:
            socketio.emit('video_ready', {'url': recording_state['video_url']})
            
        if logger:
            logger.info(f"Audio processed and video generated for SID: {sid}")
            
    except Exception as e:
        recording_state['status'] = 'error'
        error_message = f"Processing error: {str(e)}"
        if sid:
            socketio.emit('error', {'message': error_message}, room=sid)
        else:
            socketio.emit('error', {'message': error_message})
        if logger:
            logger.error(f"Error processing audio: {str(e)}")
            
    finally:
        # Clean up
        audio_chunks.clear()