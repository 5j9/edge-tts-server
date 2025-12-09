__version__ = '0.1.dev0'

import sys
import webbrowser
from asyncio import Event, QueueShutDown, new_event_loop, sleep, to_thread
from collections.abc import Awaitable, Callable
from multiprocessing import Pipe, Process
from pathlib import Path

from aiohttp.web import (
    Application,
    Request,
    Response,
    RouteTableDef,
    StreamResponse,
    WebSocketResponse,
    run_app,
)

from cliptalk import AudioQ, InputQ, OutputQ, config, logger
from cliptalk.engines import detect_lang
from cliptalk.qt_server import run_qt_app

this_dir = Path(__file__).parent


async def prefetch_audio_loop(
    in_q: InputQ,
    out_q: OutputQ,
):
    """Prefetch audio for all texts in the queue."""
    engines = load_engines()
    try:
        while True:
            text = await in_q.get()
            lang = detect_lang(text)
            short_text = text[:20] + '...'
            audio_q = AudioQ()
            await out_q.put((text, lang == 'fa', audio_q))
            fetcher = engines.get(lang) or engines['default']
            try:
                for _ in range(3):
                    try:
                        await fetcher(text, lang, audio_q)
                    except Exception as e:
                        logger.debug(f'Retrying {e!r}.')
                        continue
                    logger.info(f'Audio cached for: {short_text}')
                    break
            except QueueShutDown:
                logger.debug(f'audio_q QueueShutDown for {short_text}')
            except Exception as e:
                logger.error(
                    f'Error prefetching audio for {short_text}: {e!r}'
                )
            finally:
                logger.debug('calling audio_q.shutdown()')
                audio_q.shutdown()
                await in_q.atask_done()
    except Exception:
        logger.critical('Fatal Error')


def load_engines() -> dict[str, Callable[[str, str, AudioQ], Awaitable]]:
    """
    piper engine uses a lot more memory, but is usually more responsive.
    edge engine uses the Microsoft Edge tts servers.
    sapi uses Microsoft Speech API (SAPI). It has limited features,
        but is usually the most responsive one.
    """
    engines: dict = config.ENGINES

    for lang, engine in engines.items():
        match engine:
            case 'edge':
                from cliptalk.engines.edge import prefetch_audio

                engines[lang] = prefetch_audio

            case 'sapi':
                from cliptalk.engines.sapi import prefetch_audio

                engines[lang] = prefetch_audio

            case 'piper':
                from cliptalk.engines.piper import prefetch_audio

                engines[lang] = prefetch_audio
            case _:
                raise ValueError('unknown engine')

    return engines


routes = RouteTableDef()


in_q = InputQ(
    maxsize=50, action='input-queue-size', current_ws_container=globals()
)
out_q = OutputQ(
    maxsize=5, action='output-queue-size', current_ws_container=globals()
)


@routes.put('/monitoring')
async def _(request: Request) -> Response:
    logger.debug('/monitoring recieved request')
    new_state = await request.json()
    conn.send(new_state)
    logger.info(f'monitoring state: {new_state}')
    return Response()


monitor_clipboard_args = [
    sys.executable,
    str(this_dir / 'monitor_clipboard.py'),
]


async def listen_to_qt():
    """Monitor clipboard and add texts to queue."""
    while True:
        try:
            data = await to_thread(conn.recv)

            if type(data) is bool:
                logger.debug(f'qt toggled monitoring: {data}')
                if current_ws is None:
                    continue
                await current_ws.send_json(
                    {'action': 'toggle-monitoring', 'state': data}
                )
                continue

            if type(data) is str:
                data = data.strip()
                await in_q.put(data)
                continue

            logger.error(f'Unexpected data type recieved from conn: {data=}')
        except Exception as e:
            logger.error(f'listen_to_qt loop failed with {e!r}')


next_request = Event()


@routes.get('/next')
async def _(request: Request) -> Response:
    logger.debug('recieved /next request')
    current_audio_q.shutdown(immediate=True)
    next_request.set()
    return Response()


current_ws: WebSocketResponse | None = None


@routes.get('/ws')
async def _(request):
    global current_audio_q, current_ws
    logger.info('new websocket connection')

    ws = WebSocketResponse()
    await ws.prepare(request)
    if current_ws and not current_ws.closed:
        logger.debug('closing current_ws before using new one')
        await current_ws.close()

    current_ws = ws

    while True:
        text, is_fa, audio_q = await out_q.get()
        logger.info('Sending new clipboard text to front-end.')
        # Store audio_q in request.app for /audio endpoint
        current_audio_q = audio_q
        next_request.clear()
        try:
            await ws.send_json(
                {'action': 'new-text', 'text': text, 'is_fa': is_fa}
            )
        except Exception as e:
            logger.exception(f'WebSocket error: {e}')
            await ws.close()
            return ws
        finally:
            await out_q.atask_done()
        logger.debug('awaiting next_request')
        await next_request.wait()


@routes.get('/cliptalk.html')
async def _(_):
    return Response(
        text=(this_dir / 'cliptalk.html').read_bytes().decode(),
        content_type='text/html',
    )


@routes.get('/cliptalk.js')
async def _(_):
    return Response(
        text=(this_dir / 'cliptalk.js').read_bytes().decode(),
        content_type='application/javascript',
    )


@routes.get('/cliptalk.css')
async def _(_):
    return Response(
        text=(this_dir / 'cliptalk.css').read_bytes().decode(),
        content_type='text/css',
    )


audio_headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'audio/wav',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
}


@routes.get('/audio')
async def _(request: Request) -> StreamResponse:
    audio_q = current_audio_q
    logger.info('Serving audio started.')
    response = StreamResponse(status=200, reason='OK', headers=audio_headers)
    await response.prepare(request)
    try:
        while True:
            data = await audio_q.get()
            await response.write(data)
            audio_q.task_done()
    except QueueShutDown:
        logger.debug('/audio reached QueueShutDown')
    except Exception as e:
        logger.error(f'unexpected error: {e!r}')
    return response


async def open_tab_if_no_conn():
    await sleep(5.0)
    if current_ws is None:
        webbrowser.open('http://127.0.0.1:3775/cliptalk.html')


if __name__ == '__main__':
    app = Application()
    app.add_routes(routes)

    loop = new_event_loop()
    create_task = loop.create_task
    # loop.create_task(set_voice_names())

    qt_conn, conn = Pipe(True)
    conn.send((config.MIN_SPACE_RATIO, config.MIN_TEXT_LENGTH))
    qt_process = Process(target=run_qt_app, args=(qt_conn,))
    qt_process.start()
    listen_to_qt_task = create_task(listen_to_qt())
    prefetch_audio_task = create_task(prefetch_audio_loop(in_q, out_q))
    open_tab_task = create_task(open_tab_if_no_conn())

    try:
        run_app(app, host='127.0.0.1', port=3775, loop=loop)
    except KeyboardInterrupt:
        pass
    finally:
        qt_process.terminate()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
