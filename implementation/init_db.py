import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    instructor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER,
    course_id INTEGER,
    grade TEXT,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
-- Insert students
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES (1, 'Alice', 'A1', 95.0);
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES (2, 'Bob', 'A1', 82.5);
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES (3, 'Charlie', 'B2', 88.0);
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES (4, 'David', 'B2', 71.0);
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES (5, 'Eve', 'C3', 99.0);

-- Insert courses
INSERT OR IGNORE INTO courses (id, name, instructor) VALUES (1, 'Math 101', 'Dr. Smith');
INSERT OR IGNORE INTO courses (id, name, instructor) VALUES (2, 'Physics 201', 'Dr. Jones');
INSERT OR IGNORE INTO courses (id, name, instructor) VALUES (3, 'History 101', 'Prof. Davis');

-- Insert enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (1, 1, 'A');
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (1, 2, 'A');
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (2, 1, 'B');
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (3, 2, 'B');
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (4, 3, 'C');
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade) VALUES (5, 1, 'A');
"""


def create_database(db_path: str = None) -> str:
    """
    Initializes the SQLite database with the tables and seed data.
    Returns the path to the database.
    """
    if db_path is None:
        # Default to implementation/sqlite_lab.db relative to this file
        dir_path = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(dir_path, "sqlite_lab.db")

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # Enable foreign keys support
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Execute Schema
        cursor.executescript(SCHEMA_SQL)
        
        # Execute Seed Data
        cursor.executescript(SEED_SQL)
        
        conn.commit()
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"Database successfully created and seeded at: {path}")
