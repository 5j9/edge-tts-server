function sendMessageToBackground(message) {
    chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
            console.error('Messaging error:', chrome.runtime.lastError.message);
        }
    });
}

function toggleFront() {
    console.log('Sending toggleFront message');
    sendMessageToBackground({ action: "toggleFront" });
}

function toggleBack() {
    console.log('Sending toggleBack message');
    sendMessageToBackground({ action: "toggleBack" });
}

function playPause() {
    console.log('Sending playPause message');
    sendMessageToBackground({ action: "playPause" });
}

function stop() {
    console.log('Sending stop message');
    sendMessageToBackground({ action: "stop" });
}

function setPlaybackSpeed(speed) {
    console.log('Setting playback speed:', speed);
    sendMessageToBackground({ action: "setPlaybackSpeed", speed: parseFloat(speed) });
}

document.addEventListener('DOMContentLoaded', () => {
    const frontToggle = document.getElementById('front-toggle');
    const backToggle = document.getElementById('back-toggle');
    const playPauseBtn = document.getElementById('play-pause');
    const stopBtn = document.getElementById('stop');
    const clearBtn = document.getElementById('clear');
    const editableField = document.getElementById('editable_field');
    const playbackSpeedInput = document.getElementById('playback-speed');

    frontToggle.addEventListener('click', toggleFront);
    backToggle.addEventListener('click', toggleBack);
    playPauseBtn.addEventListener('click', playPause);
    stopBtn.addEventListener('click', stop);
    clearBtn.addEventListener('click', () => {
        editableField.textContent = '';
    });

    // Handle playback speed input
    playbackSpeedInput.addEventListener('change', (e) => {
        let speed = parseFloat(e.target.value);
        if (speed < 0.1) speed = 0.1;
        if (speed > 4) speed = 4;
        e.target.value = speed; // Enforce min/max
        setPlaybackSpeed(speed);
    });

    playbackSpeedInput.addEventListener('keydown', (e) => {
        let speed = parseFloat(playbackSpeedInput.value);
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            speed = Math.min(speed + 0.1, 4); // Step up, max 4
            playbackSpeedInput.value = speed.toFixed(1);
            setPlaybackSpeed(speed);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            speed = Math.max(speed - 0.1, 0.1); // Step down, min 0.1
            playbackSpeedInput.value = speed.toFixed(1);
            setPlaybackSpeed(speed);
        }
    });

    // Load saved playback speed, default to 2 if not set
    chrome.storage.sync.get(['playbackSpeed'], (result) => {
        const speed = result.playbackSpeed !== undefined ? result.playbackSpeed : 2;
        playbackSpeedInput.value = speed;
        setPlaybackSpeed(speed); // Ensure offscreen audio starts with this speed
    });
});

chrome.runtime.onMessage.addListener((message) => {
    console.log('Message received in popup:', message);
    const editableField = document.getElementById('editable_field');
    const frontToggle = document.getElementById('front-toggle');
    const backToggle = document.getElementById('back-toggle');
    const playPauseBtn = document.getElementById('play-pause');

    if (message.action === "updateFrontToggle") {
        frontToggle.textContent = message.text;
    } else if (message.action === "updateBackToggle") {
        backToggle.textContent = message.text;
    } else if (message.action === "updateText") {
        editableField.dir = message.isFa ? 'rtl' : 'ltr';
        editableField.textContent = message.text;
    } else if (message.action === "updatePlayState") {
        playPauseBtn.textContent = message.isPlaying ? '⏸' : '▶️';
    }
});