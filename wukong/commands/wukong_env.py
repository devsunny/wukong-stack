import tomlkit
import os


def load_config():
    """
    Loads a TOML configuration file.

    Args:
        config_dir (str): The path (directory) to the .wukong.toml TOML file.

    Returns:
        tomlkit.TOMLDocument: A TOMLDocument object representing the configuration.
    """
    file_path = os.path.join(os.getcwd(), ".wukong.toml")
    if not os.path.exists(file_path):
        doc = tomlkit.document()
    else:
        with open(file_path, "r") as f:
            doc = tomlkit.parse(f.read())
    return doc


def match_database_type(database_type):
    try:
        cfg = load_config()
        return cfg["database"]["type"] == database_type
    except Exception:
        return False


def update_config(value, config_key, *keys: str):
    if not config_key:
        raise ValueError("missing config key")
    cfg = load_config()
    if not keys:
        if value is None:
            del cfg[config_key]
        else:
            cfg[config_key] = value
    else:
        section = cfg
        for key in keys:
            if key not in section:
                section[key] = tomlkit.table()
            section = section[key]

        if value is None:
            del section[config_key]
        else:
            section[config_key] = value

    save_config(cfg)


def bulk_update_config(bulk_cfg: dict, *keys: str):
    cfg = load_config()
    section = cfg
    if keys:
        section = cfg
        for key in keys:
            if key not in section:
                section[key] = tomlkit.table()
            section = section[key]

    for cfg_key in bulk_cfg:
        if bulk_cfg.get(cfg_key):
            section[cfg_key] = bulk_cfg.get(cfg_key)
        elif cfg_key in section:
            del section[cfg_key]
    save_config(cfg)


def save_config(config: tomlkit.TOMLDocument):
    """
    Saves a TOMLDocument object back to a TOML file.

    Args:
        config (tomlkit.TOMLDocument): The TOMLDocument object to save.
        config_dir (str): The path (directory) to the TOML file.
    """
    file_path = os.path.join(os.getcwd(), ".wukong.toml")
    with open(file_path, "w") as f:
        f.write(tomlkit.dumps(config))
