// ==UserScript==
// @name        edge-tts-client
// @namespace   https://github.com/5j9/edge-tts-server
// @grant       GM_registerMenuCommand
// @grant       GM_xmlhttpRequest
// ==/UserScript==
function getText() {
  var sel = window.getSelection().toString();
  if (sel) { return sel; }
  return document.querySelector('article,body').innerText;
}

function onTextSent() {
  var audio = new Audio();
  // https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preload#none
  audio.preload = 'none';
  // https://developer.mozilla.org/en-US/docs/Web/API/MediaSource
  var mediaSource = new MediaSource();
  mediaSource.addEventListener("sourceopen", sourceOpen);
  audio.src = URL.createObjectURL(mediaSource);

  function sourceOpen(e) {
    const mimeCodec = 'audio/mpeg';
    const assetURL = 'http://127.0.0.1:1775/';
    const sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);
    fetchAB(assetURL, (buf) => {
      sourceBuffer.addEventListener("updateend", () => {
        mediaSource.endOfStream();
        audio.play();
      });
      sourceBuffer.appendBuffer(buf);
    });
  }

  function fetchAB(url, cb) {
    GM_xmlhttpRequest({
      'method': 'get',
      url,
      'responseType': 'arraybuffer',
      'onload': (xhr) => { cb(xhr.response); }
    });
  }
}

async function tts() {
  GM_xmlhttpRequest({
    url: 'http://127.0.0.1:1775/',
    'method': 'post',
    'data': document.title + '\n' + getText(),
    'onload': onTextSent
  });
}

GM_registerMenuCommand('tts', tts)
