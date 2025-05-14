import json
import os
import uuid
from src.models.user import User
from src.services.log.log_services import LogService
from src.services.password_service import PasswordService


class UserService:
    def __init__(self, file_name='data/data.json'):
        self.file_name = file_name
        self.log_service = LogService()
        self.password_service = PasswordService()

    def load_data(self):
        directory = os.path.dirname(self.file_name)
        if not os.path.exists(directory):
            os.makedirs(directory)

        if not os.path.exists(self.file_name) or os.stat(self.file_name).st_size == 0:
            return []

        try:
            with open(self.file_name, 'r', encoding='utf-8') as file:
                users = json.load(file).get("users", [])
                return users
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.log_service.add_error_log(
                error_message="Ошибка загрузки данных пользователей",
                metadata={"exception": str(e)}
            )
            return []

    def write_data(self, users):
        """Записывает данные пользователей в файл."""
        try:
            directory = os.path.dirname(self.file_name)
            if not os.path.exists(directory):
                os.makedirs(directory)

            data_to_write = json.dumps(
                {"users": users},
                indent=4,
                ensure_ascii=False
            )

            # Записываем во временный файл
            temp_file_name = f"{self.file_name}.tmp"
            with open(temp_file_name, "w", encoding="utf-8") as temp_file:
                temp_file.write(data_to_write)
                temp_file.flush()  # Ensure data is written to disk
                os.fsync(temp_file.fileno())  # Force filesystem sync

            # Проверяем, что временный файл действительно создан
            if not os.path.exists(temp_file_name) or os.path.getsize(temp_file_name) == 0:
                return False

            # Заменяем оригинальный файл временным
            os.replace(temp_file_name, self.file_name)

            # Проверяем, что файл действительно обновлен
            if not os.path.exists(self.file_name) or os.path.getsize(self.file_name) == 0:
                return False

            return True

        except Exception as e:
            print(f"Error writing user data: {str(e)}")
            self.log_service.add_error_log(
                error_message=f"Ошибка записи данных пользователей: {str(e)}"
            )
            return False

    def add_user(self, name, surname, username, password, avatar, email=None):
        # Проверяем доступность имени пользователя
        users = self.load_data()
        if not self.is_username_available(username):
            self.log_service.add_error_log(
                error_message="Попытка регистрации с занятым именем пользователя",
                metadata={"username": username}
            )
            return False

        # Проверяем сложность пароля
        password_check = self.password_service.check_password_strength(password)
        if not password_check["valid"]:
            self.log_service.add_error_log(
                error_message="Пароль не соответствует требованиям безопасности",
                metadata={"password_errors": password_check["errors"]}
            )
            return False

        # Хешируем пароль перед сохранением
        hashed_password = self.password_service.hash_password(password)

        user_id = str(uuid.uuid4())
        new_user = User(user_id, name, surname, username, hashed_password, avatar, email).to_dict()
        users.append(new_user)
        success = self.write_data(users)

        if success:
            self.log_service.add_user_action_log(
                user_id=user_id,
                action="USER_REGISTRATION",
                message=f"Пользователь {username} успешно зарегистрирован"
            )
        return success

    def delete_user(self, user_id):
        users = self.load_data()
        updated_users = [user for user in users if user['id'] != user_id]
        if len(updated_users) == len(users):
            return False
        success = self.write_data(updated_users)

        if success:
            self.log_service.add_user_action_log(
                user_id=user_id,
                action="DELETE_USER_ACCOUNT",
                message="Пользовательский аккаунт успешно удалён"
            )
        return success

    def edit_user(self, user_id, new_data):
        """Редактирует данные пользователя."""
        try:
            # Загружаем текущие данные
            users = self.load_data()
            success = False

            # Ищем пользователя для обновления
            for i, user in enumerate(users):
                if user['id'] == user_id:

                    # Сохраняем старые данные для лога
                    old_data = {k: user.get(k) for k in new_data.keys()}

                    # Обновляем данные пользователя
                    for key, value in new_data.items():
                        if key != 'id':  # Не даем изменить ID
                            user[key] = value

                    success = True
                    break

            if not success:
                return False

            # Сохраняем все данные
            return self.write_data(users)

        except Exception as e:
            print(f"Error editing user: {str(e)}")
            self.log_service.add_error_log(
                error_message=f"Ошибка при редактировании пользователя: {str(e)}",
                metadata={"user_id": user_id}
            )
            return False

    def is_username_available(self, username):
        users = self.load_data()
        return not any(user['username'] == username for user in users)

    def get_user_by_username(self, username):
        users = self.load_data()
        for user in users:
            if user['username'] == username:
                return user
        return None

    def get_user_by_id(self, user_id):
        users = self.load_data()
        for user in users:
            if user['id'] == user_id:
                return user
        return None

    def migrate_passwords(self):
        """Мигрирует все пароли из открытого текста в хешированный формат"""
        users = self.load_data()
        updated = 0

        for user in users:
            if '$' not in user['password']:
                # Пароль в открытом виде, хешируем его
                user['password'] = self.password_service.hash_password(user['password'])
                updated += 1

        if updated > 0:
            if self.write_data(users):
                self.log_service.add_system_log(
                    message=f"Миграция паролей: успешно захешировано {updated} паролей",
                    metadata={"migrated_count": updated}
                )
                return updated
            else:
                self.log_service.add_error_log(
                    error_message="Ошибка при миграции паролей",
                    metadata={"attempted_count": updated}
                )
                return 0

        return 0  # Нет паролей для миграции

    def increment_user_moves(self, user_id, count=1):
        """
        Увеличивает счетчик ходов пользователя.

        Args:
            user_id (str): ID пользователя
            count (int): Количество ходов для добавления (по умолчанию 1)

        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        users = self.load_data()
        for user in users:
            if user['id'] == user_id:
                # Проверяем существование статистики
                if 'stats' not in user:
                    user['stats'] = {}

                # Проверяем существование счетчика ходов
                if 'total_moves' not in user['stats']:
                    user['stats']['total_moves'] = 0

                # Увеличиваем счетчик
                user['stats']['total_moves'] += count

                # Записываем обновленные данные
                success = self.write_data(users)

                if success:
                    self.log_service.add_user_action_log(
                        user_id=user_id,
                        action="STAT_UPDATE_MOVES",
                        message=f"Обновлена статистика ходов пользователя (+{count})",
                        metadata={"new_total": user['stats']['total_moves']}
                    )

                return success

        # Пользователь не найден
        self.log_service.add_error_log(
            error_message=f"Не удалось обновить статистику ходов: пользователь {user_id} не найден"
        )
        return False

    def increment_user_rooms(self, user_id, room_id=None):
        """
        Увеличивает счетчик комнат, в которых был пользователь.
        Отслеживает уникальные комнаты, чтобы не дублировать счетчик.

        Args:
            user_id (str): ID пользователя
            room_id (str): ID комнаты (опционально)

        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        users = self.load_data()
        for user in users:
            if user['id'] == user_id:
                # Проверяем существование статистики
                if 'stats' not in user:
                    user['stats'] = {}

                # Проверяем существование счетчика комнат
                if 'rooms_visited' not in user['stats']:
                    user['stats']['rooms_visited'] = 0

                # Проверяем существование списка посещенных комнат
                if 'rooms_list' not in user['stats']:
                    user['stats']['rooms_list'] = []

                # Проверяем, посещал ли пользователь уже эту комнату
                if room_id and room_id not in user['stats']['rooms_list']:
                    user['stats']['rooms_list'].append(room_id)
                    user['stats']['rooms_visited'] += 1

                    # Записываем обновленные данные
                    success = self.write_data(users)

                    if success:
                        self.log_service.add_user_action_log(
                            user_id=user_id,
                            action="STAT_UPDATE_ROOMS",
                            message=f"Обновлена статистика посещенных комнат",
                            metadata={"room_id": room_id, "total_rooms": user['stats']['rooms_visited']}
                        )

                    return success
                elif not room_id:
                    # Если ID комнаты не указан, просто увеличиваем счетчик
                    user['stats']['rooms_visited'] += 1
                    success = self.write_data(users)

                    if success:
                        self.log_service.add_user_action_log(
                            user_id=user_id,
                            action="STAT_UPDATE_ROOMS",
                            message=f"Обновлена статистика посещенных комнат",
                            metadata={"total_rooms": user['stats']['rooms_visited']}
                        )

                    return success

                # Комната уже была посещена, не увеличиваем счетчик
                return True

        # Пользователь не найден
        self.log_service.add_error_log(
            error_message=f"Не удалось обновить статистику комнат: пользователь {user_id} не найден"
        )
        return False

    def increment_users_completed_games(self, room_data):
        """
        Увеличивает счетчик завершенных игр для всех пользователей в комнате.

        Args:
            room_data (dict): Данные игровой комнаты

        Returns:
            bool: True если обновление успешно для всех пользователей, False в противном случае
        """
        if not room_data or 'game_id' not in room_data or 'users' not in room_data:
            self.log_service.add_error_log(
                error_message="Не удалось обновить статистику: неверные данные комнаты",
                metadata={"room_data": str(room_data)}
            )
            return False

        users_data = self.load_data()
        game_id = room_data['game_id']
        room_users = room_data.get('users', [])

        if not room_users:
            return True  # Нет пользователей для обновления

        success_count = 0

        for room_user_id in room_users:
            user_updated = False

            for user in users_data:
                if user['id'] == room_user_id:
                    # Проверяем существование статистики
                    if 'stats' not in user:
                        user['stats'] = {}

                    # Проверяем существование счетчика завершенных игр
                    if 'games_completed' not in user['stats']:
                        user['stats']['games_completed'] = 0

                    # Проверяем существование списка завершенных игр
                    if 'completed_games_list' not in user['stats']:
                        user['stats']['completed_games_list'] = []

                    # Проверяем, завершал ли пользователь уже эту игру
                    if game_id not in user['stats']['completed_games_list']:
                        user['stats']['completed_games_list'].append(game_id)
                        user['stats']['games_completed'] += 1
                        user_updated = True

                        self.log_service.add_user_action_log(
                            user_id=room_user_id,
                            action="STAT_UPDATE_COMPLETED_GAMES",
                            message=f"Обновлена статистика завершенных игр",
                            metadata={
                                "game_id": game_id,
                                "total_completed": user['stats']['games_completed']
                            }
                        )

                    break  # Нашли пользователя, прекращаем внутренний цикл

            if user_updated:
                success_count += 1

        # Сохраняем данные только один раз после всех обновлений
        if success_count > 0:
            success = self.write_data(users_data)
            if not success:
                self.log_service.add_error_log(
                    error_message="Не удалось сохранить данные статистики после обновления",
                    metadata={"game_id": game_id, "affected_users": len(room_users)}
                )
            return success

        return True  # Все пользователи уже имели эту игру в списке завершенных


    def get_user_stats(self, user_id):
        """
        Получает статистику пользователя.
        Если статистика отсутствует, возвращает базовую структуру с нулевыми значениями.

        Args:
            user_id (str): ID пользователя

        Returns:
            dict: Статистика пользователя
        """
        user = self.get_user_by_id(user_id)

        if not user:
            self.log_service.add_error_log(
                error_message=f"Не удалось получить статистику: пользователь {user_id} не найден"
            )
            return None

        # Если статистика отсутствует, возвращаем базовую структуру
        if 'stats' not in user:
            return {
                'total_moves': 0,
                'rooms_visited': 0,
                'games_completed': 0,
                'rooms_list': [],
                'completed_games_list': []
            }

        # Проверяем наличие всех необходимых полей
        stats = user['stats']

        if 'total_moves' not in stats:
            stats['total_moves'] = 0

        if 'rooms_visited' not in stats:
            stats['rooms_visited'] = 0

        if 'games_completed' not in stats:
            stats['games_completed'] = 0

        if 'rooms_list' not in stats:
            stats['rooms_list'] = []

        if 'completed_games_list' not in stats:
            stats['completed_games_list'] = []

        return stats