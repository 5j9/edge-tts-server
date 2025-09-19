from asyncio import Queue, QueueShutDown

from edge_tts import Communicate, VoicesManager

from edge_tts_server import SizeUpdatingQ, logger
from edge_tts_server.engines import persian_match

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


async def prefetch_audio(in_q: SizeUpdatingQ, out_q: Queue):
    """Prefetch audio for all texts in the queue."""
    while True:
        text = await in_q.get()
        is_fa = persian_match(text) is not None
        voice = fa_voice if is_fa else en_voice
        short_text = text[:20] + '...'
        audio_q: Queue[bytes | None] = Queue()
        await out_q.put((text, is_fa, audio_q))
        try:
            async for message in Communicate(
                text, voice, connect_timeout=5, receive_timeout=5
            ).stream():
                if message['type'] == 'audio':
                    await audio_q.put(message['data'])  # type: ignore
            logger.info(f'Audio cached for: {short_text}')
        except QueueShutDown:
            logger.debug(f'audio_q QueueShutDown for {short_text}')
        except Exception as e:
            logger.error(f'Error prefetching audio for {short_text}: {e!r}')
        finally:
            audio_q.shutdown()
            await in_q.atask_done()
