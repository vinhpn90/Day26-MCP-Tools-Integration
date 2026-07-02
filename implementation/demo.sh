#!/bin/bash

# Clear terminal screen
clear

echo "=============================================================="
echo "          DEMO: DATABASE MCP SERVER WITH SQLITE               "
echo "=============================================================="
echo "Starting demo steps..."
sleep 2

echo -e "\n--------------------------------------------------------------"
echo "STEP 1: Initialize and Seed SQLite Database"
echo "--------------------------------------------------------------"
echo "Running: python3 implementation/init_db.py"
sleep 1
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 implementation/init_db.py
sleep 3

echo -e "\n--------------------------------------------------------------"
echo "STEP 2: Run Automated Pytest Suite (22 test cases)"
echo "--------------------------------------------------------------"
echo "Running: python3 -m pytest implementation/tests/test_server.py -v"
sleep 1
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest implementation/tests/test_server.py -v
sleep 4

echo -e "\n--------------------------------------------------------------"
echo "STEP 3: Run Programmatic Validation & Smoke Tests"
echo "--------------------------------------------------------------"
echo "Running: python3 implementation/verify_server.py"
sleep 1
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 implementation/verify_server.py
sleep 3

echo -e "\n=============================================================="
echo "                  DEMO COMPLETED SUCCESSFULLY!                "
echo "=============================================================="
