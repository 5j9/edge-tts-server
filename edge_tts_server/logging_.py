import sys

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
