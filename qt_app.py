from multiprocessing.connection import PipeConnection

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.player = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.player.setAudioOutput(self.audioOutput)

        self.playButton = QPushButton('Play')
        self.playButton.clicked.connect(self.playAudio)

        self.speedSlider = QSlider(Qt.Orientation.Horizontal)
        self.speedSlider.setMinimum(50)  # 0.5x speed
        self.speedSlider.setMaximum(300)  # 3.0x speed
        self.speedSlider.setValue(200)  # 2.0x speed
        self.speedSlider.valueChanged.connect(self.updatePlaybackRate)

        self.speedLabel = QLabel('1.0x')

        speedLayout = QHBoxLayout()
        speedLayout.addWidget(QLabel('Speed:'))
        speedLayout.addWidget(self.speedSlider)
        speedLayout.addWidget(self.speedLabel)

        layout = QVBoxLayout()
        layout.addWidget(self.playButton)
        layout.addLayout(speedLayout)
        self.setLayout(layout)

    def playAudio(self):
        url = QUrl(
            'http://127.0.0.1:3775/audio'
        )  # replace with a valid audio stream url.
        self.player.setSource(url)
        self.player.play()

    def updatePlaybackRate(self, value):
        rate = value / 100.0
        self.player.setPlaybackRate(rate)
        self.speedLabel.setText(f'{rate:.1f}x')


class SystemTrayApp(QApplication):
    def __init__(self, sys_argv, cb_master: PipeConnection):
        super().__init__(sys_argv)
        self.cb_master = cb_master

        self.setup_tray_icon()

        self.audio_player = AudioPlayer()

        clipboard = self.clipboard()
        clipboard.dataChanged.connect(self.on_clipboard_changed)

    def setup_tray_menu(self):
        menu = QMenu()

        start_action = menu.addAction('Start Monitoring')
        start_action.triggered.connect(self.on_start)

        stop_action = menu.addAction('Stop Monitoring')
        stop_action.triggered.connect(self.on_stop)

        exit_ = menu.addAction('Exit')
        exit_.triggered.connect(self.quit)

        self.menu = menu

    def setup_tray_icon(self):
        self.setQuitOnLastWindowClosed(False)  # Important for tray app

        tray_icon = self.tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon('speaker-on.svg'))
        tray_icon.setVisible(True)

        self.setup_tray_menu()
        tray_icon.setContextMenu(self.menu)
        tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        match reason:
            case QSystemTrayIcon.ActivationReason.Trigger:
                self.audio_player.show()
            case QSystemTrayIcon.ActivationReason.Context:
                print('Right click on tray icon')
            case QSystemTrayIcon.ActivationReason.DoubleClick:
                self.audio_player.player.pause()
            case QSystemTrayIcon.ActivationReason.MiddleClick:
                print('Middle click on tray icon')

    def on_stop(self):
        self.tray_icon.setIcon(QIcon('speaker-off.svg'))

    def on_start(self):
        self.tray_icon.setIcon(QIcon('speaker-on.svg'))

    def on_clipboard_changed(self):
        mime_data = self.clipboard.mimeData()
        assert mime_data is not None
        if not mime_data.hasText():
            return
        self.cb_master.send(mime_data.text())


def run_qt_app(cb_master: PipeConnection):
    app = SystemTrayApp([], cb_master)
    app.exec()


if __name__ == '__main__':
    run_qt_app(None)
