#!/usr/bin/env python3
import sys
import toml
from pathlib import Path


def validate_extras(pyproject_path="pyproject.toml"):
    path = Path(pyproject_path)
    data = toml.load(path)

    extras = data.get("tool", {}).get("poetry", {}).get("extras", {})

    required_groups = {"basic", "web", "img", "tui", "gui", "ui", "all"}
    defined_groups = set(extras.keys())

    missing_groups = required_groups - defined_groups
    if missing_groups:
        print(f"Missing groups: {', '.join(missing_groups)}\n")
        return

    errors = []

    def get(group):
        return set(extras.get(group, []))

    basic = get("basic")
    img = get("img")
    all_items = {pkg for group in extras for pkg in extras[group]}

    # 1. basic musí být v každé jiné skupině
    for group in defined_groups - {"basic"}:
        if not basic.issubset(get(group)):
            missing = basic - get(group)
            if missing:
                errors.append(f"Group '{group}' missing basic dependencies: {sorted(missing)}")

    # 2. každý balík z img musí být aspoň v gui nebo tui
    gui = get("gui")
    tui = get("tui")
    for pkg in img:
        if pkg not in gui and pkg not in tui:
            errors.append(f"Package '{pkg}' from scattered group 'img' is no among 'gui', or 'tui'")

    # 3. ui a all obsahují všechny ostatní skupiny
    expected_ui = set().union(*(get(g) for g in ["basic", "gui", "tui", "img", "web"]))
    if get("ui") != expected_ui:
        errors.append(f"Group 'ui' has wrong contents (should be {sorted(expected_ui)})")

    expected_all = expected_ui
    if get("all") != expected_all:
        errors.append(f"Group 'ui' has wrong contents (should be {sorted(expected_all)})")

    if errors:
        print("\n".join(errors))
        return False
    return True


if __name__ == "__main__":
    if not validate_extras("pyproject.toml"):
        sys.exit(1)
