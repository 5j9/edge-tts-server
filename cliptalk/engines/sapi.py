import struct
from asyncio import to_thread

import win32com.client as wincl

from cliptalk import AudioQ, logger
from cliptalk.config import SAPI_VOICE_NAME, SAPI_VOICE_RATE


# --- Voice Selection and Initialization Helper ---
def _initialize_sapi_voice_config(voice_name: str, voice_obj):
    """
    Prints a list of all available SAPI voices and attempts to set
    the specified voice by name.
    """
    selected_voice = None

    try:
        voices = voice_obj.GetVoices()
        logger.info('-' * 40)
        logger.info('Available SAPI Voices (for reference):')
        for i, voice in enumerate(voices):
            desc = voice.GetDescription()
            logger.info(f'[{i}] {desc}')

            # Check if this is the voice we want to select
            if voice_name in desc and selected_voice is None:
                selected_voice = voice
        logger.info('-' * 40)

        # 2. Attempt to set the selected voice
        if selected_voice:
            voice_obj.Voice = selected_voice
            logger.info(
                f'SAPI voice set successfully to: {selected_voice.GetDescription()}'
            )
            return

    except Exception as e:
        logger.error(f'SAPI Voice initialization error: {e!r}')

    # Fallback log if no voice was set or an error occurred
    logger.info(
        f'SAPI using default or existing voice: {voice_obj.Voice.GetDescription()}'
    )


# --- Global SAPI Initialization ---
sp_voice = wincl.Dispatch('SAPI.SpVoice')
sp_voice.Rate = SAPI_VOICE_RATE
sp_voice.Volume = 100

# Initialize voice configuration: prints list and attempts to set sapi_voice_name
_initialize_sapi_voice_config(SAPI_VOICE_NAME, sp_voice)

speak = sp_voice.Speak

# --- SAPI Constants ---
# Use SVSFlagsAsync (1) for speaking and then WaitUntilDone
SVSFlagsAsync = 1
# Audio Format: 16kHz, 16-bit, Mono
SAFT16kHz16BitMono = 18

# --- Audio Specifications for Manual Header ---
SAMPLE_RATE = 16000
CHANNELS = 1
BITS_PER_SAMPLE = 16
BLOCK_ALIGN = CHANNELS * (BITS_PER_SAMPLE // 8)
BYTE_RATE = SAMPLE_RATE * BLOCK_ALIGN


def _create_wav_header(data_size: int) -> bytes:
    """
    Manually creates the 44-byte WAV header for 16kHz, 16-bit, Mono PCM audio.
    """
    file_size = 36 + data_size

    header = struct.pack('<4sI4s', b'RIFF', file_size, b'WAVE')  # RIFF Chunk

    # Format Chunk (fmt )
    header += struct.pack(
        '<4sIHHIIHH',
        b'fmt ',  # Subchunk ID
        16,  # Subchunk Size (16 for PCM)
        1,  # Audio Format (1 = PCM)
        CHANNELS,  # Number of Channels
        SAMPLE_RATE,  # Sample Rate
        BYTE_RATE,  # Byte Rate
        BLOCK_ALIGN,  # Block Align
        BITS_PER_SAMPLE,  # Bits Per Sample
    )

    # Data Chunk (data)
    header += struct.pack('<4sI', b'data', data_size)  # Data Chunk ID and Size

    return header


def _convert_to_wave_blocking(text: str) -> bytes:
    """
    Synchronous function to convert text to a wave memory buffer using SAPI.
    Uses the globally initialized sp_voice.
    """
    raw_pcm_bytes = b''
    final_wave_bytes = b''

    try:
        # 1. Create memory stream and format objects
        sp_stream = wincl.Dispatch('SAPI.SpMemoryStream')
        sp_format = wincl.Dispatch('SAPI.SpAudioFormat')
        sp_format.Type = SAFT16kHz16BitMono
        sp_stream.Format = sp_format

        # 2. Set the global SpVoice object's audio output to the memory stream
        sp_voice.AudioOutputStream = sp_stream

        # 3. Speak the text asynchronously and wait for completion
        sp_voice.Speak(text, SVSFlagsAsync)
        sp_voice.WaitUntilDone(-1)

        # 4. Extract the RAW PCM audio data (without header)
        raw_pcm_bytes = sp_stream.GetData()

        # 5. Clean up the output stream setting
        sp_voice.AudioOutputStream = None

        # 6. Manually generate the WAV header and prepend it
        wav_header = _create_wav_header(len(raw_pcm_bytes))
        final_wave_bytes = wav_header + raw_pcm_bytes

    except Exception as e:
        # Using the global sp_voice in a non-thread-safe way might lead to COM errors here
        logger.error(f'SAPI COM operation failed: {e!r}')
        final_wave_bytes = b''

    return final_wave_bytes


async def convert_to_wave(text: str) -> bytes:
    wave_bytes = await to_thread(_convert_to_wave_blocking, text)
    return wave_bytes


async def prefetch_audio(text: str, lang: str, audio_q: AudioQ):
    """
    Fetches the audio bytes and puts them on the queue.
    """
    wave_bytes = await convert_to_wave(text)
    await audio_q.put(wave_bytes)
