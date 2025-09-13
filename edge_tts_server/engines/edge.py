from asyncio import Queue, QueueShutDown

from edge_tts import Communicate, VoicesManager
from engines import persian_match
from logging_ import logger

# See set_voice_names for how to retrieve and search available voices
fa_voice: str = (
    'Microsoft Server Speech Text to Speech Voice (fa-IR, FaridNeural)'
)
en_voice: str = (
    'Microsoft Server Speech Text to Speech Voice (en-US, AvaNeural)'
)


async def set_voice_names():
    global fa_voice, en_voice
    voice_manager = await VoicesManager.create()
    fa_voice = voice_manager.find(Gender='Male', Language='fa')[0]['Name']
    en_voice = voice_manager.find(ShortName='en-US-AvaNeural')[0]['Name']  # type: ignore


async def prefetch_audio(in_q: Queue, out_q: Queue):
    """Prefetch audio for all texts in the queue."""
    while True:
        text = await in_q.get()
        is_fa = persian_match(text) is not None
        voice = fa_voice if is_fa else en_voice
        short_text = text[:20] + '...'
        audio_q: Queue[bytes | None] = Queue()
        logger.info(
            f'Prefetching audio for: {short_text} {out_q.qsize()}/{out_q.maxsize}'
        )
        await out_q.put((text, is_fa, audio_q))

        try:
            async for message in Communicate(
                text, voice, connect_timeout=5, receive_timeout=5
            ).stream():
                if message['type'] == 'audio':
                    await audio_q.put(message['data'])  # type: ignore
            logger.info(f'Audio cached for: {short_text}')
            await audio_q.put(None)  # Sentinel for end of audio
        except QueueShutDown:
            logger.debug(f'audio_q QueueShutDown for {short_text}')
        except Exception as e:
            logger.error(f'Error prefetching audio for {short_text}: {e!r}')
        finally:
            in_q.task_done()
