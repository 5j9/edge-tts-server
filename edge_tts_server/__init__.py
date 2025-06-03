__version__ = '0.1.dev0'

import sys
import webbrowser
from asyncio import Event, Queue, new_event_loop, sleep, to_thread
from multiprocessing import Pipe, Process
from pathlib import Path
from re import compile as rc

from aiohttp.web import (
    Application,
    Request,
    Response,
    RouteTableDef,
    StreamResponse,
    WebSocketResponse,
    run_app,
)
from edge_tts import Communicate, VoicesManager
from logging_ import logger

from edge_tts_server.monitor_clipboard import run_qt_app

routes = RouteTableDef()

persian_match = rc('[\u0600-\u06ff]').search

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


all_origins = {'Access-Control-Allow-Origin': '*'}

# This event will be cleared when back-end gets deactivated.
monitoring = Event()

# Queue to store incoming clipboard texts
in_q: Queue[str] = Queue(maxsize=50)
# Queue to store pre-generated audio data (text, is_fa, audio_q)
out_q: Queue[tuple[str, bool, Queue[bytes]]] = Queue(maxsize=5)


@routes.get('/back-toggle')
async def _(_: Request) -> Response:
    if monitoring.is_set():
        monitoring.clear()
        text = 'off'
    else:
        monitoring.set()
        text = 'on'
    logger.info(f'Toggled to {text}.')
    return Response(text=text, headers=all_origins)


this_dir = Path(__file__).parent

monitor_clipboard_args = [
    sys.executable,
    str(this_dir / 'monitor_clipboard.py'),
]


async def prefetch_audio():
    """Prefetch audio for all texts in the queue."""
    while True:
        await monitoring.wait()
        try:
            text = await in_q.get()
            is_fa = persian_match(text) is not None
            voice = fa_voice if is_fa else en_voice
            logger.info(f'Prefetching audio for: {text[:30]}...')
            audio_q: Queue[bytes] = Queue()
            await out_q.put((text, is_fa, audio_q))
            try:
                async for message in Communicate(text, voice).stream():
                    if message['type'] == 'audio':
                        await audio_q.put(message['data'])  # type: ignore
                await audio_q.put(b'')  # Sentinel for end of audio
                logger.info(f'Audio cached for: {text[:30]}...')
            except Exception as e:
                logger.error(
                    f'Error prefetching audio for {text[:30]}...: {e!r}'
                )
            finally:
                in_q.task_done()
        except Exception as e:
            logger.error(f'Error in prefetch_audio: {e!r}')
        await sleep(0.1)  # Prevent tight loop


async def clipboard_monitor(cb_slave):
    """Monitor clipboard and add texts to queue."""
    while True:
        try:
            text = (await to_thread(cb_slave.recv)).strip()
            if not monitoring.is_set():
                continue
            if text:
                await in_q.put(text)
                logger.info(f'Added to queue: {text[:30]}...')
        except Exception as e:
            logger.exception(f'Error in clipboard monitor: {e}')
        await sleep(0.1)


@routes.get('/ws')
async def websocket_handler(request):
    global current_audio_q
    logger.info('New socket connection.')
    ws = WebSocketResponse()
    await ws.prepare(request)
    back_state = await ws.receive_str()
    if back_state == 'on':
        logger.info('Monitoring is already turned on on front-end.')
        monitoring.set()
    try:
        while True:
            await monitoring.wait()
            text, is_fa, audio_q = await out_q.get()
            logger.info('Sending new clipboard text to front-end.')
            await ws.send_json({'text': text, 'is_fa': is_fa})
            # Store audio_q in request.app for /audio endpoint
            current_audio_q = audio_q
            await ws.receive_str()  # Wait for front-end to finish
            for msg in ws:  # Process any other incoming messages
                logger.debug(f'ignoring {msg=}')
            out_q.task_done()  # Mark as done after front-end processes
    except Exception as e:
        logger.exception(f'WebSocket error: {e}')
        await ws.close()
        return ws


audio_headers = all_origins | {'Content-Type': 'audio/mpeg'}


@routes.get('/reader.html')
async def _(_):
    return Response(
        text=(this_dir / 'reader.html').read_bytes().decode(),
        content_type='text/html',
    )


@routes.get('/reader.js')
async def _(_):
    return Response(
        text=(this_dir / 'reader.js').read_bytes().decode(),
        content_type='application/javascript',
    )


@routes.get('/audio')
async def _(request: Request) -> StreamResponse:
    audio_q = current_audio_q
    logger.info('Serving audio started.')
    response = StreamResponse(status=200, reason='OK', headers=audio_headers)
    await response.prepare(request)
    try:
        while True:
            data = await audio_q.get()
            if not data:  # Sentinel for end of audio
                break
            await response.write(data)
            audio_q.task_done()
    except Exception as e:
        logger.error(f'Audio serving error: {e!r}')
    logger.info('Serving audio finished.')
    return response


if __name__ == '__main__':
    app = Application()
    app.add_routes(routes)

    loop = new_event_loop()
    # loop.create_task(set_voice_names())

    cb_master, cb_slave = Pipe(True)
    qt_process = Process(target=run_qt_app, args=(cb_master,))
    qt_process.start()
    loop.create_task(clipboard_monitor(cb_slave))
    loop.create_task(prefetch_audio())
    webbrowser.open('http://127.0.0.1:3775/reader.html')
    try:
        run_app(app, host='127.0.0.1', port=3775, loop=loop)
    except KeyboardInterrupt:
        pass
    finally:
        qt_process.terminate()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
