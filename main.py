import threading
import webbrowser

import webview
from app import app

HOST = '127.0.0.1'
PORT = 5000
URL = f'http://{HOST}:{PORT}'


def start_flask():
    app.run(debug=False, host=HOST, port=PORT, use_reloader=False)


if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    try:
        webview.create_window('Plex Cataloger', URL, width=1200, height=800)
        webview.start()
    except Exception as exc:
        print('Unable to launch embedded browser window:', exc)
        print('Falling back to the system browser.')
        webbrowser.open(URL)
        flask_thread.join()
