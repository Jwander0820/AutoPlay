# Environment Setup

AutoPlay uses `pyproject.toml` as the source of truth for package metadata. The `requirements*.txt` files are provided as a familiar setup shortcut.

## Windows PowerShell

```powershell
cd D:\SideProject\AutoPlay
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If editable install is inconvenient, use the requirements files:

```powershell
python -m pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
```

## Verify

```powershell
python -m unittest discover -s tests
python -m autoplay doctor
```

For LDPlayer, pass its bundled ADB path when needed:

```powershell
python -m autoplay doctor --adb-path <LDPlayer adb.exe path>
```

## PyCharm Run Entry

Set the PyCharm project interpreter to the venv Python, for example:

```text
D:\venv\AutoPlay\Scripts\python.exe
```

Then create a Run Configuration for:

```text
D:\SideProject\AutoPlay\run_autoplay.py
```

Press Run to open the AutoPlay Dev Launcher. The launcher can detect LDPlayer devices, run doctor, capture screenshots, test dry-run/real tap and scroll, and start the recorder UI without typing CLI commands each time.

The launcher UI is Traditional Chinese. The Recorder port defaults to `0`, which means it will choose a free local port each time so an old recorder server cannot accidentally be reused.

The launcher loads and saves local defaults here:

```text
config/autoplay.local.json
```

This file is ignored by git, so user-specific paths such as the LDPlayer `adb.exe` location stay local. A tracked template is available at:

```text
config/autoplay.example.json
```

The launcher also has emulator profiles. Start with `LDPlayer / LeiDian`, then edit the ADB path or connect targets in the UI if your install uses a custom location or port. Press `儲存本機預設` after changing values.

## CMD Notes

CMD is fine, but `pip list` by itself shows whichever `pip.exe` is first on PATH. To inspect the AutoPlay venv, call pip through the venv Python:

```bat
D:\venv\AutoPlay\Scripts\python.exe -m pip list
```

To activate the same venv in CMD:

```bat
D:\venv\AutoPlay\Scripts\activate.bat
cd /d D:\SideProject\AutoPlay
python -m pip install -e ".[dev]"
```

You can also run the GUI launcher from CMD or double-click it:

```bat
D:\SideProject\AutoPlay\run_autoplay.cmd
```

If your venv moves, set `AUTOPLAY_PYTHON` before running the launcher:

```bat
set AUTOPLAY_PYTHON=D:\venv\AutoPlay\Scripts\python.exe
D:\SideProject\AutoPlay\run_autoplay.cmd
```
