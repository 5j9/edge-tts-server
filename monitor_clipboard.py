from PyQt6.QtWidgets import QApplication

qt_app = QApplication([])
clipboard = qt_app.clipboard()


def on_clipboard_changed():
    mime_data = clipboard.mimeData()
    assert mime_data is not None
    if not mime_data.hasText():
        return
    print(mime_data.text())
    raise SystemExit


clipboard.dataChanged.connect(on_clipboard_changed)
qt_app.exec()
