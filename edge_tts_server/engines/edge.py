from edge_tts import Communicate, VoicesManager

from edge_tts_server import AudioQ

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


async def prefetch_audio(text: str, lang: str, audio_q: AudioQ):
    """Prefetch audio for all texts in the queue."""
    is_fa = lang == 'fa'
    voice = fa_voice if is_fa else en_voice
    async for message in Communicate(
        text, voice, connect_timeout=5, receive_timeout=20
    ).stream():
        if message['type'] == 'audio':
            await audio_q.put(message['data'])  # type: ignore
