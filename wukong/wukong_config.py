import toml
import os
import copy
import click
from pathlib import Path


# --- TOMLConfigManager Class ---
class WukongConfigManager:
    """
    A class to manage reading and writing TOML configuration files with
    built-in encryption for sensitive fields like 'password' and 'api_key'.
    """

    WUKONG_CFG_FILE = ".wukong.toml"

    # Define sensitive keys that should be encrypted
    _SENSITIVE_KEYS = {"password", "api_key"}

    def __init__(self, cfg_file_path: str = None):
        self.cfg_file_path = cfg_file_path
        self.config = {}
        self._is_loaded = False  # Track if a config has been successfully loaded
        self.load_config()

    def _find_file_in_parent_tree(self):
        if self.cfg_file_path is not None:
            os.makedirs(os.path.dirname(self.cfg_file_path), exist_ok=True)
            return os.path.abspath(self.cfg_file_path)

        dir = os.path.abspath(os.getcwd())
        root_dir = os.path.abspath(os.sep)
        file_name = WukongConfigManager.WUKONG_CFG_FILE
        while dir != root_dir:
            file_path = os.path.join(dir, file_name)
            if os.path.exists(file_path):
                return file_path
            dir = os.path.dirname(dir)

        return self._get_global_config_path()

    @staticmethod
    def _get_global_config_path():
        home_directory = os.path.abspath(os.path.expanduser("~"))
        global_wukong_cfg_dir = os.path.join(home_directory, ".wukong")
        os.makedirs(global_wukong_cfg_dir, exist_ok=True)
        return os.path.join(global_wukong_cfg_dir, WukongConfigManager.WUKONG_CFG_FILE)

    def load_config(self):
        file_path = self._find_file_in_parent_tree()
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_config = toml.load(f)
            self.config = raw_config
            self._is_loaded = True
            print(f"Configuration loaded and decrypted from '{file_path}'.")
        except toml.TomlDecodeError as e:
            raise ValueError(f"Error decoding TOML file '{file_path}': {e}")
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred while loading config from '{file_path}': {e}"
            )

    def save_config(self, is_global=False):
        if is_global:
            file_path = self._get_global_config_path()
        else:
            file_path = self._find_file_in_parent_tree(
                WukongConfigManager.WUKONG_CFG_FILE
            )

        # Create a deep copy to encrypt for saving without altering the active decrypted config
        config_to_save = copy.deepcopy(self.config)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(config_to_save, f)
            print(f"Configuration saved and encrypted to '{file_path}'.")
        except Exception as e:
            raise RuntimeError(f"Error saving TOML file '{file_path}': {e}")

    def get(self, key_path: str, default=None):
        """
        Retrieves a value from the configuration using a dot-separated path.

        Args:
            key_path (str): The dot-separated path to the desired key (e.g., "database.host").
            default: The default value to return if the key path is not found.

        Returns:
            The value at the specified key path, or the default value if not found.
        """
        keys = key_path.split(".")
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, key_path: str, value):
        """
        Sets a value in the configuration using a dot-separated path.
        This will update the internal decrypted configuration.

        Args:
            key_path (str): The dot-separated path to the key to set.
            value: The value to set.
        """
        keys = key_path.split(".")
        current = self.config
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                # Last key, set the value
                current[key] = value
            else:
                # Not the last key, traverse or create nested dictionary
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
        print(f"Set '{key_path}' to '{value}'.")
        self._is_loaded = True

    def __str__(self):
        """Returns a string representation of the currently loaded (decrypted) config."""
        return toml.dumps(self.config)


@click.group()
def config():
    """Manage Wukong configuration."""
    pass


@config.command()
@click.argument(
    "key",
    required=True,
    nargs=1,
)
@click.argument(
    "value",
    required=True,
    nargs=1,
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Set the configuration globally.",
    default=False,
)
def set(key, value, is_global):
    """Set a configuration value.

    Arguments:
        key: Dot-separated key path to get (e.g., "database.password").
        value: The value to set.
    Options:
        --global / -g: Save the configuration globally.
    """
    manager = WukongConfigManager(
        WukongConfigManager._get_global_config_path() if is_global else None
    )
    manager.set(key, value)
    manager.save_config(is_global=is_global)


@config.command()
@click.argument(
    "key",
    required=True,
    nargs=1,
)
def get(key):
    """Get a configuration value.

    Arguments:
        key: Dot-separated key path to get (e.g., "database.password").
    """
    manager = WukongConfigManager()
    value = manager.get(key)
    if value is not None:
        print(f"{key} = {value}")
    else:
        print(f"Key '{key}' not found in configuration.")


@config.command()
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Save the configuration globally.",
    default=False,
)
@click.argument(
    "key",
    required=True,
    nargs=1,
)
def delete(key, is_global):
    """Delete a configuration entry.

    Arguments:
        key: Dot-separated key path to get (e.g., "database.password").
    """
    manager = WukongConfigManager(
        WukongConfigManager._get_global_config_path() if is_global else None
    )
    if key:
        keys = key.split(".")
        current = manager.config
        for i, k in enumerate(keys):
            if k in current:
                if i == len(keys) - 1:
                    del current[k]
                    print(f"Deleted key '{key}'.")
                else:
                    current = current[k]
            else:
                print(f"Key '{key}' not found in configuration.")
                return
        manager.save_config(is_global=is_global)


@config.command()
def init():
    """Initialize a new configuration file in the current directory."""
    dir = os.path.abspath(os.getcwd())
    file_name = WukongConfigManager.WUKONG_CFG_FILE
    file_path = os.path.join(dir, file_name)
    if os.path.exists(file_path):
        print("Configuration file already exists. Use 'set' to modify values.")
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            toml.dump({}, f)
        print("Initialized new configuration file in the current directory.")
