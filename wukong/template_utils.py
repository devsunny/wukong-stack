import re
from pgsql_parser import Column, Table, ForeignKey
from typing import List


def to_composite_fk_str(fk: ForeignKey) -> str:

    cols_str = str(fk.columns)
    refcols = []
    for rfcol in fk.ref_columns:
        if fk.ref_schema:
            refcols.append(f"{fk.ref_schema}.{fk.ref_table}.{rfcol}")
        else:
            refcols.append(f"{fk.ref_table}.{rfcol}")
    refcols_str = str(refcols)

    return f"ForeignKey({cols_str}, {refcols_str})"


def to_snake_case(input_string: str) -> str:
    """
    Converts a given string to snake_case.

    This function handles:
    1. Capitalized words (e.g., "HelloWorld" becomes "hello_world").
    2. Whitespace (e.g., "Hello World" becomes "hello_world").
    3. Non-letter and non-digit characters (e.g., "foo-bar!" becomes "foo_bar").
    4. Multiple consecutive non-letter/non-digit characters or underscores
       (e.g., "foo--bar", "foo___bar" become "foo_bar").

    Args:
        input_string (str): The string to convert.

    Returns:
        str: The snake_cased version of the input string.
    """

    # Step 1.1: Insert an underscore before any uppercase letter that is followed by a lowercase letter,
    # but only if it's preceded by another uppercase letter. This helps in breaking acronyms properly.
    # Example: "HTTPResponse" -> "HTTP_Response"
    # Example: "XMLHttpRequest" -> "XML_HttpRequest"
    s = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", input_string)

    # Step 1.2: Insert an underscore before any uppercase letter that is preceded
    # by a lowercase letter or a digit. This handles "CamelCase" and "PascalCase".
    # Example: "Hello_World" -> "Hello_World" (no change from previous step if already separated)
    # Example: "TestString123" -> "Test_String123"
    # Example: "String123Test" -> "String123_Test"
    # Example: "XML_HttpRequest" -> "XML_Http_Request" (applies to 'R' in 'Request')
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", s)

    # Step 2: Replace any sequence of non-letter and non-digit characters
    # (including whitespace) with a single underscore. This regex specifically
    # targets characters that are NOT a-z, A-Z, or 0-9. Existing underscores
    # are not affected by this step.
    # Example: "Hello World! This is a Test--String123" -> "Hello_World_This_is_a_Test_String123"
    # Example: "foo-bar" -> "foo_bar"
    # Example: "foo!bar" -> "foo_bar"
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)

    # Step 3: Convert the entire string to lowercase.
    # Example: "Hello_World" -> "hello_world"
    s = s.lower()

    # Step 4: Remove any leading or trailing underscores that might have been
    # introduced by previous steps, or were present in the original string.
    # Example: "__leading_and_trailing__" -> "leading_and_trailing"
    s = s.strip("_")

    # Step 5: Replace any sequence of multiple underscores with a single underscore.
    # This is crucial for cases where the original string had multiple underscores
    # (e.g., "foo___bar"), or if previous steps inadvertently created consecutive
    # underscores (though steps 1 and 2 are designed to minimize this).
    # Example: "foo___bar" -> "foo_bar"
    s = re.sub(r"_+", "_", s)

    return s


def to_pascal_case(input_string: str) -> str:
    """
    Converts a given string to PascalCase.

    This function first converts the string to snake_case, then capitalizes
    the first letter of each word and removes underscores.

    Args:
        input_string (str): The string to convert.

    Returns:
        str: The PascalCased version of the input string.
    """
    # Convert to snake_case first to normalize separators and handle camelCase/PascalCase
    snake_cased = to_snake_case(input_string)

    # Split by underscore, capitalize the first letter of each part, and join
    pascal_cased_parts = [part.capitalize() for part in snake_cased.split("_") if part]
    return "".join(pascal_cased_parts)


def singularize(word):
    """
    Convert a plural noun to its singular form.
    Handles common English pluralization rules.

    Args:
        word (str): The plural noun to convert

    Returns:
        str: The singular form of the noun
    """
    if not word:
        return word

    word = word.lower()

    # Dictionary for irregular plurals
    irregulars = {
        "agendas": "agendum",
        "alumni": "alumnus",
        "analysis": "analysis",
        "cacti": "cactus",
        "children": "child",
        "criteria": "criterion",
        "crises": "crisis",
        "curricula": "curriculum",
        "data": "datum",
        "deer": "deer",
        "feet": "foot",
        "fish": "fish",
        "fungi": "fungus",
        "geese": "goose",
        "indices": "index",
        "lice": "louse",
        "matrices": "matrix",
        "media": "medium",
        "men": "man",
        "mice": "mouse",
        "nuclei": "nucleus",
        "octopi": "octopus",
        "octopus": "octopus",
        "oxen": "ox",
        "parentheses": "parenthesis",
        "people": "person",
        "phenomena": "phenomenon",
        "quizzes": "quiz",  # Added
        "series": "series",
        "sheep": "sheep",
        "species": "species",
        "status": "status",
        "syllabi": "syllabus",
        "teeth": "tooth",
        "theses": "thesis",
        "wolves": "wolf",
        "women": "woman",
    }

    # Check for irregular plurals
    if word in irregulars:
        return irregulars[word]

    # Handle special cases
    if word.endswith("ies"):
        if len(word) > 3 and word[-4] in "aeiou":
            return word[:-3] + "y"
        return word[:-3] + "y"
    elif word.endswith("ves"):
        if word[-3] in "aeiou":
            return word[:-3] + "f"
        return word[:-3] + "fe"
    elif word.endswith("es"):
        if (
            word.endswith("ses")
            or word.endswith("zes")
            or word.endswith("ches")
            or word.endswith("shes")
        ):
            return word[:-2]
        elif word.endswith("xes") and len(word) > 3 and word[-4] in "aeiou":
            return word[:-2]
        return word[:-1]
    elif word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    # Return unchanged if already singular or no rule applies
    return word


def pluralize(word):
    """
    Convert a singular noun to its plural form.
    Handles common English pluralization rules.

    Args:
        word (str): The singular noun to convert

    Returns:
        str: The plural form of the noun
    """
    if not word:
        return word

    word = word.lower()

    # Dictionary for irregular plurals
    irregulars = {
        "agendum": "agendas",
        "alumnus": "alumni",
        "analysis": "analysis",
        "cactus": "cacti",
        "child": "children",
        "criterion": "criteria",
        "crisis": "crises",
        "curriculum": "curricula",
        "datum": "data",
        "deer": "deer",
        "diagnosis": "diagnoses",
        "fish": "fish",
        "foot": "feet",
        "fungus": "fungi",
        "goose": "geese",
        "index": "indices",
        "louse": "lice",
        "man": "men",
        "matrix": "matrices",
        "medium": "media",
        "mouse": "mice",
        "nucleus": "nuclei",
        "octopus": "octopus",
        "ox": "oxen",
        "parenthesis": "parentheses",
        "person": "people",
        "phenomenon": "phenomena",
        "photo": "photos",
        "quiz": "quizzes",
        "series": "series",
        "sheep": "sheep",
        "species": "species",
        "status": "status",
        "syllabus": "syllabi",
        "tooth": "teeth",
        "thesis": "theses",
        "wolf": "wolves",
        "woman": "women",
    }

    # Check for irregular plurals
    if word in irregulars:
        return irregulars[word]

    # Handle special cases
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    elif word.endswith("f"):
        return word[:-1] + "ves"
    elif word.endswith("fe"):
        return word[:-2] + "ves"
    elif (
        word.endswith("s")
        or word.endswith("sh")
        or word.endswith("ch")
        or word.endswith("x")
        or word.endswith("z")
    ):
        return word + "es"
    elif word.endswith("o") and len(word) > 1 and word[-2] not in "aeiou":
        return word + "es"

    # Default case: add 's'
    return word + "s"


def get_python_type(column: Column) -> str:
    """Converts SQL data types to Python types."""
    data_type = column.data_type.lower()
    if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
        return "str"
    elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
        return "int"
    elif data_type in ["boolean"]:
        return "bool"
    elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
        return "float"  # Or Decimal from decimal module
    elif data_type in ["date"]:
        return "date"
    elif data_type in ["timestamp", "timestamptz", "datetime"]:
        return "datetime"
    elif data_type in ["bytea", "blob"]:
        return "bytes"
    return "Any"  # Fallback for unhandled types


def get_datetime_imports(table: Table) -> list[str]:
    imports = set()
    for col in table.columns.values():
        data_type = col.data_type.lower()
        if data_type in ["date"]:
            imports.add("date")
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            imports.add("datetime")
    return list(imports)


def get_pydantic_type(column: Column) -> str:
    """Returns the Pydantic type string (e.g., str, Optional[int])."""
    py_type = get_python_type(column)
    if py_type == "date":
        py_type = "date"  # pydantic.types.date
    elif py_type == "datetime":
        py_type = "datetime"  # datetime.datetime
    elif py_type == "Any":
        py_type = "typing.Any"

    if column.nullable:
        return f"Optional[{py_type}]"
    return py_type


def get_sqlalchemy_type_imports(table: Table) -> str:
    types = set()
    for col in table.columns.values():
        sqlaltype = get_sqlalchemy_type(col)
        sqlaltype = re.sub(r"[(].+[)]", "", sqlaltype)
        types.add(sqlaltype)
    return list(types)


def get_sqlalchemy_type(column: Column) -> str:
    """Returns the SQLAlchemy type string (e.g., String, Integer)."""
    data_type = column.data_type.lower()
    if data_type in ["varchar", "char"]:
        return f"String({column.char_length})" if column.char_length else "String"
    elif data_type == "text":
        return "Text"
    elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
        return "Integer"
    elif data_type == "boolean":
        return "Boolean"
    elif data_type in ["float", "real"]:
        return "Float"
    elif data_type in ["double precision"]:
        return "Double"
    elif data_type in ["numeric", "decimal"]:
        precision = (
            column.numeric_precision if column.numeric_precision is not None else ""
        )
        scale = f", {column.numeric_scale}" if column.numeric_scale is not None else ""
        return f"Numeric({precision}{scale})"
    elif data_type == "date":
        return "Date"
    elif data_type in ["timestamp", "timestamptz", "datetime"]:
        return "DateTime(timezone=True)" if "tz" in data_type else "DateTime"
    elif data_type == "uuid":
        return "UUID(as_uuid=True)"
    elif data_type in ["json", "jsonb"]:
        return "JSON"
    elif data_type in ["bytea", "blob"]:
        return "LargeBinary"
    return "String"  # Default fallback


def get_pk_columns(table: Table) -> List[Column]:
    """Returns the first primary key column, assuming a single PK column for simplicity."""
    if table.primary_key and table.primary_key.columns:
        return [
            table.columns.get(pk_col_name)
            for pk_col_name in table.primary_key.columns
            if pk_col_name in table.columns
        ]
    return []


def is_auto_generated_pk(column: Column) -> bool:
    """Checks if a column is a primary key and is likely auto-generated (serial, uuid)."""
    if not column.is_primary:
        return False
    data_type = column.data_type.lower()
    # Common auto-incrementing integer types
    if (
        data_type in ["serial", "bigserial", "integer", "smallint", "bigint"]
        and column.default_value is None
    ):
        return True
    # Common auto-generated UUID types (check for func.uuid_generate_v4() or similar in default_value)
    if data_type == "uuid" and (
        column.default_value is None
        or "uuid_generate" in str(column.default_value).lower()
        or "gen_random_uuid" in str(column.default_value).lower()
    ):
        return True
    return False


def get_pk_path_params_str(table: Table) -> str:
    """Returns a string for URL path parameters (e.g., '{id1}/{id2}')."""
    pk_cols = get_pk_columns(table)
    return "/".join([f"{{{to_snake_case(col.name)}}}" for col in pk_cols])


def get_pk_columns_types_str(table: Table) -> str:
    """Returns a comma-separated string of primary key column names and their Python types."""
    pk_cols = get_pk_columns(table)
    return ", ".join(
        [f"{to_snake_case(col.name)}: {get_python_type(col)}" for col in pk_cols]
    )


def get_pk_kwargs_str(table: Table) -> str:
    """Returns a string for keyword arguments (e.g., 'id1=id1, id2=id2')."""
    pk_cols = get_pk_columns(table)
    return ", ".join(
        [f"{to_snake_case(col.name)}={to_snake_case(col.name)}" for col in pk_cols]
    )


def get_child_tables(parent_table: Table, tables: List[Table]) -> List[Table]:
    """Returns a list of tables that have a foreign key referencing the parent_table."""
    children = []
    for table in tables:
        if table.name == parent_table.name:
            continue
        for fk in table.foreign_keys:
            if fk.ref_table == parent_table.name:
                children.append(table)
    return children


def get_parent_tables(child_table: Table, tables: List[Table]) -> List[Table]:
    """Returns a list of tables that have a foreign key referencing the parent_table."""
    parent = []
    if child_table.foreign_keys:
        for fk in child_table.foreign_keys:
            for table in tables:
                if table.name == fk.ref_table:
                    parent.append(table)
        return parent
    return []


def get_sqlalchemy_type(column: Column) -> str:
    """Returns the SQLAlchemy type string (e.g., String, Integer)."""
    data_type = column.data_type.lower()
    if data_type in ["varchar", "char"]:
        return f"String({column.char_length})" if column.char_length else "String"
    elif data_type == "text":
        return "Text"
    elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
        return "Integer"
    elif data_type == "boolean":
        return "Boolean"
    elif data_type in ["float", "real"]:
        return "Float"
    elif data_type in ["double precision"]:
        return "Double"
    elif data_type in ["numeric", "decimal"]:
        precision = (
            column.numeric_precision if column.numeric_precision is not None else ""
        )
        scale = f", {column.numeric_scale}" if column.numeric_scale is not None else ""
        return f"Numeric({precision}{scale})"
    elif data_type == "date":
        return "Date"
    elif data_type in ["timestamp", "timestamptz", "datetime"]:
        return "DateTime(timezone=True)" if "tz" in data_type else "DateTime"
    elif data_type == "uuid":
        return "UUID(as_uuid=True)"
    elif data_type in ["json", "jsonb"]:
        return "JSON"
    elif data_type in ["bytea", "blob"]:
        return "LargeBinary"
    return "String"  # Default fallback


def should_use_server_default(column: Column) -> bool:
    """Determines if a column should use server_default=func.now()."""
    # Check for specific SQL function strings in default_value
    if isinstance(column.default_value, str) and column.default_value.upper() in [
        "CURRENT_TIMESTAMP",
        "NOW()",
        "GETDATE()",
    ]:
        return True
    return False


def get_pk_names_for_repr(table: Table) -> str:
    """Returns a string of primary key assignments for __repr__."""
    pk_cols = get_pk_columns(table)
    if not pk_cols:
        return "id=None"  # Fallback if no PK

    repr_parts = []
    for col in pk_cols:
        repr_parts.append(
            f"{to_snake_case(col.name)}={{self.{to_snake_case(col.name)}}}"
        )
    return ", ".join(repr_parts)


def get_default_value_for_type(column: Column):
    """Returns a suitable default value for testing based on column type."""
    data_type = column.data_type.lower()
    if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
        return f"'{to_snake_case(column.name)}_test'"
    elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
        return 1
    elif data_type in ["boolean"]:
        return "True"
    elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
        return 1.0
    elif data_type in ["date"]:
        return "'2024-01-01'"
    elif data_type in ["timestamp", "timestamptz", "datetime"]:
        return "'2024-01-01T12:00:00Z'"
    elif data_type in ["bytea", "blob"]:
        return "'test_bytes'"
    return "'default_value'"


def get_pk_test_url_str(table: Table) -> str:
    """Returns a string for constructing test URLs (e.g., 'str(data["id1"]) + "/" + str(data["id2"])')."""
    pk_cols = get_pk_columns(table)
    if not pk_cols:
        return ""  # Should not happen for PK-based endpoints

    parts = []
    for col in pk_cols:
        parts.append(f'str(data["{to_snake_case(col.name)}"])')
    return ' + "/" + '.join(parts)


# @staticmethod
# def _get_pk_type(table: Table) -> str:
#     """Returns the Python type of the first primary key. For composite keys, use _get_pk_columns_types_str."""
#     pk_column = CRUDApiGenerator._get_pk_column(table)
#     if pk_column:
#         return CRUDApiGenerator._sql_type_to_python_type(pk_column)
#     return "int"  # Default to int if no PK found

# @staticmethod
# def _get_pk_name(table: Table) -> str:
#     """Returns the name of the first primary key column. For composite keys, use _get_pk_columns_names_str."""
#     pk_column = CRUDApiGenerator._get_pk_column(table)
#     if pk_column:
#         return pk_column.name
#     return "id"  # Default to 'id'

# @staticmethod
# def _get_pk_columns(table: Table) -> List[Column]:
#     """Returns a list of primary key columns for a table."""
#     if table.primary_key and table.primary_key.columns:
#         return [
#             table.columns[col_name]
#             for col_name in table.primary_key.columns
#             if col_name in table.columns
#         ]
#     return []

# @staticmethod
# def _get_pk_columns_names_str(table: Table) -> str:
#     """Returns a comma-separated string of primary key column names (snake_case)."""
#     pk_cols = CRUDApiGenerator._get_pk_columns(table)
#     return ", ".join([CRUDApiGenerator._to_snake_case(col.name) for col in pk_cols])

# @staticmethod

# @staticmethod

# @staticmethod
# def _get_pk_filter_conditions_str(table: Table) -> str:
#     """Returns a string for SQLAlchemy filter conditions (e.g., 'Model.id1 == id1, Model.id2 == id2')."""
#     pk_cols = CRUDApiGenerator._get_pk_columns(table)
#     conditions = [
#         f"{{{{ table_pascal_case }}}}.{CRUDApiGenerator._to_snake_case(col.name)} == {CRUDApiGenerator._to_snake_case(col.name)}"
#         for col in pk_cols
#     ]
#     return ", ".join(conditions)

# @staticmethod

# @staticmethod


# @staticmethod


# @staticmethod

# @staticmethod


# @staticmethod
# def _has_datetime_or_date_column(table: Table) -> bool:
#     """Checks if the table has any date or datetime columns."""
#     for column in table.columns.values():
#         if column.data_type.lower() in [
#             "date",
#             "timestamp",
#             "timestamptz",
#             "datetime",
#         ]:
#             return True
#     return False

# @staticmethod
