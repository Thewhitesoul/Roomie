"""Run real Chrome profile and matching checks against a temporary SQLite-backed Roomie app.

From the repository root: .venv/bin/python tests/browser/run_profile.py
Requires Node with built-in WebSocket support and a Chrome executable. Override
ROOMIE_CHROME_EXECUTABLE if Chrome is not at its usual macOS location.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/roomie'))
from app import create_app
from app.db import get_db, init_db
from werkzeug.security import generate_password_hash


def main():
    with tempfile.TemporaryDirectory(prefix='roomie-profile-browser-') as directory:
        app = create_app({'TESTING': True, 'SECRET_KEY': 'browser-test-only',
                          'DATABASE': str(Path(directory) / 'test.sqlite'),
                          'SESSION_COOKIE_SECURE': False})  # Loopback HTTP test server only.
        with app.app_context():
            init_db()
            connection = get_db()
            uid = connection.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
                ('browser_legacy', 'browser_legacy@washburn.edu', generate_password_hash('password123'))).lastrowid
            pid = connection.execute("""INSERT INTO profiles(user_id,name,age,preferred_location,budget,bio)
                VALUES(?, 'Legacy Browser', 29, 'Lawrence', 0, 'Preserved biography')""", (uid,)).lastrowid
            connection.execute("INSERT INTO profile_interests VALUES(?, 'music')", (pid,))
            connection.commit()
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(['node', str(Path(__file__).with_name('profile.mjs')),
                                     f'http://127.0.0.1:{server.server_port}', *sys.argv[1:]])
            return result.returncode
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
