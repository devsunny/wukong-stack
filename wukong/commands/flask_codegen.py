import pgsql_parser import Table, Column, PrimaryKey, ForeignKey

backend_structure = """
your_project_name/
├── backend/
│   ├── instance/
│   │   └── config.py        # Instance-specific configuration (not version controlled)
│   ├── app/
│   │   ├── __init__.py      # Flask app creation, extensions initialization
│   │   ├── config.py        # Base configuration (development, testing, production)
│   │   ├── app.py           # Main application setup (blueprints, error handlers)
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

def gen_crud_flask_artifact(table:Table):
    
    pass
