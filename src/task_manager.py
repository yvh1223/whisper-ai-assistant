#!/usr/bin/env python3
# ABOUTME: Task management with CRUD operations, JSON storage, and GPT-based natural language parsing

import os
import json
import uuid
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from logger_config import setup_logging

logger = setup_logging()

class TaskManager:
    def __init__(self, openai_client=None, task_file=None):
        """
        Initialize TaskManager with OpenAI client for parsing and task file storage.

        Args:
            openai_client: OpenAI client instance for GPT parsing (optional)
            task_file: Path to task JSON file (defaults to ~/.whisper_tasks.json)
        """
        self.openai_client = openai_client
        self.task_file = task_file or Path.home() / '.whisper_tasks.json'
        self.ensure_task_file()

    def ensure_task_file(self):
        """Create task file if it doesn't exist"""
        if not self.task_file.exists():
            logger.info(f"Creating new task file at {self.task_file}")
            self._save_tasks({'version': '1.0', 'tasks': []})

    def _load_tasks(self):
        """Load tasks from JSON file"""
        try:
            with open(self.task_file, 'r') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing task file: {e}")
            # Backup corrupted file
            backup_file = self.task_file.with_suffix('.json.backup')
            self.task_file.rename(backup_file)
            logger.info(f"Corrupted file backed up to {backup_file}")
            # Create fresh file
            self._save_tasks({'version': '1.0', 'tasks': []})
            return {'version': '1.0', 'tasks': []}
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            return {'version': '1.0', 'tasks': []}

    def _save_tasks(self, data):
        """Save tasks to JSON file using atomic write"""
        try:
            # Write to temporary file first
            temp_file = self.task_file.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.task_file)
            logger.debug(f"Tasks saved to {self.task_file}")
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
            raise

    def parse_command(self, text):
        """
        Parse natural language task command using GPT or fallback parser.
        Returns structured dict with action, description, priority, due_date, category, identifier, filter.

        Args:
            text: Raw voice command (e.g., "task add buy milk high priority tomorrow")

        Returns:
            dict: Parsed command structure or None if parsing fails
        """
        # Only use GPT parsing - no fallback
        if not self.openai_client or not self.openai_client.is_available():
            logger.error("OpenAI client not available - task parsing disabled")
            return None

        try:
            current_date = datetime.now().strftime('%Y-%m-%d')
            parsed = self.openai_client.parse_task_command(text, current_date)
            return parsed
        except Exception as e:
            logger.error(f"Error with GPT parsing: {e}")
            return None

    def _simple_parse(self, text):
        """
        Simple fallback parser for basic task commands without GPT.
        Handles: "task add DESCRIPTION [high/medium/low] [tomorrow/today]"

        Args:
            text: Raw command text

        Returns:
            dict: Parsed command or None
        """
        text = text.strip().lower()

        # Remove "task" or "todo" prefix
        for prefix in ['task', 'todo', 'to do']:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        # Determine action
        action = None
        if text.startswith('add'):
            action = 'add'
            text = text[3:].strip()
        elif text.startswith('complete'):
            action = 'complete'
            text = text[8:].strip()
        elif text.startswith('list'):
            action = 'list'
            return {'action': 'list', 'filter': 'pending'}
        elif text.startswith('archive'):
            action = 'archive'
            text = text[7:].strip()
        else:
            # Default to "add" if no action specified
            action = 'add'

        if action == 'add':
            # Parse description, priority, and due date
            priority = None
            due_date = None
            description = text

            # Extract priority
            for p in ['high priority', 'medium priority', 'low priority', 'high', 'medium', 'low']:
                if p in text:
                    priority = p.replace(' priority', '')
                    text = text.replace(p, '').strip()
                    break

            # Extract due date
            today = datetime.now()
            if 'tomorrow' in text:
                due_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                text = text.replace('tomorrow', '').strip()
            elif 'today' in text:
                due_date = today.strftime('%Y-%m-%d')
                text = text.replace('today', '').strip()

            # Clean up description
            description = ' '.join(text.split()).strip()

            if not description:
                logger.warning("No description found in task command")
                return None

            return {
                'action': 'add',
                'description': description,
                'priority': priority,
                'due_date': due_date,
                'category': None,
                'identifier': None,
                'filter': None
            }

        elif action == 'complete':
            return {
                'action': 'complete',
                'identifier': text,
                'description': None,
                'priority': None,
                'due_date': None,
                'category': None,
                'filter': None
            }

        elif action == 'archive':
            return {
                'action': 'archive',
                'identifier': text,
                'description': None,
                'priority': None,
                'due_date': None,
                'category': None,
                'filter': None
            }

        return None

    def add_task(self, description, priority=None, due_date=None, category=None):
        """
        Add a new task.

        Args:
            description: Task description
            priority: 'high', 'medium', 'low', or None
            due_date: ISO date string (YYYY-MM-DD) or None
            category: Category/tag name or None

        Returns:
            dict: Created task
        """
        if not description:
            raise ValueError("Task description is required")

        # Validate priority
        if priority and priority.lower() not in ['high', 'medium', 'low']:
            logger.warning(f"Invalid priority '{priority}', setting to None")
            priority = None

        # Validate due_date format
        if due_date:
            try:
                datetime.fromisoformat(due_date)
            except ValueError:
                logger.warning(f"Invalid date format '{due_date}', setting to None")
                due_date = None

        task = {
            'id': str(uuid.uuid4()),
            'description': description.strip(),
            'status': 'pending',
            'priority': priority.lower() if priority else None,
            'due_date': due_date,
            'category': category.strip() if category else None,
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'archived_at': None
        }

        data = self._load_tasks()
        data['tasks'].append(task)
        self._save_tasks(data)

        logger.info(f"Added task: {task['description']} (id: {task['id']})")
        return task

    def find_task(self, identifier):
        """
        Find task by ID or fuzzy description match.

        Args:
            identifier: Task ID (exact match) or description (fuzzy match)

        Returns:
            dict: Matched task or None
        """
        if not identifier:
            return None

        data = self._load_tasks()
        tasks = data.get('tasks', [])

        identifier_lower = identifier.lower().strip()

        # Try exact ID match first
        for task in tasks:
            if task['id'] == identifier:
                return task

        # Try substring match in description
        for task in tasks:
            if identifier_lower in task['description'].lower():
                return task

        # Try fuzzy matching using difflib
        descriptions = [task['description'] for task in tasks]
        matches = difflib.get_close_matches(identifier, descriptions, n=1, cutoff=0.6)

        if matches:
            for task in tasks:
                if task['description'] == matches[0]:
                    return task

        return None

    def complete_task(self, identifier):
        """
        Mark task as completed.

        Args:
            identifier: Task ID or description

        Returns:
            dict: Completed task or None if not found
        """
        task = self.find_task(identifier)
        if not task:
            logger.warning(f"Task not found: {identifier}")
            return None

        data = self._load_tasks()
        for t in data['tasks']:
            if t['id'] == task['id']:
                t['status'] = 'completed'
                t['completed_at'] = datetime.now().isoformat()
                self._save_tasks(data)
                logger.info(f"Completed task: {t['description']}")
                return t

        return None

    def uncomplete_task(self, identifier):
        """
        Mark task as pending (reopen).

        Args:
            identifier: Task ID or description

        Returns:
            dict: Uncompleted task or None if not found
        """
        task = self.find_task(identifier)
        if not task:
            logger.warning(f"Task not found: {identifier}")
            return None

        data = self._load_tasks()
        for t in data['tasks']:
            if t['id'] == task['id']:
                t['status'] = 'pending'
                t['completed_at'] = None
                self._save_tasks(data)
                logger.info(f"Reopened task: {t['description']}")
                return t

        return None

    def archive_task(self, identifier):
        """
        Archive task.

        Args:
            identifier: Task ID or description

        Returns:
            dict: Archived task or None if not found
        """
        task = self.find_task(identifier)
        if not task:
            logger.warning(f"Task not found: {identifier}")
            return None

        data = self._load_tasks()
        for t in data['tasks']:
            if t['id'] == task['id']:
                t['status'] = 'archived'
                t['archived_at'] = datetime.now().isoformat()
                self._save_tasks(data)
                logger.info(f"Archived task: {t['description']}")
                return t

        return None

    def list_tasks(self, filter_type='pending'):
        """
        List tasks with optional filter.

        Args:
            filter_type: Filter type - 'pending', 'completed', 'archived', 'all',
                        'high', 'medium', 'low', 'today', or category name

        Returns:
            list: Filtered tasks
        """
        data = self._load_tasks()
        tasks = data.get('tasks', [])

        if filter_type == 'all':
            filtered = tasks
        elif filter_type in ['pending', 'completed', 'archived']:
            filtered = [t for t in tasks if t['status'] == filter_type]
        elif filter_type in ['high', 'medium', 'low']:
            filtered = [t for t in tasks if t.get('priority') == filter_type and t['status'] == 'pending']
        elif filter_type == 'today':
            today = datetime.now().strftime('%Y-%m-%d')
            filtered = [t for t in tasks if t.get('due_date') == today and t['status'] == 'pending']
        else:
            # Filter by category
            filtered = [t for t in tasks if t.get('category') == filter_type and t['status'] == 'pending']

        # Sort by priority (high → medium → low), then by due_date (soonest first)
        priority_order = {'high': 0, 'medium': 1, 'low': 2, None: 3}

        def sort_key(task):
            priority_rank = priority_order.get(task.get('priority'), 3)
            due_date = task.get('due_date') or '9999-12-31'  # Put tasks with no due date at end
            return (priority_rank, due_date)

        filtered.sort(key=sort_key)
        return filtered

    def get_tasks(self, limit=None, status='all'):
        """
        Get tasks for menu display.

        Args:
            limit: Maximum number of tasks to return
            status: Status filter - 'pending', 'completed', 'archived', 'all'

        Returns:
            list: Tasks sorted by priority and due date
        """
        tasks = self.list_tasks(filter_type=status)

        if limit:
            return tasks[:limit]
        return tasks

    def get_pending_count(self):
        """Get count of pending tasks"""
        data = self._load_tasks()
        tasks = data.get('tasks', [])
        return len([t for t in tasks if t['status'] == 'pending'])

    def get_completed_count(self):
        """Get count of completed tasks"""
        data = self._load_tasks()
        tasks = data.get('tasks', [])
        return len([t for t in tasks if t['status'] == 'completed'])

    def get_archived_count(self):
        """Get count of archived tasks"""
        data = self._load_tasks()
        tasks = data.get('tasks', [])
        return len([t for t in tasks if t['status'] == 'archived'])

    def delete_task(self, identifier):
        """
        Permanently delete task.

        Args:
            identifier: Task ID or description

        Returns:
            bool: True if deleted, False if not found
        """
        task = self.find_task(identifier)
        if not task:
            logger.warning(f"Task not found: {identifier}")
            return False

        data = self._load_tasks()
        data['tasks'] = [t for t in data['tasks'] if t['id'] != task['id']]
        self._save_tasks(data)
        logger.info(f"Deleted task: {task['description']}")
        return True
