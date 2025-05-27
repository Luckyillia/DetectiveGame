import os
import json
import random
from src.services.log.log_services import LogService


class SpyDataService:
    """
    Сервис для работы с данными игры Шпион.
    Отвечает за загрузку категорий и локаций из JSON файла.
    """

    def __init__(self, data_file='src/minigame/spy/categories.json'):
        self.data_file = data_file
        self.log_service = LogService()
        self.categories = []
        self.ensure_data_file_exists()
        self.load_categories()

    def ensure_data_file_exists(self):
        """Проверяет существование файла данных и создает его при необходимости."""
        # Создаем директорию, если она не существует
        directory = os.path.dirname(self.data_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Если файл не существует, создаем его с базовыми данными
        if not os.path.exists(self.data_file):
            default_data = {
                "categories": [
                    {
                        "name": "Украина",
                        "locations": [
                            "Аэропорт «Борисполь»",
                            "Фестиваль «Казантип»",
                            "Банк «Приват»",
                            "Киево-Печерская лавра",
                            "Майдан Независимости",
                            "Одесский порт",
                            "ЧАЭС Реактор № 4"
                        ]
                    },
                    {
                        "name": "Россия",
                        "locations": [
                            "Красная площадь",
                            "Эрмитаж",
                            "Байкал",
                            "Кремль",
                            "Большой театр"
                        ]
                    }
                ]
            }

            try:
                with open(self.data_file, 'w', encoding='utf-8') as file:
                    json.dump(default_data, file, indent=2, ensure_ascii=False)
                self.log_service.add_log(
                    level="SYSTEM",
                    action="SPY_DATA_CREATE",
                    message=f"Создан файл данных категорий: {self.data_file}"
                )
            except Exception as e:
                self.log_service.add_error_log(
                    error_message=f"Ошибка создания файла данных: {str(e)}",
                    action="SPY_DATA_CREATE"
                )

    def load_categories(self):
        """Загружает категории и локации из JSON файла."""
        try:
            # Проверяем абсолютный путь
            if not os.path.isabs(self.data_file):
                # Создаем абсолютный путь от корня проекта
                current_dir = os.getcwd()
                abs_path = os.path.join(current_dir, self.data_file)
            else:
                abs_path = self.data_file

            if not os.path.exists(abs_path):
                self.log_service.add_error_log(
                    error_message=f"Файл данных категорий не найден: {abs_path}",
                    action="SPY_DATA_LOAD"
                )
                self.categories = []
                return

            with open(abs_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.categories = data.get('categories', [])

            self.log_service.add_log(
                level="GAME",
                action="SPY_DATA_LOAD",
                message=f"Загружено {len(self.categories)} категорий для игры Шпион из {abs_path}"
            )
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка загрузки категорий: {str(e)}",
                action="SPY_DATA_LOAD"
            )
            self.categories = []

    def get_all_categories(self):
        """Возвращает список всех категорий."""
        if not self.categories:
            # Пытаемся перезагрузить данные
            self.load_categories()

        categories_list = [category['name'] for category in self.categories]

        # Логируем для отладки
        self.log_service.add_debug_log(
            message=f"Возвращаем категории: {categories_list}",
            metadata={"categories_count": len(categories_list)}
        )

        return categories_list

    def get_locations_for_category(self, category_name):
        """Возвращает список локаций для указанной категории."""
        for category in self.categories:
            if category['name'] == category_name:
                return category['locations']
        return []

    def get_random_category(self):
        """Возвращает случайную категорию."""
        if not self.categories:
            return None
        return random.choice(self.categories)['name']

    def get_random_location_from_category(self, category_name):
        """Возвращает случайную локацию из указанной категории."""
        locations = self.get_locations_for_category(category_name)
        if not locations:
            return None
        return random.choice(locations)

    def get_random_category_and_location(self):
        """Возвращает случайную категорию и локацию из неё."""
        if not self.categories:
            return None, None

        category = random.choice(self.categories)
        category_name = category['name']
        location = random.choice(category['locations'])

        return category_name, location

    def get_category_info(self, category_name):
        """Возвращает полную информацию о категории."""
        for category in self.categories:
            if category['name'] == category_name:
                return category
        return None