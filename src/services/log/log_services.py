import os
import json
import time
from datetime import datetime
from nicegui import ui
from functools import lru_cache
from src.services.log.log_database import LogDatabase


class LogService:
    def __init__(self, logs_directory='data/logs', users_file='data/data.json', db_path='data/logs/logs.db'):
        # Initialize properties
        self.logs_directory = logs_directory
        self.users_file = users_file
        self.user_filter = None
        self.available_users = {}
        self.selected_date = datetime.now().date()
        self.level_filter = 'ALL'
        self.action_filter = 'ALL'
        self.search_query = ''
        self.available_actions = None
        self.logs_table = None
        self.current_page = 1
        self.page_size = 50
        self.total_logs = 0

        # Initialize database
        self.db = LogDatabase(db_path)

        # Ensure directories exist
        os.makedirs(logs_directory, exist_ok=True)
        os.makedirs(os.path.dirname(users_file), exist_ok=True)

        # Load users and migrate legacy data if needed
        self.load_users()
        self.migrate_legacy_data_if_needed()

    def migrate_legacy_data_if_needed(self):
        """Check if we need to migrate from JSON files to SQLite"""
        # Simple check: if there are JSON log files but no logs in DB, migrate
        if os.path.exists(self.logs_directory):
            log_files = [f for f in os.listdir(self.logs_directory) if f.startswith('log_') and f.endswith('.json')]
            if log_files:
                # Check if DB is empty
                if self.db.count_logs() == 0:
                    print("📊 Migrating logs from JSON files to SQLite database...")
                    self.db.migrate_from_json(self.logs_directory)
                    print("✅ Migration completed")

    def load_users(self):
        """Load users from the specified file."""
        if not os.path.exists(self.users_file) or os.stat(self.users_file).st_size == 0:
            self.available_users = {}
            return

        try:
            with open(self.users_file, 'r', encoding='utf-8') as file:
                users = json.load(file).get("users", [])
                self.available_users = {user["id"]: user["username"] for user in users}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"❌ Error loading users: {str(e)}")
            self.available_users = {}

    def get_user_username(self, user_id):
        """Get username for a user ID"""
        return self.available_users.get(user_id, f"User {user_id}")

    @lru_cache(maxsize=32)
    def get_available_actions(self, date_str=None):
        """Get available actions with caching"""
        date = None
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        actions = self.db.get_available_actions(date)
        return ['ALL'] + actions

    def add_log(self, message, level="INFO", user_id=None, action=None, metadata=None):
        """Add a new log entry."""
        current_time = datetime.now()

        # Create new log entry
        log_entry = {
            "timestamp": int(time.time()),
            "datetime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
            "level": level,
            "message": message,
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {}
        }

        # Add to database
        return self.db.add_log(log_entry)

    def add_error_log(self, error_message, user_id=None, action="ERROR", metadata=None):
        return self.add_log(error_message, level="ERROR", user_id=user_id, action=action, metadata=metadata)

    def add_user_action_log(self, user_id, action, message, metadata=None):
        return self.add_log(message, level="INFO", user_id=user_id, action=action, metadata=metadata)

    def add_system_log(self, message, user_id=None, metadata=None):
        return self.add_log(message, level="SYSTEM", action="SYSTEM", user_id=user_id, metadata=metadata)

    def add_debug_log(self, message, user_id=None, metadata=None, action="DEBUG"):
        return self.add_log(message, level="DEBUG", action=action, user_id=user_id, metadata=metadata)

    def log_interface(self):
        """Create the log viewing interface with optimized performance"""
        # Status bar for showing information about loaded logs
        status_bar = ui.label()

        # Container for pagination controls
        pagination_container = ui.row().classes('w-full justify-center gap-2')

        # Update the available actions for the selected date
        self.available_actions = self.get_available_actions(self.selected_date.strftime('%Y-%m-%d'))

        # Define function to render a page of logs
        def render_logs_page():
            try:
                self.load_users()  # Refresh user data

                # Get date as string
                date_str = self.selected_date.strftime('%Y-%m-%d')

                # Update available actions with caching
                self.available_actions = self.get_available_actions(date_str)
                action_selector.options = self.available_actions

                if self.action_filter not in self.available_actions:
                    self.action_filter = 'ALL'
                    action_selector.value = 'ALL'

                # Get logs with filters and pagination
                user_id = self.user_filter
                logs = self.db.get_logs(
                    date=date_str,
                    level=self.level_filter if self.level_filter != 'ALL' else None,
                    action=self.action_filter if self.action_filter != 'ALL' else None,
                    user_id=user_id,
                    search_query=self.search_query,
                    page=self.current_page,
                    page_size=self.page_size
                )

                # Get total count for pagination
                self.total_logs = self.db.count_logs(
                    date=date_str,
                    level=self.level_filter if self.level_filter != 'ALL' else None,
                    action=self.action_filter if self.action_filter != 'ALL' else None,
                    user_id=user_id,
                    search_query=self.search_query
                )

                # Calculate total pages
                total_pages = max(1, (self.total_logs + self.page_size - 1) // self.page_size)

                # Update status bar
                status_bar.text = (
                    f"Показано {len(logs)} из {self.total_logs} записей • "
                    f"Страница {self.current_page} из {total_pages}"
                )

                # Clear existing log entries
                log_container.clear()

                # Clear pagination controls
                pagination_container.clear()

                # Add log entries to the container
                with log_container:
                    if not logs:
                        ui.label('Логи не найдены').classes('text-grey italic')

                    # Level colors configuration
                    level_colors = {
                        'INFO': 'bg-sky-100 dark:bg-sky-700',
                        'ERROR': 'bg-rose-100 dark:bg-rose-700',
                        'DEBUG': 'bg-lime-100 dark:bg-lime-700',
                        'SYSTEM': 'bg-violet-100 dark:bg-violet-700',
                        'GAME': 'bg-fuchsia-100 dark:bg-fuchsia-700',
                        'ADMIN_GAME': 'bg-indigo-100 dark:bg-indigo-700',
                        'ADMIN_ROOM': 'bg-amber-100 dark:bg-amber-700',
                        'SECURITY': 'bg-slate-100 dark:bg-slate-700'
                    }

                    # Render each log entry
                    for log in logs:
                        color_class = level_colors.get(log.get('level', ''), 'bg-gray-50 dark:bg-gray-800')

                        with ui.card().classes(f'w-full mb-2 {color_class}'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label(log.get('datetime', '')).classes(
                                    'text-sm text-gray-600 dark:text-gray-300')
                                ui.badge(log.get('level', '')).classes('ml-2 text-sm py-1 px-2 rounded-full')

                                if log.get('action'):
                                    ui.badge(log.get('action')).classes(
                                        'ml-2 bg-green-600 text-sm py-1 px-2 rounded-full')

                                if log.get('user_id'):
                                    username = self.get_user_username(log.get('user_id'))
                                    ui.badge(f"User: {username}").classes(
                                        'ml-2 bg-purple-600 text-sm py-1 px-2 rounded-full')

                            ui.separator()

                            ui.label(log.get('message', '')).classes('font-medium text-gray-800 dark:text-gray-200')

                            if log.get('metadata'):
                                with ui.expansion('Metadata', icon='code').classes('w-full'):
                                    ui.code(json.dumps(log.get('metadata', {}), indent=2, ensure_ascii=False))

                # Add pagination controls
                with pagination_container:
                    # Previous page button
                    ui.button(
                        'Предыдущая',
                        on_click=lambda: change_page(max(1, self.current_page - 1))
                    ).props('icon=chevron_left').classes('px-4').bind_enabled_to(
                        pagination_container, 'self.current_page > 1')

                    # Page numbers
                    # Show up to 5 page numbers with current page in the middle
                    start_page = max(1, min(self.current_page - 2, total_pages - 4))
                    end_page = min(total_pages, start_page + 4)

                    for page in range(start_page, end_page + 1):
                        button = ui.button(
                            str(page),
                            on_click=lambda p=page: change_page(p)
                        ).classes('px-4')

                        if page == self.current_page:
                            button.props('color=primary').classes('font-bold')

                    # Next page button
                    ui.button(
                        'Следующая',
                        on_click=lambda: change_page(min(total_pages, self.current_page + 1))
                    ).props('icon=chevron_right icon-right').classes('px-4').bind_enabled_to(
                        pagination_container, 'self.current_page < total_pages')

            except Exception as e:
                ui.notify(f"Ошибка загрузки логов: {str(e)}", type='negative')
                print(f"Error loading logs: {e}")

        # Helper functions for UI interactions
        def change_page(page):
            self.current_page = page
            render_logs_page()

        def set_date(date_str):
            try:
                self.selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                self.current_page = 1  # Reset to first page
                render_logs_page()
            except Exception:
                ui.notify("Некорректный формат даты", type='warning')

        def set_level(level):
            self.level_filter = level
            self.current_page = 1  # Reset to first page
            render_logs_page()

        def set_action(action):
            self.action_filter = action
            self.current_page = 1  # Reset to first page
            render_logs_page()

        def set_user(user_selection):
            if user_selection == 'ALL':
                self.user_filter = None
            else:
                # Извлекаем user_id (UUID) из выбора (формат: "username (user_id)")
                self.user_filter = user_selection.split("(")[-1][:-1]  # Получаем только UUID
            self.current_page = 1  # Reset to first page
            render_logs_page()

        def set_search(query):
            self.search_query = query.strip()
            self.current_page = 1  # Reset to first page
            render_logs_page()

        def set_page_size(size):
            self.page_size = int(size)
            self.current_page = 1  # Reset to first page
            render_logs_page()

        # UI Layout
        with ui.card().classes('w-full p-4 gap-4'):
            # Filter section
            with ui.expansion('Фильтры поиска', icon='filter_alt').classes('w-full'):
                with ui.column().classes('w-full items-center').style('gap: 10px'):
                    with ui.row().classes('w-full items-center'):
                        ui.icon('calendar_month').classes('text-xl')
                        ui.date(value=self.selected_date, on_change=lambda e: set_date(e.value)).classes('w-48')

                        ui.separator().props('vertical').classes('mx-2')

                        ui.icon('filter_alt').classes('text-xl')
                        ui.select(
                            ['ALL', 'INFO', 'ERROR', 'DEBUG', 'SYSTEM', 'GAME', 'ROOM', 'ADMIN_GAME', 'ADMIN_ROOM'],
                            value=self.level_filter,
                            on_change=lambda e: set_level(e.value)
                        ).classes('w-40')

                        ui.separator().props('vertical').classes('mx-2')

                        ui.icon('flag').classes('text-xl')
                        action_selector = ui.select(
                            self.available_actions,
                            value=self.action_filter,
                            on_change=lambda e: set_action(e.value)
                        ).classes('w-48')

                        ui.separator().props('vertical').classes('mx-2')

                        # User Filter
                        ui.icon('person').classes('text-xl')
                        user_selector = ui.select(
                            ['ALL'] + [f"{username} ({user_id})" for user_id, username in self.available_users.items()],
                            value='ALL',
                            on_change=lambda e: set_user(e.value)
                        ).classes('w-48')

                    with ui.row().classes('w-full items-center'):
                        ui.icon('search').classes('text-xl')
                        ui.input(
                            placeholder='Поиск...',
                            on_change=lambda e: set_search(e.value)
                        ).classes('flex-grow')

                        ui.separator().props('vertical').classes('mx-2')

                        ui.icon('format_list_numbered').classes('text-xl')
                        ui.select(
                            ['10', '25', '50', '100', '250'],
                            value=str(self.page_size),
                            on_change=lambda e: set_page_size(e.value)
                        ).classes('w-24').props('label=Записей на странице')

                        ui.button('Обновить', on_click=lambda: render_logs_page()).props('icon=refresh')

            # Status bar showing log counts
            status_bar.classes('w-full text-center text-sm text-gray-600 my-2')

            # Container for log entries (will be filled dynamically)
            log_container = ui.column().classes('w-full max-h-[610px] overflow-auto')

            # Pagination controls
            with pagination_container:
                ui.label("Загрузка...").classes('text-sm text-gray-600')

        # Initial load
        render_logs_page()