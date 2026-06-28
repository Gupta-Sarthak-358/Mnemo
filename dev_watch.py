"""Dev mode: watches src/mnemo/ for .py changes and auto-restarts the daemon."""
import subprocess, time, os, sys

WATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "mnemo")
PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")


class ChangeHandler:
    def __init__(self):
        self.changed = False

    def check(self):
        if not hasattr(self, '_mtimes'):
            self._mtimes = {}
            self._snapshot()
            return False
        self.changed = False
        current = {}
        for root, dirs, files in os.walk(WATCH_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    try:
                        current[p] = os.path.getmtime(p)
                    except OSError:
                        pass
        for p, t in current.items():
            if self._mtimes.get(p, 0) < t:
                self.changed = True
                break
        if not self.changed:
            for p in self._mtimes:
                if p not in current:
                    self.changed = True
                    break
        self._mtimes = current
        return self.changed

    def _snapshot(self):
        for root, dirs, files in os.walk(WATCH_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    try:
                        self._mtimes[p] = os.path.getmtime(p)
                    except OSError:
                        pass


def start_daemon():
    return subprocess.Popen(
        [PYTHON, "-X", "utf8", "-m", "mnemo.daemon"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )


if __name__ == "__main__":
    print("===================================")
    print("  Mnemo Dev Mode")
    print("===================================")
    print(f"Watching: {WATCH_DIR}")
    print("Edit a .py file and save to auto-restart.")
    print("Ctrl+C to quit.\n")

    handler = ChangeHandler()
    handler.check()
    proc = start_daemon()
    print(f"  [Daemon started — PID {proc.pid}]\n")

    try:
        while True:
            time.sleep(1.5)
            if handler.check():
                print("  Change detected — restarting...")
                proc.kill()
                proc.wait(timeout=5)
                time.sleep(1)
                proc = start_daemon()
                print(f"  [Daemon started — PID {proc.pid}]\n")
    except KeyboardInterrupt:
        print("\n  Stopping...")
        proc.kill()
        proc.wait(timeout=5)
        print("  Done.")
