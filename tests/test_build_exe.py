"""The build script and the release workflow that calls it must agree.

A renamed command-line flag once left `args.folder` pointing at nothing (argparse names the
attribute after the flag text, which no automatic rename can see), and only a real release
would have noticed. These tests keep the flags, the workflow and build.spec in step.
"""

import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import build_exe
import duplicate_finder

ROOT = Path(__file__).resolve().parents[1]


def test_single_file_is_the_default():
    args = build_exe.parse_args([])
    assert args.folder is False and args.zip is False


def test_folder_and_zip_flags():
    args = build_exe.parse_args(["--folder", "--zip"])
    assert args.folder is True and args.zip is True


def test_zip_needs_folder():
    with pytest.raises(SystemExit):
        build_exe.parse_args(["--zip"])


def test_the_old_spanish_flag_is_gone():
    with pytest.raises(SystemExit):
        build_exe.parse_args(["--carpeta"])


def test_every_build_command_in_the_release_workflow_is_accepted():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    commands = re.findall(r"run:\s*python build_exe\.py([^\n]*)", workflow)
    assert len(commands) == 2  # the single file and the folder + ZIP
    for arguments in commands:
        build_exe.parse_args(shlex.split(arguments))


def test_the_script_and_the_spec_use_the_same_format_variable():
    script = (ROOT / "build_exe.py").read_text(encoding="utf-8")
    spec = (ROOT / "build.spec").read_text(encoding="utf-8")
    assert "BUILD_FORMAT" in script and "BUILD_FORMAT" in spec
    assert 'environment["BUILD_FORMAT"] = "folder"' in script
    assert 'os.environ.get("BUILD_FORMAT") == "folder"' in spec


def test_the_icon_the_spec_asks_for_exists():
    spec = (ROOT / "build.spec").read_text(encoding="utf-8")
    (icon,) = re.findall(r'icon="([^"]+)"', spec)
    assert (ROOT / icon).is_file()


def test_the_version_command_of_the_release_workflow_works():
    """The workflow compares the tag with the version in the code; a stale import (it once said
    `from core import ...`) would only fail on a real release."""
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    (command,) = re.findall(r'\$inCode = python -c "([^\n]+)"', workflow)
    result = subprocess.run(
        [sys.executable, "-c", command], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == duplicate_finder.__version__


def test_the_changelog_has_a_section_for_the_current_version():
    """The release notes are taken from that section of CHANGELOG.md."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{duplicate_finder.__version__}]" in changelog
