import os
import click
from .cli_utils import check_init_confict_input, write_sample_file, make_nested_dirs

backend_structure = """
your_project_name/
├── backend/
│   ├── instance/
│   │   └── config.py        # Instance-specific configuration (not version controlled)
│   ├── app/
│   │   ├── __init__.py      # Flask app creation, extensions initialization
│   │   ├── config.py        # Base configuration (development, testing, production)
│   │   ├── main.py           # Main application setup (blueprints, error handlers)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── user.py      # SQLAlchemy models (e.g., User model)
│   │   │   └── product.py   # Another model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── user_schema.py # Pydantic schemas for request/response validation
│   │   │   └── product_schema.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── namespaces/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_ns.py # Flask-RESTx namespace for user-related endpoints
│   │   │   │   └── product_ns.py # Flask-RESTx namespace for product-related endpoints
│   │   │   └── v1/
│   │   │       └── api.py   # Flask-RESTx API registration for version v1
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py # Business logic related to users
│   │   │   └── product_service.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── helpers.py   # Utility functions (e.g., decorators, common helpers)
│   │   ├── extensions.py    # Flask extensions (SQLAlchemy, Flask-RESTx, etc.)
│   │   ├── commands.py      # Flask CLI custom commands (e.g., database seeding)
│   │   └── errors.py        # Custom error handlers
│   ├── migrations/          # Alembic migrations directory
│   │   ├── versions/
│   │   └── env.py
│   │   └── script.py.mako
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── unit/
│   │   │   └── test_models.py
│   │   │   └── test_services.py
│   │   ├── integration/
│   │   │   └── test_api.py
│   │   └── conftest.py      # Pytest fixtures
│   ├── venv/                # Python virtual environment (add to .gitignore)
│   ├── .flaskenv            # Flask environment variables (e.g., FLASK_APP, FLASK_ENV)
│   ├── .gitignore
│   ├── requirements.txt     # Python dependencies
│   ├── wsgi.py              # Entry point for production servers (Gunicorn, uWSGI)
│   └── boot.py              # (Optional) Script for environment setup, database
"""


def create_flask_project_structure(
    project_base_dir: str = None, flask_base_dir="backend"
):
    project_root_dir = None
    if project_base_dir:
        project_root_dir = project_base_dir
    else:
        project_root_dir = os.getcwd()

    check_init_confict_input("flask", project_root_dir, flask_base_dir)
    write_sample_file(project_root_dir, "flaskenv.txt", ".flaskenv")
    flask_base = make_nested_dirs(project_root_dir, flask_base_dir)
    write_sample_file(flask_base, "pytest.ini")
    write_sample_file(flask_base, "requirements.txt")
    write_sample_file(flask_base, "gitignore.txt", ".gitignore")
    write_sample_file(flask_base, "wsgi.py.txt", "wsgi.py")
    app_dir = make_nested_dirs(flask_base, "app")
    write_sample_file(app_dir, "__init__.py")
    write_sample_file(app_dir, "extensions.py.txt", "extensions.py")
    write_sample_file(app_dir, "commands.py.txt", "cli.py")
    write_sample_file(app_dir, "errors.py.txt", "errors.py")
    write_sample_file(app_dir, "flask_config.py.txt", "config.py")
    write_sample_file(app_dir, "app.py.txt", "main.py")
    tests_dir = make_nested_dirs(flask_base, "tests")
    write_sample_file(tests_dir, "__init__.py")
    model_dir = make_nested_dirs(app_dir, "models")
    write_sample_file(model_dir, "__init__.py")
    write_sample_file(model_dir, "model_base.py.txt", "base.py")
    schema_dir = make_nested_dirs(app_dir, "schemas")
    write_sample_file(schema_dir, "__init__.py")
    api_dir = make_nested_dirs(app_dir, "api")
    write_sample_file(api_dir, "__init__.py")
    service_dir = make_nested_dirs(app_dir, "services")
    write_sample_file(service_dir, "__init__.py")
    utils_dir = make_nested_dirs(app_dir, "utils")
    write_sample_file(utils_dir, "__init__.py")
    click.echo(" the following directory structure and files have as been created")
    click.echo(backend_structure.strip())
    click.echo("Flask project initialization completed!!!!")
