# =============================
# Desktop Dream Recorder
# =============================
from gevent import monkey
monkey.patch_all()

import os
import logging
import gevent
import io
import argparse

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from functions.dream_db import DreamDB
from functions.audio import create_wav_file, process_audio
from functions.config_loader import load_config, get_config

# Configure logging
logging.basicConfig(level=getattr(logging, get_config()["LOG_LEVEL"]))
logger = logging.getLogger(__name__)

# =============================
# Global Variables & Constants
# =============================

# Global state for recording
recording_state = {
    'is_recording': False,
    'status': 'ready',  # ready, recording, processing, generating, complete
    'transcription': '',
    'video_prompt': '',
    'video_url': None
}

# Video playback state
video_playback_state = {
    'current_index': 0,  # Index of the current video being played
    'is_playing': False  # Whether a video is currently playing
}

# Audio buffer for storing chunks
audio_buffer = io.BytesIO()
wav_file = None

# List to store incoming audio chunks
audio_chunks = []

# =============================
# Flask App & Extensions Initialization
# =============================

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    DEBUG=os.environ.get("FLASK_ENV", "development") == "development",
    HOST="127.0.0.1",  # Changed from 0.0.0.0 for desktop
    PORT=5000
)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Initialize DreamDB
dream_db = DreamDB()

# =============================
# Core Logic / Helper Functions
# =============================

def initiate_recording():
    """Handles the common state changes and buffer resets for starting recording."""
    global audio_buffer, wav_file, audio_chunks
    recording_state['is_recording'] = True
    recording_state['status'] = 'recording'
    recording_state['transcription'] = '' # Reset transcription
    recording_state['video_prompt'] = ''  # Reset video prompt
    # Reset audio storage
    audio_buffer = io.BytesIO() 
    audio_chunks = []
    wav_file = None # Ensure wav_file is reset before creating a new one
    wav_file = create_wav_file(audio_buffer)
    if logger:
        logger.debug("Initiated recording: state set, buffers reset, wav file created.")

def init_sample_dreams_if_missing():
    """Attempt to initialize sample dreams by running the init_sample_dreams script."""
    import subprocess
    import sys
    import os
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'init_sample_dreams.py')
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("Sample dreams initialized.")
        else:
            print("Failed to initialize sample dreams.")
    except Exception as e:
        print(f"Exception while initializing sample dreams: {e}")

# =============================
# SocketIO Event Handlers
# =============================

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle new client connection."""
    if logger:
        logger.info('Client connected')
    emit('state_update', recording_state)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    if logger:
        logger.info('Client disconnected')

@socketio.on('start_recording')
def handle_start_recording():
    """Socket event to start recording."""
    if not recording_state['is_recording']:
        initiate_recording()
        emit('state_update', recording_state)
        if logger:
            logger.info('Started recording via socket event')
    else:
        if logger:
            logger.warning('Start recording event received, but already recording.')

@socketio.on('stream_recording')
def handle_audio_data(data):
    """Handle incoming audio data chunks from the client during recording."""
    if recording_state['is_recording']:
        try:
            # Convert the received data to bytes
            audio_bytes = bytes(data['data'])
            # Store the chunk
            audio_chunks.append(audio_bytes)
        except Exception as e:
            if logger:
                logger.error(f"Error handling audio data: {str(e)}")
            emit('error', {'message': f"Error handling audio data: {str(e)}"})

@socketio.on('stop_recording')
def handle_stop_recording():
    """Socket event to stop recording and trigger processing."""
    if recording_state['is_recording']:
        sid = request.sid # Get SID before changing state

        # Finalize the recording
        recording_state['is_recording'] = False
        recording_state['status'] = 'processing'
        if logger:
            logger.info(f"Finalizing recording. Status set to processing. Triggering process_audio for SID: {sid}")

        # Process the audio in a background task, passing all required arguments
        gevent.spawn(
            process_audio, sid, socketio, dream_db, recording_state, audio_chunks, logger
        )

        # Emit the comprehensive state update after finalizing
        emit('state_update', recording_state)
        if logger:
            logger.info('Stopped recording via socket event.')
    else:
        if logger:
            logger.warning('Stop recording event received, but not currently recording.')

@socketio.on('show_previous_dream')
def handle_show_previous_dream():
    """Socket event handler for showing previous dream."""
    try:
        # Get the most recent dreams
        dreams = dream_db.get_all_dreams()
        if not dreams:
            if logger:
                logger.warning("No dreams found to cycle through.")
            return None
        # If we're currently playing a video, show the next one in sequence
        if video_playback_state['is_playing']:
            video_playback_state['current_index'] += 1
            if video_playback_state['current_index'] >= len(dreams):
                video_playback_state['current_index'] = 0  # Wrap around
        else:
            # If not playing, start with the most recent dream
            video_playback_state['current_index'] = 0
            video_playback_state['is_playing'] = True
        # Get the dream at the current index
        dream = dreams[video_playback_state['current_index']]
        # Emit the video URL to the client
        socketio.emit('play_video', {
            'video_url': f"/media/video/{dream['video_filename']}",
            'loop': True  # Enable looping for the video
        })
        if logger:
            logger.info(f"Emitted play_video for dream index {video_playback_state['current_index']}: {dream['video_filename']}")

        if not dream:
            socketio.emit('error', {'message': 'No dreams found'})
    except Exception as e:
        if logger:
            logger.error(f"Error in show_previous_dream: {str(e)}")
        socketio.emit('error', {'message': f'Error showing previous dream: {str(e)}'})

@socketio.on('show_latest_dream')
def handle_show_latest_dream():
    """Socket event handler for showing the latest dream."""
    try:
        # Get the most recent dreams
        dreams = dream_db.get_all_dreams()
        if not dreams:
            if logger:
                logger.warning("No dreams found to show.")
            socketio.emit('error', {'message': 'No dreams found'})
            return None
        # Reset to the most recent dream
        video_playback_state['current_index'] = 0
        video_playback_state['is_playing'] = True
        # Get the most recent dream
        dream = dreams[0]
        # Emit the video URL to the client
        socketio.emit('play_video', {
            'video_url': f"/media/video/{dream['video_filename']}",
            'loop': True  # Enable looping for the video
        })
        if logger:
            logger.info(f"Emitted play_video for latest dream: {dream['video_filename']}")
    except Exception as e:
        if logger:
            logger.error(f"Error in show_latest_dream: {str(e)}")
        socketio.emit('error', {'message': f'Error showing latest dream: {str(e)}'})

# =============================
# Flask Routes
# =============================

@app.route('/')
def index():
    """Main page route."""
    return render_template('index_desktop.html')

@app.route('/dreams')
def dreams():
    """Dreams library page route."""
    dreams = dream_db.get_all_dreams()
    return render_template('dreams.html', dreams=dreams)

@app.route('/api/config')
def api_get_config():
    """API endpoint to get current configuration."""
    try:
        config = get_config()
        # Filter out sensitive information
        safe_config = {k: v for k, v in config.items() 
                      if not any(sensitive in k.lower() for sensitive in ['key', 'secret', 'password'])}
        return jsonify(safe_config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dreams/<int:dream_id>', methods=['DELETE'])
def delete_dream(dream_id):
    """Delete a specific dream by ID."""
    try:
        # Get the dream to find the filenames
        dream = dream_db.get_dream(dream_id)
        if not dream:
            return jsonify({'error': 'Dream not found'}), 404
        
        # Delete the dream from the database
        dream_db.delete_dream(dream_id)
        
        # Delete associated files
        import os
        from functions.config_loader import get_config
        
        # Delete video file
        if dream['video_filename']:
            video_path = os.path.join(get_config()['VIDEOS_DIR'], dream['video_filename'])
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as e:
                if logger:
                    logger.warning(f"Could not delete video file {video_path}: {e}")
        
        # Delete thumbnail file
        if dream['thumb_filename']:
            thumb_path = os.path.join(get_config()['THUMBS_DIR'], dream['thumb_filename'])
            try:
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
            except Exception as e:
                if logger:
                    logger.warning(f"Could not delete thumbnail file {thumb_path}: {e}")
        
        # Delete audio file
        if dream['audio_filename']:
            audio_path = os.path.join(get_config()['RECORDINGS_DIR'], dream['audio_filename'])
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                if logger:
                    logger.warning(f"Could not delete audio file {audio_path}: {e}")
        
        return jsonify({'message': 'Dream deleted successfully'})
    except Exception as e:
        if logger:
            logger.error(f"Error deleting dream {dream_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files."""
    from functions.config_loader import get_config
    
    # Split the path to handle media type directories
    parts = filename.split('/')
    if len(parts) > 1:
        media_type = parts[0]  # e.g., 'video', 'thumbs', 'audio'
        filename = '/'.join(parts[1:])  # rest of the path
        
        if media_type == 'video':
            media_dir = get_config()['VIDEOS_DIR']
        elif media_type == 'thumbs':
            media_dir = get_config()['THUMBS_DIR']
        elif media_type == 'audio':
            media_dir = get_config()['RECORDINGS_DIR']
        else:
            return 'Invalid media type', 400
    else:
        # Default to video dir if no media type specified
        media_dir = get_config()['VIDEOS_DIR']
    
    file_path = os.path.join(media_dir, filename)
    if not os.path.exists(file_path):
        return f'File not found: {filename}', 404
        
    return send_file(file_path)

@app.route('/media/thumbs/<path:filename>')
def serve_thumbnail(filename):
    """Serve thumbnail files."""
    from functions.config_loader import get_config
    thumbs_dir = get_config()['THUMBS_DIR']
    return send_file(os.path.join(thumbs_dir, filename))

@app.route('/media/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files."""
    from functions.config_loader import get_config
    audio_dir = get_config()['RECORDINGS_DIR']
    return send_file(os.path.join(audio_dir, filename))

# =============================
# Main Application Entry Point
# =============================

if __name__ == '__main__':
    # Initialize sample dreams if they don't exist
    init_sample_dreams_if_missing()
    
    print("🌙 Dream Recorder Desktop Edition")
    print("=" * 40)
    print("Starting server...")
    print(f"Open your browser to: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 40)
    
    # Run the application
    socketio.run(app, 
                host="127.0.0.1", 
                port=5000, 
                debug=True,
                allow_unsafe_werkzeug=True) 