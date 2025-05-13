import json
import os
import time
import random
from nicegui import app
from src.services.log_services import LogService


class ChameleonRoomService:
    """
    Сервис для управления игровыми комнатами в игре Хамелеон.
    Отвечает за создание/удаление комнат, управление игроками, 
    сохранение и загрузку состояний комнат.
    """

    def __init__(self, rooms_file='src/minigame/chameleon/chameleon_rooms.json'):
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
                error_message=f"Ошибка загрузки данных о комнатах: {str(e)}",
                action="CHAMELEON_ROOMS_LOAD"
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
                error_message=f"Ошибка сохранения данных о комнатах: {str(e)}",
                action="CHAMELEON_ROOMS_SAVE"
            )
            return False

    def create_room(self, host_id, host_name):
        """Создает новую комнату."""
        # Генерируем уникальный ID комнаты
        room_id = f"chameleon_{random.randint(1000, 9999)}"
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
                "word": None,
                "chameleon_index": -1,
                "descriptions": [],
                "votes": {},
                "round": 0,
                "current_player_index": 0
            }
        }

        # Сохраняем комнату
        rooms = self.load_rooms()
        rooms[room_id] = room_data
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CHAMELEON_ROOM_CREATE",
                message=f"Создана новая комната Хамелеон",
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
                    action="CHAMELEON_ROOM_DELETE",
                    message=f"Удалена комната Хамелеон",
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
                action="CHAMELEON_PLAYER_JOIN",
                message=f"Игрок присоединился к комнате Хамелеон",
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
                action="CHAMELEON_PLAYER_LEAVE",
                message=f"Игрок покинул комнату Хамелеон",
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
                action="CHAMELEON_PLAYER_READY",
                message=f"Игрок изменил статус готовности",
                user_id=player_id,
                metadata={"room_id": room_id, "is_ready": is_ready}
            )

        return success

    def are_all_players_ready(self, room_id):
        """Проверяет, готовы ли все игроки."""
        room = self.get_room(room_id)
        if not room:
            return False

        return all(player.get("is_ready", False) for player in room["players"])

    def start_game(self, room_id, category, word, grid_words=None):
        """Начинает игру в комнате."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что в комнате достаточно игроков
        if len(room["players"]) < 3:
            return False

        # Выбираем случайного игрока в качестве Хамелеона
        chameleon_index = random.randint(0, len(room["players"]) - 1)

        # Обновляем данные игры
        room["status"] = "playing"
        room["game_data"]["category"] = category
        room["game_data"]["word"] = word
        room["game_data"]["chameleon_index"] = chameleon_index
        room["game_data"]["descriptions"] = []
        room["game_data"]["votes"] = {}
        room["game_data"]["round"] = 1
        room["game_data"]["current_player_index"] = 0

        # Сохраняем сетку слов для стабильного отображения
        if grid_words:
            room["game_data"]["grid_words"] = grid_words

        room["last_activity"] = current_time

        # Обновляем время действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            chameleon_player = room["players"][chameleon_index]
            self.log_service.add_log(
                level="GAME",
                action="CHAMELEON_GAME_START",
                message=f"Игра Хамелеон началась",
                user_id=room["host_id"],
                metadata={
                    "room_id": room_id,
                    "category": category,
                    "word": word,
                    "chameleon_player": chameleon_player["name"],
                    "player_count": len(room["players"])
                }
            )

        return success

    def add_description(self, room_id, player_id, description):
        """Добавляет описание от игрока."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что игра в процессе
        if room["status"] != "playing":
            return False

        # Находим игрока
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if not player:
            return False

        # Обновляем время последнего действия игрока
        player["last_action"] = current_time

        # Добавляем описание
        room["game_data"]["descriptions"].append({
            "player_id": player_id,
            "player_name": player["name"],
            "description": description,
            "timestamp": current_time
        })

        # Переходим к следующему игроку
        room["game_data"]["current_player_index"] = (room["game_data"]["current_player_index"] + 1) % len(
            room["players"])

        # Если все игроки дали описания, переходим к голосованию
        if len(room["game_data"]["descriptions"]) >= len(room["players"]):
            room["game_data"]["round"] = 2  # Раунд голосования

        room["last_activity"] = current_time
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CHAMELEON_DESCRIPTION",
                message=f"Игрок добавил описание",
                user_id=player_id,
                metadata={
                    "room_id": room_id,
                    "description": description,
                    "round": room["game_data"]["round"]
                }
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
                action="CHAMELEON_VOTE",
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

        # Находим Хамелеона
        chameleon_index = room["game_data"]["chameleon_index"]
        chameleon_id = room["players"][chameleon_index]["id"] if 0 <= chameleon_index < len(room["players"]) else None

        # Определяем, был ли пойман Хамелеон
        chameleon_caught = chameleon_id in top_voted

        return {
            "votes": results,
            "max_votes": max_votes,
            "top_voted": top_voted,
            "chameleon_id": chameleon_id,
            "chameleon_caught": chameleon_caught
        }

    def check_chameleon_guess(self, room_id, chameleon_id, word_guess):
        """Проверяет догадку Хамелеона."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return None

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что идет раунд результатов
        if room["status"] != "playing" or room["game_data"]["round"] != 3:
            return None

        # Проверяем, что проверяет именно Хамелеон
        chameleon_index = room["game_data"]["chameleon_index"]
        if chameleon_index < 0 or chameleon_index >= len(room["players"]):
            return None

        actual_chameleon_id = room["players"][chameleon_index]["id"]
        if chameleon_id != actual_chameleon_id:
            return None

        # Обновляем время последнего действия игрока
        chameleon_player = room["players"][chameleon_index]
        chameleon_player["last_action"] = current_time

        # Проверяем догадку
        actual_word = room["game_data"]["word"]
        is_correct = word_guess.lower() == actual_word.lower()

        # Если игра завершена, обновляем статус
        room["status"] = "finished"
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="CHAMELEON_GUESS",
                message=f"Хамелеон сделал предположение",
                user_id=chameleon_id,
                metadata={
                    "room_id": room_id,
                    "guess": word_guess,
                    "actual_word": actual_word,
                    "is_correct": is_correct
                }
            )

        return {
            "is_correct": is_correct,
            "actual_word": actual_word
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
                action="CHAMELEON_GAME_END",
                message=f"Игра Хамелеон завершена",
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
            "word": None,
            "chameleon_index": -1,
            "descriptions": [],
            "votes": {},
            "round": 0,
            "current_player_index": 0
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
                action="CHAMELEON_GAME_RESET",
                message=f"Игра Хамелеон сброшена",
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