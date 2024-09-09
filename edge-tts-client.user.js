// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// @grant       GM_xmlhttpRequest
// ==/UserScript==
var audio = new Audio();
// https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
audio.preload = 'none';

function onSPV() {
  document.removeEventListener('securitypolicyviolation', onSPV);

  console.log('changing loader');

  function onLoad(xhr) {
    var blob = new Blob([xhr.response], { type: 'audio/mpeg' });
    audio.src = URL.createObjectURL(blob);
    audio.play();
  }

  GM_xmlhttpRequest({
    'url': 'http://127.0.0.1:1775/',
    'method': 'get',
    'responseType': 'blob',
    'onload': onLoad
  });
}

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


  await new Promise((resolve) => GM_xmlhttpRequest({
    'url': 'http://127.0.0.1:1775/',
    'method': 'post',
    'data': document.title + '\n' + getText(),
    'onload': () => { resolve(); }
  }));

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


GM_registerMenuCommand('play', play);
GM_registerMenuCommand('stop', stop);