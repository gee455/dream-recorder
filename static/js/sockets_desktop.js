// Desktop-specific socket handling
window.socket = io();

// Socket event handlers
window.socket.on('connect', () => {
    console.log('Connected to server');
    updateStatus('Connected');
});

window.socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('Disconnected');
});

window.socket.on('state_update', (state) => {
    console.log('Received state_update:', state);
    updateStatus(state.status);
});

window.socket.on('transcription_update', (data) => {
    console.log('Received transcription_update:', data);
    // Could add transcription display if needed
});

window.socket.on('video_prompt_update', (data) => {
    console.log('Received video_prompt_update:', data);
    // Could add prompt display if needed
});

window.socket.on('video_ready', (data) => {
    console.log('Received video_ready:', data);
    const videoContainer = document.getElementById('videoContainer');
    const generatedVideo = document.getElementById('generatedVideo');
    const loadingDiv = document.getElementById('loadingDiv');
    
    if (videoContainer && generatedVideo && loadingDiv) {
        videoContainer.style.display = 'block';
        generatedVideo.src = data.url;
        loadingDiv.style.display = 'none';
        updateStatus('Dream ready!');
    }
});

window.socket.on('error', (data) => {
    console.log('Received error message:', data);
    alert('Error: ' + data.message);
    updateStatus('Error occurred');
});

window.socket.on('play_video', (data) => {
    console.log('Received play_video:', data);
    const videoContainer = document.getElementById('videoContainer');
    const generatedVideo = document.getElementById('generatedVideo');
    
    if (videoContainer && generatedVideo) {
        videoContainer.style.display = 'block';
        generatedVideo.src = data.video_url;
        updateStatus('Playing dream...');
    }
});

// Helper function to update status
function updateStatus(message) {
    const statusIndicator = document.getElementById('statusIndicator');
    if (statusIndicator) {
        statusIndicator.textContent = message;
    }
} 