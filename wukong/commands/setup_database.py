import os
from .wukong_env import bulk_update_config, load_config
from .cli_utils import install_and_add_connector

database_connectors = {
    "sqlite": "sqlite3",
    "postgresql": "psycopg2-binary",
    "mysql": "mysql-connector-python",
    "oracle": "python-oracledb",
    "mssql": "pyodbc",
    "mongodb": "pymongo",
    "redis": "redis-py",
    "cassandra": "cassandra-driver",
    "snowflake": "snowflake-connector-python",
    "databricks": "databricks-sql-connector",
    "redshift": "redshift_connector",
}

sqlalchemy_url_mapping = {
    "sqlite": "sqlite:///path/to/your/database.db OR sqlite:///:memory: (for in-memory)",
    "postgresql": "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    "mysql": "mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}",
    "oracle": "oracle+oracledb://{user}:{password}@{host}:{port}/{database}",
    "mssql": "mssql+pyodbc://{user}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+18+for+SQL+Server",
    "mongodb": "mongodb://{user}:{password}@{host}:{port}/{database} (Note: SQLAlchemy is not typically used for MongoDB. This is a PyMongo connection string.)",
    "redis": "redis://{host}:6379/{db_number} (Note: SQLAlchemy is not typically used for Redis. This is a redis-py connection string.)",
    "cassandra": "cassandra://{host}:{port}/{keyspace} (Note: SQLAlchemy is not typically used for Cassandra. This is a cassandra-driver connection string.)",
    "snowflake": "snowflake://{user}:{password}@{account}/?warehouse={warehouse}&database={database}&schema={schema}&role={role}",
    "databricks": "databricks://token:{access_token}@{host}/?http_path={http_path}&catalog={catalog}&schema={schema}",
    "redshift": "postgresql+redshift_connector://{user}:{password}@{host}:{port}/{database}",
}


default_database_ports = {
    # "sqlite": None,  # SQLite is file-based and does not use a network port.
    "postgresql": 5432,
    "mysql": 3306,
    "oracle": 1521,
    "mssql": 1433,
    "mongodb": 27017,
    "redis": 6379,
    "cassandra": 9042,  # CQL (Cassandra Query Language) native protocol port
    # "snowflake": 443,  # Snowflake uses standard HTTPS port for connections
    # "databricks": 443,  # Databricks SQL Endpoints use standard HTTPS port for connections
    "redshift": 5439,
}


def args_to_db_cfg_dict(
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
    dbcfg = {
        "type": type,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "schema": schema,
        "account": account,
        "warehouse": warehouse,
        "role": role,
        "http_path": http_path,
        "catalog": catalog,
        "access_token": access_token,
    }
    if type == "sqlite":
        dbcfg = {"type": type}
    elif type in [
        "snowflake",
    ]:
        del dbcfg["host"]
        del dbcfg["port"]
        del dbcfg["http_path"]
        del dbcfg["catalog"]
        del dbcfg["access_token"]
    elif type in [
        "databrick",
    ]:
        del dbcfg["host"]
        del dbcfg["port"]
        del dbcfg["account"]
        del dbcfg["warehouse"]
        del dbcfg["role"]
        del dbcfg["user"]
        del dbcfg["password"]
    else:
        del dbcfg["account"]
        del dbcfg["warehouse"]
        del dbcfg["role"]
        del dbcfg["http_path"]
        del dbcfg["catalog"]
        del dbcfg["access_token"]

    return dbcfg


def kwargs_to_db_cfg_dict(**kwargs):
    return {**kwargs}


def setup_database(
    type: str = None,
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    database: str = None,
    schema: str = None,
    account: str = None,
    warehouse: str = None,
    role: str = None,
    http_path: str = None,
    catalog: str = None,
    access_token: str = None,
):

    dbcfg = args_to_db_cfg_dict(
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
    bulk_update_config(
        dbcfg,
        "database",
    )
    config = load_config()
    if "project_root_dir" in config and "backend" in config:
        project_root_dir = config["project_root_dir"]
        backend_dir = config["backend"]["dir"]
        requirements = os.path.join(project_root_dir, backend_dir, "requirements.txt")
        install_and_add_connector(database_connectors.get(type), requirements)
