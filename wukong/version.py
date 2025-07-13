import click
import tomlkit
from semver import VersionInfo


def update_version(increment_type):
    with open("backend/pyproject.toml", "r") as f:
        data = tomlkit.parse(f.read())

    ver = VersionInfo.parse(data["project"]["version"])

    if increment_type == "build":
        new_ver = ver.bump_build()
    elif increment_type == "minor":
        new_ver = ver.bump_minor()
    else:  # major
        new_ver = ver.bump_major()

    data["project"]["version"] = str(new_ver)

    with open("backend/pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(data))


@click.command()
def increase_build():
    update_version("build")


@click.command()
def increase_minor():
    update_version("minor")


@click.command()
def increase_major():
    update_version("major")
