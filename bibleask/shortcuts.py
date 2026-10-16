"""Windows only: put a BibleChat icon on the desktop and in the Start menu, so people just double-click it.

Done once, the first time the downloaded app is opened. If the BibleChat folder is moved later, the
existing icons are pointed at the new place. If someone deletes an icon, it is not put back.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from . import storage

NAME = "BibleChat"

_PS = r"""
$ErrorActionPreference = 'Stop'
$ws = New-Object -ComObject WScript.Shell
function Make($folder, $target) {
  if (-not $folder) { return }
  $path = Join-Path $folder 'BibleChat.lnk'
  $mode = $env:BC_MODE
  if ($mode -eq 'update' -and -not (Test-Path $path)) { return }   # the person deleted it: leave it gone
  $s = $ws.CreateShortcut($path)
  $s.TargetPath = $target
  $s.WorkingDirectory = Split-Path $target
  $s.IconLocation = "$target,0"
  $s.Description = 'Read and chat with your Bibles'
  $s.Save()
  Write-Output $path
}
$t = $env:BC_TARGET
if ($env:BC_DESKTOP) { $desk = $env:BC_DESKTOP } else { $desk = [Environment]::GetFolderPath('Desktop') }
if ($env:BC_MENU) { $menu = $env:BC_MENU } else { $menu = [Environment]::GetFolderPath('Programs') }
Make $desk $t
Make $menu $t
"""


def _run_ps(target: str, mode: str, desktop: Optional[str] = None, menu: Optional[str] = None) -> list[str]:
    env = dict(os.environ, BC_TARGET=target, BC_MODE=mode, BC_DESKTOP=desktop or "", BC_MENU=menu or "")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _PS],
                         env=env, capture_output=True, text=True, timeout=60, creationflags=flags)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "PowerShell failed")
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def ensure(target: Optional[str] = None, desktop: Optional[str] = None, menu: Optional[str] = None) -> list[str]:
    """Create the icons the first time; afterwards only re-point existing ones if the app moved.
    Returns the shortcut files written. Never raises: a missing icon must not stop BibleChat."""
    if not sys.platform.startswith("win"):
        return []
    target = target or sys.executable
    try:
        s = storage.load_settings()
        made_for = s.get("shortcut_target")
        if made_for == target:
            return []
        written = _run_ps(target, "create" if made_for is None else "update", desktop, menu)
        s = storage.load_settings()
        s["shortcut_target"] = target
        storage.save_settings(s)
        return written
    except Exception:
        return []


def ensure_in_background() -> None:
    """Called at start-up by the packaged Windows app."""
    if sys.platform.startswith("win") and getattr(sys, "frozen", False):
        import threading
        threading.Thread(target=ensure, daemon=True).start()
