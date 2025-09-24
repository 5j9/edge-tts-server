import wave
from asyncio import Queue, QueueShutDown, sleep
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path

from piper import AudioChunk, PiperVoice, SynthesisConfig

from edge_tts_server import SizeUpdatingQ, logger
from edge_tts_server.engines import AudioQ, persian_match

THIS_DIR = Path(__file__).parent
en_voice = PiperVoice.load(THIS_DIR / 'voices/en_US-hfc_male-medium.onnx')
fa_voice = PiperVoice.load(THIS_DIR / 'voices/fa_IR-gyro-medium.onnx')

# https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
en_syn_config = SynthesisConfig()
fa_syn_config = SynthesisConfig(length_scale=0.8)


async def stream_audio_to_q(
    audio_generator: Iterable[AudioChunk], audio_q: Queue
):
    first_chunk = True

    for chunk in audio_generator:
        if first_chunk:
            # Create a mock WAV file in memory to get the header
            mock_wav_file = BytesIO()
            with wave.open(mock_wav_file, 'wb') as w:
                w.setframerate(chunk.sample_rate)
                w.setsampwidth(chunk.sample_width)
                w.setnchannels(chunk.sample_channels)
                # The wave library writes a header with a data chunk of size 0
                # when you close the file without writing frames.
                # It will automatically be updated with the actual size later.
                w.close()

            # Seek to the beginning and read the header bytes
            mock_wav_file.seek(0)
            wav_header = mock_wav_file.read()

            # The header written by the wave library has a placeholder size.
            # We need to send this placeholder first. The receiver should be
            # designed to update the size or handle a stream of unknown size.
            # For a true live stream, this is the best we can do.
            await audio_q.put(wav_header)

            first_chunk = False

        # `await audio_q.put` does not yield control unless audio_q is full
        await sleep(0)
        await audio_q.put(chunk.audio_int16_bytes)

    await audio_q.put(None)  # Sentinel for end of audio
    # Note: If the receiving end needs the final size, it must be updated
    # after the stream ends. For a live stream, this is often not possible
    # and the receiving player must be tolerant of an empty or incorrect
    # size field in the header.


async def prefetch_audio(in_q: SizeUpdatingQ, out_q: Queue):
    """Prefetch audio for all texts in the queue."""
    while True:
        text = await in_q.get()
        is_fa = persian_match(text) is not None
        voice, syn_config = (
            (fa_voice, fa_syn_config) if is_fa else (en_voice, en_syn_config)
        )
        short_text = repr(text[:20] + '...')
        audio_q: AudioQ = Queue()
        await out_q.put((text, is_fa, audio_q))

        try:
            await stream_audio_to_q(
                voice.synthesize(text, syn_config), audio_q
            )
            logger.debug(f'Audio cached for {short_text}')
        except QueueShutDown:
            logger.debug(f'audio_q QueueShutDown for {short_text}')
        except Exception as e:
            logger.error(f'Error prefetching audio for {short_text}: {e!r}')
        finally:
            audio_q.shutdown()
            await in_q.atask_done()
