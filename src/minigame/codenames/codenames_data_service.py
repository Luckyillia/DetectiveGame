import os
import json
import random
from src.services.log.log_services import LogService


class CodenamesDataService:
    """
    Сервис для работы с данными игры Codenames.
    Отвечает за загрузку эмоджи из JSON файла и генерацию игрового поля.
    """

    def __init__(self, data_file='src/minigame/codenames/emoji.json'):
        self.data_file = data_file
        self.log_service = LogService()
        self.emojis = []
        self.ensure_data_file_exists()
        self.load_emojis()

    def ensure_data_file_exists(self):
        """Проверяет существование файла данных и создает его при необходимости."""
        directory = os.path.dirname(self.data_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Если файл не существует, создаем его с базовыми эмоджи
        if not os.path.exists(self.data_file):
            default_emojis = [
                "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", "🫠", "😉", "😊", "😇",
                "🥰", "😍", "🤩", "😘", "😗", "☺️", "😚", "😙", "🥲", "😋", "😛", "😜", "🤪", "😝",
                "🤑", "🤗", "🤭", "🫢", "🫣", "🤫", "🤔", "🫡", "🤐", "🤨", "😐", "😑", "😶", "🫥",
                "😶‍🌫️", "😏", "😒", "🙄", "😬", "😮‍💨", "🤥", "😔", "😪", "🤤", "😴", "😷", "🤒",
                "🤕", "🤢", "🤮", "🤧", "🥵", "🥶", "🥴", "😵", "😵‍💫", "🤯", "🤠", "🥳", "🥸",
                "😎", "🤓", "🧐", "😕", "🫤", "😟", "🙁", "☹️", "😮", "😯", "😲", "😳", "🥺", "🥹",
                "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖", "😣", "😞", "😓", "😩", "😫",
                "🥱", "😤", "😡", "😠", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👹", "👺", "👻",
                "👽", "👾", "🤖", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾"
            ]

            try:
                with open(self.data_file, 'w', encoding='utf-8') as file:
                    json.dump(default_emojis, file, indent=2, ensure_ascii=False)
                self.log_service.add_log(
                    level="SYSTEM",
                    action="CODENAMES_DATA_CREATE",
                    message=f"Создан файл данных эмоджи: {self.data_file}"
                )
            except Exception as e:
                self.log_service.add_error_log(
                    error_message=f"Ошибка создания файла данных: {str(e)}",
                    action="CODENAMES_DATA_CREATE"
                )

    def load_emojis(self):
        """Загружает эмоджи из JSON файла."""
        try:
            if not os.path.isabs(self.data_file):
                current_dir = os.getcwd()
                abs_path = os.path.join(current_dir, self.data_file)
            else:
                abs_path = self.data_file

            if not os.path.exists(abs_path):
                self.log_service.add_error_log(
                    error_message=f"Файл данных эмоджи не найден: {abs_path}",
                    action="CODENAMES_DATA_LOAD"
                )
                self.emojis = []
                return

            with open(abs_path, 'r', encoding='utf-8') as file:
                self.emojis = json.load(file)

            self.log_service.add_log(
                level="GAME",
                action="CODENAMES_DATA_LOAD",
                message=f"Загружено {len(self.emojis)} эмоджи для игры Codenames из {abs_path}"
            )
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка загрузки эмоджи: {str(e)}",
                action="CODENAMES_DATA_LOAD"
            )
            self.emojis = []

    def _get_field_config(self, team_count):
        """Возвращает конфигурацию поля для указанного количества команд."""
        configs = {
            2: {
                'grid_size': 5,
                'team_counts': {1: 9, 2: 8},
                'neutral_count': 7
            },
            3: {
                'grid_size': 5,
                'team_counts': {1: 7, 2: 7, 3: 6},
                'neutral_count': 4
            },
            4: {
                'grid_size': 6,
                'team_counts': {1: 8, 2: 8, 3: 7, 4: 7},
                'neutral_count': 5
            },
            5: {
                'grid_size': 7,
                'team_counts': {1: 9, 2: 9, 3: 8, 4: 8, 5: 8},
                'neutral_count': 6
            }
        }
        return configs.get(team_count, configs[2])

    def generate_game_field(self, team_count):
        """
        Генерирует игровое поле для указанного количества команд.

        Args:
            team_count: Количество команд (2-5)

        Returns:
            list: Список словарей с информацией о каждой карте
        """
        if not self.emojis:
            self.load_emojis()

        config = self._get_field_config(team_count)
        grid_size = config['grid_size']
        total_cards = grid_size * grid_size

        # Получаем случайные эмоджи
        selected_emojis = random.sample(self.emojis, min(total_cards, len(self.emojis)))

        # Создаем список типов карт
        card_types = []

        # Добавляем карты команд
        for team_id, count in config['team_counts'].items():
            card_types.extend([team_id] * count)

        # Добавляем нейтральные карты
        card_types.extend([0] * config['neutral_count'])

        # Добавляем карту убийцы
        card_types.append(-1)

        # Перемешиваем типы карт
        random.shuffle(card_types)

        # Создаем поле
        field = []
        for i in range(total_cards):
            field.append({
                'emoji': selected_emojis[i],
                'team': card_types[i],  # -1: убийца, 0: нейтральная, 1-5: команды
                'revealed': False,
                'row': i // grid_size,
                'col': i % grid_size
            })

        self.log_service.add_log(
            level="GAME",
            action="CODENAMES_FIELD_GENERATE",
            message=f"Сгенерировано поле {grid_size}x{grid_size} для {team_count} команд",
            metadata={
                "grid_size": grid_size,
                "team_count": team_count,
                "total_cards": total_cards
            }
        )

        return field

    def get_team_colors(self, team_count):
        """Возвращает цвета для команд."""
        colors = {
            1: "bg-red-500",
            2: "bg-blue-500",
            3: "bg-green-500",
            4: "bg-purple-500",
            5: "bg-orange-500"
        }

        return {team_id: colors[team_id] for team_id in range(1, team_count + 1)}

    def get_team_names(self, team_count):
        """Возвращает названия для команд."""
        names = {
            1: "Красная",
            2: "Синяя",
            3: "Зеленая",
            4: "Фиолетовая",
            5: "Оранжевая"
        }

        return {team_id: names[team_id] for team_id in range(1, team_count + 1)}

    def get_grid_size(self, team_count):
        """Возвращает размер сетки для указанного количества команд."""
        config = self._get_field_config(team_count)
        return config['grid_size']