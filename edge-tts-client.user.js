// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// ==/UserScript==
function getText() {
  return document.querySelector('article,body').innerText;
}



async function tts() {
  var response = await fetch(
    'http://127.0.0.1:1775/',
    { 'method': 'post', 'body': getText() }
  )
  var blob = await response.blob()
  var url = URL.createObjectURL(blob);
  var audio = new Audio(url);
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
  audio.preload = 'none';
  audio.play();
}

GM_registerMenuCommand('tts', tts)
