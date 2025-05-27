import json
import os
import time
import random
from nicegui import app
from src.services.log.log_services import LogService


class SpyRoomService:
    """
    Сервис для управления игровыми комнатами в игре Шпион.
    Отвечает за создание/удаление комнат, управление игроками,
    сохранение и загрузку состояний комнат.
    """

    def __init__(self, rooms_file='src/minigame/spy/spy_rooms.json'):
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
                error_message=f"Ошибка загрузки данных о комнатах Шпион: {str(e)}",
                action="SPY_ROOMS_LOAD"
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
                error_message=f"Ошибка сохранения данных о комнатах Шпион: {str(e)}",
                action="SPY_ROOMS_SAVE"
            )
            return False

    def create_room(self, host_id, host_name):
        """Создает новую комнату."""
        # Генерируем уникальный ID комнаты
        room_id = f"spy_{random.randint(1000, 9999)}"
        current_time = int(time.time())

        # Создаем структуру данных комнаты
        room_data = {
            "room_id": room_id,
            "created_at": current_time,
            "last_activity": current_time,
            "status": "waiting",  # waiting, playing, finished
            "host_id": host_id,
            "players": [
                {
                    "id": host_id,
                    "name": host_name,
                    "is_host": True,
                    "joined_at": current_time,
                    "last_action": current_time,
                    "is_ready": True
                }
            ],
            "game_data": {
                "category": None,
                "location": None,
                "spy_index": -1,
                "votes": {},
                "round": 0,  # 0-waiting, 1-playing, 2-voting, 3-results
                "time_per_round": 300  # 5 минут на раунд обсуждения
            }
        }

        # Сохраняем комнату
        rooms = self.load_rooms()
        rooms[room_id] = room_data
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_ROOM_CREATE",
                message=f"Создана новая комната Шпион",
                user_id=host_id,
                metadata={"room_id": room_id}
            )

        return room_id if success else None

    def delete_room(self, room_id):
        """Удаляет комнату."""
        rooms = self.load_rooms()
        if room_id in rooms:
            room_data = rooms.pop(room_id)
            success = self.save_rooms(rooms)

            if success:
                self.log_service.add_log(
                    level="GAME",
                    action="SPY_ROOM_DELETE",
                    message=f"Удалена комната Шпион",
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

        # Добавляем игрока
        room["players"].append({
            "id": player_id,
            "name": player_name,
            "is_host": False,
            "joined_at": current_time,
            "last_action": current_time,
            "is_ready": False
        })

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_PLAYER_JOIN",
                message=f"Игрок присоединился к комнате Шпион",
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

        # Проверяем, является ли игрок хостом
        is_host = player.get("is_host", False)

        # Удаляем игрока
        room["players"].pop(player_index)
        room["last_activity"] = current_time

        # Если комната пуста, удаляем её
        if not room["players"]:
            rooms.pop(room_id)
        # Если хост вышел, назначаем нового хоста
        elif is_host and room["players"]:
            room["players"][0]["is_host"] = True
            room["host_id"] = room["players"][0]["id"]
            room["players"][0]["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_PLAYER_LEAVE",
                message=f"Игрок покинул комнату Шпион",
                user_id=player_id,
                metadata={"room_id": room_id}
            )

        return success

    def set_player_ready(self, room_id, player_id, is_ready=True):
        """Устанавливает статус готовности игрока."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Находим игрока
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if not player:
            return False

        # Устанавливаем статус готовности и время последнего действия
        player["is_ready"] = is_ready
        player["last_action"] = current_time
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_PLAYER_READY",
                message=f"Игрок изменил статус готовности",
                user_id=player_id,
                metadata={"room_id": room_id, "is_ready": is_ready}
            )

        return success

    def start_game(self, room_id, category, location):
        """Начинает игру в комнате."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что в комнате достаточно игроков
        if len(room["players"]) < 3:
            return False

        # Выбираем случайного игрока в качестве Шпиона
        spy_index = random.randint(0, len(room["players"]) - 1)

        # Обновляем данные игры
        room["status"] = "playing"
        room["game_data"]["category"] = category
        room["game_data"]["location"] = location
        room["game_data"]["spy_index"] = spy_index
        room["game_data"]["votes"] = {}
        room["game_data"]["round"] = 1
        room["game_data"]["round_start_time"] = current_time

        room["last_activity"] = current_time

        # Обновляем время действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            spy_player = room["players"][spy_index]
            self.log_service.add_log(
                level="GAME",
                action="SPY_GAME_START",
                message=f"Игра Шпион началась",
                user_id=room["host_id"],
                metadata={
                    "room_id": room_id,
                    "category": category,
                    "location": location,
                    "spy_player": spy_player["name"],
                    "player_count": len(room["players"])
                }
            )

        return success

    def start_voting_round(self, room_id):
        """Переводит игру в раунд голосования."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        if room["status"] != "playing" or room["game_data"]["round"] != 1:
            return False

        room["game_data"]["round"] = 2
        room["game_data"]["votes"] = {}
        room["game_data"]["voting_start_time"] = current_time
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_VOTING_START",
                message=f"Начался раунд голосования",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )

        return success

    def add_vote(self, room_id, voter_id, voted_id):
        """Добавляет голос от игрока."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что идет раунд голосования
        if room["status"] != "playing" or room["game_data"]["round"] != 2:
            return False

        # Находим голосующего игрока
        voter = next((p for p in room["players"] if p["id"] == voter_id), None)
        if not voter:
            return False

        # Находим игрока, за которого голосуют
        voted = next((p for p in room["players"] if p["id"] == voted_id), None)
        if not voted:
            return False

        # Обновляем время последнего действия игрока
        voter["last_action"] = current_time

        # Добавляем голос
        room["game_data"]["votes"][voter_id] = voted_id
        room["last_activity"] = current_time

        # Если все проголосовали, переходим к результатам
        if len(room["game_data"]["votes"]) >= len(room["players"]):
            room["game_data"]["round"] = 3  # Раунд результатов

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_VOTE",
                message=f"Игрок проголосовал",
                user_id=voter_id,
                metadata={
                    "room_id": room_id,
                    "voted_for": voted["name"],
                    "round": room["game_data"]["round"]
                }
            )

        return success

    def get_vote_results(self, room_id):
        """Получает результаты голосования."""
        room = self.get_room(room_id)
        if not room or room["status"] != "playing" or room["game_data"]["round"] < 3:
            return None

        votes = room["game_data"]["votes"]
        results = {}

        # Подсчитываем голоса
        for voted_id in votes.values():
            results[voted_id] = results.get(voted_id, 0) + 1

        # Определяем, кто набрал больше всего голосов
        max_votes = 0
        top_voted = []

        for player_id, vote_count in results.items():
            if vote_count > max_votes:
                max_votes = vote_count
                top_voted = [player_id]
            elif vote_count == max_votes:
                top_voted.append(player_id)

        # Находим Шпиона
        spy_index = room["game_data"]["spy_index"]
        spy_id = room["players"][spy_index]["id"] if 0 <= spy_index < len(room["players"]) else None

        # Определяем, был ли пойман Шпион
        spy_caught = spy_id in top_voted

        return {
            "votes": results,
            "max_votes": max_votes,
            "top_voted": top_voted,
            "spy_id": spy_id,
            "spy_caught": spy_caught
        }

    def check_spy_guess(self, room_id, spy_id, location_guess):
        """Проверяет догадку Шпиона о локации."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return None

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что идет раунд результатов
        if room["status"] != "playing" or room["game_data"]["round"] != 3:
            return None

        # Проверяем, что проверяет именно Шпион
        spy_index = room["game_data"]["spy_index"]
        if spy_index < 0 or spy_index >= len(room["players"]):
            return None

        actual_spy_id = room["players"][spy_index]["id"]
        if spy_id != actual_spy_id:
            return None

        # Обновляем время последнего действия игрока
        spy_player = room["players"][spy_index]
        spy_player["last_action"] = current_time

        # Проверяем догадку
        actual_location = room["game_data"]["location"]
        is_correct = location_guess.lower() == actual_location.lower()

        # Если игра завершена, обновляем статус
        room["status"] = "finished"
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_GUESS",
                message=f"Шпион сделал предположение о локации",
                user_id=spy_id,
                metadata={
                    "room_id": room_id,
                    "guess": location_guess,
                    "actual_location": actual_location,
                    "is_correct": is_correct
                }
            )

        return {
            "is_correct": is_correct,
            "actual_location": actual_location
        }

    def finish_game(self, room_id):
        """Завершает игру."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        room["status"] = "finished"
        room["last_activity"] = current_time

        # Обновляем время последнего действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_GAME_END",
                message=f"Игра Шпион завершена",
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
            "category": None,
            "location": None,
            "spy_index": -1,
            "votes": {},
            "round": 0,
            "time_per_round": 300
        }

        # Сбрасываем готовность игроков и обновляем время действия
        for player in room["players"]:
            player["is_ready"] = player.get("is_host", False)
            player["last_action"] = current_time

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="SPY_GAME_RESET",
                message=f"Игра Шпион сброшена",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )

        return success

    def get_rooms_list(self):
        """Возвращает список доступных комнат."""
        rooms = self.load_rooms()
        rooms_list = []

        for room_id, room_data in rooms.items():
            # Добавляем только комнаты в состоянии ожидания
            if room_data["status"] == "waiting":
                rooms_list.append({
                    "room_id": room_id,
                    "host_name": next((p["name"] for p in room_data["players"] if p.get("is_host")), "Неизвестно"),
                    "player_count": len(room_data["players"]),
                    "created_at": room_data["created_at"]
                })

        # Сортируем по времени создания (новые первыми)
        rooms_list.sort(key=lambda x: x["created_at"], reverse=True)

        return rooms_list