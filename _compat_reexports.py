import importlib.util
import sys
from pathlib import Path


def re_export_module(target: str) -> None:
    spec = importlib.util.find_spec(target)
    if spec is None or not spec.origin:
        raise ImportError(f"Unable to locate source for {target}")

    source = Path(spec.origin).read_text(encoding="utf-8")
    caller_globals = sys._getframe(1).f_globals
    caller_globals.setdefault("__all__", [])
    exec(compile(source, spec.origin, "exec"), caller_globals)
