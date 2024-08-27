// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// ==/UserScript==
function getText() {
  var sel = window.getSelection().toString();
  if (sel) { return sel; }
  return document.querySelector('article,body').innerText;
}

async function tts() {
  await fetch(
    'http://127.0.0.1:1775/',
    { 'method': 'post', 'body': document.title + '\n' + getText() }
  );
  var audio = new Audio();
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
  audio.preload = 'none';
  audio.src = 'http://127.0.0.1:1775/';
  audio.play();
}

GM_registerMenuCommand('tts', tts)
