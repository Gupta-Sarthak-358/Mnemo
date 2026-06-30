import sys
import traceback
import os
import time
from pathlib import Path

start = time.time()

def t():
    return round((time.time() - start) * 1000)

# --- Fix sys.stderr BEFORE any imports (frozen builds have stderr=None) ---
if sys.stderr is None:
    class _NullStream:
        def isatty(self): return False
        def write(self, *a, **kw): pass
        def flush(self, *a, **kw): pass
    sys.stderr = _NullStream()

# File-based debug log
error_log = Path.home() / "mnemo_crash.log"
debug_log = Path.home() / "mnemo_debug.log"

def log_debug(msg):
    try:
        with open(debug_log, "a") as f:
            f.write(f"{t()}ms {msg}\n")
    except Exception:
        pass

log_debug("=== Mnemo Start ===")
log_debug(f"frozen: {getattr(sys, 'frozen', False)}")
log_debug(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

try:
    log_debug("Importing mnemo.daemon...")
    from mnemo.daemon import main
    log_debug("Import OK")
except Exception:
    log_debug("IMPORT ERROR")
    with open(error_log, "w") as f:
        f.write("IMPORT ERROR\n")
        traceback.print_exc(file=f)
    sys.exit(1)

try:
    log_debug("Calling main()...")
    main()
except Exception:
    log_debug("RUNTIME ERROR")
    with open(error_log, "w") as f:
        f.write("RUNTIME ERROR\n")
        traceback.print_exc(file=f)
    raise
