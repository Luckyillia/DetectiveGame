import json
import os
import time
import random
from nicegui import app
from src.services.log.log_services import LogService


class CodenamesRoomService:
    """
    Сервис для управления игровыми комнатами в игре Codenames.
    Отвечает за создание/удаление комнат, управление игроками, командами и ходами.
    """

    def __init__(self, rooms_file='src/minigame/codenames/codenames_rooms.json'):
        self.rooms_file = rooms_file
        self.log_service = LogService()
        self.ensure_rooms_file_exists()

    def ensure_rooms_file_exists(self):
        """Проверяет существование файла с данными о комнатах."""
        directory = os.path.dirname(self.rooms_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

        if not os.path.exists(self.rooms_file):
            self.save_rooms({})

    def load_rooms(self):
        """Загружает данные о комнатах из файла."""
        try:
            with open(self.rooms_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка загрузки данных о комнатах Codenames: {str(e)}",
                action="CODENAMES_ROOMS_LOAD"
            )
            return {}

    def save_rooms(self, rooms_data):
        """Сохраняет данные о комнатах в файл."""
        try:
            directory = os.path.dirname(self.rooms_file)
            if not os.path.exists(directory):
                os.makedirs(directory)

            temp_file = f"{self.rooms_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as file:
                json.dump(rooms_data, file, indent=2, ensure_ascii=False)

            os.replace(temp_file, self.rooms_file)
            return True
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка сохранения данных о комнатах Codenames: {str(e)}",
                action="CODENAMES_ROOMS_SAVE"
            )
            return False

    def create_room(self, host_id, host_name):
        """Создает новую комнату."""
        room_id = f"codenames_{random.randint(1000, 9999)}"
        current_time = int(time.time())

        room_data = {
            "room_id": room_id,
            "created_at": current_time,
            "last_activity": current_time,
            "status": "waiting",  # waiting, playing, finished
            "host_id": host_id,
            "settings": {
                "team_count": 2,
                "hint_mode": "written"  # written или verbal
            },
            "teams": {
                "1": {
                    "captain": host_id,
                    "members": [],
                    "color": "bg-red-500",
                    "name": "Красная"
                }
            },
            "players": [
                {
                    "id": host_id,
                    "name": host_name,
                    "is_host": True,
                    "joined_at": current_time,
                    "last_action": current_time,
                    "team": "1",
                    "role": "captain"  # captain или member
                }
            ],
            "game_data": {
                "field": [],
                "current_team": 1,
                "current_hint": None,
                "round": 0,
                "turn_order": [],
                "game_started": False
            }
        }

        rooms = self.load_rooms()
        rooms[room_id] = room_data
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_ROOM_CREATE",
                message=f"Создана новая комната Codenames",
                user_id=host_id,
                metadata={"room_id": room_id}
            )

        return room_id if success else None

    def delete_room(self, room_id):
        """Удаляет комнату."""
        rooms = self.load_rooms()
        if room_id in rooms:
            rooms.pop(room_id)
            success = self.save_rooms(rooms)

            if success:
                self.log_service.add_log(
                    level="GAME",
                    action="CODENAMES_ROOM_DELETE",
                    message=f"Удалена комната Codenames",
                    user_id=app.storage.user.get('user_id'),
                    metadata={"room_id": room_id}
                )

            return success
        return False

    def room_exists(self, room_id):
        """Проверяет существование комнаты."""
        rooms = self.load_rooms()
        return room_id in rooms

    def get_room(self, room_id):
        """Получает данные о комнате."""
        rooms = self.load_rooms()
        return rooms.get(room_id)

    def add_player(self, room_id, player_id, player_name):
        """Добавляет игрока в комнату."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, не находится ли уже игрок в комнате
        if any(player["id"] == player_id for player in room["players"]):
            return True

        # Добавляем игрока в комнату без команды
        room["players"].append({
            "id": player_id,
            "name": player_name,
            "is_host": False,
            "joined_at": current_time,
            "last_action": current_time,
            "team": None,
            "role": None
        })

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_PLAYER_JOIN",
                message=f"Игрок присоединился к комнате Codenames",
                user_id=player_id,
                metadata={"room_id": room_id, "player_name": player_name}
            )

        return success

    def remove_player(self, room_id, player_id):
        """Удаляет игрока из комнаты."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Находим игрока
        player_index = next((i for i, p in enumerate(room["players"]) if p["id"] == player_id), -1)
        if player_index == -1:
            return False

        player = room["players"][player_index]

        # Удаляем игрока из команды, если он в ней состоял
        if player.get("team"):
            team_id = player["team"]
            if team_id in room["teams"]:
                team = room["teams"][team_id]
                if team["captain"] == player_id:
                    # Если капитан покидает команду, удаляем всю команду
                    for member_id in team["members"]:
                        for p in room["players"]:
                            if p["id"] == member_id:
                                p["team"] = None
                                p["role"] = None
                    del room["teams"][team_id]
                else:
                    # Удаляем участника из команды
                    if player_id in team["members"]:
                        team["members"].remove(player_id)

        # Удаляем игрока
        room["players"].pop(player_index)

        # Проверяем, является ли игрок хостом
        is_host = player.get("is_host", False)

        # Если комната пуста, удаляем её
        if not room["players"]:
            rooms.pop(room_id)
        # Если хост вышел, назначаем нового хоста
        elif is_host and room["players"]:
            room["players"][0]["is_host"] = True
            room["host_id"] = room["players"][0]["id"]
            room["players"][0]["last_action"] = current_time

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_PLAYER_LEAVE",
                message=f"Игрок покинул комнату Codenames",
                user_id=player_id,
                metadata={"room_id": room_id}
            )

        return success

    def start_game(self, room_id, field):
        """Начинает игру в комнате."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем минимальные требования
        if not self._check_game_requirements(room):
            return False

        # Определяем порядок ходов (случайный выбор первой команды)
        team_ids = list(room["teams"].keys())
        random.shuffle(team_ids)

        # Обновляем данные игры
        room["status"] = "playing"
        room["game_data"]["field"] = field
        room["game_data"]["current_team"] = int(team_ids[0])
        room["game_data"]["turn_order"] = [int(tid) for tid in team_ids]
        room["game_data"]["round"] = 1
        room["game_data"]["game_started"] = True
        room["last_activity"] = current_time

        # Обновляем время действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_GAME_START",
                message=f"Игра Codenames началась",
                user_id=room["host_id"],
                metadata={
                    "room_id": room_id,
                    "team_count": len(room["teams"]),
                    "player_count": len(room["players"]),
                    "first_team": team_ids[0]
                }
            )

        return success

    # Исправления для codenames_room_service.py

    @staticmethod
    def _check_game_requirements(room):
        """Проверяет минимальные требования для начала игры."""
        # Минимум 2 команды с капитанами
        if len(room["teams"]) < 2:
            return False

        # В каждой команде должен быть капитан (участники необязательны)
        for team_id, team in room["teams"].items():
            if not team["captain"]:
                return False
            # Убираем требование минимум одного участника
            # Капитан может играть один в команде

        return True

    def join_team(self, room_id, player_id, team_id, role):
        """Присоединяет игрока к команде в указанной роли."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Находим игрока
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if not player:
            return False

        # ИСПРАВЛЕНИЕ: Сначала удаляем игрока из старой команды
        if player.get("team"):
            old_team_id = player["team"]
            if old_team_id in room["teams"]:
                old_team = room["teams"][old_team_id]
                if old_team["captain"] == player_id:
                    # Если это был капитан, назначаем нового или удаляем команду
                    if old_team["members"]:
                        # Назначаем первого участника новым капитаном
                        new_captain_id = old_team["members"][0]
                        old_team["captain"] = new_captain_id
                        old_team["members"].remove(new_captain_id)
                        # Обновляем роль нового капитана
                        for p in room["players"]:
                            if p["id"] == new_captain_id:
                                p["role"] = "captain"
                                break
                    else:
                        # Команда остается без игроков, удаляем её
                        del room["teams"][old_team_id]
                elif player_id in old_team["members"]:
                    old_team["members"].remove(player_id)

        # Если роль капитан и команда не существует, создаем её
        if role == "captain" and team_id not in room["teams"]:
            team_colors = {
                "1": {"color": "bg-red-500", "name": "Красная"},
                "2": {"color": "bg-blue-500", "name": "Синяя"},
                "3": {"color": "bg-green-500", "name": "Зеленая"},
                "4": {"color": "bg-purple-500", "name": "Фиолетовая"},
                "5": {"color": "bg-orange-500", "name": "Оранжевая"}
            }

            team_info = team_colors.get(team_id, {"color": "bg-gray-500", "name": f"Команда {team_id}"})

            room["teams"][team_id] = {
                "captain": player_id,
                "members": [],
                "color": team_info["color"],
                "name": team_info["name"]
            }
        elif role == "captain" and team_id in room["teams"]:
            # ИСПРАВЛЕНИЕ: Правильно меняем капитана команды
            old_captain_id = room["teams"][team_id]["captain"]
            room["teams"][team_id]["captain"] = player_id

            # Если у команды был старый капитан, делаем его участником
            if old_captain_id and old_captain_id != player_id:
                if old_captain_id not in room["teams"][team_id]["members"]:
                    room["teams"][team_id]["members"].append(old_captain_id)
                # Обновляем роль старого капитана
                for p in room["players"]:
                    if p["id"] == old_captain_id:
                        p["role"] = "member"
                        break

        elif role == "member" and team_id in room["teams"]:
            # Добавляем игрока как участника
            if player_id not in room["teams"][team_id]["members"]:
                room["teams"][team_id]["members"].append(player_id)

        # Обновляем информацию игрока
        player["team"] = team_id
        player["role"] = role
        player["last_action"] = current_time
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_JOIN_TEAM",
                message=f"Игрок присоединился к команде {team_id} как {role}",
                user_id=player_id,
                metadata={"room_id": room_id, "team_id": team_id, "role": role}
            )

        return success

    def update_settings(self, room_id, settings):
        """Обновляет настройки комнаты."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]

        # ИСПРАВЛЕНИЕ: Если изменилось количество команд, нужно проверить существующие команды
        old_team_count = room["settings"].get("team_count", 2)
        new_team_count = settings.get("team_count", old_team_count)

        room["settings"].update(settings)

        # Если уменьшилось количество команд, удаляем лишние
        if new_team_count < old_team_count:
            teams_to_remove = []
            for team_id in room["teams"]:
                if int(team_id) > new_team_count:
                    teams_to_remove.append(team_id)

            for team_id in teams_to_remove:
                # Убираем игроков из удаляемых команд
                team = room["teams"][team_id]
                players_to_reset = [team["captain"]] + team["members"]
                for player_id in players_to_reset:
                    for player in room["players"]:
                        if player["id"] == player_id:
                            player["team"] = None
                            player["role"] = None
                            break
                del room["teams"][team_id]

        room["last_activity"] = int(time.time())

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_UPDATE_SETTINGS",
                message=f"Обновлены настройки комнаты",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id, "settings": settings}
            )

        return success

    def set_hint(self, room_id, player_id, hint_text, hint_count):
        """Устанавливает подсказку от капитана."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что игрок - капитан текущей команды
        current_team = str(room["game_data"]["current_team"])
        if current_team not in room["teams"] or room["teams"][current_team]["captain"] != player_id:
            return False

        # Устанавливаем подсказку
        room["game_data"]["current_hint"] = {
            "text": hint_text,
            "count": hint_count,
            "guesses_made": 0,
            "captain_id": player_id
        }

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_SET_HINT",
                message=f"Капитан дал подсказку: {hint_text} {hint_count}",
                user_id=player_id,
                metadata={"room_id": room_id, "team": current_team, "hint": hint_text, "count": hint_count}
            )

        return success

    def make_guess(self, room_id, player_id, card_index):
        """Обрабатывает угадывание карты игроком."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что игрок в текущей команде
        current_team = room["game_data"]["current_team"]
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if not player or player.get("team") != str(current_team):
            return False

        # Проверяем, что карта существует и не открыта
        field = room["game_data"]["field"]
        if card_index >= len(field) or field[card_index]["revealed"]:
            return False

        # Открываем карту
        card = field[card_index]
        card["revealed"] = True

        # Увеличиваем счетчик попыток
        hint = room["game_data"]["current_hint"]
        if hint:
            hint["guesses_made"] += 1

        # Определяем результат хода
        result = self._process_guess_result(room, card, current_team)

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_MAKE_GUESS",
                message=f"Игрок открыл карту {card['emoji']}",
                user_id=player_id,
                metadata={
                    "room_id": room_id,
                    "team": current_team,
                    "card_team": card["team"],
                    "result": result
                }
            )

        return success

    def _process_guess_result(self, room, card, current_team):
        """Обрабатывает результат угадывания."""
        card_team = card["team"]

        if card_team == -1:
            # Попали на убийцу - команда проигрывает
            room["status"] = "finished"
            room["game_data"]["winner"] = "assassin"
            return "assassin"
        elif card_team == current_team:
            # Угадали свою карту - могут продолжать
            # Проверяем, выиграла ли команда
            if self._check_team_victory(room, current_team):
                room["status"] = "finished"
                room["game_data"]["winner"] = current_team
                return "victory"
            return "correct"
        else:
            # Угадали чужую или нейтральную карту - ход переходит
            self._switch_turn(room)
            return "wrong"

    @staticmethod
    def _check_team_victory(room, team_id):
        """Проверяет, выиграла ли команда."""
        field = room["game_data"]["field"]
        team_cards = [card for card in field if card["team"] == team_id]
        revealed_team_cards = [card for card in team_cards if card["revealed"]]

        return len(revealed_team_cards) == len(team_cards)

    @staticmethod
    def _switch_turn(room):
        """Переключает ход на следующую команду."""
        turn_order = room["game_data"]["turn_order"]
        current_team = room["game_data"]["current_team"]

        try:
            current_index = turn_order.index(current_team)
            next_index = (current_index + 1) % len(turn_order)
            room["game_data"]["current_team"] = turn_order[next_index]
        except ValueError:
            # Если текущая команда не найдена, берем первую
            room["game_data"]["current_team"] = turn_order[0]

        # Сбрасываем подсказку
        room["game_data"]["current_hint"] = None

    def end_turn(self, room_id, player_id):
        """Заканчивает ход команды."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что игрок в текущей команде
        current_team = room["game_data"]["current_team"]
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if not player or player.get("team") != str(current_team):
            return False

        # Переключаем ход
        self._switch_turn(room)

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_END_TURN",
                message=f"Команда {current_team} завершила ход",
                user_id=player_id,
                metadata={"room_id": room_id, "team": current_team}
            )

        return success

    def finish_game(self, room_id):
        """Завершает игру."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        room["status"] = "finished"
        room["last_activity"] = int(time.time())

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_GAME_END",
                message=f"Игра Codenames завершена",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )

        return success

    def reset_game(self, room_id):
        """Сбрасывает игру для повторной игры."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Сбрасываем данные игры
        room["status"] = "waiting"
        room["game_data"] = {
            "field": [],
            "current_team": 1,
            "current_hint": None,
            "round": 0,
            "turn_order": [],
            "game_started": False
        }

        # Обновляем время действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_GAME_RESET",
                message=f"Игра Codenames сброшена",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )

        return success

    def get_rooms_list(self):
        """Возвращает список доступных комнат."""
        rooms = self.load_rooms()
        rooms_list = []

        for room_id, room_data in rooms.items():
            if room_data["status"] == "waiting":
                rooms_list.append({
                    "room_id": room_id,
                    "host_name": next((p["name"] for p in room_data["players"] if p.get("is_host")), "Неизвестно"),
                    "player_count": len(room_data["players"]),
                    "team_count": len(room_data["teams"]),
                    "created_at": room_data["created_at"]
                })

        rooms_list.sort(key=lambda x: x["created_at"], reverse=True)
        return rooms_list