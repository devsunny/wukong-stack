"""This module contains tool for metadata extraction from RDB"""

import re
from typing import List, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from pgsql_parser import Table, Column, ForeignKey, PrimaryKey, Index, Constraint


def get_sqlalchemy_url(db_name: str, **kwargs) -> str:
    """
    Returns a formatted SQLAlchemy database URL based on a template and provided keyword arguments,
    using f-strings for construction.

    Args:
        db_name (str): The name of the database (e.g., "mysql", "snowflake").
        **kwargs: Keyword arguments containing the values to substitute into the URL.

    Returns:
        str: The formatted database URL.

    Raises:
        ValueError: If the db_name is not supported or if a required variable for the
                    template is missing from kwargs.
    """
    if not db_name:
        raise ValueError("invalid database name or type")

    db_name = db_name.lower()
    if db_name == "sqlite":
        return "sqlite:///:memory:"

    # Dictionary to store parameter requirements for each database type
    # Note: 'databricks' has no specific URL parameters in this context.
    required_params = {
        "mysql": ["user", "password", "host", "port", "database"],
        "oracle": ["user", "password", "host", "port", "database"],
        "postgresql": ["user", "password", "host", "port", "database"],
        "mssql": ["user", "password", "host", "port", "database"],
        "redshift": ["user", "password", "host", "port", "database"],
        "snowflake": ["user", "password", "account", "database", "schema"],
        "databricks": ["host", "access_token", "http_path", "catalog", "schema"],
    }

    # Create a mutable copy of kwargs and set default values for optional parameters
    params = {**kwargs}
    params.setdefault("warehouse", "")  # Default for Snowflake
    params.setdefault("role", "")  # Default for Snowflake

    # Check if the database name is supported
    if db_name not in required_params:
        raise ValueError(
            f"Database name '{db_name}' not supported or found in URL templates."
        )

    # Helper function to check for missing required parameters
    def _check_missing_params(db: str, current_params: dict, req_keys: list):
        for key in req_keys:
            if key not in current_params:
                raise ValueError(
                    f"Missing required variable for {db} URL: '{key}'. "
                    "Please provide it in the keyword arguments."
                )

    # Construct the URL using f-strings based on the database name
    if db_name == "databricks":
        # Databricks often configures connection details separately, so the URL is simple.
        return (
            f"databricks://token:{params['access_token']}@"
            f"{params['server_hostname']}?http_path={params['http_path']}"
            f"&catalog={params['catalog']}&schema={params['schema']}"
        )
    elif db_name == "mysql":
        _check_missing_params(db_name, params, required_params["mysql"])
        return (
            f"mysql+mysqlconnector://"
            f"{params['user']}:{params['password']}@{params['host']}:"
            f"{params['port']}/{params['database']}"
        )
    elif db_name == "oracle":
        _check_missing_params(db_name, params, required_params["oracle"])
        return (
            f"oracle+oracledb://"
            f"{params['user']}:{params['password']}@{params['host']}:"
            f"{params['port']}/{params['database']}"
        )
    elif db_name == "postgresql":
        _check_missing_params(db_name, params, required_params["postgresql"])
        return (
            f"postgresql+psycopg2://"
            f"{params['user']}:{params['password']}@{params['host']}:"
            f"{params['port']}/{params['database']}"
        )
    elif db_name == "mssql":
        _check_missing_params(db_name, params, required_params["mssql"])
        return (
            f"mssql+pyodbc://"
            f"{params['user']}:{params['password']}@{params['host']}:"
            f"{params['port']}/{params['database']}?driver=ODBC+Driver+18+for+SQL+Server"
        )
    elif db_name == "redshift":
        _check_missing_params(db_name, params, required_params["redshift"])
        return (
            f"redshift+redshift_connector://"
            f"{params['user']}:{params['password']}@{params['host']}:"
            f"{params['port']}/{params['database']}"
        )
    elif db_name == "snowflake":
        _check_missing_params(db_name, params, required_params["snowflake"])
        return (
            f"snowflake://"
            f"{params['user']}:{params['password']}@{params['account']}/"
            f"{params['database']}/{params['schema']}?"
            f"warehouse={params['warehouse']}&role={params['role']}"
        )
    # This else block should ideally not be reached due to the initial check
    else:
        raise ValueError(f"Internal error: Unhandled database name '{db_name}'.")


class RdbMetadataExtractor:
    """
    A class to extract relational database table metadata using SQLAlchemy's reflection capabilities.
    """

    def __init__(self, **kwargs):
        try:
            dbname = (
                kwargs.get("type")
                or kwargs.get("db_type")
                or kwargs.get("dbtype")
                or kwargs.get("database_type")
            )
            self.engine = create_engine(get_sqlalchemy_url(dbname, **kwargs))
            self.inspector = inspect(self.engine)
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Failed to connect to the database: {e}") from e

    def get_all_schemas(self) -> List[str]:
        try:
            return self.inspector.get_schema_names()
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Error retrieving schema names: {e}") from e

    def get_tables_in_schema(self, schema: Optional[str] = None) -> List[str]:
        try:
            return self.inspector.get_table_names(schema=schema)
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Error retrieving table names for schema '{schema}': {e}"
            ) from e

    def get_views_in_schema(self, schema: Optional[str] = None) -> List[str]:
        try:
            return self.inspector.get_view_names(schema=schema)
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Error retrieving view names for schema '{schema}': {e}"
            ) from e

    def get_all_table_metadata(
        self, schema: Optional[str] = None, include_views: bool = False
    ) -> List[Table]:
        tables_metadata: List[Table] = []
        try:
            table_names = self.inspector.get_table_names(schema=schema)
            if include_views:
                view_names = self.inspector.get_view_names(schema=schema)
                all_names = list(set(table_names + view_names))
            else:
                all_names = table_names

            for table_name in all_names:
                table_type = "TABLE"
                is_view = False
                view_definition = None

                if include_views and table_name in self.inspector.get_view_names(
                    schema=schema
                ):
                    table_type = "VIEW"
                    is_view = True
                    try:
                        view_definition = self.inspector.get_view_definition(
                            table_name, schema=schema
                        )
                        if view_definition:
                            view_definition = str(view_definition).strip()
                    except NotImplementedError:
                        view_definition = None

                table_obj = Table(name=table_name, schema=schema, table_type=table_type)
                table_obj.is_view = is_view
                table_obj.view_definition = view_definition

                self._populate_columns(table_obj, schema)
                self._populate_primary_key(table_obj, schema)
                self._populate_foreign_keys(table_obj, schema)
                self._populate_constraints(table_obj, schema)
                self._populate_indexes(table_obj, schema)

                tables_metadata.append(table_obj)

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Error during metadata extraction: {e}") from e
        return tables_metadata

    def _populate_columns(self, table_obj: Table, schema: Optional[str]):
        columns_info = self.inspector.get_columns(table_obj.name, schema=schema)
        for col_info in columns_info:
            col_type_str = str(col_info["type"])
            pat_match = re.search(r"^([A-Za-z0-9]+)[(].+$", col_type_str, re.IGNORECASE)
            if pat_match is not None:
                col_type_str = pat_match.group(1)
            column = Column(
                table_name=table_obj.name,
                name=col_info["name"],
                data_type=col_type_str,
                nullable=col_info.get("nullable", True),
                default_value=col_info.get("default"),
            )
            if hasattr(col_info["type"], "length"):
                column.char_length = col_info["type"].length
            if hasattr(col_info["type"], "precision"):
                column.numeric_precision = col_info["type"].precision
            if hasattr(col_info["type"], "scale"):
                column.numeric_scale = col_info["type"].scale
            table_obj.add_column(column)

    def _populate_primary_key(self, table_obj: Table, schema: Optional[str]):
        pk_constraint = self.inspector.get_pk_constraint(table_obj.name, schema=schema)
        if pk_constraint and pk_constraint.get("constrained_columns"):
            pk_name = pk_constraint.get("name")
            pk_columns = pk_constraint["constrained_columns"]
            table_obj.primary_key = PrimaryKey(
                name=pk_name, table_name=table_obj.name, columns=pk_columns
            )
            for i, col_name in enumerate(pk_columns):
                if col_name in table_obj.columns:
                    table_obj.columns[col_name].is_primary = True
                    table_obj.columns[col_name].nullable = False
                    table_obj.columns[col_name].primary_key_position = i + 1

    def _populate_foreign_keys(self, table_obj: Table, schema: Optional[str]):
        fks_info = self.inspector.get_foreign_keys(table_obj.name, schema=schema)
        for fk_info in fks_info:
            fk_name = fk_info.get("name")
            constrained_columns = fk_info["constrained_columns"]
            referred_table = fk_info["referred_table"]
            referred_columns = fk_info["referred_columns"]
            referred_schema = fk_info.get("referred_schema")

            foreign_key = ForeignKey(
                name=fk_name,
                table_name=table_obj.name,
                columns=constrained_columns,
                ref_table=referred_table,
                ref_columns=referred_columns,
                ref_schema=referred_schema,
                is_composite_key=len(constrained_columns) > 1,
            )
            table_obj.foreign_keys.append(foreign_key)
            for i, col_name in enumerate(constrained_columns):
                if col_name in table_obj.columns:
                    table_obj.columns[col_name].foreign_key_ref = (
                        referred_schema,
                        referred_table,
                        referred_columns[i] if i < len(referred_columns) else None,
                    )

    def _populate_constraints(self, table_obj: Table, schema: Optional[str]):
        unique_constraints = self.inspector.get_unique_constraints(
            table_obj.name, schema=schema
        )
        for uc_info in unique_constraints:
            table_obj.constraints.append(
                Constraint(
                    name=uc_info.get("name", "anon_unique"),
                    ctype="UNIQUE",
                    columns=uc_info.get("constrained_columns"),
                )
            )

        check_constraints = self.inspector.get_check_constraints(
            table_obj.name, schema=schema
        )
        for cc_info in check_constraints:
            table_obj.constraints.append(
                Constraint(
                    name=cc_info.get("name", "anon_check"),
                    ctype="CHECK",
                    expression=str(cc_info.get("sqltext")),
                )
            )

    def _populate_indexes(self, table_obj: Table, schema: Optional[str]):
        indexes_info = self.inspector.get_indexes(table_obj.name, schema=schema)
        for idx_info in indexes_info:
            table_obj.constraints.append(
                Index(
                    name=idx_info.get("name"),
                    table=table_obj.name,
                    columns=idx_info.get("column_names"),
                    is_unique=idx_info.get("unique", False),
                    method=idx_info.get("dialect_options", {}).get("postgresql_using"),
                )
            )
