import click
from .commands.setup_database import (
    setup_database,
    database_connectors,
    default_database_ports,
)
from .commands.wukong_env import load_config


def type_driven_activation(ctx, param, value):
    """Callback to deactivate prompts if --batch is specified."""
    # config = load_config()
    # if "project_root_dir" not in config:
    #     click.echo("Please init backend flask/fastapi first")
    #     raise click.Abort()
    while value not in database_connectors:
        types = str(sorted(database_connectors.keys()))
        value = click.prompt(f"select one of database type {types}")

    if value and value in ["snowflake"]:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.name in [
                "host",
                "port",
                "http_path",
                "catalog",
                "access_token",
            ]:
                p.prompt = None  # Disable prompting for these options
    elif value and value in ["databrick"]:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.name in [
                "host",
                "port",
                "account",
                "warehouse",
                "role",
                "user",
                "database",
                "password",
            ]:
                p.prompt = None  # Disable prompting for these options
    elif value and value in ["sqllite"]:  # If --batch is True (batch mode)
        click.echo("Entering batch mode, deactivating prompts for 'name' and 'age'...")
        # Find and modify the 'prompt' attribute of other options
        for p in ctx.command.params:
            if isinstance(p, click.Option):
                p.prompt = None  # Disable prompting for these options
    else:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.name in [
                "account",
                "warehouse",
                "role",
                "http_path",
                "catalog",
                "access_token",
            ]:
                p.prompt = None  # Disable prompting for these options

            if (
                isinstance(p, click.Option)
                and p.name == "port"
                and value in default_database_ports
            ):
                p.default = default_database_ports[value]

    return value


dbtypes = str(sorted(database_connectors.keys()))


@click.command()
@click.option(
    "--type",
    type=str,
    required=True,
    default="postgresql",
    callback=type_driven_activation,
    prompt="Enter database hostname[postgresql]:",
    help=f"select a database type {dbtypes} ",
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    required=True,
    prompt="Enter database hostname[localhost]:",
)
@click.option(
    "--port",
    type=int,
    default="0",
    required=True,
    prompt="Enter database server port[0]:",
)
@click.option(
    "--user",
    type=str,
    required=True,
    default="developer",
    prompt="Enter database user:",
)
@click.option(
    "--password",
    type=str,
    required=True,
    default="secret",
    prompt="Enter database password:",
)
@click.option(
    "--access-token",
    type=str,
    required=False,
    prompt="Enter databrick access_token:",
)
@click.option(
    "--http-path",
    type=str,
    required=False,
    prompt="Enter databrick http_path:",
)
@click.option(
    "--database",
    type=str,
    required=True,
    default="appdb",
    prompt="Enter database name:",
)
@click.option(
    "--catalog",
    type=str,
    required=False,
    prompt="Enter databrick catalog:",
)
@click.option(
    "--schema",
    type=str,
    required=False,
    default="public",
    prompt="Enter database schema:",
)
@click.option(
    "--account",
    type=str,
    required=False,
    prompt="Enter snowflake account:",
)
@click.option(
    "--warehouse",
    type=str,
    required=False,
    prompt="Enter snowflake warehouse:",
)
@click.option(
    "--role",
    type=str,
    required=False,
    prompt="Enter snowflake role:",
)
def database(
    type: str,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    schema: str,
    account: str,
    warehouse: str,
    role: str,
    http_path: str,
    catalog: str,
    access_token: str,
):
    setup_database(
        type,
        host,
        port,
        user,
        password,
        database,
        schema,
        account,
        warehouse,
        role,
        http_path,
        catalog,
        access_token,
    )
    pass
