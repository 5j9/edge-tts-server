import asyncio
from typing import AsyncGenerator, Any

from aiohttp.web import (
    Application,
    Request,
    StreamResponse,
    post,
    run_app,
    get,
    Response,
)
from edge_tts import Communicate, VoicesManager

voice_name: str


async def set_voice_name():
    global voice_name
    voices = await VoicesManager.create()
    voice_name = voices.find(Gender="Male", Language="fa")[0]["Name"]


stream: AsyncGenerator[dict[str, Any], None]


async def src(request: Request) -> StreamResponse:
    response = StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "audio/mpeg",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await response.prepare(request)

    async for message in stream:
        match message["type"]:
            case "audio":
                await response.write(message["data"])
            case _:
                # print(message)
                pass
    print("done")
    return response


async def tts(request: Request) -> Response:
    global stream
    title, _, text = (await request.text()).partition("\n")
    print(f"serving {title}")
    stream = Communicate(text, voice_name).stream()
    return Response(headers={"Access-Control-Allow-Origin": "*"})


app = Application()
app.add_routes([post("/", tts), get("/", src)])

loop = asyncio.new_event_loop()
loop.create_task(set_voice_name())
run_app(app, host="127.0.0.1", port=1775, loop=loop)
