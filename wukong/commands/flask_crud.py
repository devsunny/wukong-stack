import os
from typing_extensions import List
from pgsql_parser import Table, Column, ForeignKey, PrimaryKey
from . import template_utils as utils
from .jinja2_template_render import Jinja2TemplateRender
from .wukong_env import match_database_type, load_config

template_render = Jinja2TemplateRender("templates")


def generate_crud_sqlalchemy_model(context):
    output = template_render.render_template("backend/model.py.j2", context)
    return output


def generate_crud_pydantic_schema(context):
    output = template_render.render_template("backend/schema.py.j2", context)
    return output


def generate_crud_service(context):
    pass


def generate_crud_api_resource(context):
    output = template_render.render_template("backend/api_resource.py.j2", context)
    print(output)
    return output


def publish_crud_api_resource(context):

    pass


def generate_crud(table: Table, tables: List[Table]):
    print("generating CRUD", table.name)
    wukong_cfg = load_config()
    if "project_root_dir" not in wukong_cfg or "backend" not in wukong_cfg:
        raise ValueError("Please run `wukong init flask` first")
    project_root_dir = wukong_cfg["project_root_dir"]
    backend_dir = wukong_cfg["backend"]["dir"]

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
        "pk_columns": utils.get_pk_columns(table),
        "has_table_args": has_table_args,
        "table_singular_snakecase_name": table_singular_snakecase_name,
        "table_singular_pascal_name": table_singular_pascal_name,
        "table_plural_snakecase_name": table_plural_snakecase_name,
        "table_plural_pascal_name": table_plural_pascal_name,
        "is_postgres": is_postgres,
        "child_relationships": child_relationships,
    }
    model_path = os.path.join(
        project_root_dir,
        backend_dir,
        "app/models",
        f"{table_singular_snakecase_name}.py",
    )
    utils.write_source_file(model_path, generate_crud_sqlalchemy_model(context))
    print("writed flask-sqlalchemy model to", model_path)

    schema_path = os.path.join(
        project_root_dir,
        backend_dir,
        "app/schemas",
        f"{table_singular_snakecase_name}.py",
    )
    utils.write_source_file(schema_path, generate_crud_pydantic_schema(context))
    print("writed pydantic schema to", schema_path)

    schema_path = os.path.join(
        project_root_dir,
        backend_dir,
        "app/api",
        f"{table_singular_snakecase_name}.py",
    )
    utils.write_source_file(schema_path, generate_crud_api_resource(context))

    generate_crud_service(context)
    publish_crud_api_resource(context)
