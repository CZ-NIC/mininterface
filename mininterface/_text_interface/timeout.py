import sys
import threading
import time
from io import UnsupportedOperation
from ..exceptions import Cancelled

if sys.platform == "win32":
    import msvcrt
else:
    import select
    import tty
    import termios


def input_timeout(prompt: str, timeout: int = 0, exit_on_keypress: bool = False) -> str:
    """
    Cross-platform input with timeout and visual dots.

    - Shows dots every second until user starts typing.
    - exit_on_keypress=True: returns immediately after any key (prints newline immediately).
    - exit_on_keypress=False: disables timeout after first key, waits for Enter (newline printed at Enter).
    - Returns user input string or empty string if timeout expires.
    - Ctrl+C raises Cancelled.
    """
    input_started = threading.Event()
    inp = []

    # Thread to print dots
    def dots_thread():
        for _ in range(timeout):
            if input_started.is_set():
                break
            time.sleep(1)
            if not input_started.is_set():
                print(".", end="", flush=True)

    if timeout:
        print(f"{prompt} (countdown {int(timeout)} sec)", end="", flush=True)
        t_dots = threading.Thread(target=dots_thread, daemon=True)
        t_dots.start()
        timeout_running = True
    else:
        print(prompt + " ", end="", flush=True)
        timeout_running = False

    start_time = time.time()

    try:
        if sys.platform == "win32":
            while True:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    if char == "\r":
                        print()  # newline at Enter
                        return "".join(inp)
                    elif char == "\x03":  # Ctrl+C
                        raise Cancelled
                    elif char == "\x1b":  # Escape
                        raise Cancelled
                    elif char == "\x08":  # Backspace
                        if inp:
                            inp.pop()
                            print("\b \b", end="", flush=True)
                        continue
                    else:
                        inp.append(char)
                        print(char, end="", flush=True)

                    input_started.set()
                    if exit_on_keypress:
                        print()  # newline immediately
                        return "".join(inp)

                if timeout_running and (time.time() - start_time >= timeout) and not input_started.is_set():
                    input_started.set()
                    print()
                    return ""
                time.sleep(0.01)

        else:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            try:
                while True:
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if rlist:
                        char = sys.stdin.read(1)
                        if char == "\n":
                            print()  # newline at Enter
                            return "".join(inp)
                        elif char == "\x03":  # Ctrl+C
                            raise Cancelled
                        elif char == "\x1b":  # Escape
                            raise Cancelled
                        elif char == "\x7f":  # Backspace
                            if inp:
                                inp.pop()
                                print("\b \b", end="", flush=True)
                            continue
                        else:
                            inp.append(char)
                            print(char, end="", flush=True)

                        input_started.set()
                        if exit_on_keypress:
                            print()  # newline immediately
                            return "".join(inp)

                    if timeout_running and (time.time() - start_time >= timeout) and not input_started.is_set():
                        input_started.set()
                        print()
                        return ""
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    except Exception:
        # Fallback to class input.
        # 'Press any key' will not work.
        # Github actions raises `termios.error: (25, 'Inappropriate ioctl for device')`
        # pytest test_interface.py::TestInterface::test_ask raises `io.UnsupportedOperation: redirected stdin is pseudofile, has no fileno()`
        return input(prompt + " ")
    finally:
        input_started.set()  # ensure dots thread stops
