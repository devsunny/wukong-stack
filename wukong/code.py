import os
import re
import click

from typing_extensions import List
from .commands.flask_crud import (
    generate_crud as generate_flask_crud,
    generate_routes as generate_flask_routes,
)
from pgsql_parser import SQLParser, Table


@click.group()
def crud():
    pass


def multiple_tables_callback(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    return re.split(r"[, ]", value)


@click.command
@click.option(
    "--ddl",
    help="path to ddl file or directory",
    type=str,
    default="sqls",
    required=True,
    prompt="enter DDL file or directory path",
)
@click.option(
    "--tables",
    help="generate CRUD artifacts for selected tables",
    type=str,
    default=[],
    multiple=True,
    required=False,
)
def ddl_crud(ddl, tables):
    sqlparser = SQLParser()
    if os.path.isfile(ddl):
        with open(ddl, "rt", encoding="utf-8") as fin:
            sqlparser.parse_script(fin.read())
    elif os.path.isdir(ddl):
        for dirpath, dirnames, filenames in os.walk(ddl):
            for filename in filenames:
                if filename.endswith(".sql"):
                    file_path = os.path.join(dirpath, filename)
                    with open(file_path, "rt", encoding="utf-8") as fin:
                        sqlparser.parse_script(fin.read())
    ddl_tables = sqlparser.get_tables()
    filters = [table.upper() for table in tables] if tables else []
    generated_tables = []
    for table in ddl_tables:
        if filters and table.name.upper() not in filters:
            continue
        generate_flask_crud(table, ddl_tables)
        generated_tables.append(table)
    generate_flask_routes(generated_tables)


@click.command
@click.option(
    "--tables",
    help="generate CRUD artifacts for selected tables",
    required=False,
    prompt="enter names of tables for generating CRUD artifacts",
)
def database_crud(tables):

    pass


@click.command
@click.option(
    "--query",
    help="generate a read only service endpoint based on input query",
    type=str,
    multiple=True,
    required=False,
    prompt="enter names of tables",
)
@click.option(
    "--http-method",
    help="HTTP Method [GET, POST]",
    type=click.Choice(["GET", "POST"]),
    show_choices=True,
    default="GET",
    required=True,
    prompt="enter names of HTTP Method",
)
def query_crud(tables):

    pass


crud.add_command(ddl_crud, "ddl")
crud.add_command(database_crud, "rdb")
crud.add_command(query_crud, "quuery")
