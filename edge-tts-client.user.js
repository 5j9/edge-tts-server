// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// @grant       GM_xmlhttpRequest
// ==/UserScript==
const audio = new Audio();
// https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
audio.preload = 'none';

var sourceBuffer, mediaSource;

function getText() {
  var sel = window.getSelection().toString();
  if (sel) { return sel; }
  return document.querySelector('article,body').innerText;
}

function base64ToArrayBuffer(base64) {
  var binaryString = atob(base64);
  var bytes = new Uint8Array(binaryString.length);
  for (var i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

function onAudioLoad(xhr) {
  console.log('onAudioLoad');
  // var buf = base64ToArrayBuffer(xhr.response);
  // sourceBuffer.appendBuffer(buf);
  lastLoudPos = 0;
}

var lastLoudPos = 0;

function onAudioProgress(xhr) {
  var buf = base64ToArrayBuffer(xhr.response.slice(lastLoudPos, xhr.loaded));
  sourceBuffer.appendBuffer(buf);
  lastLoudPos = xhr.loaded;
}

function onSourceOpen(e) {
  sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
  sourceBuffer.addEventListener("updateend", () => {
    console.log('end of stream');
    mediaSource.endOfStream();
  });

  GM_xmlhttpRequest({
    'method': 'get',
    'url': 'http://127.0.0.1:1775/',
    // arraybuffer does not provide progress chunks
    // 'responseType': 'arraybuffer',
    'onload': onAudioLoad,
    'onprogress': onAudioProgress
  });
}


function onTextSent() {
  // https://developer.mozilla.org/en-US/docs/Web/API/MediaSource
  mediaSource = new MediaSource();
  mediaSource.addEventListener("sourceopen", onSourceOpen);
  audio.src = URL.createObjectURL(mediaSource);

  audio.play().catch((e) => {
    if (e != 'AbortError: The play() request was interrupted by a call to pause().') {
      throw e;
    }
  });
}


async function play() {
  if (!audio.paused) {
    audio.pause();
    return;
  } else if (audio.currentTime != 0 && !audio.ended) {
    audio.play();
    return;
  }
  GM_xmlhttpRequest({
    'url': 'http://127.0.0.1:1775/',
    'method': 'post',
    'data': document.title + '\n' + getText(),
    'onload': onTextSent
  });
}

function stop() {
  audio.pause();
  audio.currentTime = 0;
}


GM_registerMenuCommand('play', play);
GM_registerMenuCommand('stop', stop);