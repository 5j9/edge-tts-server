// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// @grant       GM_xmlhttpRequest
// ==/UserScript==
// @ts-check
var autoplaySetup = false;
try {  // in greasemonkey script
	// @ts-ignore
	GM_registerMenuCommand('play', () => {
		if (!autoplaySetup) {
			setupSelectionAutoPlay();
		}
		play();
	});
	// @ts-ignore
	GM_registerMenuCommand('stop', stop);
	// @ts-ignore
	var request = GM_xmlhttpRequest;
} catch (undefinedReferenceError) {  // in reader.html
	// @ts-ignore
	function request(requestData) {
		var xhr = new XMLHttpRequest()
		if (requestData['onload']) {
			xhr.addEventListener("load", requestData['onload']);
		}
		if (requestData['responseType']) {
			xhr.responseType = requestData['responseType'];
		}

		xhr.open(requestData['method'], requestData['url']);
		xhr.send(requestData['data'] || null);
	}
}

var audio = new Audio();
// https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
// audio.preload = 'none';

function onSPV() {
	document.removeEventListener('securitypolicyviolation', onSPV);

	console.log('changing loader');

	function onLoad(xhr) {
		var blob = new Blob([xhr.response], { type: 'audio/mpeg' });
		audio.src = URL.createObjectURL(blob);
		audio.play();
	}

	request({
		'url': 'http://127.0.0.1:1775/',
		'method': 'get',
		'responseType': 'blob',
		'onload': onLoad
	});
}


function selectionText() {
	var sel = getSelection();
	if (sel !== null) {
		text = sel.toString().trim();
		return text;
	}
}

/**
 * 
 * @returns String
 */
function selectionOrBody() {
	// @ts-ignore
	return selectionText() || document.querySelector('article,body').innerText;
}

var selectionAutoPlayTimeout;

function setupSelectionAutoPlay() {
	autoplaySetup = true;
	document.addEventListener('mouseup', () => {
		if (selectionAutoPlayTimeout !== undefined) {
			clearTimeout(selectionAutoPlayTimeout);
		}
		var text = selectionText();
		if (!text || text == prevtext) return;
		play(text);
	});
}

var text, prevtext;

/**
 * 
 * @param {String | null} text 
 * @returns
 */
async function play(text = null) {
	if (text === null) {
		text = selectionOrBody();
	}
	if (prevtext == text) {
		if (!audio.paused) {
			audio.pause();
			return;
		}
		audio.play();
		return;
	}

	await new Promise((resolve) => request({
		'url': 'http://127.0.0.1:1775/',
		'method': 'post',
		'data': document.title + '\n' + text,
		'onload': () => { resolve(null); }
	}));
	prevtext = text;

	document.addEventListener('securitypolicyviolation', onSPV);

	audio.src = 'http://127.0.0.1:1775/';
	audio.play().catch((e) => {
		if (e != 'AbortError: The play() request was interrupted by a call to pause().') {
			throw e;
		}
	});
}

function stop() {
	audio.pause();
	audio.currentTime = 0;
}