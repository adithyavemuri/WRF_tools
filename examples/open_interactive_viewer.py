#!/usr/bin/env python3
"""Open an existing viewer; never edits browser settings or WRF data.

From the repository root:
    python examples/open_interactive_viewer.py

If graphics acceleration cannot be used, explicit trusted-local-file fallback:
    python examples/open_interactive_viewer.py --software-webgl

Software mode opens an isolated Chrome/Chromium profile. It does NOT disable
the browser sandbox, but SwiftShader lowers WebGL security guarantees: use this
window only for your trusted viewer, not general browsing. Close it to return
to the terminal and remove its temporary profile. No root access is required.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import webbrowser


def _chrome_executable():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        if executable := shutil.which(name):
            return executable
    candidates = [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    for key in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        if directory := os.environ.get(key):
            candidates.append(Path(directory)/"Google/Chrome/Application/chrome.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("Chrome/Chromium was not found; supply its executable with --chrome")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    default = Path(__file__).resolve().parents[1]/"example_results/diagnostic-explorer/viewer.html"
    parser.add_argument("html",nargs="?",type=Path,default=default,help="Existing local viewer.html")
    parser.add_argument("--software-webgl",action="store_true",help="Explicit lower-security software rendering for this trusted local file")
    parser.add_argument("--chrome",type=Path,help="Chrome executable for software mode")
    args = parser.parse_args(argv)
    html = args.html.resolve()
    if not html.is_file() or html.suffix.lower() not in {".html", ".htm"}:
        parser.error("Supply an existing local HTML file; generate it with interactive_isosurfaces.py first")
    if args.chrome is not None and not args.software_webgl:
        parser.error("--chrome is used with --software-webgl")
    if not args.software_webgl:
        print("Opening the existing viewer in your default browser.")
        print("Chrome WebGL error? Enable graphics acceleration at chrome://settings/system and relaunch.")
        if not webbrowser.open_new_tab(html.as_uri()):
            parser.error("Could not open a browser; open the HTML manually")
        return 0
    try:
        executable = str(args.chrome.resolve()) if args.chrome else _chrome_executable()
        if not Path(executable).is_file():
            parser.error("The supplied Chrome executable does not exist")
    except FileNotFoundError as exc:
        parser.error(str(exc))
    print("WARNING: software WebGL lowers graphics security guarantees; trusted local files only.",flush=True)
    print("Opening a separate Chrome profile, without changing your normal browser preferences.",flush=True)
    print("Close this isolated browser window to return here and clean its temporary profile.",flush=True)
    with tempfile.TemporaryDirectory(prefix="wrf-viewer-chrome-") as profile:
        command = [executable,f"--user-data-dir={profile}","--no-first-run","--new-window",
            "--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader",html.as_uri()]
        return subprocess.run(command,check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
