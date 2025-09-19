import sys
from asyncio import Queue

from loguru import logger

# Remove the default handler to prevent duplicate output if you're reconfiguring
logger.remove()

# Add a new handler with DEBUG level, custom format, and colors
logger.add(
    sys.stderr,  # Output to console
    level='DEBUG',
    # This format includes color tags for time, level, and message
    format='<green>{time:%H:%M:%S}</green> | <level>{level: <8}</level> | <cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
)


class SizeUpdatingQ[T](Queue):
    def __init__(self, action: str, current_ws_container, maxsize=0):
        self.action = action
        super().__init__(maxsize)
        self.current_ws_container = current_ws_container

    async def put(self, item: T):
        await super().put(item)
        await self.update_front_end_status()

    async def update_front_end_status(self):
        current_ws = self.current_ws_container.get('current_ws')
        if current_ws is not None:
            await current_ws.send_json(
                {
                    'action': self.action,
                    'value': f'{self.qsize()}/{self.maxsize}',
                }
            )

    def task_done(self):
        raise NotImplementedError('use `atask_done` instead')

    async def atask_done(self):
        super().task_done()
        await self.update_front_end_status()
