# scenes/loader.py

import pkgutil
import importlib

def register_all(registry):
    """
    Dynamically import every module in `scenes/` (except this one)
    and call its `register(registry)` function if present.
    """
    import scenes  # your package
    for _, modname, _ in pkgutil.iter_modules(scenes.__path__):
        if modname == "loader":
            continue
        module = importlib.import_module(f"scenes.{modname}")
        if hasattr(module, "register"):
            module.register(registry)
