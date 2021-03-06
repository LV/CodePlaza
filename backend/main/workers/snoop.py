import ast
import inspect
import sys

import snoop
import snoop.formatting
import snoop.tracer

from .worker import execute
from ..utils import internal_dir

snoop.tracer.internal_directories += (internal_dir,)


class PatchedFrameInfo(snoop.tracer.FrameInfo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        code = self.frame.f_code
        self.is_ipython_cell = (
                code.co_name == '<module>' and
                code.co_filename == "my_program.py"
        )


snoop.tracer.FrameInfo = PatchedFrameInfo


def exec_snoop(filename, code, code_obj):
    snoop.formatting.Source._class_local('__source_cache', {}).pop(filename, None)

    config = snoop.Config(
        columns=(),
        out=sys.stdout,
        color=True,
    )
    tracer = config.snoop()
    tracer.variable_whitelist = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Name):
            name = node.id
            tracer.variable_whitelist.add(name)
    tracer.target_codes.add(code_obj)

    def find_code(root_code):
        """
        Trace all functions recursively, like trace_module_deep.
        """
        for sub_code_obj in root_code.co_consts:
            if not inspect.iscode(sub_code_obj):
                continue

            find_code(sub_code_obj)
            tracer.target_codes.add(sub_code_obj)

    find_code(code_obj)

    with tracer:
        execute(code_obj)
