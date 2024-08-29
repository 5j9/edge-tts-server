// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// ==/UserScript==
var audio = new Audio();

function getText() {
  var sel = window.getSelection().toString();
  if (sel) { return sel; }
  return document.querySelector('article,body').innerText;
}

async function play() {
  if (!audio.paused) {
    audio.pause();
    return;
  } else if (audio.currentTime != 0 && !audio.ended) {
    audio.play();
    return;
  }


  await fetch(
    'http://127.0.0.1:1775/',
    { 'method': 'post', 'body': document.title + '\n' + getText() }
  );
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
  audio.preload = 'none';
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


GM_registerMenuCommand('play', play);
GM_registerMenuCommand('stop', stop);