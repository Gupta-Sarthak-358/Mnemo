import sys
import traceback
import os
from pathlib import Path

# --- Fix sys.stderr BEFORE any imports (frozen builds have stderr=None) ---
if sys.stderr is None:
    class _NullStream:
        def isatty(self): return False
        def write(self, *a, **kw): pass
        def flush(self, *a, **kw): pass
    sys.stderr = _NullStream()

try:
    from mnemo.daemon import main
except Exception:
    with open(Path.home() / "mnemo_crash.log", "w") as f:
        f.write("IMPORT ERROR\n")
        traceback.print_exc(file=f)
    sys.exit(1)

try:
    main()
except Exception:
    with open(Path.home() / "mnemo_crash.log", "w") as f:
        f.write("RUNTIME ERROR\n")
        traceback.print_exc(file=f)
    raise
