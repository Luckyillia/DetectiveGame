from nicegui import ui, app

from src.services.user.user_service import UserService
from src.game.game_state_service import GameStateService
from src.game.game_room_management import GameRoomManagement


class GameRoomManagementUI:
    def __init__(self):
        """
        Инициализирует UI для управления игровыми комнатами
        """
        self.room_manager = GameRoomManagement()
        self.user_service = UserService()
        self.game_state_service = GameStateService()
        self.log_service = self.room_manager.log_service

        # Данные о комнатах и играх
        self.room_data = {}
        self.game_ids = []  # Список ID игр вместо словаря всех игр
        self.display_container = None

    def load_data(self):
        """Загружает данные о комнатах и список доступных игр"""
        self.room_data = self.room_manager.load()
        # Получаем список всех ID игр вместо загрузки всех данных
        self.game_ids = self.game_state_service.list_all_games()

    def get_username_by_id(self, user_id):
        """Получает имя пользователя по его ID"""
        users = self.user_service.load_data()
        for user in users:
            if user['id'] == user_id:
                return user.get('username', 'Неизвестный пользователь')
        return 'Неизвестный пользователь'

    def get_location_name_by_id(self, location_id, game_id):
        """Получает название локации по ее ID и ID игры"""
        # Загружаем данные только для нужной игры
        game_data = self.game_state_service.get_game_state(game_id)

        if not game_data:
            return f"Локация {location_id}"

        locations = game_data.get('locations', [])
        for location in locations:
            if location.get('id') == location_id:
                return location.get('name', 'Название недоступно')

        return f"Локация {location_id}"

    def create_new_room_dialog(self):
        """Диалог создания новой комнаты"""
        import time

        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label('Создать новую комнату').classes('text-xl font-bold mb-4')

            room_id_input = ui.input(label='ID комнаты').classes('w-full mb-4')
            game_id_select = ui.select(
                label='ID игры',
                options=self.game_ids if self.game_ids else []
            ).classes('w-full mb-4')

            def confirm_create():
                new_room_id = room_id_input.value.strip()
                selected_game_id = game_id_select.value

                if not new_room_id:
                    ui.notify('Пожалуйста, введите ID комнаты', type='negative')
                    return

                if new_room_id in self.room_data:
                    ui.notify('Комната с таким ID уже существует', type='negative')
                    return

                # Создаем новую комнату
                self.room_data[new_room_id] = {
                    'game_id': selected_game_id,
                    'users': [],
                    'status': 'playing',
                    'last_visited_at': int(time.time()),
                    'move': 0,
                    'location_history': [],
                    'current_location': None
                }

                self.room_manager.save(self.room_data)
                self.log_service.add_log(
                    level="ADMIN_ROOM",
                    action='ADMIN_ROOM_CREATE_NEW_ROOM',
                    user_id=app.storage.user.get('user_id'),
                    message=f"Создана новая комната",
                    metadata={"room_id": new_room_id, "game_id": selected_game_id}
                )

                ui.notify('Комната успешно создана', type='positive')
                self.refresh_ui()
                dialog.close()

            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300')
                ui.button('Создать', on_click=confirm_create).classes('bg-green-500 text-white')

        dialog.open()

    def show_location_history(self, room_id):
        """Показывает историю перемещений для комнаты"""
        from datetime import datetime

        if room_id not in self.room_data:
            return

        with ui.dialog() as dialog, ui.card().classes('p-6 w-full max-w-3xl'):
            ui.label(f'История перемещений в комнате {room_id}').classes('text-xl font-bold mb-4')

            location_history = self.room_data[room_id].get('location_history', [])
            game_id = self.room_data[room_id].get('game_id')

            self.column = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'center'},
                {'name': 'name', 'label': 'Название локации', 'field': 'name', 'align': 'center'},
                {'name': 'time', 'label': 'Время посещения', 'field': 'time', 'align': 'center'},
                {'name': 'step', 'label': 'Шаг', 'field': 'step', 'align': 'center'},
            ]
            if location_history:
                with ui.table(columns=self.column, rows=[]).classes('w-full').style('max-height: 400px') as table:

                    for i, loc in enumerate(location_history):
                        loc_id = loc.get('id', 'Неизвестно')
                        # Передаем game_id для получения названия локации из правильной игры
                        loc_name = self.get_location_name_by_id(loc_id, game_id) if game_id else f"Локация {loc_id}"
                        visited_time = datetime.fromtimestamp(loc.get('visited_at', 0)).strftime('%d.%m.%Y %H:%M:%S')

                        table.rows.append({
                            "id": loc_id,
                            "name": loc_name,
                            "time": visited_time,
                            "step": str(i + 1)
                        })
            else:
                ui.label('История перемещений пуста').classes('text-gray-500 my-1')

            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-blue-500 text-white')

        dialog.open()

    def show_users_in_room(self, room_id):
        """Показывает пользователей в комнате"""
        if room_id not in self.room_data:
            return

        with ui.dialog() as dialog, ui.card().classes('p-6 w-full max-w-3xl'):
            ui.label(f'Пользователи в комнате {room_id}').classes('text-xl font-bold mb-4')

            user_list = self.room_data[room_id].get('users', [])
            self.column = [
                {'name': 'user_id', 'label': 'ID', 'field': 'user_id', 'align': 'center'},
                {'name': 'username', 'label': 'Пользователь', 'field': 'username', 'align': 'center'},
            ]
            if user_list:
                with ui.table(columns=self.column, rows=[]).classes('w-full') as table:
                    for user_id in user_list:
                        username = self.get_username_by_id(user_id)
                        table.rows.append({"user_id": user_id, "username": username})
            else:
                ui.label('В комнате нет пользователей').classes('text-gray-500 my-1')

            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-blue-500 text-white')

        dialog.open()

    def delete_room_confirmation(self, room_id):
        """Диалог подтверждения удаления комнаты"""
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 w-96'):
            ui.label(f'Удалить комнату {room_id}?').classes('text-xl font-bold mb-4')
            ui.label('Это действие нельзя отменить').classes('text-red-500 mb-4')

            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=confirm_dialog.close).classes('bg-gray-300')

                def confirm_delete():
                    if room_id in self.room_data:
                        del self.room_data[room_id]
                        self.room_manager.save(self.room_data)
                        self.log_service.add_log(
                            level="ADMIN_ROOM",
                            action='ADMIN_ROOM_DELETE_ROOM',
                            user_id=app.storage.user.get('user_id'),
                            message=f"Комната удалена",
                            metadata={"room_id": room_id}
                        )

                        ui.notify(f'Комната {room_id} удалена', type='positive')
                        self.refresh_ui()
                        confirm_dialog.close()

                ui.button('Удалить', on_click=confirm_delete).classes('bg-red-500 text-white')

        confirm_dialog.open()

    def reset_room(self, room_id):
        """Сбрасывает состояние комнаты"""
        import time

        if room_id not in self.room_data:
            ui.notify('Комната не найдена', type='negative')
            return

        self.room_data[room_id]['status'] = 'playing'
        self.room_data[room_id]['last_visited_at'] = int(time.time())
        self.room_data[room_id]['move'] = 0
        self.room_data[room_id]['tooltip'] = False
        self.room_data[room_id]['location_history'] = []
        self.room_data[room_id]['users'] = []
        self.room_data[room_id]['current_location'] = None

        self.room_manager.save(self.room_data)
        self.log_service.add_log(
            level="ADMIN_ROOM",
            action='ADMIN_ROOM_RESET_ROOM',
            user_id=app.storage.user.get('user_id'),
            message=f"Комната сброшена",
            metadata={"room_id": room_id}
        )

        ui.notify(f'Комната {room_id} сброшена', type='positive')
        self.refresh_ui()

    def finish_game(self, room_id):
        """Устанавливает статус игры как завершенный"""
        import time

        if room_id not in self.room_data:
            ui.notify('Комната не найдена', type='negative')
            return

        self.room_data[room_id]['status'] = 'finished'
        self.room_data[room_id]['last_visited_at'] = int(time.time())

        self.room_manager.save(self.room_data)
        self.log_service.add_log(
            level="ADMIN_ROOM",
            action='ADMIN_ROOM_CHANGE_STATUS',
            user_id=app.storage.user.get('user_id'),
            message=f"Игра в комнате завершена",
            metadata={"room_id": room_id, "new_status": self.room_data[room_id]['status']}
        )

        ui.notify(f'Игра в комнате {room_id} помечена как завершенная', type='positive')
        self.refresh_ui()

    def change_game_id(self, room_id, new_game_id):
        """Изменяет ID игры для комнаты"""
        if room_id not in self.room_data:
            ui.notify('Комната не найдена', type='negative')
            return

        self.room_data[room_id]['game_id'] = new_game_id
        self.room_manager.save(self.room_data)
        self.log_service.add_log(
            level="ADMIN_ROOM",
            action='ADMIN_ROOM_CHANGE_GAME_ID',
            user_id=app.storage.user.get('user_id'),
            message=f"Изменен ID игры для комнаты {room_id}",
            metadata={"room_id": room_id, "new_game_id": new_game_id}
        )

        ui.notify(f'ID игры изменен на {new_game_id}', type='positive')
        self.refresh_ui()

    def save_game_id_change(self, dialog, room_id, new_game_id):
        self.change_game_id(room_id, new_game_id)
        dialog.close()

    def open_change_game_id_dialog(self, room_id: str):
        dialog = ui.dialog()

        with dialog:
            with ui.card():
                ui.label('Выберите новый ID игры').classes('text-lg')

                # Селект с опциями - используем список ID игр
                current_game_id = self.room_data[room_id].get('game_id')
                selected_game_id = ui.select(
                    options=self.game_ids if self.game_ids else [],
                    value=current_game_id if current_game_id in self.game_ids else None
                ).classes('w-full')

                # Кнопки
                with ui.row():
                    ui.button('Сохранить',
                              on_click=lambda: self.save_game_id_change(dialog, room_id, selected_game_id.value)).props(
                        'color=primary')
                    ui.button('Отмена', on_click=dialog.close).props('color=secondary')

        dialog.open()

    def refresh_ui(self):
        """Обновляет данные и пересоздает UI"""
        self.load_data()
        if self.display_container:
            self.display_container.clear()
            self.create_room_cards()

    def create_room_cards(self):
        """Создает карточки для всех комнат"""
        from datetime import datetime

        if not self.room_data:
            with self.display_container:
                ui.label('Нет доступных комнат').classes('text-xl text-gray-500 text-center w-full my-8')
            return

        with self.display_container:
            for room_id, room in self.room_data.items():
                status_class = 'text-green-500' if room.get('status') == 'playing' else 'text-red-500'
                status_text = 'Активна' if room.get('status') == 'playing' else 'Завершена'
                game_id = room.get("game_id", "Не указан")

                # Проверяем существование игры в новом формате
                game_exists = game_id in self.game_ids

                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.expansion(f'Комната: {room_id}', icon='meeting_room', group='rooms').classes('w-full'):
                        with ui.column().classes('w-full'):
                            # Основная информация о комнате
                            with ui.row().classes('w-full items-center'):
                                ui.label(f'Статус: ').classes('font-bold')
                                ui.label(status_text).classes(f'{status_class} mr-4')

                                # Добавляем индикатор существования игры
                                game_id_text = f'ID игры: {game_id}'
                                if not game_exists and game_id != "Не указан":
                                    game_id_text += ' (Файл игры не найден)'
                                    game_id_class = 'mr-4 text-red-500'
                                else:
                                    game_id_class = 'mr-4'

                                ui.label(game_id_text).classes(game_id_class)

                                last_visited = room.get('last_visited_at', 0)
                                last_visited_str = datetime.fromtimestamp(last_visited).strftime(
                                    '%d.%m.%Y %H:%M:%S') if last_visited else "Никогда"
                                ui.label(f'Последнее посещение: {last_visited_str}').classes('mr-4')

                                ui.label(f'Текущий ход: {room.get("move", 0)}').classes('mr-4')

                            # Текущая локация и пользователи
                            with ui.row().classes('w-full mt-2'):
                                ui.label(f'Текущая локация: {room.get("current_location", "Не определена")}').classes(
                                    'mr-4')

                                user_count = len(room.get('users', []))
                                ui.label(f'Пользователей в комнате: {user_count}').classes('mr-4')

                            # Кнопки действий
                            with ui.row().classes('w-full justify-between mt-4'):
                                # Кнопки информации
                                with ui.row():
                                    ui.button('История перемещений', icon='history',
                                              on_click=lambda rid=room_id: self.show_location_history(rid)).classes(
                                        'mr-2 bg-blue-600 text-white')

                                    ui.button('Пользователи', icon='people',
                                              on_click=lambda rid=room_id: self.show_users_in_room(rid)).classes(
                                        'mr-2 bg-blue-600 text-white')

                                    ui.button('Изменить ID игры',
                                              on_click=lambda rid=room_id: self.open_change_game_id_dialog(
                                                  rid)).classes('mr-2 bg-blue-600 text-white')

                                # Кнопки управления
                                with ui.row():
                                    ui.button('Сбросить', icon='refresh',
                                              on_click=lambda rid=room_id: self.reset_room(rid)) \
                                        .classes('mr-2 bg-yellow-500 text-white')

                                    ui.button('Завершить', icon='done_all',
                                              on_click=lambda rid=room_id: self.finish_game(rid)) \
                                        .classes('mr-2 bg-orange-500 text-white')

                                    ui.button('Удалить', icon='delete',
                                              on_click=lambda rid=room_id: self.delete_room_confirmation(rid)) \
                                        .classes('bg-red-500 text-white')

    def create_ui(self):
        """Создает интерфейс управления комнатами"""
        self.load_data()

        with ui.card().classes('w-full p-4'):
            ui.label('Управление игровыми комнатами').classes('text-xl font-bold mb-4')

            # Кнопки верхнего уровня
            with ui.row().classes('w-full justify-between mb-4'):
                ui.button('Обновить данные', icon='refresh', on_click=lambda: self.refresh_ui()) \
                    .classes('bg-blue-500 text-white')

                ui.button('Создать комнату', icon='add', on_click=lambda: self.create_new_room_dialog()) \
                    .classes('bg-green-500 text-white')

            # Контейнер для карточек комнат
            self.display_container = ui.column().classes('w-full max-h-[70vh] overflow-auto')
            self.create_room_cards()