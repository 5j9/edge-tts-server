const port = '3775'
const home = `http://127.0.0.1:${port}/`

// @ts-check
var audio = new Audio();

function requestNextStream(e) {
	if (e.type != 'ended') {
		console.log(e);
	}
	fetch(home + 'next');
}
audio.onended = requestNextStream;
audio.onstalled = requestNextStream;
audio.onerror = requestNextStream;

/**@type{HTMLLinkElement} */
// @ts-ignore
var favicon = document.createElement('link');
favicon.rel = 'icon'
favicon.type = 'image/svg+xml'
favicon.href = `data:image/svg+xml,
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
    	<text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" font-size="16" fill="black">🗣️</text>
	</svg >`
document.head.appendChild(favicon);
document.body.style.zoom = '2';

/**@type{HTMLButtonElement} */
// @ts-ignore
const pausePlayButton = document.getElementById('pauseOrPlay');

async function pauseOrPlay() {
	if (!audio.paused) {
		audio.pause();
		pausePlayButton.textContent = '▶';
		return;
	}

	audio.play();
	pausePlayButton.textContent = '⏸';
}

function jumpBackward() {
	audio.currentTime -= 10;
}

function jumpForward() {
	audio.currentTime += 10;
}

function stop() {
	audio.pause();
	audio.currentTime = 0;
	pausePlayButton.textContent = '▶';
}

/**@type{HTMLButtonElement} */
// @ts-ignore
const nextButton = document.getElementById('next');

function next() {
	audio.pause();
	nextButton.disabled = true;
	fetch(home + 'next');
}

async function play() {
	audio.src = 'audio';
	audio.play().catch((e) => {
		console.error(e);
	});
}


var monitoring = false;
/** @type {HTMLElement} */
// @ts-ignore
var toggleButton = document.getElementById('toggle-monitoring');
async function toggleMonitoring() {
	monitoring = !monitoring;
	var r = await fetch(home + 'monitoring', { method: 'PUT', body: JSON.stringify(monitoring) });
	toggleButton.textContent = monitoring ? '⏽' : '⭘';
}
toggleButton.onclick = toggleMonitoring;


var ws;
function onCloseOrError(e) {
	ws.onclose = ws.onmessage = ws.onopen = ws.onerror = null;
	var dt = new Date();
	editableField.textContent = `${dt}: WebSocket closed or error; will retry in 2 seconds ${e}`;
	setTimeout(startWs, 2000);
	ws.close();
}

function startWs() {
	console.log('new websocket');
	try {
		ws = new WebSocket(`ws://127.0.0.1:${port}/ws`);
	} catch {
		console.log('new WebSocket failed.');
		onCloseOrError();
		return;
	}

	ws.onerror = ws.onclose = onCloseOrError;
	ws.onopen = () => { // sync up the monitoring state with server
		fetch(home + 'monitoring', { method: 'PUT', body: JSON.stringify(monitoring) });
	}
	ws.onmessage = (e) => {
		var j = JSON.parse(e.data);
		switch (j['action']) {
			case 'toggle-monitoring':
				monitoring = j['state'];
				toggleButton.textContent = monitoring ? '⏽' : '⭘';
				break;
			case 'new-text':
				var text = j['text'];
				editableField.dir = j['is_fa'] ? 'rtl' : 'ltr';
				editableField.textContent = text;
				nextButton.disabled = false;
				play();
				break;
		}
	}

}


/** @type {HTMLElement} */
// @ts-ignore
var editableField = document.getElementById('editable_field');
/** @type {HTMLElement} */
// @ts-ignore
var clear = document.getElementById('clear');
clear.addEventListener('click', () => {
	editableField.textContent = '';
});

startWs();