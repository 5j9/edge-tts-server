// @ts-check
var audio = new Audio();

async function play_pause() {
	if (!audio.paused) {
		audio.pause();
		return;
	}
	audio.play();
}

function stop() {
	audio.pause();
	audio.currentTime = 0;
}

async function play() {
	audio.src = 'http://127.0.0.1:3775/audio';
	audio.play().catch((e) => {
		if (e != 'AbortError: The play() request was interrupted by a call to pause().') {
			throw e;
		}
	});
}


/** @type {HTMLElement} */
// @ts-ignore
var toggleElem = document.getElementById('toggle');
async function toggle(e) {
	var r = await fetch('http://127.0.0.1:3775/toggle');
	toggleElem.textContent = await r.text();
}


var ws;
function startWs() {
	if (ws) { // Check if a WebSocket already exists
		ws.close(); // Close any existing connection
		ws.onopen = null; //Remove previous event listeners to avoid unexpected behavior
		ws.onclose = null;
		ws.onmessage = null;
	}
	console.log('new websocket')
	ws = new WebSocket('http://127.0.0.1:3775/ws');

	ws.onopen = () => { ws.send('hello') }

	ws.onclose = (e) => {
		var dt = new Date();
		editableField.textContent = dt + ': WebSocket was closed; will retry in 2 seconds ' + e.reason;
		setTimeout(startWs, 2000);
	};

	ws.onmessage = (e) => {
		var msg = e.data;
		editableField.textContent = msg;
		play();
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