import re
from pgsql_parser import Column, Table, ForeignKey
from typing import List


sql_type_to_flask_sqlalchemy_types = {
    "VARCHAR": "db.String",
    "TEXT": "db.Text",
    "INTEGER": "db.Integer",
    "INT": "db.Integer",
    "BIGINT": "db.BigInteger",
    "SMALLINT": "db.SmallInteger",
    "BOOLEAN": "db.Boolean",
    "DATE": "db.Date",
    "DATETIME": "db.DateTime",
    "TIMESTAMP": "db.TIMESTAMP",
    "FLOAT": "db.Float",
    "REAL": "db.REAL",
    "NUMERIC": "db.Numeric",
    "DECIMAL": "db.Numeric",
    "BLOB": "db.LargeBinary",
    "JSON": "db.JSON",
    # PostgreSQL Specific Types
    "UUID": "sqlalchemy.dialects.postgresql.UUID(as_uuid=True)",
    "JSONB": "sqlalchemy.dialects.postgresql.JSONB",
    "ARRAY": "sqlalchemy.dialects.postgresql.ARRAY(db.Integer)",
    "INET": "sqlalchemy.dialects.postgresql.INET",
    "MACADDR": "sqlalchemy.dialects.postgresql.MACADDR",
    "DOUBLE PRECISION": "sqlalchemy.dialects.postgresql.DOUBLE_PRECISION",
    "SMALLSERIAL": "db.SmallInteger",  # Autoincrement handled by primary_key=True
    "SERIAL": "db.Integer",  # Autoincrement handled by primary_key=True
    "BIGSERIAL": "db.BigInteger",  # Autoincrement handled by primary_key=True
    "CHARACTER VARYING": "db.String",
    "CHARACTER": "db.String",
    "CHAR": "db.String",
    "BPCHAR": "db.String",  # Fixed-length, blank-padded character type
    # "BPCHAR": "db.String", # Fixed-length, blank-padded character type without explicit length
    # SQL Server Specific Types
    "NVARCHAR": "db.NVARCHAR",
    "VARBINARY": "db.VARBINARY",
    "IMAGE": "db.LargeBinary",  # Similar to BLOB
    "MONEY": "db.Numeric(19, 4)",  # Common mapping for MONEY
    "SMALLDATETIME": "db.DateTime",
    "DATETIME2": "db.DateTime",
    "UNIQUEIDENTIFIER": "sqlalchemy.dialects.mssql.UNIQUEIDENTIFIER",
    # # Oracle Specific Types
    "NUMBER": "db.Numeric",
    "VARCHAR2": "db.String",
    "NVARCHAR2": "db.NVARCHAR",
    "CLOB": "db.Text",
    # "DATE": "db.DateTime", # Oracle's DATE includes time component
    "RAW": "db.LargeBinary",
    # # MySQL Specific Types
    "TINYINT(1)": "db.Boolean",  # Often used for boolean
    "MEDIUMINT": "db.Integer",
    "YEAR": "db.Integer",  # Stored as integer
    "ENUM": "db.Enum",  # SQLAlchemy's generic Enum
    "SET": "db.String",  # Typically stored as comma-separated string
    "JSON": "db.JSON",
}


def get_child_relationships(table: Table, tables: List[Table]) -> List[ForeignKey]:
    child_relationships: List[ForeignKey] = []
    if table.primary_key:
        for tb in tables:
            if not tb.foreign_keys:
                continue
            for fk in tb.foreign_keys:
                if fk.ref_table.upper() == table.name.upper():
                    child_relationships.append(fk)
    return child_relationships


def get_pk_columns(table: Table) -> List[Column]:
    if not table.primary_key:
        return []
    pk_cols = []
    for col_name in table.primary_key.columns:
        pk_col = table.columns.get(col_name)
        pk_cols.append(pk_col)
    return pk_cols


def is_composite_foreign_key(fk: ForeignKey):
    return len(fk.columns) > 1


def to_flask_sqlalchemy_type(column):
    data_type = column.data_type.upper()
    alchemy_type = sql_type_to_flask_sqlalchemy_types.get(data_type)
    if not alchemy_type:
        raise ValueError(f"unrecognized data type:{data_type}")
    if (
        alchemy_type in ["db.String", "db.NVARCHAR", "db.VARBINARY"]
        and column.char_length > 0
    ):
        return f"{alchemy_type}({column.char_length})"
    elif alchemy_type in ["db.Numeric"] and column.numeric_precision:
        if column.numeric_scale:
            return f"{alchemy_type}({column.numeric_precision}, {column.numeric_scale})"
        return f"{alchemy_type}({column.numeric_precision}, 0)"

    return alchemy_type


def to_composite_fk_str(fk: ForeignKey) -> str:

    cols_str = str(fk.columns)
    refcols = []
    for rfcol in fk.ref_columns:
        if fk.ref_schema:
            refcols.append(f"{fk.ref_schema}.{fk.ref_table}.{rfcol}")
        else:
            refcols.append(f"{fk.ref_table}.{rfcol}")
    refcols_str = str(refcols)
    return f"db.ForeignKeyConstraint({cols_str}, {refcols_str})"


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


def normalize_words(words: List[str]) -> List[str]:
    norm_words = []
    buf = []
    for word in words:
        if len(word) > 1:
            if len(buf) > 0:
                norm_words.append("".join(buf))
                buf = []
            norm_words.append(word)
        elif re.match(r"^[^A-Z0-9]$", word):

            if len(buf) > 0:
                norm_words.append("".join(buf))
                buf = []
            if len(norm_words) > 0:
                norm_words.append(word)
        else:
            buf.append(word)
    if len(buf) > 0:
        norm_words.append("".join(buf))
        buf = []
    ret_cnt = len(norm_words)
    if ret_cnt > 1:
        for idx in range(1, ret_cnt + 1):
            if norm_words[ret_cnt - idx] != "_":
                brk = ret_cnt - idx + 1
                norm_words = norm_words[0:brk]
                break
    return norm_words


def split_words(word_or_multi_words: str) -> List[str]:
    lcnt = len(word_or_multi_words)
    pos = 0
    words = []
    buf = []
    while pos < lcnt:
        c = word_or_multi_words[pos]
        pos += 1
        if re.match(r"^[A-Z]$", c):
            if len(buf) > 0:
                words.append("".join(buf))
                buf = []
            buf.append(c)
        elif re.match(r"^[^a-zA-Z0-9]$", c):
            if len(buf) > 0:
                words.append("".join(buf))
                buf = []
            words.append("_")
        else:
            buf.append(c)

    if len(buf) > 0:
        words.append("".join(buf))
    return normalize_words(words)


def to_singular(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    singular = singularize(last_word)
    plural = pluralize(singular)
    if plural.lower() == last_word.lower():
        words[-1] = singular
    return "".join(words)


def to_singular_snake_case(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    singular = singularize(last_word)
    plural = pluralize(singular)
    if plural.lower() == last_word.lower():
        words[-1] = singular
    ret_word = "_".join(words).lower()
    return re.sub(r"[_]+", "_", ret_word).strip("_")


def to_singular_pascal_case(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    singular = singularize(last_word)
    plural = pluralize(singular)
    if plural.lower() == last_word.lower():
        words[-1] = singular
    ret_word = "".join([wrd.lower().capitalize() for wrd in words if wrd != "_"])
    return ret_word


def to_decription(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")

    ret_word = " ".join([wrd.lower() for wrd in words if wrd != "_"]).strip()
    ret_word = ret_word.capitalize()
    return ret_word


def to_plural(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    plural = pluralize(last_word)
    singular = singularize(plural)
    if singular.lower() == last_word.lower():
        words[-1] = plural
    return "".join(words)


def to_plural_snake_case(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    singular = singularize(last_word)
    plural = pluralize(singular)
    words[-1] = plural
    ret_word = "_".join(words).lower()
    return re.sub(r"[_]+", "_", ret_word).strip("_")


def to_plural_pascal_case(word_or_multi_words) -> str:
    words = split_words(word_or_multi_words)
    if not words:
        raise ValueError(f"Invalid identifier [{word_or_multi_words}]")
    last_word = words[-1]
    singular = singularize(last_word)
    plural = pluralize(singular)
    words[-1] = plural
    ret_word = "".join([wrd.lower().capitalize() for wrd in words if wrd != "_"])
    return ret_word


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
    original_word = word
    word = word.lower()
    if word.endswith("phases"):
        return original_word[0:-1]

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

    if word.endswith("phases"):
        return word

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
    elif data_type in [
        "integer",
        "smallint",
        "bigint",
        "serial",
        "smallserial",
        "bigserial",
        "int",
    ]:
        return "int"
    elif data_type in ["boolean"]:
        return "bool"
    elif data_type in [
        "float",
        "double precision",
        "real",
        "numeric",
        "decimal",
        "double",
        "number",
    ]:
        return "float"  # Or Decimal from decimal module
    elif data_type in ["date"]:
        return "date"
    elif data_type in ["timestamp", "timestamptz", "datetime"]:
        return "datetime"
    elif data_type in ["bytea", "blob", "varbinary", "image"]:
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


def to_pydantic_field_attrs(column: Column):
    buf = ""
    data_type = column.data_type.lower()
    if column.nullable is False:
        buf += "...,"
    # else:
    #     buf += "None,"

    if column.default_value is not None:
        buf += f" default={column.default_value},"
    else:
        buf += " default=None,"

    if data_type in [
        "varchar",
        "char",
        "varchar2",
        "nvarchar",
        "nvarchar2",
        "character varying",
    ]:
        buf += f" min_length=1, max_length={column.char_length},"

    buf += f' description="{to_decription(column.name)}"'
    return buf


def to_flask_restx_field_attrs(column: Column) -> str:
    buf = ""

    if column.is_primary is True:
        buf += "readOnly=True,"

    if column.nullable is False:
        buf += "required=True,"

    buf += f' description="{to_decription(column.name)}"'
    return buf


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
    if data_type in [
        "varchar",
        "char",
        "character",
        "varchar2",
        "nvarchar",
        "nvarchar2",
        "character varying",
        "bpchar",
    ]:
        return f"String({column.char_length})" if column.char_length else "String"
    elif data_type == "text":
        return "Text"
    elif data_type in [
        "integer",
        "smallint",
        "bigint",
        "int",
        "smallserial",
        "serial",
        "bigserial",
    ]:
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


def get_flask_restx_type(column: Column) -> str:
    """
    Returns the Flask-RESTx document model field type string
    (e.g., 'fields.String', 'fields.Integer') based on a given database type string.

    Args:
        db_type (str): The database column type as a string (e.g., "varchar", "integer", "timestamp").

    Returns:
        str: The corresponding Flask-RESTx field type string.
    """
    # Normalize the input type to lowercase for case-insensitive matching
    normalized_db_type = column.data_type.lower()

    # Dictionary mapping common database types to Flask-RESTx field types
    # This provides a quick lookup for direct mappings.
    type_map = {
        # String types
        "varchar": "fields.String",
        "char": "fields.String",
        "character": "fields.String",
        "varchar2": "fields.String",
        "nvarchar": "fields.String",
        "nvarchar2": "fields.String",
        "character varying": "fields.String",
        "bpchar": "fields.String",
        "text": "fields.String",  # TEXT maps to String in Flask-RESTx for API representation
        # Integer types
        "integer": "fields.Integer",
        "smallint": "fields.Integer",
        "bigint": "fields.Integer",
        "int": "fields.Integer",
        "smallserial": "fields.Integer",  # PostgreSQL serial types map to Integer
        "serial": "fields.Integer",
        "bigserial": "fields.Integer",
        # Boolean type
        "boolean": "fields.Boolean",
        "bool": "fields.Boolean",
        # Floating point types
        "float": "fields.Float",
        "real": "fields.Float",
        "double precision": "fields.Float",  # Maps to Float for general API use
        # Numeric/Decimal types
        "numeric": "fields.Float",  # Often mapped to Float for simplicity in APIs
        "decimal": "fields.Float",  # Or fields.Raw if exact precision is critical and handled client-side
        # Date and Time types
        "date": "fields.Date",
        "timestamp": "fields.DateTime",
        "timestamptz": "fields.DateTime",  # With timezone, still DateTime in Flask-RESTx
        "datetime": "fields.DateTime",
        # UUID type (often represented as a string in APIs)
        "uuid": "fields.String",
        # JSON and Binary types (often represented as raw data or strings)
        "json": "fields.Raw",  # Can be fields.String if always stringified JSON
        "jsonb": "fields.Raw",
        "bytea": "fields.Raw",  # Binary data, often base64 encoded string in APIs
        "blob": "fields.Raw",
        "binary": "fields.Raw",
    }

    # Check for direct mapping
    if normalized_db_type in type_map:
        return type_map[normalized_db_type]

    # Handle cases where the type might have parameters, but Flask-RESTx doesn't
    # typically use them directly in the field type string (e.g., String(255) is just String)
    # For example, if input is "varchar(255)", we still want "fields.String"
    if "(" in normalized_db_type and ")" in normalized_db_type:
        base_type = normalized_db_type.split("(")[0]
        if base_type in type_map:
            return type_map[base_type]

    # Default fallback for unhandled types
    return "fields.String"


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


def write_source_file(file_path, content):
    with open(file_path, "wt", encoding="utf-8") as fout:
        fout.write(content)
