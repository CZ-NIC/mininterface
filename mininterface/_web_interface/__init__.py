"""WebInterface: browser-based Textual UI via textual-serve.

Architecture
------------
Each browser connection spawns a fresh run of the user script.
Code before run() executes once per session (per tab).

Main process (launcher)
  → detects no TEXTUAL_DRIVER env var
  → starts textual-serve with [sys.executable] + sys.argv as command
  → opens browser, waits until textual-serve exits, then sys.exit(0)

Child process (per browser connection, spawned by textual-serve)
  → has TEXTUAL_DRIVER=textual.drivers.web_driver:WebDriver in env
  → WebInterface detects this and uses TextualSubprocessAdaptor
  → TextualSubprocessAdaptor spawns a grandchild subprocess
  → grandchild inherits TEXTUAL_DRIVER and runs TextualApp with WebDriver
  → WebSocket is established via the grandchild; multiple .form() calls
    are served over the same connection via IPC pipes
"""
import os
import subprocess
import sys
import time
import webbrowser

from .._textual_interface.interface import TextualInterface
from .._textual_interface.subprocess_adaptor import TextualSubprocessAdaptor

_DEFAULT_PORT = 64646


class WebInterface(TextualInterface):
    """Browser-based interface. Each tab gets its own independent session."""

    _adaptor: TextualSubprocessAdaptor

    def __init__(self, *args, cmd=None, port=_DEFAULT_PORT, **kwargs):
        if not os.environ.get("TEXTUAL_DRIVER"):
            # Launcher mode: start textual-serve, open browser, block.
            _launch_web_server(cmd=cmd, port=port)
            sys.exit(0)
        # Child mode: running inside a textual-serve subprocess.
        super().__init__(*args, need_atty=False, **kwargs)


def _launch_web_server(cmd=None, port=_DEFAULT_PORT) -> None:
    """Start textual-serve with the user script as command, open browser, block."""
    import shlex

    try:
        from textual_serve.server import Server  # noqa: F401 – check availability
    except ImportError:
        from ..exceptions import DependencyRequired
        raise DependencyRequired("web")

    if cmd is not None:
        # Launched via `mininterface web script.py` — run the given script directly.
        command = shlex.join([sys.executable, str(cmd)])
    else:
        # Launched via MININTERFACE_INTERFACE=web python3 script.py — re-run as-is.
        command = shlex.join([sys.executable] + sys.argv)
    # Suppress the "RuntimeError: Event loop is closed" noise that asyncio emits
    # during shutdown when GC collects BaseSubprocessTransport after the loop closes.
    # This is a known asyncio/Python issue in the textual-serve process.
    serve_code = "\n".join([
        "import sys",
        "_orig_hook = sys.unraisablehook",
        "def _hook(u):",
        "    if isinstance(getattr(u, 'exc_value', None), RuntimeError) and 'Event loop is closed' in str(u.exc_value):",
        "        return",
        "    _orig_hook(u)",
        "sys.unraisablehook = _hook",
        f"from textual_serve.server import Server",
        f"Server({command!r}, port={port}, title='mininterface').serve()",
    ])
    env = os.environ.copy()
    env["MININTERFACE_ENFORCED_WEB"] = "1"
    serve_process = subprocess.Popen([sys.executable, "-c", serve_code], env=env)

    time.sleep(0.5)
    url = f"http://localhost:{port}"
    print(f"Web interface: {url}", flush=True)
    webbrowser.open(url)

    try:
        serve_process.wait()
    except KeyboardInterrupt:
        serve_process.terminate()
        serve_process.wait()
