import pytest
from datetime import date, datetime
from typing import Optional, List, Dict, Tuple
from pgsql_parser import Column, PrimaryKey, ForeignKey, Constraint, Table, Index

from wukong.commands.template_utils import (  # Uncomment and adjust if your code is in a different file
    to_composite_fk_str,
    to_snake_case,
    to_pascal_case,
    singularize,
    pluralize,
    get_python_type,
    get_datetime_imports,
    get_pydantic_type,
    get_sqlalchemy_type_imports,
    get_sqlalchemy_type,
    get_pk_columns,
    is_auto_generated_pk,
    get_pk_path_params_str,
    get_pk_columns_types_str,
    get_pk_kwargs_str,
    get_child_tables,
    get_parent_tables,
    should_use_server_default,
    get_pk_names_for_repr,
    get_default_value_for_type,
    get_pk_test_url_str,
)

# --- Test Classes for Data Model Objects ---


class TestColumn:
    def test_init(self):
        col = Column("users", "id", "INTEGER", nullable=False, is_primary=True)
        assert col.table_name == (
            "users",
        )  # This matches the tuple in your Column init
        assert col.name == "id"
        assert col.data_type == "INTEGER"
        assert col.nullable is False
        assert col.is_primary is True
        assert col.default_value is None
        assert col.char_length is None
        assert col.numeric_precision is None
        assert col.foreign_key_ref is None

    def test_repr(self):
        col = Column("products", "name", "VARCHAR(255)")
        assert (
            repr(col)
            == "Column(table_name=('products',), name='name', type='VARCHAR(255)', nullable=True)"
        )


# ---


class TestPrimaryKey:
    def test_init(self):
        pk = PrimaryKey("pk_users", "users", ["id"])
        assert pk.name == "pk_users"
        assert pk.table_name == "users"
        assert pk.columns == ["id"]

    def test_repr(self):
        pk = PrimaryKey(None, "orders", ["order_id", "customer_id"])
        assert (
            repr(pk)
            == "PrimaryKey(name=None, table_name=orders, columns=['order_id', 'customer_id'])"
        )


# ---


class TestForeignKey:
    def test_init(self):
        fk = ForeignKey(
            "fk_user_id", "orders", ["user_id"], "users", ["id"], ref_schema="public"
        )
        assert fk.name == "fk_user_id"
        assert fk.table_name == "orders"
        assert fk.columns == ["user_id"]
        assert fk.ref_table == "users"
        assert fk.ref_columns == ["id"]
        assert fk.ref_schema == "public"
        assert fk.is_composite_key is False

    def test_repr(self):
        fk = ForeignKey(
            "fk_comp_key",
            "order_items",
            ["order_id", "product_id"],
            "products",
            ["id", "item_code"],
            is_composite_key=True,
        )
        expected_repr = "ForeignKey(name='fk_comp_key', table_name=order_items, columns=['order_id', 'product_id'], ref_table='products', ref_columns=['id', 'item_code'])"
        assert repr(fk) == expected_repr


# ---


class TestConstraint:
    def test_init(self):
        c = Constraint("chk_age", "CHECK", "age > 18", columns=["age"])
        assert c.name == "chk_age"
        assert c.ctype == "CHECK"
        assert c.expression == "age > 18"
        assert c.columns == ["age"]

    def test_repr(self):
        c = Constraint("uq_email", "UNIQUE", columns=["email"])
        assert repr(c) == "Constraint(UNIQUE, name='uq_email', cols=['email'])"


# ---


class TestIndex:
    def test_init(self):
        idx = Index(
            "idx_users_email", "users", ["email"], is_unique=True, method="btree"
        )
        assert idx.name == "idx_users_email"
        assert idx.table == "users"
        assert idx.columns == ["email"]
        assert idx.is_unique is True
        assert idx.method == "btree"

    def test_repr(self):
        idx = Index("idx_products_name", "products", ["name"])
        assert (
            repr(idx)
            == "Index(name='idx_products_name', table=products, columns=['name'])"
        )


# ---


class TestTable:
    def test_init(self):
        table = Table("users", schema="public", database="mydb")
        assert table.name == "users"
        assert table.schema == "public"
        assert table.database == "mydb"
        assert table.table_type == "TABLE"
        assert table.primary_key is None
        assert table.columns == {}
        assert table.foreign_keys == []
        assert table.constraints == []
        assert table.is_view is False

    def test_add_column(self):
        table = Table("users")
        col1 = Column("users", "id", "INTEGER", is_primary=True)
        col2 = Column("users", "name", "VARCHAR")
        fk = ForeignKey("fk_address", "users", ["address_id"], "addresses", ["id"])
        pk = PrimaryKey("users_pk", "users", ["id"])

        table.add_column(col1)
        table.add_column(col2)
        table.add_column(fk)
        table.add_column(
            pk
        )  # Adding a PrimaryKey object sets the primary_key attribute

        assert len(table.columns) == 2
        assert "id" in table.columns
        assert "name" in table.columns
        assert table.columns["id"] == col1
        assert len(table.foreign_keys) == 1
        assert table.foreign_keys[0] == fk
        assert table.primary_key == pk

    def test_get_qualified_name(self):
        table = Table("users")
        assert table.get_qualified_name() == "users"

        table_schema = Table("products", schema="public")
        assert table_schema.get_qualified_name() == "public.products"

        table_db_schema = Table("orders", schema="sales", database="warehouse")
        assert table_db_schema.get_qualified_name() == "warehouse.sales.orders"

    def test_repr(self):
        table = Table("items", schema="inventory")
        col = Column("items", "item_id", "INTEGER", is_primary=True)
        pk = PrimaryKey("item_pk", "items", ["item_id"])
        table.add_column(col)
        table.add_column(pk)
        assert (
            repr(table)
            == "Table(name=inventory.items, type=TABLE, columns=1, pkey=PrimaryKey(name='item_pk', table_name=items, columns=['item_id']))"
        )


# --- Test Functions ---


def test_to_composite_fk_str():
    fk_single = ForeignKey(
        "fk_user_address",
        "users",
        ["address_id"],
        "addresses",
        ["id"],
        ref_schema="public",
    )
    assert (
        to_composite_fk_str(fk_single)
        == "ForeignKey(['address_id'], ['public.addresses.id'])"
    )

    fk_composite = ForeignKey(
        "fk_order_product",
        "order_items",
        ["order_id", "product_id"],
        "products",
        ["id", "sku"],
        ref_schema="catalog",
    )
    assert (
        to_composite_fk_str(fk_composite)
        == "ForeignKey(['order_id', 'product_id'], ['catalog.products.id', 'catalog.products.sku'])"
    )

    fk_no_schema = ForeignKey("fk_no_schema", "t1", ["col1"], "t2", ["col2"])
    assert to_composite_fk_str(fk_no_schema) == "ForeignKey(['col1'], ['t2.col2'])"


# ---


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        ("PascalCaseString", "pascal_case_string"),
        ("camelCaseString", "camel_case_string"),
        ("snake_case_string", "snake_case_string"),
        ("space separated string", "space_separated_string"),
        ("XMLHttpRequest", "xml_http_request"),
        ("ID", "id"),  # Test all caps
        ("A", "a"),  # Single letter
        ("", ""),  # Empty string
        ("My New Table Name", "my_new_table_name"),
    ],
)
def test_to_snake_case(input_string, expected_output):
    assert to_snake_case(input_string) == expected_output


# ---


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        ("snake_case_string", "SnakeCaseString"),
        ("kebab-case-string", "KebabCaseString"),
        ("space separated string", "SpaceSeparatedString"),
        ("pascalCase", "PascalCase"),
        ("ID", "Id"),  # Ensure consistent capitalization
        ("a", "A"),
        ("", ""),
        ("my_new_table_name", "MyNewTableName"),
    ],
)
def test_to_pascal_case(input_string, expected_output):
    assert to_pascal_case(input_string) == expected_output


# ---


@pytest.mark.parametrize(
    "plural_word, singular_word",
    [
        ("cats", "cat"),
        ("buses", "bus"),
        ("quizzes", "quiz"),
        ("churches", "church"),
        ("dishes", "dish"),
        ("boxes", "box"),
        ("armies", "army"),
        ("ladies", "lady"),
        ("wolves", "wolf"),
        ("knives", "knife"),
        ("children", "child"),
        ("people", "person"),
        ("men", "man"),
        ("women", "woman"),
        ("teeth", "tooth"),
        ("feet", "foot"),
        ("mice", "mouse"),
        ("geese", "goose"),
        ("status", "status"),  # Already singular
        ("octopus", "octopus"),  # Another already singular
        ("analysis", "analysis"),  # No change
        ("series", "series"),  # No change
        ("", ""),  # Empty string
        ("toys", "toy"),  # vowel before 'y'
    ],
)
def test_singularize(plural_word, singular_word):
    assert singularize(plural_word) == singular_word


# ---


@pytest.mark.parametrize(
    "singular_word, plural_word",
    [
        ("cat", "cats"),
        ("bus", "buses"),
        ("quiz", "quizzes"),
        ("church", "churches"),
        ("dish", "dishes"),
        ("box", "boxes"),
        ("army", "armies"),
        ("lady", "ladies"),
        ("wolf", "wolves"),
        ("knife", "knives"),
        ("child", "children"),
        ("person", "people"),
        ("man", "men"),
        ("woman", "women"),
        ("tooth", "teeth"),
        ("foot", "feet"),
        ("mouse", "mice"),
        ("goose", "geese"),
        ("tomato", "tomatoes"),  # Ends with 'o'
        ("photo", "photos"),  # Exception for 'o'
        ("day", "days"),  # Vowel before 'y'
        ("status", "status"),  # Ends with 's'
        ("", ""),  # Empty string
    ],
)
def test_pluralize(singular_word, plural_word):
    assert pluralize(singular_word) == plural_word


# ---


@pytest.mark.parametrize(
    "data_type, expected_python_type",
    [
        ("VARCHAR", "str"),
        ("TEXT", "str"),
        ("CHAR", "str"),
        ("UUID", "str"),
        ("JSON", "str"),
        ("JSONB", "str"),
        ("INTEGER", "int"),
        ("SMALLINT", "int"),
        ("BIGINT", "int"),
        ("SERIAL", "int"),
        ("BIGSERIAL", "int"),
        ("BOOLEAN", "bool"),
        ("FLOAT", "float"),
        ("DOUBLE PRECISION", "float"),
        ("REAL", "float"),
        ("NUMERIC", "float"),
        ("DECIMAL", "float"),
        ("DATE", "date"),
        ("TIMESTAMP", "datetime"),
        ("TIMESTAMPTZ", "datetime"),
        ("DATETIME", "datetime"),
        ("BYTEA", "bytes"),
        ("BLOB", "bytes"),
        ("UNKNOWN_TYPE", "Any"),  # Fallback
    ],
)
def test_get_python_type(data_type, expected_python_type):
    col = Column("test_table", "test_col", data_type)
    assert get_python_type(col) == expected_python_type


# ---


def test_get_datetime_imports():
    table = Table("events")
    table.add_column(Column("events", "event_id", "INTEGER"))
    table.add_column(Column("events", "event_date", "DATE"))
    table.add_column(Column("events", "created_at", "TIMESTAMPTZ"))
    table.add_column(Column("events", "name", "VARCHAR"))

    imports = get_datetime_imports(table)
    assert sorted(imports) == sorted(["date", "datetime"])

    # No datetime columns
    table_no_dt = Table("users")
    table_no_dt.add_column(Column("users", "id", "INTEGER"))
    table_no_dt.add_column(Column("users", "name", "VARCHAR"))
    assert get_datetime_imports(table_no_dt) == []

    # Empty table
    empty_table = Table("empty")
    assert get_datetime_imports(empty_table) == []


# ---


@pytest.mark.parametrize(
    "data_type, nullable, expected_pydantic_type",
    [
        ("INTEGER", True, "Optional[int]"),
        ("INTEGER", False, "int"),
        ("VARCHAR", True, "Optional[str]"),
        ("TEXT", False, "str"),
        ("BOOLEAN", True, "Optional[bool]"),
        ("DATE", False, "date"),
        ("TIMESTAMP", True, "Optional[datetime]"),
        ("UNKNOWN_TYPE", True, "Optional[typing.Any]"),
        ("UNKNOWN_TYPE", False, "typing.Any"),
    ],
)
def test_get_pydantic_type(data_type, nullable, expected_pydantic_type):
    col = Column("test_table", "test_col", data_type, nullable=nullable)
    assert get_pydantic_type(col) == expected_pydantic_type


# ---


def test_get_sqlalchemy_type_imports():
    table = Table("mixed_types")
    table.add_column(Column("mixed_types", "id", "INTEGER"))
    col_str_len = Column("mixed_types", "name", "VARCHAR")
    col_str_len.char_length = 255
    table.add_column(col_str_len)
    table.add_column(Column("mixed_types", "is_active", "BOOLEAN"))
    table.add_column(Column("mixed_types", "created_at", "TIMESTAMPTZ"))
    col_numeric = Column("mixed_types", "price", "NUMERIC")
    col_numeric.numeric_precision = 10
    col_numeric.numeric_scale = 2
    table.add_column(col_numeric)
    table.add_column(Column("mixed_types", "description", "TEXT"))
    table.add_column(Column("mixed_types", "uuid_col", "UUID"))
    table.add_column(Column("mixed_types", "json_data", "JSONB"))

    imports = get_sqlalchemy_type_imports(table)
    # Expected types without length/precision: Integer, String, Boolean, DateTime, Numeric, Text, UUID, JSON
    expected_imports = {
        "Integer",
        "String",
        "Boolean",
        "DateTime",
        "Numeric",
        "Text",
        "UUID",
        "JSON",
    }
    assert set(imports) == expected_imports

    # Test with empty table
    empty_table = Table("empty")
    assert get_sqlalchemy_type_imports(empty_table) == []


# ---


@pytest.mark.parametrize(
    "data_type, char_length, precision, scale, expected_sqlalchemy_type",
    [
        ("VARCHAR", 255, None, None, "String(255)"),
        ("VARCHAR", None, None, None, "String"),
        ("TEXT", None, None, None, "Text"),
        ("INTEGER", None, None, None, "Integer"),
        ("BIGINT", None, None, None, "Integer"),
        ("BOOLEAN", None, None, None, "Boolean"),
        ("FLOAT", None, None, None, "Float"),
        ("DOUBLE PRECISION", None, None, None, "Double"),
        (
            "NUMERIC",
            None,
            10,
            2,
            "Numeric(10, 2)",
        ),  # Note: your implementation combines scale with precision string
        ("NUMERIC", None, 10, None, "Numeric(10)"),
        ("NUMERIC", None, None, None, "Numeric()"),
        ("DATE", None, None, None, "Date"),
        ("TIMESTAMP", None, None, None, "DateTime"),
        ("TIMESTAMPTZ", None, None, None, "DateTime(timezone=True)"),
        ("UUID", None, None, None, "UUID(as_uuid=True)"),
        ("JSON", None, None, None, "JSON"),
        ("BYTEA", None, None, None, "LargeBinary"),
        ("UNKNOWN_TYPE", None, None, None, "String"),  # Default fallback
    ],
)
def test_get_sqlalchemy_type(
    data_type, char_length, precision, scale, expected_sqlalchemy_type
):
    col = Column("test_table", "test_col", data_type)
    col.char_length = char_length
    col.numeric_precision = precision
    col.numeric_scale = scale
    assert get_sqlalchemy_type(col) == expected_sqlalchemy_type


# ---


def test_get_pk_columns():
    table = Table("users")
    col_id = Column("users", "user_id", "INTEGER", is_primary=True)
    col_name = Column("users", "user_name", "VARCHAR")
    col_email = Column("users", "email", "VARCHAR")

    table.add_column(col_id)
    table.add_column(col_name)
    table.add_column(col_email)

    # Single primary key
    table.add_column(PrimaryKey("user_pk", "users", ["user_id"]))
    pk_cols = get_pk_columns(table)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "user_id"

    # Composite primary key
    table_composite_pk = Table("order_items")
    col_order_id = Column("order_items", "order_id", "INTEGER", is_primary=True)
    col_item_id = Column("order_items", "item_id", "INTEGER", is_primary=True)
    table_composite_pk.add_column(col_order_id)
    table_composite_pk.add_column(col_item_id)
    table_composite_pk.add_column(
        PrimaryKey("order_item_pk", "order_items", ["order_id", "item_id"])
    )
    pk_cols_composite = get_pk_columns(table_composite_pk)
    assert len(pk_cols_composite) == 2
    assert pk_cols_composite[0].name == "order_id"
    assert pk_cols_composite[1].name == "item_id"

    # No primary key
    table_no_pk = Table("logs")
    table_no_pk.add_column(Column("logs", "message", "TEXT"))
    assert get_pk_columns(table_no_pk) == []

    # PK defined but columns not added to table.columns (edge case)
    table_missing_cols = Table("test")
    table_missing_cols.add_column(PrimaryKey("test_pk", "test", ["non_existent_col"]))
    assert get_pk_columns(table_missing_cols) == []


# ---


@pytest.mark.parametrize(
    "data_type, is_primary, default_value, expected_auto_generated",
    [
        ("SERIAL", True, None, True),
        ("BIGSERIAL", True, None, True),
        ("INTEGER", True, None, True),
        ("SMALLINT", True, None, True),
        ("BIGINT", True, None, True),
        ("UUID", True, None, True),
        ("UUID", True, "uuid_generate_v4()", True),
        ("UUID", True, "gen_random_uuid()", True),
        ("VARCHAR", True, None, False),  # Primary but not auto-generated type
        ("INTEGER", False, None, False),  # Not primary
        (
            "INTEGER",
            True,
            "10",
            False,
        ),  # Primary but has a specific default, not auto-generated
        ("TEXT", True, None, False),  # Not an auto-generated type
    ],
)
def test_is_auto_generated_pk(
    data_type, is_primary, default_value, expected_auto_generated
):
    col = Column(
        "test_table",
        "test_id",
        data_type,
        is_primary=is_primary,
        default_value=default_value,
    )
    assert is_auto_generated_pk(col) == expected_auto_generated


# ---


def test_get_pk_path_params_str():
    table_single_pk = Table("users")
    table_single_pk.add_column(Column("users", "user_id", "INTEGER", is_primary=True))
    table_single_pk.primary_key = PrimaryKey("pk", "users", ["user_id"])
    assert get_pk_path_params_str(table_single_pk) == "{user_id}"

    table_composite_pk = Table("order_items")
    table_composite_pk.add_column(
        Column("order_items", "order_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.add_column(
        Column("order_items", "product_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.primary_key = PrimaryKey(
        "pk", "order_items", ["order_id", "product_id"]
    )
    assert get_pk_path_params_str(table_composite_pk) == "{order_id}/{product_id}"

    table_no_pk = Table("logs")
    assert get_pk_path_params_str(table_no_pk) == ""


# ---


def test_get_pk_columns_types_str():
    table_single_pk = Table("users")
    table_single_pk.add_column(Column("users", "user_id", "INTEGER", is_primary=True))
    table_single_pk.primary_key = PrimaryKey("pk", "users", ["user_id"])
    assert get_pk_columns_types_str(table_single_pk) == "user_id: int"

    table_composite_pk = Table("order_items")
    table_composite_pk.add_column(
        Column("order_items", "order_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.add_column(
        Column("order_items", "product_uuid", "UUID", is_primary=True)
    )
    table_composite_pk.primary_key = PrimaryKey(
        "pk", "order_items", ["order_id", "product_uuid"]
    )
    assert (
        get_pk_columns_types_str(table_composite_pk)
        == "order_id: int, product_uuid: str"
    )

    table_no_pk = Table("logs")
    assert get_pk_columns_types_str(table_no_pk) == ""


# ---


def test_get_pk_kwargs_str():
    table_single_pk = Table("users")
    table_single_pk.add_column(Column("users", "user_id", "INTEGER", is_primary=True))
    table_single_pk.primary_key = PrimaryKey("pk", "users", ["user_id"])
    assert get_pk_kwargs_str(table_single_pk) == "user_id=user_id"

    table_composite_pk = Table("order_items")
    table_composite_pk.add_column(
        Column("order_items", "order_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.add_column(
        Column("order_items", "product_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.primary_key = PrimaryKey(
        "pk", "order_items", ["order_id", "product_id"]
    )
    assert (
        get_pk_kwargs_str(table_composite_pk)
        == "order_id=order_id, product_id=product_id"
    )

    table_no_pk = Table("logs")
    assert get_pk_kwargs_str(table_no_pk) == ""


# ---


def test_get_child_tables():
    # Setup tables
    users_table = Table("users")
    users_table.add_column(Column("users", "id", "INTEGER", is_primary=True))
    users_table.add_column(PrimaryKey("users_pk", "users", ["id"]))

    posts_table = Table("posts")
    posts_table.add_column(Column("posts", "id", "INTEGER", is_primary=True))
    posts_table.add_column(Column("posts", "user_id", "INTEGER"))
    posts_table.add_column(
        ForeignKey("fk_user_id", "posts", ["user_id"], "users", ["id"])
    )
    posts_table.add_column(PrimaryKey("posts_pk", "posts", ["id"]))

    comments_table = Table("comments")
    comments_table.add_column(Column("comments", "id", "INTEGER", is_primary=True))
    comments_table.add_column(Column("comments", "post_id", "INTEGER"))
    comments_table.add_column(
        ForeignKey("fk_post_id", "comments", ["post_id"], "posts", ["id"])
    )
    comments_table.add_column(PrimaryKey("comments_pk", "comments", ["id"]))

    categories_table = Table("categories")
    categories_table.add_column(Column("categories", "id", "INTEGER", is_primary=True))
    categories_table.add_column(PrimaryKey("categories_pk", "categories", ["id"]))

    all_tables = [users_table, posts_table, comments_table, categories_table]

    # Test users_table children
    user_children = get_child_tables(users_table, all_tables)
    assert len(user_children) == 1
    assert user_children[0].name == "posts"

    # Test posts_table children
    post_children = get_child_tables(posts_table, all_tables)
    assert len(post_children) == 1
    assert post_children[0].name == "comments"

    # Test comments_table children (should have none)
    comment_children = get_child_tables(comments_table, all_tables)
    assert len(comment_children) == 0

    # Test categories_table children (should have none)
    category_children = get_child_tables(categories_table, all_tables)
    assert len(category_children) == 0

    # Test with empty table list
    assert get_child_tables(users_table, []) == []


# ---


def test_get_parent_tables():
    # Setup tables (same as get_child_tables for consistency)
    users_table = Table("users")
    users_table.add_column(Column("users", "id", "INTEGER", is_primary=True))
    users_table.add_column(PrimaryKey("users_pk", "users", ["id"]))

    posts_table = Table("posts")
    posts_table.add_column(Column("posts", "id", "INTEGER", is_primary=True))
    posts_table.add_column(Column("posts", "user_id", "INTEGER"))
    posts_table.add_column(
        ForeignKey("fk_user_id", "posts", ["user_id"], "users", ["id"])
    )
    posts_table.add_column(PrimaryKey("posts_pk", "posts", ["id"]))

    comments_table = Table("comments")
    comments_table.add_column(Column("comments", "id", "INTEGER", is_primary=True))
    comments_table.add_column(Column("comments", "post_id", "INTEGER"))
    comments_table.add_column(
        ForeignKey("fk_post_id", "comments", ["post_id"], "posts", ["id"])
    )
    comments_table.add_column(PrimaryKey("comments_pk", "comments", ["id"]))

    categories_table = Table("categories")
    categories_table.add_column(Column("categories", "id", "INTEGER", is_primary=True))
    categories_table.add_column(PrimaryKey("categories_pk", "categories", ["id"]))

    all_tables = [users_table, posts_table, comments_table, categories_table]

    # Test comments_table parents
    comment_parents = get_parent_tables(comments_table, all_tables)
    assert len(comment_parents) == 1
    assert comment_parents[0].name == "posts"

    # Test posts_table parents
    post_parents = get_parent_tables(posts_table, all_tables)
    assert len(post_parents) == 1
    assert post_parents[0].name == "users"

    # Test users_table parents (should have none)
    user_parents = get_parent_tables(users_table, all_tables)
    assert len(user_parents) == 0

    # Test categories_table parents (should have none)
    category_parents = get_parent_tables(categories_table, all_tables)
    assert len(category_parents) == 0

    # Test with empty foreign keys
    no_fk_table = Table("no_fk_table")
    assert get_parent_tables(no_fk_table, all_tables) == []

    # Test with empty table list
    assert get_parent_tables(comments_table, []) == []


# ---


@pytest.mark.parametrize(
    "default_value, expected_result",
    [
        ("CURRENT_TIMESTAMP", True),
        ("NOW()", True),
        ("GETDATE()", True),
        ("current_timestamp", True),  # Case insensitivity
        ("now()", True),
        ("some_other_function()", False),
        ("123", False),
        (None, False),
        ("DEFAULT", False),
    ],
)
def test_should_use_server_default(default_value, expected_result):
    col = Column("test", "timestamp_col", "TIMESTAMPTZ", default_value=default_value)
    assert should_use_server_default(col) == expected_result


# ---


def test_get_pk_names_for_repr():
    table_single_pk = Table("users")
    table_single_pk.add_column(Column("users", "user_id", "INTEGER", is_primary=True))
    table_single_pk.primary_key = PrimaryKey("pk", "users", ["user_id"])
    assert get_pk_names_for_repr(table_single_pk) == "user_id={self.user_id}"

    table_composite_pk = Table("order_items")
    table_composite_pk.add_column(
        Column("order_items", "order_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.add_column(
        Column("order_items", "product_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.primary_key = PrimaryKey(
        "pk", "order_items", ["order_id", "product_id"]
    )
    assert (
        get_pk_names_for_repr(table_composite_pk)
        == "order_id={self.order_id}, product_id={self.product_id}"
    )

    table_no_pk = Table("logs")
    assert get_pk_names_for_repr(table_no_pk) == "id=None"


# ---


@pytest.mark.parametrize(
    "data_type, column_name, expected_default_value",
    [
        ("VARCHAR", "user_name", "'user_name_test'"),
        ("TEXT", "description", "'description_test'"),
        ("UUID", "record_uuid", "'record_uuid_test'"),
        ("INTEGER", "count", 1),
        ("BIGINT", "total_sum", 1),
        ("BOOLEAN", "is_active", "True"),
        ("FLOAT", "price", 1.0),
        ("DECIMAL", "amount", 1.0),
        ("DATE", "event_date", "'2024-01-01'"),
        ("TIMESTAMP", "created_at", "'2024-01-01T12:00:00Z'"),
        ("BYTEA", "image_data", "'test_bytes'"),
        ("UNKNOWN", "unknown_col", "'default_value'"),  # Fallback
    ],
)
def test_get_default_value_for_type(data_type, column_name, expected_default_value):
    col = Column("test_table", column_name, data_type)
    assert get_default_value_for_type(col) == expected_default_value


# ---


def test_get_pk_test_url_str():
    table_single_pk = Table("users")
    table_single_pk.add_column(Column("users", "user_id", "INTEGER", is_primary=True))
    table_single_pk.primary_key = PrimaryKey("pk", "users", ["user_id"])
    assert get_pk_test_url_str(table_single_pk) == 'str(data["user_id"])'

    table_composite_pk = Table("order_items")
    table_composite_pk.add_column(
        Column("order_items", "order_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.add_column(
        Column("order_items", "product_id", "INTEGER", is_primary=True)
    )
    table_composite_pk.primary_key = PrimaryKey(
        "pk", "order_items", ["order_id", "product_id"]
    )
    assert (
        get_pk_test_url_str(table_composite_pk)
        == 'str(data["order_id"]) + "/" + str(data["product_id"])'
    )

    table_no_pk = Table("logs")
    assert get_pk_test_url_str(table_no_pk) == ""
