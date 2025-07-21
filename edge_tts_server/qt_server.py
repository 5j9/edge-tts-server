import re
from functools import partial
from multiprocessing.connection import PipeConnection
from time import time

from logging_ import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QClipboard
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
)

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


def on_clipboard_changed():
    """
    Callback function triggered when clipboard content changes.
    Processes the text if monitoring is active and sends it via the pipe.
    """
    global last_processed_time

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
    if skip(text):
        return

    logger.info(f'Received text: {text[:50]}...')  # Log a snippet for brevity
    # Send the processed text (URLs removed) through the pipe
    conn.send(rm_urls(text))


partial_on_clipboard_changed = partial(on_clipboard_changed)

# --- Functions for controlling monitoring state via tray icon and pipe ---


def _update_tray_ui(
    activate: bool,
    tray_icon: QSystemTrayIcon,
    pause_action: QAction,
    resume_action: QAction,
    style: QStyle,
):
    """
    Updates the system tray icon and menu actions.
    """
    if activate:
        pause_action.setEnabled(True)
        resume_action.setEnabled(False)
        tray_icon.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        )
        tray_icon.setToolTip('Clipboard Monitor (Active)')

        clipboard.dataChanged.connect(partial_on_clipboard_changed)
    else:
        pause_action.setEnabled(False)
        resume_action.setEnabled(True)
        tray_icon.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        tray_icon.setToolTip('Clipboard Monitor (Paused)')

        try:
            clipboard.dataChanged.disconnect(partial_on_clipboard_changed)
        except TypeError:
            # dataChanged is not connected yet the first time app starts
            pass


def handle_tray_click(
    tray_icon: QSystemTrayIcon,
    pause_action: QAction,
    resume_action: QAction,
    style: QStyle,
):
    """
    Toggles the monitoring state (pause/resume) and updates the tray icon's menu actions.
    """
    is_paused = resume_action.isEnabled()
    if is_paused:
        conn.send(True)
        logger.info('Monitoring resumed via tray icon.')
    else:
        conn.send(False)
        logger.info('Monitoring paused via tray icon.')

    _update_tray_ui(is_paused, tray_icon, pause_action, resume_action, style)


def handle_pipe_recv(
    monitoring: bool,
    tray_icon: QSystemTrayIcon,
    pause_action: QAction,
    resume_action: QAction,
    style: QStyle,
):
    """
    Sets the monitoring state (True for active, False for paused) and updates the UI.
    This function is called by the pipe listener.
    """
    if monitoring:
        logger.info('Monitoring resumed via pipe message.')
    else:
        logger.info('Monitoring paused via pipe message.')

    _update_tray_ui(monitoring, tray_icon, pause_action, resume_action, style)


def show_about_message():
    """
    Displays an 'About' message box with a clickable link.
    """
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setText('Clipboard Monitor Application')

    # Use HTML for the link
    link_text = '<a href="https://github.com/5j9/edge-tts-server">GitHub Repository</a>'
    informative_text = (
        'Monitors clipboard changes and processes text.\n\nDeveloped with PyQt6.\n'
        f'For more information, visit our {link_text}.'
    )
    msg_box.setInformativeText(informative_text)

    # Set the text format to RichText to enable HTML parsing
    msg_box.setTextFormat(Qt.TextFormat.RichText)

    msg_box.setWindowTitle('About')
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


class PipeReaderThread(QThread):
    """
    A QThread subclass to read boolean messages from a multiprocessing PipeConnection
    and emit them as a Qt signal.
    """

    data_received = pyqtSignal(bool)  # Signal to emit boolean messages

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        """
        Continuously reads from the pipe and emits data.
        """
        logger.info('PipeReaderThread started.')
        while self._running:
            try:
                msg = conn.recv()
                if type(msg) is bool:
                    logger.info(f'PipeReaderThread received message: {msg}')
                    self.data_received.emit(msg)
                else:
                    logger.warning(
                        f'PipeReaderThread received non-boolean message from pipe: {msg}'
                    )
            except EOFError:
                logger.info('Pipe closed, PipeReaderThread exiting.')
                self._running = False
            except Exception as e:
                logger.error(f'Error in PipeReaderThread: {e}')
            finally:
                pass

        logger.info('PipeReaderThread stopped.')

    def stop(self):
        """
        Stops the thread's run loop.
        """
        self._running = False
        self.wait()  # Wait for the thread to finish execution


def run_qt_app(pipe: PipeConnection):
    """
    Initializes and runs the PyQt6 application, including the system tray icon
    and a listener for control messages from the pipe.
    """
    global conn
    conn = pipe
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
    # Add "Resume Monitoring" action
    resume_action = QAction('Resume Monitoring', qt_app)

    # Connect actions using partial to pass necessary UI elements
    # These actions will toggle the state
    pause_action.triggered.connect(
        partial(
            handle_tray_click,
            tray_icon,
            pause_action,
            resume_action,
            style,
        )
    )
    resume_action.triggered.connect(
        partial(
            handle_tray_click,
            tray_icon,
            pause_action,
            resume_action,
            style,
        )
    )

    tray_menu.addAction(pause_action)
    tray_menu.addAction(resume_action)

    # Initially update UI based on global monitoring_paused state (which is False by default)
    _update_tray_ui(False, tray_icon, pause_action, resume_action, style)

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
        lambda reason: handle_tray_click(
            tray_icon, pause_action, resume_action, style
        )
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )

    # --- Control Pipe Listener Setup ---
    # This pipe reads control messages *from* the main process *into* the Qt app
    pipe_recv_thread = PipeReaderThread()
    # Connect the thread's data_received signal to a slot that updates monitoring state
    pipe_recv_thread.data_received.connect(
        partial(
            handle_pipe_recv,
            tray_icon=tray_icon,
            pause_action=pause_action,
            resume_action=resume_action,
            style=style,
        )
    )
    pipe_recv_thread.start()  # Start the thread

    # Ensure the pipe_thread is stopped when the application quits
    qt_app.aboutToQuit.connect(pipe_recv_thread.stop)

    # Start the Qt application event loop
    qt_app.exec()


if __name__ == '__main__':
    # This block is for testing the tray icon functionality independently.
    # In your actual multiprocessing setup, `run_qt_app` will be called
    # in a separate process with two PipeConnections.
    # For a standalone test, we create two dummy PipeConnection pairs.

    import threading
    import time
    from multiprocessing import Pipe

    aio_conn, conn = Pipe()

    print(
        'Running Qt application with tray icon. Look for the icon in your system tray.'
    )
    print('Right-click the icon to see options.')
    print('Simulating control messages being sent to the Qt app...')

    # Simulate sending control messages from the "main process" side
    def simulate_control_messages():
        print('\nSimulating control messages (True/False) to Qt app...')
        # Send False after 3 seconds (pause monitoring)
        aio_conn.send(False)
        print('Sent False to control pipe (pause monitoring)')
        time.sleep(3)

        # Send True after 3 more seconds (resume monitoring)
        aio_conn.send(True)
        print('Sent True to control pipe (resume monitoring)')
        time.sleep(3)

        # Send False again after 3 more seconds
        aio_conn.send(False)
        print('Sent False to control pipe (pause monitoring)')
        time.sleep(3)

        # Send True again after 3 more seconds
        aio_conn.send(True)
        print('Sent True to control pipe (resume monitoring)')
        time.sleep(3)

        # Close the control pipe to signal end of messages
        aio_conn.close()

    # This part would typically be in the *other* process that communicates with the Qt app.
    # For this standalone test, we run it in a separate thread to avoid blocking the Qt event loop.
    control_sim_thread = threading.Thread(target=simulate_control_messages)
    control_sim_thread.daemon = (
        True  # Allow thread to exit when main program exits
    )
    control_sim_thread.start()

    # Start the Qt application
    # Pass the appropriate ends of the pipes to run_qt_app
    run_qt_app(conn)

    # After qt_app.exec() finishes (when the app quits), clean up pipes
    conn.close()

    # In a real multiprocessing scenario, the main process would read from
    # main_clipboard_recv_pipe here if it needed to process clipboard data.
    # For this test, we just ensure it's closed.
    aio_conn.close()
    control_sim_thread.join(
        timeout=1
    )  # Give the simulation thread a chance to finish
    print('Qt application exited.')
