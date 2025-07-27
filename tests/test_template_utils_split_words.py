import pytest
import re
from wukong.commands.template_utils import split_words


# Pytest unit tests for the split_words function


def test_single_word_lowercase():
    """Test with a single lowercase word."""
    assert split_words("hello") == ["hello"]


def test_single_word_uppercase():
    """Test with a single uppercase word."""
    assert split_words("HELLO") == ["HELLO"]


def test_camel_case():
    """Test with a camelCase string."""
    assert split_words("helloWorld") == ["hello", "World"]


def test_pascal_case():
    """Test with a PascalCase string."""
    assert split_words("HelloWorld") == ["Hello", "World"]


def test_kebab_case():
    """Test with a kebab-case string (special character)."""
    assert split_words("hello-world") == ["hello", "_", "world"]


def test_snake_case():
    """Test with a snake_case string (special character)."""
    assert split_words("hello_world") == ["hello", "_", "world"]


def test_mixed_delimiters():
    """Test with a mix of camelCase and special characters."""
    assert split_words("firstName_lastName-emailAddress") == [
        "first",
        "Name",
        "_",
        "last",
        "Name",
        "_",
        "email",
        "Address",
    ]


def test_empty_string():
    """Test with an empty string."""
    assert split_words("") == []


def test_string_with_only_special_characters():
    """Test with a string consisting only of special characters."""
    assert split_words("---") == []


def test_string_with_leading_special_character():
    """Test with a string starting with a special character."""
    assert split_words("-hello") == ["hello"]


def test_string_with_trailing_special_character():
    """Test with a string ending with a special character."""
    assert split_words("hello-") == ["hello"]


def test_string_with_numbers():
    """Test with a string containing numbers."""
    assert split_words("version1_0") == ["version1", "_", "0"]


def test_acronyms():
    """Test with consecutive uppercase letters (acronyms)."""
    # The original logic splits each uppercase letter individually.
    assert split_words("HTTPResponse") == ["HTTP", "Response"]


def test_multiple_special_chars_together():
    """Test with multiple consecutive special characters."""
    assert split_words("item__id") == ["item", "_", "_", "id"]


def test_leading_uppercase():
    """Test with a string starting with an uppercase letter."""
    assert split_words("Item") == ["Item"]


def test_trailing_number():
    """Test with a string ending with a number."""
    assert split_words("data2") == ["data2"]


def test_mixed_case_and_numbers_and_symbols():
    """Test a complex string with various elements."""
    assert split_words("User_ID_123-ProfileName") == [
        "User",
        "_",
        "ID",
        "_",
        "123",
        "_",
        "Profile",
        "Name",
    ]
