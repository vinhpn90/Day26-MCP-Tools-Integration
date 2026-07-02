import sqlite3
import os
from typing import List, Dict, Any, Optional, Union

class ValidationError(Exception):
    """Exception raised for safety and database input validation errors."""
    pass


class SQLiteAdapter:
    """
    SQLite adapter responsible for:
    - Connecting to the SQLite database
    - Inspecting schemas dynamically
    - Validating inputs (tables, columns, operators, metrics) to prevent SQL injection
    - Safely building and executing parameterized queries
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Pre-cache schema information for fast validation (optional, we query PRAGMA dynamically or cache)
        self._cached_schema: Dict[str, Dict[str, str]] = {}

    def connect(self) -> sqlite3.Connection:
        """Returns a connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def list_tables(self) -> List[str]:
        """Queries sqlite_master to return user tables."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            return tables

    def get_table_schema(self, table: str) -> Dict[str, str]:
        """Runs PRAGMA table_info to return a dict of {column_name: data_type}."""
        # Check table name first
        tables = self.list_tables()
        if table not in tables:
            raise ValidationError(f"Table '{table}' does not exist in the database.")

        with self.connect() as conn:
            cursor = conn.cursor()
            # PRAGMA statements cannot be parameterized, but we already validated the table name is in list_tables()
            cursor.execute(f"PRAGMA table_info({table});")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}
            return columns

    def get_primary_key(self, table: str) -> Optional[str]:
        """Returns the primary key column name for a table."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table});")
            for row in cursor.fetchall():
                if row["pk"] == 1:
                    return row["name"]
        return None

    def validate_table(self, table: str) -> None:
        """Validates that a table exists."""
        if table not in self.list_tables():
            raise ValidationError(f"Invalid table: '{table}'. Only existing user tables are allowed.")

    def validate_columns(self, table: str, columns: List[str]) -> None:
        """Validates that a list of columns exist in a table."""
        schema = self.get_table_schema(table)
        for col in columns:
            if col not in schema:
                raise ValidationError(f"Invalid column: '{col}' for table '{table}'. Valid columns are: {list(schema.keys())}")

    def validate_filters(self, table: str, filters: Optional[Dict[str, Any]]) -> None:
        """
        Validates filter keys (columns) and operator structures.
        Supports:
        - Simple equality: {"column": "value"}
        - Extended operators: {"column": {"op": ">", "val": 10}} or {"column": {"operator": ">", "value": 10}}
        Supported operators: =, !=, >, <, >=, <=, like, in
        """
        if not filters:
            return

        schema = self.get_table_schema(table)
        allowed_operators = {"=", "!=", ">", "<", ">=", "<=", "like", "in"}

        for col, val in filters.items():
            if col not in schema:
                raise ValidationError(f"Invalid filter column: '{col}' for table '{table}'.")

            if isinstance(val, dict):
                # Extended operator structure
                # Check for either 'op' or 'operator' keys
                op = val.get("op") or val.get("operator")
                # Check for either 'val' or 'value' keys
                value_key_exists = "val" in val or "value" in val

                if not op or not value_key_exists:
                    raise ValidationError(
                        f"Extended filter for '{col}' must specify both an operator ('op' or 'operator') and a value ('val' or 'value')."
                    )

                if str(op).lower() not in allowed_operators:
                    raise ValidationError(
                        f"Unsupported filter operator '{op}' for column '{col}'. Supported operators: {list(allowed_operators)}"
                    )
                
                # Check list/tuple for IN operator
                if str(op).lower() == "in":
                    inner_val = val.get("val") if "val" in val else val.get("value")
                    if not isinstance(inner_val, (list, tuple)):
                        raise ValidationError(
                            f"Value for 'IN' operator on column '{col}' must be a list or tuple."
                        )

    def validate_metric(self, metric: str) -> None:
        """Validates that aggregate metric is supported."""
        allowed_metrics = {"count", "avg", "sum", "min", "max"}
        if metric.lower() not in allowed_metrics:
            raise ValidationError(
                f"Unsupported aggregate metric '{metric}'. Allowed: {list(allowed_metrics)}"
            )

    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> tuple[str, List[Any]]:
        """
        Helper to construct WHERE clause and list of parameters safely.
        """
        if not filters:
            return "", []

        clauses = []
        params = []

        for col, val in filters.items():
            if isinstance(val, dict):
                op = (val.get("op") or val.get("operator")).upper()
                inner_val = val.get("val") if "val" in val else val.get("value")
                
                if op == "IN":
                    placeholders = ", ".join(["?"] * len(inner_val))
                    clauses.append(f"{col} IN ({placeholders})")
                    params.extend(inner_val)
                else:
                    clauses.append(f"{col} {op} ?")
                    params.append(inner_val)
            else:
                clauses.append(f"{col} = ?")
                params.append(val)

        return " WHERE " + " AND ".join(clauses), params

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Performs a query on a table with filters, projection, ordering, and pagination.
        All table, column, and operator inputs are validated against whitelist.
        Values are passed using query parameters.
        """
        self.validate_table(table)

        # Handle projection
        if not columns:
            # Query all columns in the schema
            schema = self.get_table_schema(table)
            columns = list(schema.keys())
        else:
            self.validate_columns(table, columns)

        # Handle filters
        self.validate_filters(table, filters)
        where_clause, params = self._build_where_clause(filters)

        # Build SQL parts safely
        select_cols = ", ".join(columns)
        sql = f"SELECT {select_cols} FROM {table}{where_clause}"

        # Handle ORDER BY
        if order_by:
            self.validate_columns(table, [order_by])
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY {order_by} {direction}"

        # Handle Pagination (strictly cast to int, then we can append safely or bind)
        try:
            limit = int(limit)
            offset = int(offset)
        except ValueError:
            raise ValidationError("Limit and offset must be integers.")

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def insert(self, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a row into a table.
        Validates table, keys, and values.
        Returns the inserted record.
        """
        self.validate_table(table)

        if not values or not isinstance(values, dict):
            raise ValidationError("Insert values cannot be empty and must be a dictionary.")

        # Validate that all keys correspond to actual columns
        cols = list(values.keys())
        self.validate_columns(table, cols)

        col_names = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        params = list(values.values())

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            last_id = cursor.lastrowid

        # Retrieve the inserted row
        pk = self.get_primary_key(table)
        if pk and last_id is not None:
            # Table has a single auto-incrementing primary key
            results = self.search(table, filters={pk: last_id}, limit=1)
            if results:
                return results[0]

        # Fallback if no single auto-increment primary key (e.g. enrollments)
        # Search by matching all values inserted
        results = self.search(table, filters=values, limit=1)
        if results:
            return results[0]
        
        return values

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs aggregate analysis on the database.
        Metric must be in COUNT, AVG, SUM, MIN, MAX.
        """
        self.validate_table(table)
        self.validate_metric(metric)

        metric = metric.upper()
        
        # Column validation
        if not column or column == "*":
            if metric != "COUNT":
                raise ValidationError(f"Metric '{metric}' requires a specific column, cannot aggregate '*' or empty column.")
            col_sql = "*"
        else:
            self.validate_columns(table, [column])
            col_sql = column

        # Group by validation
        if group_by:
            self.validate_columns(table, [group_by])

        # Filter validation
        self.validate_filters(table, filters)
        where_clause, params = self._build_where_clause(filters)

        # Build SQL
        if group_by:
            sql = f"SELECT {group_by}, {metric}({col_sql}) AS value FROM {table}{where_clause} GROUP BY {group_by}"
        else:
            sql = f"SELECT {metric}({col_sql}) AS value FROM {table}{where_clause}"

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
