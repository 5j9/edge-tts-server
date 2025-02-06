## How It Works

1. Run `server.py`.
2. Open the `reader.html` file in your browser.
3. Click the `Front-end: Off` button. (Browsers require user interaction for activating autoplay, which is why this is not active by default.)
4. Copy some text to your clipboard.
5. The reader will start reading the text!

The reader will ignore texts shorter than 20 characters and will automatically toggle the front-end state to off if the length is 0 or 1 characters. This can be used to switch the state without going to the tab.

**Todo**: Add speed control. For now, I suggest using *Global Speed* ([Firefox](https://addons.mozilla.org/en-US/firefox/addon/global-speed/), [Chrome](https://chromewebstore.google.com/detail/global-speed/jpbjcnkcffbooppibceonlgknpkniiff), [Edge](https://microsoftedge.microsoft.com/addons/detail/global-speed/mjhlabbcmjflkpjknnicihkfnmbdfced)) for adjusting the reading speed.
