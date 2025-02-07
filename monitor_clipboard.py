from functools import partial
from multiprocessing.connection import PipeConnection

from PyQt6.QtWidgets import QApplication

qt_app = QApplication([])
clipboard = qt_app.clipboard()


def on_clipboard_changed(cb_master: PipeConnection):
    mime_data = clipboard.mimeData()
    assert mime_data is not None
    if not mime_data.hasText():
        return
    cb_master.send(mime_data.text())


def run_qt_app(cb_master: PipeConnection):
    clipboard.dataChanged.connect(partial(on_clipboard_changed, cb_master))
    qt_app.exec()
