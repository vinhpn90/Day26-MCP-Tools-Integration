import os
import json
import sys
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Robust imports to support running from root or implementation dir
try:
    from implementation.db import SQLiteAdapter, ValidationError
    from implementation.init_db import create_database
except ImportError:
    from db import SQLiteAdapter, ValidationError
    from init_db import create_database

# Create the server object
mcp = FastMCP("SQLite Lab MCP Server")

# Determine DB path and initialize if not exists
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR_PATH, "sqlite_lab.db")

if not os.path.exists(DB_PATH):
    # Dynamically create and seed the database if it doesn't exist
    create_database(DB_PATH)

adapter = SQLiteAdapter(DB_PATH)


@mcp.tool(name="search")
def search(
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    columns: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False,
) -> str:
    """
    Search rows in a database table with projection, filtering, sorting, and pagination.

    Args:
        table: Name of the table to search (e.g., 'students', 'courses', 'enrollments').
        filters: Optional dict mapping column names to values for equality filtering, or to dicts with 'op' and 'val' / 'operator' and 'value'.
                 Supported operators: '=', '!=', '>', '<', '>=', '<=', 'like', 'in'.
                 Examples: {"cohort": "A1"} or {"score": {"op": ">", "val": 80}} or {"id": {"op": "in", "val": [1, 2]}}.
        columns: Optional list of column names to retrieve. If None, retrieves all columns.
        limit: Maximum number of rows to return (default 20).
        offset: Number of rows to skip (default 0).
        order_by: Optional column name to sort the results by.
        descending: Set to True to sort in descending order, False for ascending.
    """
    try:
        results = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
        return json.dumps({"status": "success", "data": results}, indent=2)
    except ValidationError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool(name="insert")
def insert(table: str, values: Dict[str, Any]) -> str:
    """
    Insert a new row into a database table.

    Args:
        table: Name of the table to insert into (e.g., 'students', 'courses', 'enrollments').
        values: A dictionary of column names and their corresponding values.
                Examples: {"name": "Frank", "cohort": "B2", "score": 85.5} or {"student_id": 1, "course_id": 3, "grade": "B"}.
    """
    try:
        inserted = adapter.insert(table=table, values=values)
        return json.dumps({"status": "success", "data": inserted}, indent=2)
    except ValidationError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    group_by: Optional[str] = None,
) -> str:
    """
    Perform aggregate queries (COUNT, AVG, SUM, MIN, MAX) on a table.

    Args:
        table: Name of the table (e.g., 'students', 'courses', 'enrollments').
        metric: Aggregate function to run (e.g., 'count', 'avg', 'sum', 'min', 'max').
        column: Column to aggregate (required for avg, sum, min, max; optional for count).
        filters: Optional dict of search filters to apply before aggregating.
        group_by: Optional column name to group the aggregate results by.
    """
    try:
        results = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
        return json.dumps({"status": "success", "data": results}, indent=2)
    except ValidationError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"}, indent=2)


@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Retrieve the schema details for all tables in the database.
    """
    try:
        tables = adapter.list_tables()
        schema = {}
        for t in tables:
            schema[t] = adapter.get_table_schema(t)
        return json.dumps({"status": "success", "schema": schema}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to retrieve database schema: {str(e)}"}, indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Retrieve the schema details for a specific table in the database.

    Args:
        table_name: Name of the table to inspect.
    """
    try:
        schema = adapter.get_table_schema(table_name)
        return json.dumps({"status": "success", "table": table_name, "schema": schema}, indent=2)
    except ValidationError as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"}, indent=2)


if __name__ == "__main__":
    # run stdio transport by default (standard for MCP integration)
    mcp.run()
