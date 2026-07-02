# Database MCP Server with FastMCP and SQLite

This project is a Model Context Protocol (MCP) server that connects to a SQLite database. It is built using the `FastMCP` framework in Python. The server exposes tools to search, insert, and aggregate database data, alongside resources exposing database schemas, and includes safety-critical input validation to prevent SQL injection.

## Project Structure

- **[README.md](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/README.md)**: Setup, client configuration, and usage guide (this file).
- **[Rubric.md](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/Rubric.md)**: Grading rubric for the lab.
- **[Tips.md](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/Tips.md)**: Setup tips and tricks for client integrations.
- **[pseudocode/](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/tree/main/pseudocode)**: Starter pseudocode directory (reference).
- **implementation/**: The complete codebase:
  - **[db.py](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/implementation/db.py)**: `SQLiteAdapter` with SQL-safe validation and database operations.
  - **[init_db.py](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/implementation/init_db.py)**: Database schema definitions and seed data script.
  - **[mcp_server.py](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/implementation/mcp_server.py)**: FastMCP server wrapping the adapter.
  - **sqlite_lab.db**: SQLite database file (auto-generated).
  - **[verify_server.py](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/implementation/verify_server.py)**: Smoke tests script for programmatically testing features.
  - **tests/**:
    - **[test_server.py](https://github.com/vinhpn90/Day26-MCP-Tools-Integration/blob/main/implementation/tests/test_server.py)**: Automated unit test suite using Pytest.

## Database Schema & Seed Data

The database consists of three related tables:
1. `students`: `id` (INTEGER PRIMARY KEY), `name` (TEXT), `cohort` (TEXT), `score` (REAL)
2. `courses`: `id` (INTEGER PRIMARY KEY), `name` (TEXT), `instructor` (TEXT)
3. `enrollments`: `student_id` (INTEGER FK), `course_id` (INTEGER FK), `grade` (TEXT), PK is `(student_id, course_id)`

Seed data includes:
- Students: Alice, Bob, Charlie, David, Eve
- Courses: Math 101, Physics 201, History 101
- Enrollments: Multi-table student enrollments with letter grades (A, B, C)

---

## Getting Started

### 1. Prerequisites
Ensure you have Python 3.11 installed, containing `fastmcp`, `mcp`, and `pytest`.

To check and install dependencies:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/pip install fastmcp mcp pydantic pytest
```

### 2. Initialize Database
Create and seed the SQLite database file (`implementation/sqlite_lab.db`):
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 implementation/init_db.py
```

### 3. Run Automated Tests
Execute the unit test suite to verify correct behavior:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest implementation/tests/test_server.py -v
```

### 4. Run Smoke Verification Tests
Run the programmatic verification suite covering tool discoverability, inputs, outputs, and validation rules:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 implementation/verify_server.py
```

---

## Exposed MCP Features

### Tools

1. **`search`**
   - **Description**: Search rows in a database table with projection, filtering, sorting, and pagination.
   - **Arguments**:
     - `table` (string, required): Table name (`students`, `courses`, `enrollments`).
     - `filters` (object, optional): Column name mapping to a value or query operator structure, e.g. `{"cohort": "A1"}` or `{"score": {"op": ">", "val": 85.0}}`. Supported operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`.
     - `columns` (array of strings, optional): Subset of columns to retrieve.
     - `limit` (integer, default `20`): Pagination size limit.
     - `offset` (integer, default `0`): Pagination offset.
     - `order_by` (string, optional): Column to sort results by.
     - `descending` (boolean, default `false`): Ascending or descending order.

2. **`insert`**
   - **Description**: Insert a new row into a database table.
   - **Arguments**:
     - `table` (string, required): Table name to insert into.
     - `values` (object, required): Dict of column keys and values to insert, e.g. `{"name": "Frank", "cohort": "C3", "score": 88.5}`.

3. **`aggregate`**
   - **Description**: Calculate aggregate metrics on a table (COUNT, AVG, SUM, MIN, MAX).
   - **Arguments**:
     - `table` (string, required): Table name.
     - `metric` (string, required): Function to use (`count`, `avg`, `sum`, `min`, `max`).
     - `column` (string, optional): Column to aggregate. Optional only for `count`; required for other metrics.
     - `filters` (object, optional): Query filters to restrict aggregation scope.
     - `group_by` (string, optional): Column to group results by.

### Resources

1. **`schema://database`**
   - Returns the full database schema definitions (all user tables and their column metadata) as JSON.

2. **`schema://table/{table_name}`**
   - Returns the schema definitions for the requested `table_name` as JSON.

---

## Safety and Error Handling

Input validation is enforced strictly before translating inputs into SQL to avoid SQL injection vulnerability:
1. **Table Whitelisting**: The requested table name is verified against user tables in `sqlite_master`.
2. **Column Whitelisting**: Projected columns, sorting columns, grouping columns, and filter columns are matched against the table's schema.
3. **Operator Validation**: Filter operator strings are restricted to `=, !=, >, <, >=, <=, LIKE, IN`.
4. **Parameterized Queries**: All user-provided filter values and insertion values are bound dynamically using `?` placeholders (standard safe SQL pattern).

If validation fails, a `ValidationError` is raised, returning an error response (e.g. `{"status": "error", "message": "<reason>"}`).

---

## MCP Client Configuration

Below are configurations using absolute paths for this specific workspace.

### 1. Claude Code
Add to your project-local `.mcp.json` or global configuration:
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "args": ["/Users/ngocvinh/ownCloud/HocTap/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"]
    }
  }
}
```

### 2. Gemini CLI
Register the server in Gemini CLI:
```bash
gemini mcp add sqlite-lab /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /Users/ngocvinh/ownCloud/HocTap/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
```
Verify the connection and query:
```bash
gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Show the schema for database and search for students in cohort A1."
```

### 3. Antigravity (IDE Integration)
Add to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "args": ["/Users/ngocvinh/ownCloud/HocTap/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"],
      "cwd": "/Users/ngocvinh/ownCloud/HocTap/Day26-Track3-MCP-tool-integration/implementation"
    }
  }
}
```

### 4. MCP Inspector (Debugging Tool)
Start the MCP Inspector to interactively debug tools and resources:
```bash
npx @modelcontextprotocol/inspector /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /Users/ngocvinh/ownCloud/HocTap/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py
```
This will launch a web interface at `http://localhost:5173` (or next free port) allowing you to inspect tool schemas and execute calls.