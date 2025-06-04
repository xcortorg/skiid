import os
import sys
from pathlib import Path

from setuptools import find_namespace_packages, setup

ROOT_FOLDER = Path(__file__).parent.absolute()
REQUIREMENTS_FOLDER = ROOT_FOLDER / "grief"

# Since we're importing `grief` package, we have to ensure that it's in sys.path.
sys.path.insert(0, str(ROOT_FOLDER))

from grief import VersionInfo

version, _ = VersionInfo._get_version(ignore_installed=True)


def get_requirements(fp):
    return [
        line.strip()
        for line in fp.read().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


with open(REQUIREMENTS_FOLDER / "base.txt", encoding="utf-8") as fp:
    install_requires = get_requirements(fp)


python_requires = ">=3.8.1"
if not os.getenv("TOX_RED", False) or sys.version_info < (3, 12):
    python_requires += ",<3.12"

# Metadata and options defined in pyproject.toml
setup(
    name="Grief-DiscordBot",
    author="resemt",
    version=version,
    python_requires=python_requires,
    # TODO: use [tool.setuptools.dynamic] table once this feature gets out of beta
    packages=find_namespace_packages(include=["grief", "grief.*"]),
)
