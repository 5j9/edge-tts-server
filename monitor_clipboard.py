from functools import partial
from multiprocessing.connection import PipeConnection
from time import strftime

from PyQt6.QtWidgets import QApplication

qt_app = QApplication([])
clipboard = qt_app.clipboard()


def skip(text: str):
    length = len(text)
    if length < 30:
        if length > 3:
            print(f'{strftime("%H:%M:%S")}: len(text) < 30.')
            return True
        return False
    if text.count(' ') / len(text) < 0.05:
        print(f'{strftime("%H:%M:%S")}: space less than 5%.')
        return True
    return False


def on_clipboard_changed(cb_master: PipeConnection):
    mime_data = clipboard.mimeData()
    assert mime_data is not None
    if not mime_data.hasText():
        return
    text = mime_data.text()
    if skip(text) is True:
        return
    cb_master.send(text)


def run_qt_app(cb_master: PipeConnection):
    clipboard.dataChanged.connect(partial(on_clipboard_changed, cb_master))
    qt_app.exec()
