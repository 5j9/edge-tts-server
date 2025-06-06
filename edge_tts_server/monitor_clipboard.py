import re
from functools import partial
from multiprocessing.connection import PipeConnection
from time import time

from logging_ import logger
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication

qt_app = QApplication([])
clipboard: QClipboard = qt_app.clipboard()  # type: ignore

rm_urls = partial(re.compile(r'https?:\/\/[^\s]*').sub, '')


def skip(text: str):
    length = len(text)
    if length < 30:
        logger.info('len(text) < 30.')
        return True
    if text.count(' ') / len(text) < 0.05:
        logger.info('space less than 5%.')
        return True
    return False


last_processed_time = 0.0
DEBOUNCE_SECONDS = 0.1


def on_clipboard_changed(cb_master: PipeConnection):
    global last_processed_time
    current_time = time()
    if current_time - last_processed_time < DEBOUNCE_SECONDS:
        logger.info('Debouncing duplicate signal')
        return
    last_processed_time = current_time
    mime_data = clipboard.mimeData()
    assert mime_data is not None
    if not mime_data.hasText():
        return
    text = mime_data.text()
    if skip(text) is True:
        return
    logger.info(f'Received text: {text[:30]}')
    cb_master.send(rm_urls(text))


def run_qt_app(cb_master: PipeConnection):
    clipboard.dataChanged.connect(
        partial(on_clipboard_changed, cb_master=cb_master)
    )
    qt_app.exec()
