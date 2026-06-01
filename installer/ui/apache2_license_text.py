"""Apache 2.0 license text for display in the installer UI."""

from __future__ import annotations

import sys
from pathlib import Path


def _read_apache2_text() -> str:
    candidates: list[Path] = []

    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "LICENSE")
    except Exception:
        pass

    try:
        candidates.append(Path(sys.executable).resolve().parent / "LICENSE")
    except Exception:
        pass

    try:
        candidates.append(Path(__file__).resolve().parents[2] / "LICENSE")
    except Exception:
        pass

    candidates.append(Path.cwd() / "LICENSE")

    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

    return (
        "Apache License, Version 2.0\n\n"
        "Copyright 2026 Oliver Ernster\n\n"
        'Licensed under the Apache License, Version 2.0 (the "License");\n'
        "you may not use this file except in compliance with the License.\n"
        "You may obtain a copy of the License at\n\n"
        "    http://www.apache.org/licenses/LICENSE-2.0\n\n"
        "Unless required by applicable law or agreed to in writing, software\n"
        'distributed under the License is distributed on an "AS IS" BASIS,\n'
        "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n"
        "See the License for the specific language governing permissions and\n"
        "limitations under the License."
    )


APACHE2_TEXT = _read_apache2_text()
