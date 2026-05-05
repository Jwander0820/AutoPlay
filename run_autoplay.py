from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    try:
        from autoplay.dev_launcher import main as launcher_main
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        print(f"Missing Python package: {missing}")
        print("In PyCharm, set the project interpreter to your venv, then install project dependencies.")
        print(r"Expected venv example: D:\venv\AutoPlay\Scripts\python.exe")
        print('Install command inside that interpreter: python -m pip install -e ".[dev]"')
        return 1
    launcher_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
