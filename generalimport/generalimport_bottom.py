import importlib
import inspect
import pkgutil
import sys
from pathlib import Path


def get_installed_modules_names():
    """ https://stackoverflow.com/a/73958089/3936044 """
    iter_modules = {module.name for module in pkgutil.iter_modules()}
    builtin = sys.builtin_module_names
    return set.union(iter_modules, builtin)

def module_is_installed(*names):
    """ Returns whether a package is installed.
        `find_spec(name) is None` was the previous solution but namespaces returned True.
        Todo: Change back to find_spec if spec_is_namespace works. """
    packages = get_installed_modules_names()
    for name in names:
        if name not in packages:
            return False
    return True

def _safe_import(name):
    try:
        return importlib.import_module(name=name)
    except (ModuleNotFoundError, TypeError, ImportError) as e:
        return None

def import_module(name, error=True):
    """ Like importlib.import_module with optional error paremeter to return None if errored.
        Also excludes namespaces. """
    module = _safe_import(name=name)
    if module_is_namespace(module=module):
        if error:
            raise ModuleNotFoundError(f"Module '{name}' is only a namespace.")
        return None
    else:
        if module is None and error:
            raise ModuleNotFoundError(f"Module '{name}' isn't installed.")
        return module

def spec_is_namespace(spec):
    return spec and spec.loader is None

def module_is_namespace(module):
    """ Returns if given module is a namespace. """
    return hasattr(module, "__path__") and getattr(module, "__file__", None) is None

def module_name_is_namespace(name):
    """ Checks if module's name is a namespace without adding it to sys.modules. """
    was_in_modules = name in sys.modules
    module = _safe_import(name=name)
    is_namespace = module_is_namespace(module=module)

    if was_in_modules:
        sys.modules.pop(name, None)

    return is_namespace

def _get_previous_frame_filename(depth):
    # from pprint import pprint
    # pprint(inspect.stack())
    for frame in inspect.stack()[depth:]:
        if "importlib" not in frame.filename and "bottom.py" not in frame.filename:
            return frame.filename

def _get_scope_from_filename(filename):
    last_part = Path(filename).parts[-1]
    return filename[0:filename.index(last_part)]

def _get_top_name(fullname):
    return fullname.split(".")[0]
