from asyncio import create_task, to_thread
from types import MethodType

import win32com.client as wincl

from edge_tts_server import AudioQ, OutputQ
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


async def out_q_get_wrapper(self: OutputQ):
    global speak_task  # create_task requires saving a ref
    item = await original_out_q_get()
    speak_task = create_task(to_thread(speak, item[0], SVSFPurgeBeforeSpeak))
    return item


def patch_out_q(out_q: OutputQ):
    global original_out_q_get
    original_out_q_get = out_q.get
    out_q.get = MethodType(out_q_get_wrapper, out_q)


async def prefetch_audio(text: str, lang: str, audio_q: AudioQ):
    pass
