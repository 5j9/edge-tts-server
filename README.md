## Usage

1. `uv run python edge_tts_server`.
2. `reader.html` should automatically open in your browser.
3. Click the `⭘` button to toggle it to `⏽`. (Browsers require user interaction for activating autoplay, which is why this is not `on` by default.)
4. Copy some text to your clipboard.
5. The reader will start reading the text!

Notes:
* The reader will ignore texts shorter than 30 characters or texts that do not contain space.
* If the reader tab frequently goes to sleep, add the reader URL to the "Never put these sites to sleep" list in your browser settings.

**Todo**: Add speed control. For now, I suggest using *Global Speed* ([Firefox](https://addons.mozilla.org/en-US/firefox/addon/global-speed/), [Chrome](https://chromewebstore.google.com/detail/global-speed/jpbjcnkcffbooppibceonlgknpkniiff), [Edge](https://microsoftedge.microsoft.com/addons/detail/global-speed/mjhlabbcmjflkpjknnicihkfnmbdfced)) for adjusting the reading speed.