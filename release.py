"""
release.py — Build, tag, and publish a new Skrybe Studio release.

Run from the project root:
    uv run python release.py

What it does:
    1. Asks for a version number
    2. Checks dependencies are installed (uv, git, and syncs the `build` group)
    3. Builds the app via PyInstaller (SkrybeStudio.spec)
       - macOS   → SkrybeStudio.app + SkrybeStudio.dmg
       - Windows → SkrybeStudio.exe folder + SkrybeStudio.zip
       - Linux   → SkrybeStudio folder + SkrybeStudio.tar.gz
    4. Updates the version in pyproject.toml, src/skrybe_studio/__init__.py,
       and SkrybeStudio.spec
    5. Commits any uncommitted changes
    6. Tags the release (vX.Y.Z)
    7. Pushes the commit + tag to GitHub
       → GitHub Actions picks up the tag and attaches the artifact to a GitHub Release
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

APP_NAME = "SkrybeStudio"
SPEC_FILE = "SkrybeStudio.spec"

ROOT = Path(__file__).parent

# Per-platform output artifact
if sys.platform == "darwin":
    ARTIFACT_NAME = f"{APP_NAME}.dmg"
elif sys.platform == "win32":
    ARTIFACT_NAME = f"{APP_NAME}.zip"
else:
    ARTIFACT_NAME = f"{APP_NAME}.tar.gz"

# ── Helpers ───────────────────────────────────────────────────────────────────


def success(msg: str):
    print(f"✅  {msg}")


def info(msg: str):
    print(f"→   {msg}")


def warn(msg: str):
    print(f"⚠️   {msg}")


def die(msg: str):
    print(f"\n❌  {msg}\n")
    sys.exit(1)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=False)


def run_output(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


# ── Steps ─────────────────────────────────────────────────────────────────────


def ask_version() -> str:
    last_tag = run_output(["git", "describe", "--tags", "--abbrev=0"]) or "none"
    print(f"  Last release tag: {last_tag}")
    print()
    while True:
        version = input("  Enter version number (e.g. 0.2.0): ").strip().lstrip("v")
        if re.match(r"^\d+\.\d+\.\d+$", version):
            return version
        warn("Please use the format X.Y.Z  (e.g.  0.2.0)")


def check_tag(tag: str):
    result = subprocess.run(["git", "rev-parse", tag], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        die(f"Tag {tag} already exists. Choose a different version.")


def check_dependencies():
    info("Checking dependencies…")

    if not shutil.which("uv"):
        die("uv not found. Install it from https://docs.astral.sh/uv/ and re-run.")

    if not shutil.which("git"):
        die("git not found.")

    remote = run_output(["git", "remote", "get-url", "origin"])
    if not remote:
        die("No git remote 'origin' configured.")

    info("Syncing build dependencies (uv sync --group build)…")
    result = subprocess.run(["uv", "sync", "--group", "build"], cwd=ROOT)
    if result.returncode != 0:
        die("uv sync --group build failed.")

    # macOS: check for create-dmg (optional — falls back to hdiutil)
    if sys.platform == "darwin" and not shutil.which("create-dmg"):
        warn(
            "create-dmg not found — will use hdiutil fallback. Install with: brew install create-dmg"
        )

    success("Dependencies OK")


def build_app() -> Path:
    info("Running PyInstaller (this takes a few minutes)…")

    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(ROOT / "dist", ignore_errors=True)

    result = subprocess.run(["uv", "run", "pyinstaller", SPEC_FILE, "--noconfirm"], cwd=ROOT)
    if result.returncode != 0:
        die("PyInstaller build failed.")

    if sys.platform == "darwin":
        app_path = ROOT / "dist" / f"{APP_NAME}.app"
        if not app_path.exists():
            die(f".app bundle not found at {app_path}")
        success("App bundle created")
        return app_path
    else:
        app_path = ROOT / "dist" / APP_NAME
        if not app_path.exists():
            die(f"Build output not found at {app_path}")
        success("App build created")
        return app_path


def package_macos(app_path: Path) -> Path:
    info("Creating DMG…")
    dmg_path = ROOT / "dist" / ARTIFACT_NAME

    if shutil.which("create-dmg"):
        result = subprocess.run(
            [
                "create-dmg",
                "--volname",
                "Skrybe Studio",
                "--window-pos",
                "200",
                "140",
                "--window-size",
                "660",
                "400",
                "--icon-size",
                "120",
                "--icon",
                f"{APP_NAME}.app",
                "180",
                "170",
                "--hide-extension",
                f"{APP_NAME}.app",
                "--app-drop-link",
                "480",
                "170",
                "--no-internet-enable",
                str(dmg_path),
                str(app_path),
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            warn("create-dmg reported an issue — falling back to hdiutil.")
            dmg_path.unlink(missing_ok=True)

    if not dmg_path.exists():
        run(
            [
                "hdiutil",
                "create",
                "-volname",
                "Skrybe Studio",
                "-srcfolder",
                str(app_path),
                "-ov",
                "-format",
                "UDZO",
                str(dmg_path),
            ]
        )

    if not dmg_path.exists():
        die("DMG creation failed.")

    size_mb = dmg_path.stat().st_size / (1024 * 1024)
    success(f"DMG created  ({size_mb:.0f} MB)")
    return dmg_path


def package_windows(app_path: Path) -> Path:
    info("Creating ZIP…")
    zip_base = ROOT / "dist" / APP_NAME
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", str(app_path.parent), app_path.name))
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    success(f"ZIP created  ({size_mb:.0f} MB)")
    return zip_path


def package_linux(app_path: Path) -> Path:
    info("Creating tar.gz…")
    tar_base = ROOT / "dist" / APP_NAME
    tar_path = Path(
        shutil.make_archive(str(tar_base), "gztar", str(app_path.parent), app_path.name)
    )
    size_mb = tar_path.stat().st_size / (1024 * 1024)
    success(f"tar.gz created  ({size_mb:.0f} MB)")
    return tar_path


def package(app_path: Path) -> Path:
    if sys.platform == "darwin":
        return package_macos(app_path)
    elif sys.platform == "win32":
        return package_windows(app_path)
    else:
        return package_linux(app_path)


def update_versions(version: str):
    info(f"Updating version strings to {version}…")

    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text()
    text = re.sub(r'(?m)^version = "[^"]*"', f'version = "{version}"', text, count=1)
    pyproject.write_text(text)

    init_file = ROOT / "src" / "skrybe_studio" / "__init__.py"
    text = init_file.read_text()
    text = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', text)
    init_file.write_text(text)

    spec = (ROOT / SPEC_FILE).read_text()
    spec = re.sub(
        r'"CFBundleShortVersionString":\s*"[^"]*"',
        f'"CFBundleShortVersionString": "{version}"',
        spec,
    )
    spec = re.sub(
        r'"CFBundleVersion":\s*"[^"]*"',
        f'"CFBundleVersion": "{version}"',
        spec,
    )
    (ROOT / SPEC_FILE).write_text(spec)


_SENSITIVE_PATTERNS = (
    ".env",
    ".env.",
    "credentials",
    "secret",
    "keyring",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".p12",
    ".pfx",
)


def _check_staged_for_secrets():
    """Abort if any staged file looks like it might contain credentials."""
    staged = run_output(["git", "diff", "--cached", "--name-only"])
    if not staged:
        return
    flagged = []
    for line in staged.splitlines():
        lower = line.lower()
        if any(pat in lower for pat in _SENSITIVE_PATTERNS):
            flagged.append(line)
    if flagged:
        print()
        warn("Potentially sensitive files are staged:")
        for f in flagged:
            print(f"     {f}")
        answer = input("  Continue anyway? [y/N]: ").strip().lower()
        if answer != "y":
            die("Aborted by user.")


def commit_and_tag(version: str) -> str:
    tag = f"v{version}"

    info("Staging changes…")
    # Stage only files already tracked by git plus the specific files this
    # script itself modifies. Deliberately avoid -A so stray build/dist
    # output or local .env files aren't swept in.
    run(["git", "add", "--update"])  # tracked modifications
    run(["git", "add", "src/", "tests/", "docs/", "--"])  # any new source/test/doc files
    run(["git", "add", "pyproject.toml", SPEC_FILE, "uv.lock", "--"], check=False)

    _check_staged_for_secrets()

    status = run_output(["git", "diff", "--cached", "--name-only"])
    if status:
        info("Committing…")
        run(["git", "commit", "-m", f"chore: release {tag}"])
        success("Changes committed")
    else:
        info("Nothing new to commit — working tree already clean.")

    info(f"Creating tag {tag}…")
    run(["git", "tag", tag])
    success(f"Tag {tag} created")

    info("Pushing to GitHub…")
    # Regular push only — never force-push to main. If this fails because the
    # remote is ahead, the developer must pull and re-run rather than silently
    # overwriting upstream history.
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Delete the local tag so the developer can retry cleanly.
        subprocess.run(["git", "tag", "-d", tag], cwd=ROOT)
        print(result.stderr)
        die(
            "Push to origin/main failed.\n"
            "  → Pull the latest changes (git pull --rebase origin main),\n"
            "    then re-run release.py.\n"
            f"  → Local tag {tag} has been removed so you can retry."
        )
    run(["git", "push", "origin", tag])
    success("Pushed to GitHub")

    return tag


def print_summary(version: str, artifact_path: Path):
    tag = f"v{version}"
    remote_url = run_output(["git", "remote", "get-url", "origin"])
    remote_url = remote_url.replace("git@github.com:", "https://github.com/").removesuffix(".git")

    print()
    print("╔══════════════════════════════════════════════╗")
    print(f"║       Release {tag} published!                  ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print(f"  Artifact:       dist/{artifact_path.name}")
    print(f"  Size:           {artifact_path.stat().st_size / (1024 * 1024):.0f} MB")
    print()
    print("  GitHub Actions is now building the release for all platforms.")
    print(f"  Watch progress: {remote_url}/actions")
    print(f"  Releases page:  {remote_url}/releases")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    platform_label = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, "Linux")

    print()
    print("╔══════════════════════════════════════════════╗")
    print(f"║   Skrybe Studio — Release Publisher ({platform_label:<8}) ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    version = ask_version()
    tag = f"v{version}"

    print()
    info(f"Building release {tag}…")
    print()

    check_tag(tag)
    check_dependencies()

    app_path = build_app()
    artifact_path = package(app_path)

    update_versions(version)
    commit_and_tag(version)
    print_summary(version, artifact_path)


if __name__ == "__main__":
    main()
