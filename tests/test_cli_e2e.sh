#!/bin/bash
# test_cli_e2e.sh - End-to-end tests for VaccineGraph CLI

# Enforce script runs from project root
cd "$(dirname "$0")/.."

source venv/bin/activate
mkdir -p test_output

echo "Testing doses..."
./vaccinegraph --chart doses -o test_output/doses.png || { echo "ERROR: doses"; exit 1; }

echo "Testing people..."
./vaccinegraph --chart people -o test_output/people.png || { echo "ERROR: people"; exit 1; }

echo "Testing timeline..."
./vaccinegraph --chart timeline -o test_output/timeline.png || { echo "ERROR: timeline"; exit 1; }

echo "Testing total_yearly..."
./vaccinegraph --chart total_yearly -o test_output/total_yearly.png || { echo "ERROR: total_yearly"; exit 1; }

echo "Testing monthly..."
./vaccinegraph --chart monthly -o test_output/monthly.png || { echo "ERROR: monthly"; exit 1; }

echo "Testing profile..."
./vaccinegraph --chart profile -o test_output/profile.png || { echo "ERROR: profile"; exit 1; }

echo "Testing complications..."
./vaccinegraph --chart complications -o test_output/complications.png || { echo "ERROR: complications"; exit 1; }

echo "Testing infographic..."
./vaccinegraph --chart infographic --search HPV -o test_output/infographic.png || { echo "ERROR: infographic"; exit 1; }

echo "Testing combinations (monthly + search + state)..."
./vaccinegraph --chart monthly --search HPV --state RS -o test_output/monthly_rs.png || { echo "ERROR: monthly combination"; exit 1; }

echo "All tests passed successfully!"

echo "Testing list-vaccines..."
./vaccinegraph --list-vaccines > /dev/null || { echo "ERROR: list-vaccines"; exit 1; }

echo "Testing invalid arguments..."
./vaccinegraph --clean 2>/dev/null && { echo "ERROR: invalid argument was accepted"; exit 1; }

echo "Basic tests passed successfully!"
