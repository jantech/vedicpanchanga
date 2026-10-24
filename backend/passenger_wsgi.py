"""Phusion Passenger entry point for cPanel "Setup Python App".

Passenger speaks WSGI, FastAPI is ASGI, so a2wsgi bridges the two. The VPS
deploy (uvicorn server:app) does not use this file.

cPanel mounts the app at a URL such as /api and hands us PATH_INFO with that
prefix stripped (SCRIPT_NAME=/api). Our routes already include the /api
prefix, so the shim below puts the prefix back into PATH_INFO.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Spawned PDF worker processes are unreliable under Passenger - render inline.
os.environ.setdefault("PDF_IN_PROCESS", "1")

from a2wsgi import ASGIMiddleware  # noqa: E402

from server import app  # noqa: E402

_wsgi = ASGIMiddleware(app)


def application(environ, start_response):
    script_name = environ.get("SCRIPT_NAME", "")
    if script_name:
        path = environ.get("PATH_INFO", "")
        if not path.startswith(script_name):
            environ["PATH_INFO"] = script_name + path
        environ["SCRIPT_NAME"] = ""
    return _wsgi(environ, start_response)
