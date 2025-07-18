import re
from functools import partial
from multiprocessing.connection import PipeConnection
from time import time
from typing import Any

from logging_ import logger
from PyQt6.QtGui import QAction, QClipboard
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
)

# Global flag to control monitoring state
monitoring_paused = False

qt_app = QApplication([])
# Ensure the application continues to run even if there are no visible windows,
# which is necessary for the system tray icon to persist.
qt_app.setQuitOnLastWindowClosed(False)

clipboard: QClipboard = qt_app.clipboard()  # type: ignore

rm_urls = partial(re.compile(r'https?:\/\/[^\s]*').sub, '')


def skip(text: str):
    """
    Determines if the given text should be skipped based on length and space density.
    """
    length = len(text)
    if length < 30:
        logger.info('len(text) < 30. Skipping.')
        return True
    if text.count(' ') / length < 0.05:
        logger.info('Space count less than 5%. Skipping.')
        return True
    return False


last_processed_time = 0.0
DEBOUNCE_SECONDS = 0.1


def on_clipboard_changed(cb_master: PipeConnection):
    """
    Callback function triggered when clipboard content changes.
    Processes the text if monitoring is active and sends it via the pipe.
    """
    global last_processed_time, monitoring_paused

    # If monitoring is paused, do not process clipboard changes
    if monitoring_paused:
        logger.info('Monitoring is paused. Skipping clipboard change event.')
        return

    current_time = time()
    # Debounce mechanism to prevent rapid, duplicate processing
    if current_time - last_processed_time < DEBOUNCE_SECONDS:
        logger.info('Debouncing duplicate signal.')
        return
    last_processed_time = current_time

    mime_data = clipboard.mimeData()
    assert mime_data is not None
    # Only process if the clipboard contains text
    if not mime_data.hasText():
        return

    text = mime_data.text()
    if skip(text) is True:
        return

    logger.info(f'Received text: {text[:50]}...')  # Log a snippet for brevity
    # Send the processed text (URLs removed) through the pipe
    cb_master.send(rm_urls(text))


# --- Functions for controlling monitoring state via tray icon ---


def toggle_monitoring(
    tray_icon: QSystemTrayIcon,
    pause_action: QAction,
    resume_action: QAction,
    style: QStyle,
):
    """
    Toggles the monitoring state (pause/resume) and updates the tray icon's menu actions.
    Also changes the tray icon to reflect the current state.
    """
    global monitoring_paused
    monitoring_paused = not monitoring_paused

    if monitoring_paused:
        logger.info('Monitoring paused via tray icon.')
        # tray_icon.showMessage(
        #     'Clipboard Monitor',
        #     'Monitoring is now PAUSED.',
        #     QSystemTrayIcon.MessageIcon.Information,
        #     2000,  # Message will disappear after 2 seconds
        # )
        pause_action.setEnabled(False)  # Disable pause option
        resume_action.setEnabled(True)  # Enable resume option
        tray_icon.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        )  # Change icon to pause
        tray_icon.setToolTip('Clipboard Monitor (Paused)')
    else:
        logger.info('Monitoring resumed via tray icon.')
        # tray_icon.showMessage(
        #     'Clipboard Monitor',
        #     'Monitoring is now RESUMED.',
        #     QSystemTrayIcon.MessageIcon.Information,
        #     2000,
        # )
        pause_action.setEnabled(True)  # Enable pause option
        resume_action.setEnabled(False)  # Disable resume option
        tray_icon.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )  # Change icon to play
        tray_icon.setToolTip('Clipboard Monitor (Active)')


def show_about_message():
    """
    Displays an 'About' message box.
    """
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setText('Clipboard Monitor Application')
    msg_box.setInformativeText(
        'Monitors clipboard changes and processes text.\n\nDeveloped with PyQt6.'
    )
    msg_box.setWindowTitle('About')
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def run_qt_app(cb_master: PipeConnection):
    """
    Initializes and runs the PyQt6 application, including the system tray icon.
    """
    # Create the system tray icon
    style = qt_app.style()
    assert style is not None
    # Set initial icon to SP_MediaPlay as monitoring starts active
    tray_icon = QSystemTrayIcon(
        style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), qt_app
    )
    tray_icon.setToolTip('Clipboard Monitor (Active)')  # Initial tooltip
    tray_icon.setVisible(True)

    # Create the context menu for the tray icon
    tray_menu = QMenu()

    # Add "Pause Monitoring" action
    pause_action = QAction('Pause Monitoring', qt_app)
    # Initially enabled because monitoring starts active
    pause_action.triggered.connect(
        partial(toggle_monitoring, tray_icon, pause_action, QAction(), style)
    )  # QAction() is a placeholder, will be replaced below
    tray_menu.addAction(pause_action)

    # Add "Resume Monitoring" action
    resume_action = QAction('Resume Monitoring', qt_app)
    # Initially disabled because monitoring starts active
    resume_action.setEnabled(False)
    resume_action.triggered.connect(
        partial(
            toggle_monitoring, tray_icon, pause_action, resume_action, style
        )
    )
    tray_menu.addAction(resume_action)

    # Update the partial for pause_action to include the actual resume_action and style
    # This is a bit of a workaround because `resume_action` isn't fully defined
    # when `pause_action` is created.
    pause_action.triggered.disconnect()  # Disconnect the placeholder partial
    pause_action.triggered.connect(
        partial(
            toggle_monitoring, tray_icon, pause_action, resume_action, style
        )
    )

    tray_menu.addSeparator()  # Add a separator line

    # Add "About" action
    about_action = QAction('About', qt_app)
    about_action.triggered.connect(show_about_message)
    tray_menu.addAction(about_action)

    # Add "Quit" action
    quit_action = QAction('Quit', qt_app)
    quit_action.triggered.connect(qt_app.quit)
    tray_menu.addAction(quit_action)

    # Set the context menu for the tray icon
    tray_icon.setContextMenu(tray_menu)

    # Connect the activated signal of the tray icon to toggle_monitoring
    # This will trigger toggle_monitoring when the icon is clicked (left-click by default)
    tray_icon.activated.connect(
        lambda reason: toggle_monitoring(
            tray_icon, pause_action, resume_action, style
        )
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )

    # Connect the clipboard dataChanged signal to your handler
    clipboard.dataChanged.connect(
        partial(on_clipboard_changed, cb_master=cb_master)
    )

    # Start the Qt application event loop
    qt_app.exec()


if __name__ == '__main__':
    # This block is for testing the tray icon functionality independently.
    # In your actual multiprocessing setup, `run_qt_app` will be called
    # in a separate process with a PipeConnection.
    # For a standalone test, we create a dummy PipeConnection.

    class DummyPipeConnection:
        def send(self, data):
            print(f"Dummy Pipe: Sent '{data[:50]}...'")

    dummy_pipe_con: Any = DummyPipeConnection()

    print(
        'Running Qt application with tray icon. Look for the icon in your system tray.'
    )
    print('Right-click the icon to see options.')
    run_qt_app(dummy_pipe_con)
