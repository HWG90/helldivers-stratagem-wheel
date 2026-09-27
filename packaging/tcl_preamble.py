# Inserted into the Windows launch script before tkinter is imported.
# The embeddable CPython zip has no tcl/tk paths of its own.
from pathlib import Path

_py_home = Path(sys.executable).resolve().parent
_tcl_dir = _py_home / "tcl" / "tcl8.6"
_tk_dir = _py_home / "tcl" / "tk8.6"
if (_tcl_dir / "init.tcl").is_file():
    os.environ.setdefault("TCL_LIBRARY", str(_tcl_dir))
if (_tk_dir / "tk.tcl").is_file():
    os.environ.setdefault("TK_LIBRARY", str(_tk_dir))
