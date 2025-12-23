#!/usr/bin/env python3
# ABOUTME: Unit tests for TaskManager

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from task_manager import TaskManager

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        """Create a temporary task file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.task_manager = TaskManager(task_file=Path(self.temp_file.name))

    def tearDown(self):
        """Clean up temporary file"""
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_task_file_creation(self):
        """Test that task file is created on init"""
        self.assertTrue(Path(self.temp_file.name).exists())

        # Verify file structure
        with open(self.temp_file.name) as f:
            data = json.load(f)
            self.assertEqual(data['version'], '1.0')
            self.assertEqual(data['tasks'], [])

    def test_add_task_basic(self):
        """Test adding a basic task"""
        task = self.task_manager.add_task("Buy milk")

        self.assertIsNotNone(task['id'])
        self.assertEqual(task['description'], "Buy milk")
        self.assertEqual(task['status'], 'pending')
        self.assertIsNone(task['priority'])
        self.assertIsNone(task['due_date'])
        self.assertIsNone(task['category'])
        self.assertIsNotNone(task['created_at'])

    def test_add_task_with_all_fields(self):
        """Test adding a task with all fields"""
        task = self.task_manager.add_task(
            description="Buy groceries",
            priority="high",
            due_date="2025-12-25",
            category="shopping"
        )

        self.assertEqual(task['description'], "Buy groceries")
        self.assertEqual(task['priority'], "high")
        self.assertEqual(task['due_date'], "2025-12-25")
        self.assertEqual(task['category'], "shopping")

    def test_add_task_invalid_priority(self):
        """Test that invalid priority is set to None"""
        task = self.task_manager.add_task("Test task", priority="urgent")
        self.assertIsNone(task['priority'])

    def test_add_task_invalid_date(self):
        """Test that invalid date is set to None"""
        task = self.task_manager.add_task("Test task", due_date="invalid-date")
        self.assertIsNone(task['due_date'])

    def test_complete_task_by_id(self):
        """Test completing a task by exact ID"""
        task = self.task_manager.add_task("Buy milk")
        completed = self.task_manager.complete_task(task['id'])

        self.assertIsNotNone(completed)
        self.assertEqual(completed['status'], 'completed')
        self.assertIsNotNone(completed['completed_at'])

    def test_complete_task_by_description(self):
        """Test completing a task by description"""
        self.task_manager.add_task("Buy milk")
        completed = self.task_manager.complete_task("Buy milk")

        self.assertIsNotNone(completed)
        self.assertEqual(completed['status'], 'completed')

    def test_complete_task_fuzzy_match(self):
        """Test completing a task with partial description"""
        self.task_manager.add_task("Buy groceries and milk")
        completed = self.task_manager.complete_task("buy milk")

        self.assertIsNotNone(completed)
        self.assertEqual(completed['description'], "Buy groceries and milk")

    def test_complete_task_not_found(self):
        """Test completing a non-existent task"""
        result = self.task_manager.complete_task("nonexistent task")
        self.assertIsNone(result)

    def test_uncomplete_task(self):
        """Test reopening a completed task"""
        task = self.task_manager.add_task("Buy milk")
        self.task_manager.complete_task(task['id'])
        uncompleted = self.task_manager.uncomplete_task(task['id'])

        self.assertEqual(uncompleted['status'], 'pending')
        self.assertIsNone(uncompleted['completed_at'])

    def test_archive_task(self):
        """Test archiving a task"""
        task = self.task_manager.add_task("Old task")
        archived = self.task_manager.archive_task(task['id'])

        self.assertEqual(archived['status'], 'archived')
        self.assertIsNotNone(archived['archived_at'])

    def test_list_pending_tasks(self):
        """Test listing only pending tasks"""
        self.task_manager.add_task("Task 1")
        self.task_manager.add_task("Task 2")
        task3 = self.task_manager.add_task("Task 3")
        self.task_manager.complete_task(task3['id'])

        pending = self.task_manager.list_tasks(filter_type='pending')
        self.assertEqual(len(pending), 2)

    def test_list_completed_tasks(self):
        """Test listing only completed tasks"""
        task1 = self.task_manager.add_task("Task 1")
        task2 = self.task_manager.add_task("Task 2")
        self.task_manager.complete_task(task1['id'])
        self.task_manager.complete_task(task2['id'])

        completed = self.task_manager.list_tasks(filter_type='completed')
        self.assertEqual(len(completed), 2)

    def test_list_by_priority(self):
        """Test filtering tasks by priority"""
        self.task_manager.add_task("Task 1", priority="high")
        self.task_manager.add_task("Task 2", priority="low")
        self.task_manager.add_task("Task 3", priority="high")

        high_priority = self.task_manager.list_tasks(filter_type='high')
        self.assertEqual(len(high_priority), 2)

    def test_list_by_category(self):
        """Test filtering tasks by category"""
        self.task_manager.add_task("Task 1", category="work")
        self.task_manager.add_task("Task 2", category="personal")
        self.task_manager.add_task("Task 3", category="work")

        work_tasks = self.task_manager.list_tasks(filter_type='work')
        self.assertEqual(len(work_tasks), 2)

    def test_list_today_tasks(self):
        """Test filtering tasks due today"""
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        self.task_manager.add_task("Task today", due_date=today)
        self.task_manager.add_task("Task tomorrow", due_date=tomorrow)

        today_tasks = self.task_manager.list_tasks(filter_type='today')
        self.assertEqual(len(today_tasks), 1)

    def test_task_sorting(self):
        """Test that tasks are sorted by priority and due_date"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        self.task_manager.add_task("Low priority, far", priority="low", due_date=next_week)
        self.task_manager.add_task("High priority, soon", priority="high", due_date=tomorrow)
        self.task_manager.add_task("Medium priority, far", priority="medium", due_date=next_week)

        tasks = self.task_manager.list_tasks(filter_type='all')

        # High priority should be first
        self.assertEqual(tasks[0]['priority'], 'high')
        self.assertEqual(tasks[1]['priority'], 'medium')
        self.assertEqual(tasks[2]['priority'], 'low')

    def test_get_pending_count(self):
        """Test getting count of pending tasks"""
        self.task_manager.add_task("Task 1")
        self.task_manager.add_task("Task 2")
        task3 = self.task_manager.add_task("Task 3")
        self.task_manager.complete_task(task3['id'])

        count = self.task_manager.get_pending_count()
        self.assertEqual(count, 2)

    def test_get_completed_count(self):
        """Test getting count of completed tasks"""
        task1 = self.task_manager.add_task("Task 1")
        task2 = self.task_manager.add_task("Task 2")
        self.task_manager.complete_task(task1['id'])
        self.task_manager.complete_task(task2['id'])

        count = self.task_manager.get_completed_count()
        self.assertEqual(count, 2)

    def test_delete_task(self):
        """Test permanently deleting a task"""
        task = self.task_manager.add_task("Task to delete")
        result = self.task_manager.delete_task(task['id'])

        self.assertTrue(result)

        # Verify task is gone
        all_tasks = self.task_manager.list_tasks(filter_type='all')
        self.assertEqual(len(all_tasks), 0)

    def test_json_persistence(self):
        """Test that tasks are persisted to JSON file"""
        self.task_manager.add_task("Persistent task", priority="high")

        # Create new TaskManager instance with same file
        new_manager = TaskManager(task_file=Path(self.temp_file.name))
        tasks = new_manager.list_tasks(filter_type='all')

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['description'], "Persistent task")
        self.assertEqual(tasks[0]['priority'], "high")

    def test_find_task_exact_id(self):
        """Test finding task by exact ID"""
        task = self.task_manager.add_task("Find me")
        found = self.task_manager.find_task(task['id'])

        self.assertIsNotNone(found)
        self.assertEqual(found['id'], task['id'])

    def test_find_task_substring(self):
        """Test finding task by substring match"""
        self.task_manager.add_task("Buy groceries and milk")
        found = self.task_manager.find_task("milk")

        self.assertIsNotNone(found)
        self.assertEqual(found['description'], "Buy groceries and milk")

    def test_find_task_fuzzy(self):
        """Test finding task with fuzzy matching"""
        self.task_manager.add_task("Schedule dentist appointment")
        found = self.task_manager.find_task("dentist")

        self.assertIsNotNone(found)
        self.assertIn("dentist", found['description'].lower())

    def test_find_task_not_found(self):
        """Test finding non-existent task"""
        found = self.task_manager.find_task("nonexistent")
        self.assertIsNone(found)

    def test_empty_description_raises_error(self):
        """Test that empty description raises ValueError"""
        with self.assertRaises(ValueError):
            self.task_manager.add_task("")

    def test_get_tasks_with_limit(self):
        """Test getting tasks with limit"""
        for i in range(10):
            self.task_manager.add_task(f"Task {i}")

        tasks = self.task_manager.get_tasks(limit=5)
        self.assertEqual(len(tasks), 5)

    def test_corrupted_json_recovery(self):
        """Test recovery from corrupted JSON file"""
        # Write invalid JSON
        with open(self.temp_file.name, 'w') as f:
            f.write("invalid json{")

        # Should create backup and fresh file
        new_manager = TaskManager(task_file=Path(self.temp_file.name))
        tasks = new_manager.list_tasks(filter_type='all')

        self.assertEqual(len(tasks), 0)
        # Check backup was created
        backup_file = Path(self.temp_file.name).with_suffix('.json.backup')
        self.assertTrue(backup_file.exists())
        backup_file.unlink()


if __name__ == '__main__':
    unittest.main()
