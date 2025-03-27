import sys
from asyncio import Event, new_event_loop, to_thread
from logging import INFO, basicConfig, error, exception, info
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

from monitor_clipboard import run_qt_app

basicConfig(level=INFO)
routes = RouteTableDef()

persian_match = rc('[\u0600-\u06ff]').search

# see set_voice_names for how to retrieve and search available voices
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
    en_voice = voice_manager.find(ShortName='en-US-AvaNeural')[0]['Name']


all_origins = {'Access-Control-Allow-Origin': '*'}


# This event will be cleared when back-end gets deactivated.
monitoring = Event()


@routes.get('/back-toggle')
async def _(_: Request) -> Response:
    if monitoring.is_set():
        monitoring.clear()
        text = 'off'
    else:
        monitoring.set()
        text = 'on'
    info(f'Toggled to {text}.')
    return Response(text=text, headers=all_origins)


monitor_clipboard_args = [
    sys.executable,
    str(Path(__file__).parent / 'monitor_clipboard.py'),
]

cb_data = {'text': '', 'is_fa': False}


@routes.get('/ws')
async def websocket_handler(request):
    global cb_data
    info('New socket connection.')
    ws = WebSocketResponse()
    await ws.prepare(request)
    back_state = await ws.receive_str()
    if back_state == 'on':
        info('Monitoring is already turned on on front-end.')
        monitoring.set()
    try:
        while True:
            await monitoring.wait()
            cb_data = {
                'text': (text := (await to_thread(cb_slave.recv)).strip()),
                'is_fa': persian_match(text) is not None,
            }
            if monitoring.is_set() is False:
                continue
            info('New clipboard text recieved.')
            await ws.send_json(cb_data)
    except Exception as e:
        exception(e)
        await ws.close()
        return ws


audio_headers = all_origins | {'Content-Type': 'audio/mpeg'}


@routes.get('/audio')
async def _(request: Request) -> StreamResponse:
    info('Serving audio started.')
    response = StreamResponse(status=200, reason='OK', headers=audio_headers)
    await response.prepare(request)

    try:
        async for message in Communicate(
            cb_data['text'], fa_voice if cb_data['is_fa'] else en_voice
        ).stream():
            match message['type']:
                case 'audio':
                    await response.write(message['data'])
                case _:
                    # debug(message)
                    pass
    except Exception as e:
        error(f'{e!r}')
    else:
        info('Serving audio finished.')
    return response


if __name__ == '__main__':
    app = Application()
    app.add_routes(routes)

    loop = new_event_loop()
    # loop.create_task(set_voice_names())

    cb_master, cb_slave = Pipe(True)
    qt_process = Process(target=run_qt_app, args=(cb_master,))
    qt_process.start()
    try:
        run_app(app, host='127.0.0.1', port=3775, loop=loop)
    except KeyboardInterrupt:
        pass
