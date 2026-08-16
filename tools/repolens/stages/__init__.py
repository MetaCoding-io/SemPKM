"""Importing this package registers every stage.

To add a stage: create a module here, decorate functions with @stage(...),
and add the module to the import list below.
"""
from . import source, code, conventions, drill, symbols, output, graph   # noqa: F401
