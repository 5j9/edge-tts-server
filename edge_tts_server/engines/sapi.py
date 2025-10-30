# WIP

import win32com.client as wincl

from edge_tts_server import AudioQ
from edge_tts_server.config import sapi_rate

# Initialize the SAPI.SpVoice COM object
speaker = wincl.Dispatch('SAPI.SpVoice')
speaker.Rate = sapi_rate
# https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720892(v=vs.85)
SVSFDefault = 0
SVSFlagsAsync = 1
SVSFPurgeBeforeSpeak = 2
# The flag value (1 | 2 = 3) clears the queue and starts the new message immediately (asynchronously).
INTERRUPT_AND_SPEAK = SVSFlagsAsync | SVSFPurgeBeforeSpeak
speak = speaker.Speak


async def prefetch_audio(text: str, lang: str, audio_q: AudioQ):
    speak(text, SVSFDefault)
