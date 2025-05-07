import os
import json
import random
from src.services.log_services import LogService


class ChameleonDataService:
    """
    Сервис для работы с данными игры Хамелеон.
    Отвечает за загрузку категорий и слов из JSON файла.
    """

    def __init__(self, data_file='src/minigame/chameleon/categories.json'):
        self.data_file = data_file
        self.log_service = LogService()
        self.categories = []
        self.load_categories()

    def load_categories(self):
        """Загружает категории и слова из JSON файла."""
        try:
            if not os.path.exists(self.data_file):
                self.log_service.add_error_log(
                    error_message=f"Файл данных категорий не найден: {self.data_file}",
                    action="CHAMELEON_DATA_LOAD"
                )
                self.categories = []
                return

            with open(self.data_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.categories = data.get('categories', [])

            self.log_service.add_log(
                level="GAME",
                action="CHAMELEON_DATA_LOAD",
                message=f"Загружено {len(self.categories)} категорий"
            )
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка загрузки категорий: {str(e)}",
                action="CHAMELEON_DATA_LOAD"
            )
            self.categories = []

    def get_all_categories(self):
        """Возвращает список всех категорий."""
        return [category['name'] for category in self.categories]

    def get_words_for_category(self, category_name):
        """Возвращает список слов для указанной категории."""
        for category in self.categories:
            if category['name'] == category_name:
                return category['words']
        return []

    def get_random_category(self):
        """Возвращает случайную категорию."""
        if not self.categories:
            return None
        return random.choice(self.categories)['name']

    def get_random_word(self, category_name):
        """Возвращает случайное слово из указанной категории."""
        words = self.get_words_for_category(category_name)
        if not words:
            return None
        return random.choice(words)

    def get_random_category_and_word(self):
        """Возвращает случайную категорию и слово из неё."""
        if not self.categories:
            return None, None

        category = random.choice(self.categories)
        category_name = category['name']
        word = random.choice(category['words'])

        return category_name, word