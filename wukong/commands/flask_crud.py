from pgsql_parser import Table, Column, ForeignKey, PrimaryKey
from . import template_utils as utils
from .jinja2_template_render import Jinja2TemplateRender
from .wukong_env import match_database_type

template_render = Jinja2TemplateRender("templates")


def generate_crud_sqlalchemy_model(table: Table):
    singular_tbname = utils.singularize(table.name)
    print("XXXXXXXXXXXXXXXXXXX>>>>>>>>>>>>>>>>>>>", singular_tbname)
    table_snakecase_name = utils.to_snake_case(table.name)
    table_pascal_name = utils.to_pascal_case(table.name)
    print(">>>>>>>>>>>>>>>>>>>", table_snakecase_name)
    print(">>>>>>>>>>>>>>>>>>>", table_pascal_name)

    table_singular_snakecase_name = utils.singularize(table_snakecase_name)
    table_plural_snakecase_name = utils.pluralize(table_snakecase_name)
    print(">>>>>>>>>>>>>>>>>>>", table_singular_snakecase_name)
    print(">>>>>>>>>>>>>>>>>>>", table_plural_snakecase_name)

    table_singular_pascal_name = utils.singularize(table_pascal_name)

    table_plural_pascal_name = utils.pluralize(table_pascal_name)
    is_postgres = match_database_type("postgresql")
    context = {
        "table": table,
        "columns": table.columns.values(),
        "table_singular_snakecase_name": table_singular_snakecase_name,
        "table_singular_pascal_name": table_singular_pascal_name,
        "table_plural_snakecase_name": table_plural_snakecase_name,
        "table_plural_pascal_name": table_plural_pascal_name,
        "is_postgres": is_postgres,
    }
    output = template_render.render_template("backend/model.py.j2", context)
    print(output)
    pass


def generate_crud_service(table: Table):
    pass


def generate_crud_api_resource(table: Table):
    pass


def public_crud_api_resource(table: Table):

    pass


def generate_crud(table: Table):
    print("generating CRUD", table.name)
    generate_crud_sqlalchemy_model(table)
    generate_crud_service(table)
    generate_crud_api_resource(table)
    public_crud_api_resource(table)
