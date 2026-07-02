import os
import json
import pytest
import tempfile
import sqlite3

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture(scope="function")
def temp_db():
    """Fixture that initializes a temporary seeded database and deletes it after test completes."""
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize schema and seed data
    create_database(temp_path)
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def adapter(temp_db):
    """Fixture that returns a SQLiteAdapter instance connected to the temporary DB."""
    return SQLiteAdapter(temp_db)


def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert "students" in tables
    assert "courses" in tables
    assert "enrollments" in tables
    assert len(tables) == 3


def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    assert "id" in schema
    assert "name" in schema
    assert "cohort" in schema
    assert "score" in schema
    assert schema["score"] == "REAL"


def test_get_table_schema_invalid(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.get_table_schema("non_existent")
    assert "does not exist in the database" in str(excinfo.value)


def test_search_all(adapter):
    results = adapter.search("students")
    assert len(results) == 5
    assert results[0]["name"] == "Alice"


def test_search_filters_equality(adapter):
    results = adapter.search("students", filters={"cohort": "A1"})
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert names == {"Alice", "Bob"}


def test_search_filters_operator_greater_than(adapter):
    results = adapter.search("students", filters={"score": {"op": ">", "val": 85.0}})
    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"Alice", "Charlie", "Eve"}


def test_search_filters_operator_in(adapter):
    results = adapter.search("students", filters={"id": {"op": "in", "val": [1, 3]}})
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert names == {"Alice", "Charlie"}


def test_search_projection(adapter):
    results = adapter.search("students", columns=["name", "cohort"])
    assert len(results) > 0
    assert "name" in results[0]
    assert "cohort" in results[0]
    assert "id" not in results[0]
    assert "score" not in results[0]


def test_search_order_by(adapter):
    # Ascending
    results_asc = adapter.search("students", order_by="score", descending=False)
    # Descending
    results_desc = adapter.search("students", order_by="score", descending=True)
    
    assert results_asc[0]["score"] < results_asc[-1]["score"]
    assert results_desc[0]["score"] > results_desc[-1]["score"]
    assert results_desc[0]["name"] == "Eve"  # Eve has 99.0


def test_search_pagination(adapter):
    # Limit 2
    results = adapter.search("students", limit=2, offset=0, order_by="id")
    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"

    # Offset 2
    results_page2 = adapter.search("students", limit=2, offset=2, order_by="id")
    assert len(results_page2) == 2
    assert results_page2[0]["name"] == "Charlie"
    assert results_page2[1]["name"] == "David"


def test_insert_student(adapter):
    initial_count = len(adapter.search("students"))
    new_student = {"name": "Grace", "cohort": "A1", "score": 92.0}
    inserted = adapter.insert("students", new_student)
    
    assert inserted["id"] is not None
    assert inserted["name"] == "Grace"
    assert inserted["cohort"] == "A1"
    assert inserted["score"] == 92.0
    
    assert len(adapter.search("students")) == initial_count + 1


def test_insert_empty_fails(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.insert("students", {})
    assert "Insert values cannot be empty" in str(excinfo.value)


def test_insert_invalid_column_fails(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.insert("students", {"name": "Grace", "wrong_column": "value"})
    assert "Invalid column" in str(excinfo.value)


def test_aggregate_count(adapter):
    results = adapter.aggregate("students", metric="count")
    assert len(results) == 1
    assert results[0]["value"] == 5


def test_aggregate_avg(adapter):
    results = adapter.aggregate("students", metric="avg", column="score")
    assert len(results) == 1
    # Average of 95, 82.5, 88, 71, 99 is 87.1
    assert abs(results[0]["value"] - 87.1) < 0.01


def test_aggregate_group_by(adapter):
    results = adapter.aggregate("students", metric="avg", column="score", group_by="cohort")
    assert len(results) == 3
    
    cohort_avgs = {row["cohort"]: row["value"] for row in results}
    # Cohort A1: Alice (95) and Bob (82.5) -> avg = 88.75
    assert abs(cohort_avgs["A1"] - 88.75) < 0.01
    # Cohort B2: Charlie (88) and David (71) -> avg = 79.5
    assert abs(cohort_avgs["B2"] - 79.5) < 0.01
    # Cohort C3: Eve (99) -> avg = 99.0
    assert abs(cohort_avgs["C3"] - 99.0) < 0.01


def test_aggregate_invalid_metric(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.aggregate("students", metric="invalid_metric", column="score")
    assert "Unsupported aggregate metric" in str(excinfo.value)


def test_aggregate_missing_column_for_avg(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.aggregate("students", metric="avg", column=None)
    assert "requires a specific column" in str(excinfo.value)


def test_validation_invalid_table(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.search("unknown_table")
    assert "Invalid table" in str(excinfo.value)


def test_validation_invalid_column(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.search("students", columns=["invalid_col"])
    assert "Invalid column" in str(excinfo.value)


def test_validation_invalid_filter_column(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.search("students", filters={"invalid_filter_col": "val"})
    assert "Invalid filter column" in str(excinfo.value)


def test_validation_unsupported_operator(adapter):
    with pytest.raises(ValidationError) as excinfo:
        adapter.search("students", filters={"score": {"op": "BETWEEN", "val": [80, 90]}})
    assert "Unsupported filter operator" in str(excinfo.value)
