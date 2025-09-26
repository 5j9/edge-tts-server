# WIP
from asyncio import QueueShutDown

import win32com.client as wincl

from edge_tts_server import AudioQ, InputQ, OutputQ, logger
from edge_tts_server.engines import persian_match

# Initialize the SAPI.SpVoice COM object
speaker = wincl.Dispatch('SAPI.SpVoice')
speaker.Rate = 6.0
SVSFlagsAsync = 1
SVSFPurgeBeforeSpeak = 2
# The flag value (1 | 2 = 3) clears the queue and starts the new message immediately (asynchronously).
INTERRUPT_AND_SPEAK = SVSFlagsAsync | SVSFPurgeBeforeSpeak
speak = speaker.Speak


async def prefetch_audio(in_q: InputQ, out_q: OutputQ):
    """Prefetch audio for all texts in the queue."""
    while True:
        text: str = await in_q.get()
        is_fa = persian_match(text) is not None
        short_text = text[:20] + '...'
        audio_q = AudioQ()
        await out_q.put((text, is_fa, audio_q))
        try:
            speak(text, INTERRUPT_AND_SPEAK)
            logger.info(f'Audio cached for: {short_text}')
        except QueueShutDown:
            logger.debug(f'audio_q QueueShutDown for {short_text}')
        except Exception as e:
            logger.error(f'Error prefetching audio for {short_text}: {e!r}')
        finally:
            audio_q.shutdown()
            await in_q.atask_done()
