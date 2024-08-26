import asyncio

from aiohttp.web import (
    Application,
    Request,
    StreamResponse,
    post,
    run_app,
)
from edge_tts import Communicate, VoicesManager

voice_name: str


async def set_voice_name():
    global voice_name
    voices = await VoicesManager.create()
    voice_name = voices.find(Gender="Male", Language="fa")[0]["Name"]


async def tts(request: Request) -> StreamResponse:
    text = await request.text()
    communicate = Communicate(text, voice_name)

    response = StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "audio/mpeg",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await response.prepare(request)

    async for message in communicate.stream():
        match message["type"]:
            case "audio":
                await response.write(message["data"])
            case _:
                # print(message)
                pass

    await response.write_eof()
    return response


app = Application()
app.add_routes([post("/", tts)])

loop = asyncio.new_event_loop()
loop.create_task(set_voice_name())
run_app(app, host="127.0.0.1", port=1775, loop=loop)
