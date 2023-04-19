from typing import Optional
import sys
import logging
from functools import partialmethod
from generalimport import MissingOptionalDependency, missing_exception


EXCEPTION_NAMING_PATTERNS = ["Exception", "Error"]


logger = logging.getLogger("generalimport")


NON_CALLABLE_DUNDERS = (
    # Callable
    "__annotations__", "__closure__", "__code__", "__defaults__", "__globals__", "__kwdefaults__",
    # Info
    "__bases__", "__class__", "__dict__", "__doc__", "__module__", "__name__", "__qualname__", "__all__", "__slots__",
    # Pydantic
    "_nparams",
)

CALLABLE_DUNDERS = [
    # Binary
    "__ilshift__", "__invert__", "__irshift__", "__ixor__", "__lshift__", "__rlshift__", "__rrshift__", "__rshift__", 
    # Callable
    "__call__", 
    # Cast
    "__bool__", "__bytes__", "__complex__", "__float__", "__int__", "__iter__", "__hash__", 
    # Compare
    "__eq__", "__ge__", "__gt__", "__instancecheck__", "__le__", "__lt__", "__ne__", "__subclasscheck__", 
    # Context
    "__enter__", "__exit__", 
    # Delete
    "__delattr__", "__delitem__", "__delslice__", 
    # Info
    "__sizeof__", "__subclasses__", 
    # Iterable
    "__len__", "__next__", "__reversed__", "__contains__", "__getitem__", "__setitem__", 
    # Logic
    "__and__", "__iand__", "__ior__", "__or__", "__rand__", "__ror__", "__rxor__", "__xor__", 
    # Lookup
    "__class_getitem__", "__dir__", 
    # Math
    "__abs__", "__add__", "__ceil__", "__divmod__", "__floor__", "__floordiv__", "__iadd__", "__ifloordiv__", 
    "__imod__", "__imul__", "__ipow__", "__isub__", "__itruediv__", "__mod__", "__mul__", "__neg__", "__pos__", 
    "__pow__", "__radd__", "__rdiv__", "__rdivmod__", "__rfloordiv__", "__rmod__", "__rmul__", "__round__", 
    "__rpow__", "__rsub__", "__rtruediv__", "__sub__", "__truediv__", "__trunc__", 
    # Matrix
    "__imatmul__", "__matmul__", "__rmatmul__", 
    # Object
    "__init_subclass__", "__prepare__", "__set_name__", 
    # Pickle 
    "__getnewargs__", "__getnewargs_ex__", "__getstate__", "__reduce__", "__reduce_ex__", 
    # String
    "__format__", "__fspath__", "__repr__", "__str__", 
    # Thread
    "__aenter__", "__aexit__", "__aiter__", "__anext__", "__await__",
    # Typing
    "__origin__", 
]


class FakeModule:
    """ Behaves like a module but any attrs asked for always returns self.
        Raises a ModuleNotFoundError when used in any way.
        Unhandled use-cases: https://github.com/ManderaGeneral/generalimport/issues?q=is%3Aissue+is%3Aopen+label%3Aunhandled """
    __path__ = []

    def __init__(self, spec, trigger: Optional[str] = None):
        self.name = spec.name
        self.trigger = trigger or spec.name

        self.__name__ = spec.name
        self.__loader__ = spec.loader
        self.__spec__ = spec
        self.__fake_module__ = True  # Should not be needed, but let's keep it for safety?

    def error_func(self, __caller: str, *args, **kwargs):
        """
        Function that is invoked every time the module is accessed through a callable or non callable attribute, most
        dunders included.
        """
        name = f"'{self.name}'" if hasattr(self, "name") else ""  # For __class_getitem__
        trigger = f"'{self.trigger}'" if hasattr(self, "trigger") else ""  # For __class_getitem__
        raise MissingOptionalDependency(
            f"Optional dependency {name} (required by '{trigger}') was used but it isn't installed."
        )

    def __getattr__(self, item):

        if any(str(item).endswith(pattern) for pattern in EXCEPTION_NAMING_PATTERNS):
            return missing_exception(dependency=self.name, trigger=item)
        
        if item in NON_CALLABLE_DUNDERS:
            self.error_func()
        
        return FakeModule(spec=self.__spec__, trigger=item)

    def __mro_entries__(self, *a, **k):
        """
        This prevents the creation of subclasses from triggering `generalimport`.

        The classes so generated will trigger generalimport as soon as they're instantiated.
        """
        class FakeBaseClass:

            def __new__(fake_cls, *args, **kwargs):
                self.error_func("__new__")

            def __init__(fake_self, *args, **kwargs):
                self.error_func("__init__")

        return (FakeBaseClass, )
        

# Sets all the callable dunders of FakeModule to 'error_func()' by preserving the name of the dunder that triggered it.
# Mainly useful for debug purposes.
for dunder in CALLABLE_DUNDERS:
    setattr(FakeModule, dunder, partialmethod(FakeModule.error_func, dunder))


def is_imported(module_name: str) -> bool:
    """
    Returns True if the module was actually imported, False, if generalimport mocked it.
    """
    module = sys.modules.get(module_name)
    try:
        return bool(module and not isinstance(module, FakeModule))
    except MissingOptionalDependency as exc:
        # isinstance() raises MissingOptionalDependency: fake module
        pass
    return False
