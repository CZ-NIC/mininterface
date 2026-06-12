"""Griffe extension that exposes lazy __getattr__ imports in mininterface.__init__ as aliases."""

import ast
from pathlib import Path

import griffe


class LazyAliasExtension(griffe.Extension):
    """Read __getattr__ in mininterface/__init__.py and register each name as an Alias."""

    def on_package_loaded(self, *, pkg: griffe.Module, **kwargs) -> None:
        if pkg.path != "mininterface":
            return

        init_path = Path(pkg.filepath).parent / "__init__.py"
        tree = ast.parse(init_path.read_text())

        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name == "__getattr__"):
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.ImportFrom):
                    continue
                module = ("mininterface." + child.module) if child.module else "mininterface"
                for alias in child.names:
                    name = alias.asname or alias.name
                    target = f"{module}.{alias.name}"
                    if name not in pkg.members:
                        pkg.set_member(name, griffe.Alias(name, target, parent=pkg))
