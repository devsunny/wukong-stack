import sys
import os
import subprocess
import shutil
import click


def check_init_confict_input(name: str, project_base: str, dir: str):
    out_base = os.path.join(project_base, dir)
    if os.path.exists(out_base):
        proceed = click.prompt(
            f"{name} base directory [{out_base}] exists, do you want to proceed? [Yes/No]",
            type=bool,
        )
        if proceed is False:
            print(f"{name} initialization aborted")
            return
        new_name = click.prompt(
            f"Do you want to rename existing [{dir}]? enter new name or [enter] to overwrite",
            type=str,
            default="",
        )
        if new_name:
            new_path = os.path.join(project_base, new_name)
            shutil.move(out_base, new_path)
        else:
            shutil.rmtree(out_base)


def write_sample_file(target_directory, filename, target_filename=None):
    src_dir = os.path.dirname(__file__)
    file_path = os.path.join(src_dir, "samples", filename)
    tgt_filename = target_filename or filename
    out_path = os.path.join(target_directory, tgt_filename)
    with open(file_path, "rb") as fin:
        with open(out_path, "wb") as fout:
            fout.write(fin.read())


def make_nested_dirs(first_dir, *dirs):
    directory = os.path.join(first_dir, *dirs)
    os.makedirs(directory, exist_ok=True)
    return directory


def install_and_add_connector(
    connector_package_name: str, requirements_file: str = "requirements.txt"
):
    """
    Installs a Python package (database connector) using pip and adds its name
    to a specified requirements.txt file if not already present.

    Args:
        connector_package_name (str): The exact package name to install (e.g., "psycopg2", "snowflake-connector-python").
        requirements_file (str): The path to the requirements file (default: "requirements.txt").

    Returns:
        bool: True if the operation was successful (installed or already present), False otherwise.
    """
    print(
        f"Attempting to install '{connector_package_name}' and add to '{requirements_file}'..."
    )

    # --- Step 1: Check if the package is already in requirements.txt ---
    package_in_requirements = False
    if os.path.exists(requirements_file):
        try:
            with open(requirements_file, "r") as f:
                for line in f:
                    # Basic check: ignore comments and empty lines, check if package name is in line
                    if line.strip() and not line.strip().startswith("#"):
                        # Check for exact package name or package name with version specifiers
                        if (
                            line.strip()
                            .split("==")[0]
                            .split(">=")[0]
                            .split("<=")[0]
                            .split("~=")[0]
                            .strip()
                            .lower()
                            == connector_package_name.lower()
                        ):
                            package_in_requirements = True
                            print(
                                f"'{connector_package_name}' already found in '{requirements_file}'."
                            )
                            break
        except IOError as e:
            print(f"Error reading '{requirements_file}': {e}")
            return False

    # --- Step 2: Add package to requirements.txt if not present ---
    if not package_in_requirements:
        try:
            with open(requirements_file, "a") as f:
                f.write(f"\n{connector_package_name}")
            print(f"Added '{connector_package_name}' to '{requirements_file}'.")
        except IOError as e:
            print(f"Error writing to '{requirements_file}': {e}")
            return False

    # --- Step 3: Install the package using pip ---
    try:
        # Use sys.executable to ensure the correct pip is used (associated with the current Python environment)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", connector_package_name],
            capture_output=True,
            text=True,
            check=True,  # Raises CalledProcessError if the command returns a non-zero exit code
        )
        print(f"Successfully installed '{connector_package_name}'.")
        # print("Pip stdout:\n", result.stdout) # Uncomment for detailed pip output
        # print("Pip stderr:\n", result.stderr) # Uncomment for detailed pip errors
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing '{connector_package_name}':")
        print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(
            "Error: 'pip' command not found. Ensure Python and pip are correctly installed and in your PATH."
        )
        return False
    except Exception as e:
        print(f"An unexpected error occurred during installation: {e}")
        return False
