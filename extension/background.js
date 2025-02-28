console.log('Background script started');

let ws;
let activeFront = true; // Default to On

async function createOffscreen() {
    if (await chrome.offscreen.hasDocument()) return;
    await chrome.offscreen.createDocument({
        url: 'offscreen.html',
        reasons: ['AUDIO_PLAYBACK'],
        justification: 'Playing audio in the background'
    });
    console.log('Offscreen document created');
    // Send initial playback speed after creation
    chrome.storage.sync.get(['playbackSpeed'], (result) => {
        const speed = result.playbackSpeed !== undefined ? result.playbackSpeed : 2;
        chrome.runtime.sendMessage({ action: "setPlaybackSpeed", speed });
    });
}

function startWs() {
    if (ws) {
        ws.onclose = ws.onmessage = ws.onopen = ws.onerror = null;
        ws.close();
    }
    console.log('Attempting to start new WebSocket');
    ws = new WebSocket('ws://127.0.0.1:3775/ws');

    ws.onopen = () => {
        console.log('WebSocket connected');
        ws.send('hello');
    };

    ws.onclose = ws.onerror = (e) => {
        console.log('WebSocket closed or error:', e);
        chrome.runtime.sendMessage({
            action: "updateText",
            text: `${new Date()}: WebSocket closed or error; will retry in 2 seconds`,
            isFa: false,
            play: false
        });
        setTimeout(startWs, 2000);
    };

    ws.onmessage = async (e) => {
        console.log('WebSocket message received:', e.data);
        const j = JSON.parse(e.data);
        const text = j['text'];
        if (text.length < 3) {
            toggleFront();
            return;
        }
        if (!activeFront) return;

        chrome.runtime.sendMessage({
            action: "updateText",
            text: text,
            isFa: j['is_fa'],
            play: true
        });

        await chrome.runtime.sendMessage({
            action: "playAudio",
            src: 'http://127.0.0.1:3775/audio'
        });
    };
}

function toggleFront() {
    activeFront = !activeFront;
    console.log('Toggling front:', activeFront);
    chrome.runtime.sendMessage({
        action: "updateFrontToggle",
        text: `Front-end: ${activeFront ? 'On' : 'Off'}`,
        activeFront: activeFront
    });
    if (!activeFront) {
        chrome.runtime.sendMessage({ action: "pauseAudio" });
    }
}

async function toggleBack() {
    console.log('Toggling back');
    const r = await fetch('http://127.0.0.1:3775/back-toggle');
    const text = await r.text();
    chrome.runtime.sendMessage({
        action: "updateBackToggle",
        text: text
    });
}

async function handleAudioCommand(message) {
    await createOffscreen();
    chrome.runtime.sendMessage(message);
}

// Initialize with Front-end On and playback speed
createOffscreen().then(() => {
    startWs();
    chrome.runtime.sendMessage({
        action: "updateFrontToggle",
        text: "Front-end: On",
        activeFront: true
    });
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Message received in background:', message);
    if (message.action === "toggleFront") {
        toggleFront();
    } else if (message.action === "toggleBack") {
        toggleBack();
    } else if (message.action === "playPause") {
        handleAudioCommand({ action: "playPauseAudio" });
    } else if (message.action === "stop") {
        handleAudioCommand({ action: "stopAudio" });
    } else if (message.action === "updatePlayState") {
        chrome.runtime.sendMessage(message);
    } else if (message.action === "setPlaybackSpeed") {
        chrome.storage.sync.set({ playbackSpeed: message.speed }, () => {
            console.log('Playback speed saved:', message.speed);
            handleAudioCommand({ action: "setPlaybackSpeed", speed: message.speed });
        });
    }
});