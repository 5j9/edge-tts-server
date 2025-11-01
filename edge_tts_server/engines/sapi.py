from asyncio import QueueShutDown, to_thread
from types import MethodType

import win32com.client as wincl

from edge_tts_server import AudioQ
from edge_tts_server.config import sapi_rate

# Initialize the SAPI.SpVoice COM object
sp_voice = wincl.Dispatch('SAPI.SpVoice')
sp_voice.Rate = sapi_rate
sp_voice.Volume = 100
speak = sp_voice.Speak

# https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720892(v=vs.85)
SVSFDefault = 0  # synchronous and not to purge pending
SVSFlagsAsync = 1  # return immediately after the speak request is queued
SVSFPurgeBeforeSpeak = 2  # Purges all pending speak requests
# The flag value (1 | 2 = 3) clears the queue and starts the new message immediately (asynchronously).
ASYNC_PURGE = SVSFlagsAsync | SVSFPurgeBeforeSpeak


def audio_q_get_substitute(text: str):
    async def substitute(self: AudioQ):
        await to_thread(speak, text, SVSFPurgeBeforeSpeak)
        raise QueueShutDown

    return substitute


async def prefetch_audio(text: str, lang: str, audio_q: AudioQ):
    audio_q.get = MethodType(audio_q_get_substitute(text), audio_q)
