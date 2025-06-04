# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
Copyright (c) 2020 - NeuroAssassin
"""
import base64
import json
import logging
import os
import sys
# Background thread libraries
import threading
import time
import traceback

import websocket
# Base libraries
from babel import Locale
# Secret key libraries
from cryptography import fernet
# Flask related libraries
from flask import Flask, render_template, session, url_for
from flask_babel import Babel
# Relative imports
from reddash.app.constants import ALLOWED_LOCALES, DEFAULTS, WS_URL, Lock
from reddash.app.tasks import TaskManager
from reddash.app.utils import (add_constants, apply_themes, initialize_babel,
                               register_blueprints, startup_message)
# Terminal related libraries
from rich import console
from rich import logging as richlogging
from rich import progress
from rich import traceback as rtb
from waitress import serve

# Logging and terminal set up

log = logging.getLogger("werkzeug")
dashlog = logging.getLogger("reddash")
queuelog = logging.getLogger("waitress.queue")

console = console.Console()
oldexcepthook = rtb.install()
progress_bar = progress.Progress(
    "{task.description}", progress.TextColumn("{task.fields[status]}\n")
)

logging.basicConfig(
    format="%(message)s", handlers=[richlogging.RichHandler(console=progress_bar)]
)
queuelog.setLevel(logging.ERROR)

# Base variable setup
app = Flask("reddash", static_folder="app/base/static")
lock = Lock()
babel = Babel()


def create_app(host, port, rpcport, interval, debug, dev):
    url = f"{WS_URL}{rpcport}"

    # Session encoding
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)

    # JWT encoding
    jwt_fernet_key = fernet.Fernet.generate_key()
    jwt_secret_key = base64.urlsafe_b64decode(jwt_fernet_key)

    # Initialize websocket variables
    app.ws_url = url
    app.ws = None
    app.lock = lock
    app.rpcport = str(rpcport)
    app.rpcversion = 0
    app.interval = interval

    # Initialize core variables
    app.task_manager = TaskManager(app, console, progress_bar)
    app.dashlog = dashlog
    app.progress = progress_bar
    app.running = True
    app.variables = {}
    app.commanddata = {}
    app.cooldowns = {
        "serverprefix": {},
        "adminroles": {},
        "modroles": {},
        "fetchrules": {},
        "fetchtargets": {},
        "fetchcogcommands": {},
        "addrule": {},
        "adddefaultrule": {},
        "removerule": {},
        "removedefaultrule": {},
        "fetchaliases": {},
    }
    app.blacklisted = []

    # Initialize config
    app.config.from_object(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = "app/translations"

    locale_dict = {}
    for locale in ALLOWED_LOCALES:
        l = Locale.parse(locale)
        lang = l.get_language_name(locale)
        if territory := l.get_territory_name(locale):
            lang = f"{l.get_language_name(locale)} - {l.get_territory_name(locale)}"
        locale_dict[locale] = lang

    app.config["LANGUAGES"] = ALLOWED_LOCALES
    app.config["LOCALE_DICT"] = locale_dict
    app.secret_key = secret_key
    app.jwt_secret_key = jwt_secret_key

    babel = Babel(app)

    # Initialize core app functions
    register_blueprints(app)
    apply_themes(app)
    add_constants(app)
    initialize_babel(app, babel)

    if debug:
        log.setLevel(logging.DEBUG)
        dashlog.setLevel(logging.DEBUG)

    kwargs = {"host": host, "port": port, "dev": dev, "debug": debug}
    progress_tasks = startup_message(app, progress_bar, kwargs)

    app.task_manager.start_tasks(progress_tasks)

    if dev:
        app.run(host=host, port=port, debug=debug)
    else:
        serve(app, host=host, port=port, _quiet=True)

    app.dashlog.fatal("Shutting down...")
    app.running = False
    app.task_manager.stop_tasks()

    app.dashlog.fatal("Webserver terminated")
