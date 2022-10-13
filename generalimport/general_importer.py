import importlib
import sys

from logging import getLogger

from generalimport import FakeModule, spec_is_namespace, _get_previous_frame_filename


class GeneralImporter:
    """ Creates fake packages if they don't exist.
        These fake packages' attrs are always a function that raises a ModuleNotFoundError when used.
        This lets you write a single line to handle all your optional dependencies.
        If wildcard (default "*") is provided then this will work on any missing package. """

    singleton_instance = None

    def __init__(self):
        self.catchers = []

        self._singleton()
        self._skip_fullname = None
        sys.meta_path.insert(0, self)

    def catch(self, fullname):
        """ Return first catcher that handles given fullname and filename.

            :rtype: generalimport.ImportCatcher """
        for catcher in self.catchers:
            if catcher.handle(fullname=fullname):
                return catcher

    def find_module(self, fullname, path=None):
        """ Returns self if fullname is in names, or if wildcard is present. """
        if self._ignore_next_import(fullname=fullname):
            return self._handle_ignore(fullname=fullname, reason="Recursive break")

        if not self.catch(fullname=fullname):
            return self._handle_ignore(fullname=fullname, reason="Unhandled")

        spec = importlib.util.find_spec(fullname)
        if not spec:
            return self._handle_handle(fullname=fullname, reason="Doesn't exist")

        if spec_is_namespace(spec=spec):
            return self._handle_handle(fullname=fullname, reason="Namespace package")

        return self._handle_relay(fullname=fullname, loader=spec.loader)

    def load_module(self, fullname):
        """ Adds a FakeModule instance to sys.modules. """
        module = FakeModule(name=fullname)
        sys.modules[fullname] = module



    def _singleton(self):
        assert self.singleton_instance is None
        GeneralImporter.singleton_instance = self

    def _ignore_next_import(self, fullname):
        if fullname == self._skip_fullname:
            self._skip_fullname = None
            return True
        else:
            self._skip_fullname = fullname
            return False

    def _handle_ignore(self, fullname, reason):
        # print(f"Ignoring '{fullname}' - {reason}")
        getLogger(__name__).debug(f"Ignoring '{fullname}' - {reason}")
        return None

    def _handle_handle(self, fullname, reason):
        # print(f"Handling '{fullname}' - {reason}")
        getLogger(__name__).info(f"Handling '{fullname}' - {reason}")
        sys.modules.pop(fullname, None)  # Remove possible namespace
        return self

    def _handle_relay(self, fullname, loader):
        # print(f"'{fullname}' exists, returning it's loader '{loader}'")
        getLogger(__name__).debug(f"'{fullname}' exists, returning it's loader '{loader}'")
        return loader
