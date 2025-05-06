from nicegui import ui, app
import os, json, time

from src.game import GameStateService
from src.services.user_service import UserService
from src.services.log_services import LogService


class GameRoomManagement:
    def __init__(self, filepath='data/gameRoomState.json', game_ui=None):
        self.filepath = filepath
        self.user_service = UserService()
        self.game_state_service = GameStateService()  # Теперь использует обновленный класс с файлами для каждой игры
        self.log_service = LogService()
        self.game_ui = game_ui
        self.ensure_file_exists()

    def ensure_file_exists(self):
        directory = os.path.dirname(self.filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

        if not os.path.exists(self.filepath):
            self.save({})

    def load(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            print("❌ Error: Could not load game state data.")
            return {}

    def save(self, data):
        try:
            directory = os.path.dirname(self.filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)

            # Convert data to JSON format
            data_to_write = json.dumps(
                data,
                indent=4,
                ensure_ascii=False
            )

            # Write to a temporary file and then replace the original file
            temp_filepath = f"{self.filepath}.tmp"
            with open(temp_filepath, 'w', encoding='utf-8') as temp_file:
                temp_file.write(data_to_write)

            # Replace the original file with the temporary one
            os.replace(temp_filepath, self.filepath)
            return True
        except Exception as e:
            print(f"❌ Error writing game state to file: {e}")
            return False

    def room_exists(self, room_id):
        data = self.load()
        return room_id in data

    def leave_game(self, game_ui):
        if not app.storage.user.get('game_state_id'):
            ui.notify('В данный момент ты не находишься в комнате', type='warning')
            self.log_service.add_user_action_log(
                user_id=app.storage.user.get('user_id'),
                action="leave_game_attempt",
                message="Пользователь попытался выйти, но не находился в игре"
            )
            return

        game_state_id = app.storage.user.get('game_state_id')
        app.storage.user.update({'game_state_id': None})
        self.update_user_game_state(app.storage.user.get('user_id'), None)
        self.remove_user_from_room(app.storage.user.get('user_id'), game_state_id)

        self.log_service.add_user_action_log(
            user_id=app.storage.user.get('user_id'),
            action="leave_game",
            message=f"Пользователь покинул игру",
            metadata={"previous_game_state_id": game_state_id}
        )

        # Безопасная остановка таймера
        if hasattr(game_ui, 'timer') and game_ui.timer:
            try:
                game_ui.timer.cancel()
                game_ui.timer = None
                self.log_service.add_system_log(
                    user_id=app.storage.user.get('user_id'),
                    message="Таймер успешно остановлен при выходе из игры"
                )
            except Exception as e:
                self.log_service.add_error_log(
                    error_message=f"Ошибка при остановке таймера: {str(e)}",
                    user_id=app.storage.user.get('user_id'),
                    metadata={"error_type": type(e).__name__}
                )

        game_ui.show_game_interface

    def show_join_game_dialog(self, game_ui):
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label('Присоединиться к игре').classes('text-xl font-bold mb-4')

            room_id_input = None
            status_label = ui.label('').classes('mt-2')

            def try_join():
                room_id = room_id_input.value.strip()
                if not room_id:
                    status_label.text = 'Пожалуйста, введите ID игры.'
                    status_label.classes('text-red-500 mt-2')
                    self.log_service.add_user_action_log(
                        user_id=app.storage.user.get('user_id'),
                        action="JOIN_GAME_FAILED",
                        message="Пользователь не ввел ID игры"
                    )
                    return

                if self.room_exists(room_id):
                    app.storage.user.update({'game_state_id': room_id})
                    self.update_user_game_state(app.storage.user.get('user_id'), room_id)
                    self.add_user_for_room(app.storage.user.get('user_id'), room_id)

                    self.log_service.add_user_action_log(
                        user_id=app.storage.user.get('user_id'),
                        action="JOIN_GAME_SUCCESS",
                        message=f"Пользователь успешно присоединился к игре",
                        metadata={"joined_room_id": room_id}
                    )

                    status_label.text = ''
                    dialog.close()
                    ui.notify('✅ Вы успешно присоединились к игре!', type='positive')
                    game_ui.show_game_interface
                else:
                    status_label.text = '❌ Игры с таким ID не существует.'
                    status_label.classes('text-red-500 mt-2')

                    self.log_service.add_user_action_log(
                        user_id=app.storage.user.get('user_id'),
                        action="JOIN_GAME_FAILED",
                        message=f"Пользователь пытался присоединиться к несуществующей игре",
                        metadata={"attempted_room_id": room_id}
                    )

            room_id_input = ui.input(label='Введите ID места').classes('w-full mb-4').on('keydown.enter', try_join)
            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300 dark:bg-gray-700')
                ui.button('Войти', on_click=lambda: try_join()).classes('bg-blue-500 text-white')

        dialog.open()

    def update_user_game_state(self, user_id, game_state_id):
        users = self.user_service.load_data()
        for user in users:
            if user['id'] == user_id:
                user['gameState'] = game_state_id
                self.user_service.write_data(users)

                self.log_service.add_system_log(
                    user_id=user_id,
                    message=f"Обновлено состояние игры пользователя",
                    metadata={"new_game_state_id": game_state_id, "username": user['username']}
                )

                return True
        self.log_service.add_error_log(
            error_message=f"Не удалось найти пользователя с id {user_id} для обновления состояния игры",
            user_id=user_id,
            metadata={"attempted_game_state_id": game_state_id}
        )
        return False

    def get_game_state(self, room_id):
        """Возвращает данные игры по идентификатору"""
        data = self.load()
        room_data = data.get(room_id, {})

        if room_data:
            return room_data
        return {}

    def add_location_to_history(self, room_id, location_id, tooltip=False):
        """Добавляет ID локации в историю перемещений игрока"""
        data = self.load()
        if room_id not in data:
            self.log_service.add_error_log(
                error_message=f"Попытка добавить локацию в историю несуществующей игры",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id, "location_id": location_id}
            )
            return False

        if 'location_history' not in data[room_id]:
            data[room_id]['location_history'] = []

        location_entry = {
            'id': location_id,
            'visited_at': int(time.time()),
            'is_tooltip': tooltip  # Сохраняем флаг, что это подсказка
        }

        data[room_id]['location_history'].append(location_entry)
        data[room_id]['current_location'] = location_id
        data[room_id]['last_visited_at'] = int(time.time())

        # Увеличиваем счетчик ходов ТОЛЬКО если это не подсказка
        if not tooltip:
            data[room_id]['move'] = data[room_id].get('move', 0) + 1

        # Улучшенное логирование
        log_message = "Подсказка добавлена" if tooltip else "Локация добавлена"
        self.log_service.add_system_log(
            user_id=app.storage.user.get('user_id'),
            message=f"{log_message} в историю перемещений",
            metadata={
                "room_id": room_id,
                "location_id": location_id,
                "move": data[room_id]['move'],
                "is_tooltip": tooltip
            }
        )

        return self.save(data)

    def get_location_history(self, room_id):
        """Возвращает историю перемещений игрока"""
        data = self.load()
        if room_id not in data:
            self.log_service.add_error_log(
                error_message=f"Попытка получить историю локаций несуществующей игры",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )
            return []

        return data[room_id].get('location_history', [])

    def get_current_location(self, room_id, game_ui):
        """Возвращает текущую локацию игрока"""
        data = self.load()
        if room_id not in data:
            self.log_service.add_error_log(
                error_message=f"Попытка получить текущую локацию несуществующей игры",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )
            return None

        return data[room_id].get('current_location', None)

    def check_for_updates(self):
        """Проверяет обновления в игре и обновляет интерфейс при необходимости"""
        if not hasattr(self, 'game_ui') or self.game_ui is None:

            self.log_service.add_error_log(
                error_message="Ошибка при проверке обновлений: game_ui не инициализирован",
                user_id=app.storage.user.get('user_id')
            )
            return

        data = self.load()
        room_id = app.storage.user.get('game_state_id')

        if not room_id or room_id not in data:
            return

        last_move_time = data[room_id].get('last_visited_at', 0)

        if hasattr(self.game_ui, 'last_update') and last_move_time > self.game_ui.last_update:
            self.game_ui.show_game_interface
            self.game_ui.last_update = last_move_time

            self.log_service.add_system_log(
                user_id=app.storage.user.get('user_id'),
                message="Интерфейс игры обновлен",
                metadata={"room_id": room_id, "last_move_time": last_move_time}
            )

    def accuse_suspect(self, room_id, suspect_id):
        """
        Проверяет, соответствуют ли обвиняемые подозреваемые виновным
        Поддерживает любое количество виновных

        Args:
            room_id: ID игровой комнаты
            suspect_id: Строка с ID подозреваемых, разделенных пробелами

        Returns:
            bool: True если все виновные были правильно идентифицированы
        """
        room_data = self.load().get(room_id, {})
        game_id = room_data.get('game_id')

        if not game_id:
            self.log_service.add_error_log(
                error_message=f"Не удалось получить game_id для комнаты {room_id}",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )
            return False

        # Получаем данные игры через GameStateService
        game_data = self.game_state_service.get_game_state(game_id)
        culprit = game_data.get('isCulprit', {})

        # Разбиваем ID подозреваемых и ID виновных по пробелам и очищаем от пробелов
        suspect_id_parts = set(part.strip() for part in suspect_id.strip().split() if part.strip())
        culprit_id_parts = set(part.strip() for part in culprit.get('id', '').strip().split() if part.strip())

        # Сравниваем множества для проверки правильности обвинения
        # Обвинение правильное, если множества ID подозреваемых и ID виновных идентичны
        result = suspect_id_parts == culprit_id_parts

        self.log_service.add_user_action_log(
            user_id=app.storage.user.get('user_id'),
            action="ACCUSE_SUSPECT",
            message=f"Пользователь обвинил подозреваемого",
            metadata={
                "room_id": room_id,
                "game_id": game_id,
                "suspect_id": suspect_id,
                "culprit_id": culprit.get('id'),
                "result": result
            }
        )

        return result

    def finishing_game(self, room_id):
        data = self.load()
        if room_id in data:
            data[room_id]['status'] = 'finished'
            data[room_id]['last_visited_at'] = int(time.time())

            self.log_service.add_system_log(
                user_id=app.storage.user.get('user_id'),
                message="Игра завершена",
                metadata={"room_id": room_id}
            )

            return self.save(data)
        return False

    def reset_game(self, room_id):
        data = self.load()
        if room_id in data:
            data[room_id]['status'] = 'playing'
            data[room_id]['last_visited_at'] = int(time.time())
            data[room_id]['move'] = 0
            data[room_id]['location_history'] = []
            data[room_id]['current_location'] = None
            data[room_id]['users'] = []

            self.log_service.add_system_log(
                user_id=app.storage.user.get('user_id'),
                message="Игра сброшена",
                metadata={"room_id": room_id}
            )

            return self.save(data)
        return False

    def increment_move(self, room_id):
        """Увеличивает счетчик ходов на 1"""
        data = self.load()
        if room_id in data:
            data[room_id]['last_visited_at'] = int(time.time())
            data[room_id]['move'] = data[room_id].get('move', 0) + 1

            self.log_service.add_system_log(
                user_id=app.storage.user.get('user_id'),
                message="Счетчик ходов увеличен",
                metadata={"room_id": room_id, "move": data[room_id]['move']}
            )

            return self.save(data)
        return False

    def add_user_for_room(self, user_id, room_id):
        data = self.load()
        if room_id in data:
            if 'users' not in data[room_id]:
                data[room_id]['users'] = []
            data[room_id]['users'].append(user_id)

            self.log_service.add_system_log(
                user_id=app.storage.user.get('user_id'),
                message=f"Пользователь добавлен в комнату",
                metadata={"room_id": room_id, "user_id": user_id}
            )

            return self.save(data)
        return False

    def remove_user_from_room(self, user_id, room_id):
        data = self.load()
        if room_id in data:
            if 'users' in data[room_id]:
                if user_id in data[room_id]['users']:
                    data[room_id]['users'].remove(user_id)

                    self.log_service.add_system_log(
                        user_id=app.storage.user.get('user_id'),
                        message=f"Пользователь удален из комнаты",
                        metadata={"room_id": room_id, "user_id": user_id}
                    )

                    return self.save(data)
                else:
                    self.log_service.add_error_log(
                        error_message=f"Пользователь не найден в комнате",
                        user_id=app.storage.user.get('user_id'),
                        metadata={"room_id": room_id, "user_id": user_id}
                    )
            else:
                self.log_service.add_error_log(
                    error_message=f"В комнате нет списка пользователей",
                    user_id=app.storage.user.get('user_id'),
                    metadata={"room_id": room_id}
                )
        else:
            self.log_service.add_error_log(
                error_message=f"Комната не найдена",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )
        return False

    def location_visited(self, room_id, location_id, status=False):
        data = self.load()
        if room_id in data:
            for location_visited in data[room_id]['location_history']:
                if location_id == location_visited['id']:
                    location_visited['open'] = status
        self.save(data)