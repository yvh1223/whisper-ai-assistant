#!/usr/bin/env python3
"""Test script for task parsing - verifies GPT and fallback parsers work"""

import sys
sys.path.insert(0, 'src')

from openai_client import OpenAIClient
from task_manager import TaskManager

print("=" * 60)
print("Task Parsing Test")
print("=" * 60)

# Initialize clients
openai_client = OpenAIClient()
task_manager = TaskManager(openai_client=openai_client)

print(f"\nOpenAI available: {openai_client.is_available()}")
if openai_client.is_available():
    print(f"Task model: {openai_client.task_model}")

# Test cases
test_cases = [
    "task add buy milk tomorrow",
    "task add meeting next friday high priority",
    "add call dentist",
    "buy groceries today",
    "task add oil change for car",
]

print("\n" + "=" * 60)
print("Testing Task Parser")
print("=" * 60)

for test_input in test_cases:
    print(f"\nInput: '{test_input}'")
    result = task_manager.parse_command(test_input)
    if result:
        print(f"✓ Parsed: {result}")
    else:
        print(f"✗ Failed to parse")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
