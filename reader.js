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


var activeFront = false;
/** @type {HTMLElement} */
// @ts-ignore
var frontToggle = document.getElementById('front-toggle');
async function toggleFront() {
	activeFront = !activeFront;
	if (activeFront) {
		frontToggle.textContent = 'Front-end: On';
		// if paused in the middle, not finished playing
		if (!audio.ended) { audio.play() }
	} else {
		frontToggle.textContent = 'Front-end: Off';
		audio.pause();
	}
}

/** @type {HTMLElement} */
// @ts-ignore
var backToggle = document.getElementById('back-toggle');
async function toggleBack() {
	var r = await fetch('http://127.0.0.1:3775/back-toggle');
	backToggle.textContent = await r.text();
}


var ws;
function startWs() {
	if (ws) { // Check if a WebSocket already exists
		ws.onclose = ws.onmessage = ws.onopen = ws.onerror = null;
		ws.close();
	}
	console.log('new websocket')
	ws = new WebSocket('ws://127.0.0.1:3775/ws');

	ws.onopen = () => { ws.send('hello') }

	function onCloseOrError(e) {
		var dt = new Date();
		editableField.textContent = `${dt}: WebSocket closed or error; will retry in 2 seconds ${e}`;
		setTimeout(startWs, 2000);
	}
	ws.onerror = ws.onclose = onCloseOrError;

	ws.onmessage = (e) => {
		var j = JSON.parse(e.data);
		var text = j['text']
		if (text.length < 30) {
			if (text.length < 3) {
				toggleFront();
				return;
			}
			return;
		}

		if (!activeFront) {
			return;
		}

		editableField.dir = j['is_fa'] ? 'rtl' : 'ltr';
		editableField.textContent = text;
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