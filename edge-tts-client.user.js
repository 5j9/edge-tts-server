// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @match       *
// @grant       GM_registerMenuCommand
// ==/UserScript==
function getText() {
  return document.querySelector('article').innerText;
}



async function tts() {
  response = await fetch('http://127.0.0.1:1775/', {'method': 'post', 'body': getText()})
  blob = await response.blob()
  var url = URL.createObjectURL(blob);
  new Audio(url).play();
}

GM_registerMenuCommand('tts', tts)
