import sys
from asyncio import Event, create_subprocess_exec, new_event_loop
from logging import error, exception, info
from pathlib import Path
from re import compile as rc
from subprocess import PIPE

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

routes = RouteTableDef()


is_persian = rc('[\u0600-\u06ff]').search

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


monitoring = Event()


@routes.get('/toggle')
async def _(_: Request) -> Response:
    if monitoring.is_set():
        monitoring.clear()
        return Response(text='Clipboard Monitoring: Off', headers=all_origins)
    monitoring.set()
    return Response(text='Clipboard Monitoring: On', headers=all_origins)


monitor_clipboard_args = [
    sys.executable,
    str(Path(__file__).parent / 'monitor_clipboard.py'),
]


async def clipboard_text() -> str:
    process = await create_subprocess_exec(
        *monitor_clipboard_args, stdout=PIPE
    )
    return (await process.communicate())[0].decode()


@routes.get('/ws')
async def websocket_handler(request):
    global cb_text
    info('new socket connection')
    ws = WebSocketResponse()
    await ws.prepare(request)
    try:
        while True:
            await monitoring.wait()
            cb_text = await clipboard_text()
            if monitoring.is_set() is False:
                continue
            info('new clipboard text recieved')
            await ws.send_str(cb_text)
    except Exception as e:
        exception(e)
        return ws


audio_headers = all_origins | {'Content-Type': 'audio/mpeg'}


@routes.get('/audio')
async def _(request: Request) -> StreamResponse:
    info('serving audio started')
    response = StreamResponse(status=200, reason='OK', headers=audio_headers)
    await response.prepare(request)

    try:
        async for message in Communicate(
            cb_text, fa_voice if is_persian(cb_text) else en_voice
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
        info('serving audio finished')
    return response


if __name__ == '__main__':
    app = Application()
    app.add_routes(routes)

    loop = new_event_loop()
    # loop.create_task(set_voice_names())
    try:
        run_app(app, host='127.0.0.1', port=3775, loop=loop)
    except KeyboardInterrupt:
        pass
