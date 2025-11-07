#!/usr/bin/env python3
import sys
import re
from pathlib import Path


def generate_readme(index_path="docs/index.md", readme_path = Path("README.md")):
    index_file = Path(index_path)
    if not index_file.exists():
        print(f"❌ Error: {index_path} not found.")
        return False

    text = index_file.read_text(encoding="utf-8")

    base_url = "https://cz-nic.github.io/mininterface"

    def replace_ref(match):
        link_text = match.group(1).strip()
        ref = match.group(2).strip()
        parts = ref.split(".")

        # Case 1: mininterface.run → base/run/
        if len(parts) == 2:
            url = f"{base_url}/{parts[1]}/"

        # Case 2: mininterface.Mininterface.confirm → base/Mininterface/#mininterface.Mininterface.confirm
        elif len(parts) == 3:
            url = f"{base_url}/{parts[1]}/#{ref}"

        # Fallback
        else:
            url = f"{base_url}/#{ref}"

        return f"[{link_text}]({url})"


    new_text = re.sub(r"\[([^\[\]]+)\]\[([^\[\]]+)\]", replace_ref, text)

    Path(readme_path).write_text(new_text, encoding="utf-8")

    print(f"✅ README.md generated successfully from {index_path}")
    return True


if __name__ == "__main__":
    if not generate_readme():
        sys.exit(1)
