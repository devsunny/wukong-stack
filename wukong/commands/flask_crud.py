from typing_extensions import List
from pgsql_parser import Table, Column, ForeignKey, PrimaryKey
from . import template_utils as utils
from .jinja2_template_render import Jinja2TemplateRender
from .wukong_env import match_database_type

template_render = Jinja2TemplateRender("templates")


def generate_crud_sqlalchemy_model(context):
    output = template_render.render_template("backend/model.py.j2", context)
    print(output)
    pass


def generate_crud_service(context):
    pass


def generate_crud_api_resource(context):
    pass


def publish_crud_api_resource(context):

    pass


def generate_crud(table: Table, tables: List[Table]):
    print("generating CRUD", table.name)
    table_singular_snakecase_name = utils.to_singular_snake_case(table.name)
    table_plural_snakecase_name = utils.to_plural_snake_case(table.name)
    table_singular_pascal_name = utils.to_singular_pascal_case(table.name)
    table_plural_pascal_name = utils.to_plural_pascal_case(table.name)
    is_postgres = match_database_type("postgresql")

    composite_fks: List[ForeignKey] = (
        [fk for fk in table.foreign_keys if len(fk.columns) > 1]
        if table.foreign_keys
        else []
    )
    has_table_args: bool = len(composite_fks) > 0 or (
        table.schema is not None and len(table.schema) > 1
    )
    child_relationships = utils.get_child_relationships(table, tables)
    context = {
        "table": table,
        "columns": table.columns.values(),
        "composite_fks": composite_fks,
        "has_table_args": has_table_args,
        "table_singular_snakecase_name": table_singular_snakecase_name,
        "table_singular_pascal_name": table_singular_pascal_name,
        "table_plural_snakecase_name": table_plural_snakecase_name,
        "table_plural_pascal_name": table_plural_pascal_name,
        "is_postgres": is_postgres,
        "child_relationships": child_relationships,
    }
    generate_crud_sqlalchemy_model(context)
    generate_crud_service(context)
    generate_crud_api_resource(context)
    publish_crud_api_resource(context)
