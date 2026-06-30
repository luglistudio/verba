"""Costanti e utility condivise."""

import os
import shutil
import sys
from datetime import datetime


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WIKI_DIR = os.path.join(BASE_DIR, "wiki")
NOTEBOOKLM_CLI = shutil.which("notebooklm") or os.path.join(os.path.expanduser("~"), ".local", "bin", "notebooklm")


def debug_log(msg):
    log_path = os.path.join(BASE_DIR, "app_debug.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def get_notebooklm_env():
    env = os.environ.copy()
    user_home = os.path.expanduser("~")
    extra_paths = [
        os.path.join(user_home, ".local", "bin"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin"
    ]
    current_path = env.get("PATH", "")
    for p in extra_paths:
        if p not in current_path:
            current_path = p + os.pathsep + current_path
    env["PATH"] = current_path
    env["HOME"] = user_home
    env["PYTHONUNBUFFERED"] = "1"
    return env
