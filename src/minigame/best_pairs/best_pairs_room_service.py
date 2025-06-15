import json
import os
import time
import random
from nicegui import app
from src.services.log.log_services import LogService


class BestPairsRoomService:
    """
    Сервис для управления игровыми комнатами в игре Лучшие Пары.
    Отвечает за создание/удаление комнат, управление игроками,
    сохранение и загрузку состояний комнат.
    """

    def __init__(self, rooms_file='src/minigame/best_pairs/best_pairs_rooms.json'):
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
                error_message=f"Ошибка загрузки данных о комнатах Лучшие Пары: {str(e)}",
                action="BEST_PAIRS_ROOMS_LOAD"
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
                error_message=f"Ошибка сохранения данных о комнатах Лучшие Пары: {str(e)}",
                action="BEST_PAIRS_ROOMS_SAVE"
            )
            return False

    def create_room(self, host_id, host_name):
        """Создает новую комнату."""
        # Генерируем уникальный ID комнаты
        room_id = f"pairs_{random.randint(1000, 9999)}"
        current_time = int(time.time())

        # Создаем структуру данных комнаты
        room_data = {
            "room_id": room_id,
            "created_at": current_time,
            "last_activity": current_time,
            "status": "waiting",  # waiting, playing, finished
            "host_id": host_id,
            "current_host_index": 0,  # Индекс текущего ведущего
            "rounds_played": 0,  # Количество сыгранных раундов
            "players": [
                {
                    "id": host_id,
                    "name": host_name,
                    "is_host": True,
                    "joined_at": current_time,
                    "last_action": current_time,
                    "is_ready": True,
                    "score": 0,
                    "rounds_as_host": 0
                }
            ],
            "game_data": {
                "nouns": [],  # 5 существительных
                "adjectives": [],  # 5 прилагательных
                "host_pairings": {},  # Как ведущий разложил пары {noun_index: adjective}
                "player_guesses": {},  # Догадки игроков {player_id: {noun_index: adjective}}
                "round": 0,  # 0-waiting, 1-host_pairing, 2-players_guessing, 3-results, 4-round_end
                "current_round_host": host_id,
                "round_scores": {}  # Очки за текущий раунд
            }
        }

        # Сохраняем комнату
        rooms = self.load_rooms()
        rooms[room_id] = room_data
        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_ROOM_CREATE",
                message=f"Создана новая комната Лучшие Пары",
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
                    action="BEST_PAIRS_ROOM_DELETE",
                    message=f"Удалена комната Лучшие Пары",
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

        # Проверяем, не находится ли игрок уже в комнате
        existing_player = next((p for p in room["players"] if p["id"] == player_id), None)
        if existing_player:
            # Обновляем время последнего действия
            existing_player["last_action"] = current_time
            room["last_activity"] = current_time
            return self.save_rooms(rooms)

        # Добавляем нового игрока
        new_player = {
            "id": player_id,
            "name": player_name,
            "is_host": False,
            "joined_at": current_time,
            "last_action": current_time,
            "is_ready": False,
            "score": 0,
            "rounds_as_host": 0
        }

        room["players"].append(new_player)
        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_PLAYER_JOIN",
                message=f"Игрок присоединился к комнате",
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

        # Находим и удаляем игрока
        room["players"] = [p for p in room["players"] if p["id"] != player_id]
        room["last_activity"] = current_time

        # Если не осталось игроков, удаляем комнату
        if not room["players"]:
            return self.delete_room(room_id)

        # Если удаленный игрок был хостом, назначаем нового
        if not any(p.get("is_host") for p in room["players"]) and room["players"]:
            room["players"][0]["is_host"] = True
            room["host_id"] = room["players"][0]["id"]

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_PLAYER_LEAVE",
                message=f"Игрок покинул комнату",
                user_id=player_id,
                metadata={"room_id": room_id}
            )

        return success

    def set_player_ready(self, room_id, player_id, is_ready):
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
                action="BEST_PAIRS_PLAYER_READY",
                message=f"Игрок изменил статус готовности",
                user_id=player_id,
                metadata={"room_id": room_id, "is_ready": is_ready}
            )

        return success

    def all_players_ready(self, room_id):
        """Проверяет, все ли игроки готовы."""
        room = self.get_room(room_id)
        if not room:
            return False

        return all(player.get("is_ready", False) for player in room["players"])

    def start_round(self, room_id, nouns, adjectives):
        """Начинает новый раунд игры."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что в комнате достаточно игроков
        if len(room["players"]) < 2:
            return False

        # Определяем следующего ведущего
        current_host_index = room["current_host_index"]
        current_host = room["players"][current_host_index]

        # Обновляем данные игры
        room["status"] = "playing"
        room["game_data"]["nouns"] = nouns
        room["game_data"]["adjectives"] = adjectives
        room["game_data"]["host_pairings"] = {}
        room["game_data"]["player_guesses"] = {}
        room["game_data"]["round"] = 1  # Ведущий раскладывает пары
        room["game_data"]["current_round_host"] = current_host["id"]
        room["game_data"]["round_scores"] = {}

        room["last_activity"] = current_time

        # Обновляем время действия для всех игроков
        for player in room["players"]:
            player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_ROUND_START",
                message=f"Начался новый раунд",
                user_id=room["host_id"],
                metadata={
                    "room_id": room_id,
                    "round_host": current_host["name"],
                    "player_count": len(room["players"])
                }
            )

        return success

    def set_host_pairings(self, room_id, host_id, pairings):
        """Сохраняет пары, составленные ведущим."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что это действительно ведущий раунда
        if room["game_data"]["current_round_host"] != host_id:
            return False

        # Сохраняем пары
        room["game_data"]["host_pairings"] = pairings
        room["game_data"]["round"] = 2  # Переходим к угадыванию
        room["last_activity"] = current_time

        # Обновляем время действия ведущего
        host_player = next((p for p in room["players"] if p["id"] == host_id), None)
        if host_player:
            host_player["last_action"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_HOST_SET",
                message=f"Ведущий разложил пары",
                user_id=host_id,
                metadata={"room_id": room_id}
            )

        return success

    def submit_player_guess(self, room_id, player_id, guesses):
        """Сохраняет догадки игрока."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Проверяем, что идет раунд угадывания
        if room["game_data"]["round"] != 2:
            return False

        # Проверяем, что это не ведущий
        if room["game_data"]["current_round_host"] == player_id:
            return False

        # Сохраняем догадки
        room["game_data"]["player_guesses"][player_id] = guesses
        room["last_activity"] = current_time

        # Обновляем время действия игрока
        player = next((p for p in room["players"] if p["id"] == player_id), None)
        if player:
            player["last_action"] = current_time

        # Если все игроки (кроме ведущего) сделали догадки, переходим к результатам
        non_host_players = [p for p in room["players"] if p["id"] != room["game_data"]["current_round_host"]]
        if len(room["game_data"]["player_guesses"]) >= len(non_host_players):
            room["game_data"]["round"] = 3  # Результаты

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_GUESS_SUBMIT",
                message=f"Игрок отправил догадки",
                user_id=player_id,
                metadata={"room_id": room_id}
            )

        return success

    def calculate_round_scores(self, room_id):
        """Подсчитывает очки за раунд."""
        room = self.get_room(room_id)
        if not room or room["game_data"]["round"] != 3:
            return None

        host_pairings = room["game_data"]["host_pairings"]
        player_guesses = room["game_data"]["player_guesses"]
        scores = {}
        host_bonus = 0

        # Подсчитываем очки для каждого игрока
        for player_id, guesses in player_guesses.items():
            correct_count = 0
            for noun_idx, adj in guesses.items():
                if host_pairings.get(str(noun_idx)) == adj:
                    correct_count += 1

            # 2 очка за каждое совпадение
            player_score = correct_count * 2
            scores[player_id] = player_score

            # Бонус ведущему за каждого игрока, угадавшего >= 3 пар
            if correct_count >= 3:
                host_bonus += 1

        # Добавляем бонус ведущему
        host_id = room["game_data"]["current_round_host"]
        scores[host_id] = scores.get(host_id, 0) + host_bonus

        return scores

    def apply_round_scores(self, room_id):
        """Применяет подсчитанные очки к общему счету."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        scores = self.calculate_round_scores(room_id)

        if not scores:
            return False

        # Применяем очки
        for player in room["players"]:
            if player["id"] in scores:
                player["score"] += scores[player["id"]]

        # Сохраняем очки раунда
        room["game_data"]["round_scores"] = scores
        room["game_data"]["round"] = 4  # Конец раунда
        room["last_activity"] = int(time.time())

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_SCORES_APPLIED",
                message=f"Подсчитаны очки за раунд",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id, "scores": scores}
            )

        return success

    def next_round(self, room_id):
        """Переходит к следующему раунду."""
        rooms = self.load_rooms()
        if room_id not in rooms:
            return False

        room = rooms[room_id]
        current_time = int(time.time())

        # Увеличиваем счетчик раундов
        room["rounds_played"] += 1

        # Переходим к следующему ведущему
        room["current_host_index"] = (room["current_host_index"] + 1) % len(room["players"])

        # Увеличиваем счетчик раундов для прошлого ведущего
        prev_host_id = room["game_data"]["current_round_host"]
        prev_host = next((p for p in room["players"] if p["id"] == prev_host_id), None)
        if prev_host:
            prev_host["rounds_as_host"] += 1

        # Сбрасываем состояние для нового раунда
        room["status"] = "waiting"
        room["game_data"] = {
            "nouns": [],
            "adjectives": [],
            "host_pairings": {},
            "player_guesses": {},
            "round": 0,
            "current_round_host": room["players"][room["current_host_index"]]["id"],
            "round_scores": {}
        }

        # Сбрасываем готовность игроков
        for player in room["players"]:
            player["is_ready"] = False
            player["last_action"] = current_time

        room["last_activity"] = current_time

        success = self.save_rooms(rooms)

        if success:
            self.log_service.add_log(
                level="GAME",
                action="BEST_PAIRS_NEXT_ROUND",
                message=f"Переход к следующему раунду",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id, "rounds_played": room["rounds_played"]}
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