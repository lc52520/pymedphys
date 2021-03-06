# Copyright (C) 2020 Simon Biggs

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import pathlib
import re
import subprocess
import tarfile
import textwrap

from pymedphys._imports import black, tomlkit

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PYPROJECT_TOML_PATH = REPO_ROOT.joinpath("pyproject.toml")

LIBRARY_PATH = REPO_ROOT.joinpath("pymedphys")
VERSION_PATH = LIBRARY_PATH.joinpath("_version.py")

DIST_DIR = REPO_ROOT.joinpath("dist")
SETUP_PY = REPO_ROOT.joinpath("setup.py")

REQUIREMENTS_TXT = REPO_ROOT.joinpath("requirements.txt")

AUTOGEN_MESSAGE = [
    "# DO NOT EDIT THIS FILE!",
    "# This file has been autogenerated by `pymedphys dev propagate`",
]


def propagate_all(_):
    propagate_version()
    propagate_extras()
    propagate_requirements()
    propagate_setup()


def read_pyproject():
    with open(PYPROJECT_TOML_PATH) as f:
        pyproject_contents = tomlkit.loads(f.read())

    return pyproject_contents


def get_version_string():
    pyproject_contents = read_pyproject()
    version_string = pyproject_contents["tool"]["poetry"]["version"]

    return version_string


def propagate_version():
    version_string = get_version_string()
    version_list = re.split(r"[-\.]", version_string)

    for i, item in enumerate(version_list):
        try:
            version_list[i] = int(item)
        except ValueError:
            pass

    version_contents = textwrap.dedent(
        f"""\
        {AUTOGEN_MESSAGE[0]}
        {AUTOGEN_MESSAGE[1]}

        version_info = {version_list}
        __version__ = "{version_string}"
        """
    )

    version_contents = black.format_str(version_contents, mode=black.FileMode())

    with open(VERSION_PATH, "w") as f:
        f.write(version_contents)


def propagate_setup():
    subprocess.check_call("poetry build -f sdist", cwd=REPO_ROOT, shell=True)

    version_string = get_version_string()
    version_dots_only = version_string.replace("-", ".")

    filename = f"pymedphys-{version_dots_only}.tar.gz"
    filepath = DIST_DIR.joinpath(filename)

    with tarfile.open(filepath, "r:gz") as tar:
        f = tar.extractfile(f"pymedphys-{version_dots_only}/setup.py")
        setup_contents = f.read().decode()

    setup_contents_list = setup_contents.split("\n")
    setup_contents_list.insert(1, f"\n{AUTOGEN_MESSAGE[0]}")
    setup_contents_list.insert(2, f"{AUTOGEN_MESSAGE[1]}\n")
    setup_contents = "\n".join(setup_contents_list)

    setup_contents = black.format_str(setup_contents, mode=black.FileMode())

    setup_contents = setup_contents.encode("utf-8")

    with open(SETUP_PY, "bw") as f:
        f.write(setup_contents)


def propagate_requirements():
    subprocess.check_call("poetry update pymedphys", shell=True)
    subprocess.check_call(
        "poetry export --without-hashes -E user -f requirements.txt --output requirements.txt",
        shell=True,
    )

    with open(REQUIREMENTS_TXT, "a") as f:
        f.write(".[user]\n")


def propagate_extras():
    pyproject_contents = read_pyproject()

    deps = pyproject_contents["tool"]["poetry"]["dependencies"]

    extras = {}

    for key in deps:
        value = deps[key]
        comment = value.trivia.comment

        if comment.startswith("# groups"):
            split = comment.split("=")
            assert len(split) == 2
            groups = json.loads(split[-1])

            for group in groups:
                try:
                    extras[group].append(key)
                except KeyError:
                    extras[group] = [key]

    if pyproject_contents["tool"]["poetry"]["extras"] != extras:
        pyproject_contents["tool"]["poetry"]["extras"] = extras

        with open(PYPROJECT_TOML_PATH, "w") as f:
            f.write(tomlkit.dumps(pyproject_contents))
