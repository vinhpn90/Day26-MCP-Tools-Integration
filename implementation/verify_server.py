import json
import sys
import os

try:
    from implementation.mcp_server import (
        search,
        insert,
        aggregate,
        database_schema,
        table_schema,
    )
except ImportError:
    from mcp_server import (
        search,
        insert,
        aggregate,
        database_schema,
        table_schema,
    )


def print_test_header(title: str):
    print("\n" + "=" * 60)
    print(f" TEST: {title}")
    print("=" * 60)


def assert_status(result_str: str, expected_status: str):
    data = json.loads(result_str)
    status = data.get("status")
    if status == expected_status:
        print(f" [PASS] Status is '{status}' as expected.")
    else:
        print(f" [FAIL] Expected status '{expected_status}', got '{status}'.")
        print(f" Details: {result_str}")
        sys.exit(1)
    return data


def run_tests():
    print("Starting verification tests for SQLite Lab MCP Server...")

    # 1. Test database schema resource
    print_test_header("Full Database Schema Resource")
    res = database_schema()
    data = assert_status(res, "success")
    print(json.dumps(data.get("schema"), indent=2))

    # 2. Test table schema resource for 'students'
    print_test_header("Table Schema Resource: students")
    res = table_schema("students")
    data = assert_status(res, "success")
    print(json.dumps(data.get("schema"), indent=2))

    # 3. Test search students in cohort A1
    print_test_header("Search Students in Cohort A1")
    res = search(table="students", filters={"cohort": "A1"})
    data = assert_status(res, "success")
    print(f"Found {len(data.get('data'))} students in A1:")
    for row in data.get("data"):
        print(f" - {row['name']} (Score: {row['score']})")

    # 4. Test search using extended filter (Score > 85)
    print_test_header("Search Students with Score > 85")
    res = search(table="students", filters={"score": {"op": ">", "val": 85.0}})
    data = assert_status(res, "success")
    for row in data.get("data"):
        print(f" - {row['name']} (Cohort: {row['cohort']}, Score: {row['score']})")

    # 5. Test search with sorting and limit/offset
    print_test_header("Search Courses Sorted by Name (DESC), Limit 2")
    res = search(table="courses", order_by="name", descending=True, limit=2)
    data = assert_status(res, "success")
    for row in data.get("data"):
        print(f" - {row['name']} (Instructor: {row['instructor']})")

    # 6. Test insert a new student
    print_test_header("Insert New Student")
    res = insert(table="students", values={"name": "Frank", "cohort": "C3", "score": 88.5})
    data = assert_status(res, "success")
    inserted_student = data.get("data")
    print(f"Inserted payload: {inserted_student}")
    # Verify insert actually occurred by searching
    verify_res = search(table="students", filters={"name": "Frank"})
    verify_data = json.loads(verify_res)
    if len(verify_data.get("data")) > 0:
        print(" [PASS] Verification search successfully retrieved inserted student.")
    else:
        print(" [FAIL] Verification search could not retrieve inserted student.")
        sys.exit(1)

    # 7. Test aggregate average score by cohort
    print_test_header("Aggregate: Average Score Grouped by Cohort")
    res = aggregate(table="students", metric="avg", column="score", group_by="cohort")
    data = assert_status(res, "success")
    for row in data.get("data"):
        print(f" Cohort {row['cohort']}: Avg Score = {row['value']:.2f}")

    # 8. Test aggregate: count rows in enrollments
    print_test_header("Aggregate: Count rows in enrollments")
    res = aggregate(table="enrollments", metric="count")
    data = assert_status(res, "success")
    print(f"Total enrollments: {data.get('data')[0]['value']}")

    # 9. Test safety validation: invalid table
    print_test_header("Invalid Table Name rejection (Expected Failure)")
    res = search(table="non_existent_table")
    data = assert_status(res, "error")
    print(f"Error Message: {data.get('message')}")

    # 10. Test safety validation: invalid column
    print_test_header("Invalid Column Name rejection (Expected Failure)")
    res = search(table="students", columns=["id", "fake_column"])
    data = assert_status(res, "error")
    print(f"Error Message: {data.get('message')}")

    # 11. Test safety validation: unsupported filter operator
    print_test_header("Unsupported Operator rejection (Expected Failure)")
    res = search(table="students", filters={"score": {"op": "BETWEEN", "val": [80, 90]}})
    data = assert_status(res, "error")
    print(f"Error Message: {data.get('message')}")

    # 12. Test safety validation: empty inserts
    print_test_header("Empty Insert rejection (Expected Failure)")
    res = insert(table="students", values={})
    data = assert_status(res, "error")
    print(f"Error Message: {data.get('message')}")

    print("\n" + "=" * 60)
    print(" ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
