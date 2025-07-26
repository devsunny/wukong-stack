import os
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
