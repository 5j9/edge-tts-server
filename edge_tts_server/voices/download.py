import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

THIS_DIR = Path(__file__).parent


async def download_file(session: aiohttp.ClientSession, url: str):
    # Parse the URL to get the filename from the path
    filename = os.path.basename(urlparse(url).path)

    print(f'Starting download of {filename}...')

    try:
        # Use an async context manager for the GET request
        async with session.get(url) as response:
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # Open the file in binary write mode
            with open(THIS_DIR / filename, 'wb') as f:
                # Read the content in chunks to handle large files
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)

            print(f'Successfully downloaded {filename}')
    except aiohttp.ClientError as e:
        print(f'Failed to download {filename}: {e}')
    except OSError as e:
        print(f'Failed to save {filename}: {e}')


async def main():
    # List of URLs to download
    urls = [
        'https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx?download=true',
        'https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json?download=true',
        'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx?download=true',
        'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx.json?download=true',
    ]

    # Create an aiohttp client session
    async with aiohttp.ClientSession() as session:
        for url in urls:
            await download_file(session, url)


if __name__ == '__main__':
    asyncio.run(main())
