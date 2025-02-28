const audio = new Audio();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Offscreen received message:', message);
    if (message.action === "playAudio") {
        audio.src = message.src || 'http://127.0.0.1:3775/audio';
        audio.play().catch((e) => {
            if (e.name !== 'AbortError') console.error('Audio play error:', e);
        });
        sendResponse({ success: true });
    } else if (message.action === "pauseAudio") {
        audio.pause();
        sendResponse({ success: true });
    } else if (message.action === "stopAudio") {
        audio.pause();
        audio.currentTime = 0;
        sendResponse({ success: true });
    } else if (message.action === "playPauseAudio") {
        if (!audio.paused) {
            audio.pause();
        } else {
            audio.play();
        }
        chrome.runtime.sendMessage({
            action: "updatePlayState",
            isPlaying: !audio.paused
        });
        sendResponse({ success: true });
    } else if (message.action === "setPlaybackSpeed") {
        audio.playbackRate = message.speed;
        sendResponse({ success: true });
    }
    return true; // Indicates async response
});