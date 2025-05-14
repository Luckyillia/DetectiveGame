import sqlite3
import threading
import os, json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

class LogDatabase:
    """SQLite database handler for logs with connection pooling"""

    def __init__(self, db_path='data/logs/logs.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.local = threading.local()
        self.init_db()

    def get_connection(self):
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                date TEXT NOT NULL,
                level TEXT NOT NULL,
                action TEXT,
                user_id TEXT,
                message TEXT NOT NULL,
                metadata TEXT
            )
            ''')

            # Create indices for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_date ON logs (date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON logs (level)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_action ON logs (action)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs (user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs (timestamp)')
            conn.commit()

    def add_log(self, log_entry: Dict[str, Any]) -> bool:
        try:
            with self.get_connection() as conn:
                date = datetime.fromtimestamp(log_entry['timestamp']).strftime('%Y-%m-%d')

                # Convert metadata to JSON string if present
                metadata_json = None
                if 'metadata' in log_entry and log_entry['metadata']:
                    metadata_json = json.dumps(log_entry['metadata'], ensure_ascii=False)

                conn.execute(
                    '''
                    INSERT INTO logs (timestamp, datetime, date, level, action, user_id, message, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        log_entry['timestamp'],
                        log_entry['datetime'],
                        date,
                        log_entry['level'],
                        log_entry.get('action'),
                        log_entry.get('user_id'),
                        log_entry['message'],
                        metadata_json
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error adding log to database: {e}")
            return False

    def get_logs(self, date=None, level=None, action=None, user_id=None,
                 search_query=None, page=1, page_size=50) -> List[Dict[str, Any]]:
        """Get logs with pagination and various filters"""
        try:
            query = "SELECT * FROM logs WHERE 1=1"
            params = []

            # Add filters
            if date:
                query += " AND date = ?"
                params.append(date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date)

            if level and level != 'ALL':
                query += " AND level = ?"
                params.append(level)

            if action and action != 'ALL':
                query += " AND action = ?"
                params.append(action)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if search_query:
                query += " AND (message LIKE ? OR metadata LIKE ?)"
                search_param = f"%{search_query}%"
                params.append(search_param)
                params.append(search_param)

            # Add ordering
            query += " ORDER BY timestamp DESC"

            # Add pagination
            offset = (page - 1) * page_size
            query += f" LIMIT {page_size} OFFSET {offset}"

            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log = dict(row)

                    # Parse metadata JSON if present
                    if log['metadata']:
                        try:
                            log['metadata'] = json.loads(log['metadata'])
                        except json.JSONDecodeError:
                            log['metadata'] = {}
                    else:
                        log['metadata'] = {}

                    logs.append(log)

                return logs
        except Exception as e:
            print(f"❌ Error retrieving logs from database: {e}")
            return []

    def count_logs(self, date=None, level=None, action=None, user_id=None, search_query=None) -> int:
        """Count logs matching the filters"""
        try:
            query = "SELECT COUNT(*) FROM logs WHERE 1=1"
            params = []

            # Add filters (same as get_logs)
            if date:
                query += " AND date = ?"
                params.append(date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date)

            if level and level != 'ALL':
                query += " AND level = ?"
                params.append(level)

            if action and action != 'ALL':
                query += " AND action = ?"
                params.append(action)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if search_query:
                query += " AND (message LIKE ? OR metadata LIKE ?)"
                search_param = f"%{search_query}%"
                params.append(search_param)
                params.append(search_param)

            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            print(f"❌ Error counting logs: {e}")
            return 0

    def get_available_actions(self, date=None) -> List[str]:
        """Get unique action values from logs"""
        try:
            query = "SELECT DISTINCT action FROM logs WHERE action IS NOT NULL"
            params = []

            if date:
                query += " AND date = ?"
                params.append(date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date)

            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                actions = [row[0] for row in cursor.fetchall() if row[0]]
                return sorted(actions)
        except Exception as e:
            print(f"❌ Error retrieving available actions: {e}")
            return []

    def migrate_from_json(self, logs_directory: str):
        """Migrate logs from JSON files to SQLite database"""
        if not os.path.exists(logs_directory):
            return

        # List all JSON log files
        log_files = [f for f in os.listdir(logs_directory) if f.startswith('log_') and f.endswith('.json')]

        for log_file in log_files:
            try:
                file_path = os.path.join(logs_directory, log_file)
                with open(file_path, 'r', encoding='utf-8') as file:
                    logs = json.load(file)

                if not logs:
                    continue

                # Add each log entry to database
                for log in logs:
                    self.add_log(log)

                print(f"✅ Migrated logs from {log_file}")
            except Exception as e:
                print(f"❌ Error migrating logs from {log_file}: {e}")