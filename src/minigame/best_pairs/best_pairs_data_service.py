import json
import os
import random
from src.services.log.log_services import LogService


class BestPairsDataService:
    """
    Сервис для работы с данными игры Лучшие Пары.
    Управляет карточками существительных и прилагательных.
    """

    def __init__(self, data_file='src/minigame/best_pairs/best_pairs_data.json'):
        self.data_file = data_file
        self.log_service = LogService()
        self.ensure_data_file_exists()

    def ensure_data_file_exists(self):
        """Проверяет существование файла с данными и создает его при необходимости."""
        directory = os.path.dirname(self.data_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

        if not os.path.exists(self.data_file):
            default_data = self.get_default_data()
            self.save_data(default_data)

    def get_default_data(self):
        """Возвращает стандартный набор данных для игры."""
        return {
            "nouns": {
                "Животные": ["Кот", "Собака", "Слон", "Тигр", "Медведь", "Лиса", "Волк", "Заяц",
                             "Лев", "Обезьяна", "Жираф", "Зебра", "Крокодил", "Дельфин", "Орел"],
                "Еда": ["Торт", "Пицца", "Суп", "Салат", "Мороженое", "Хлеб", "Сыр", "Яблоко",
                        "Банан", "Шоколад", "Кофе", "Чай", "Молоко", "Мясо", "Рыба"],
                "Предметы": ["Стол", "Стул", "Книга", "Телефон", "Компьютер", "Машина", "Велосипед",
                             "Дом", "Окно", "Дверь", "Часы", "Сумка", "Ключ", "Зеркало", "Лампа"],
                "Природа": ["Дерево", "Цветок", "Гора", "Река", "Море", "Озеро", "Лес", "Поле",
                            "Небо", "Облако", "Солнце", "Луна", "Звезда", "Дождь", "Снег"],
                "Люди": ["Учитель", "Врач", "Художник", "Музыкант", "Спортсмен", "Ребенок", "Студент",
                         "Родитель", "Друг", "Сосед", "Начальник", "Коллега", "Клиент", "Продавец", "Водитель"]
            },
            "adjectives": {
                "Размер": ["Большой", "Маленький", "Огромный", "Крошечный", "Широкий", "Узкий",
                           "Высокий", "Низкий", "Длинный", "Короткий", "Толстый", "Тонкий"],
                "Цвет": ["Красный", "Синий", "Зеленый", "Желтый", "Черный", "Белый", "Серый",
                         "Оранжевый", "Фиолетовый", "Розовый", "Коричневый", "Золотой"],
                "Характер": ["Добрый", "Злой", "Веселый", "Грустный", "Смелый", "Трусливый",
                             "Умный", "Глупый", "Хитрый", "Честный", "Ленивый", "Трудолюбивый"],
                "Состояние": ["Новый", "Старый", "Чистый", "Грязный", "Мокрый", "Сухой", "Горячий",
                              "Холодный", "Твердый", "Мягкий", "Острый", "Тупой", "Гладкий", "Шершавый"],
                "Качество": ["Красивый", "Уродливый", "Интересный", "Скучный", "Полезный", "Вредный",
                             "Дорогой", "Дешевый", "Быстрый", "Медленный", "Сильный", "Слабый"],
                "Вкус": ["Сладкий", "Соленый", "Кислый", "Горький", "Острый", "Пресный", "Вкусный",
                         "Невкусный", "Ароматный", "Свежий", "Испорченный", "Пряный"]
            }
        }

    def load_data(self):
        """Загружает данные из файла."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка загрузки данных игры: {str(e)}",
                action="BEST_PAIRS_DATA_LOAD"
            )
            return self.get_default_data()

    def save_data(self, data):
        """Сохраняет данные в файл."""
        try:
            directory = os.path.dirname(self.data_file)
            if not os.path.exists(directory):
                os.makedirs(directory)

            temp_file = f"{self.data_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)

            os.replace(temp_file, self.data_file)
            return True
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка сохранения данных игры: {str(e)}",
                action="BEST_PAIRS_DATA_SAVE"
            )
            return False

    def get_categories(self):
        """Возвращает список доступных категорий."""
        data = self.load_data()
        return {
            "nouns": list(data.get("nouns", {}).keys()),
            "adjectives": list(data.get("adjectives", {}).keys())
        }

    def get_random_cards(self, noun_category=None, adjective_category=None, count=5):
        """
        Возвращает случайные карточки для игры.

        Args:
            noun_category: Категория существительных (если None - случайная)
            adjective_category: Категория прилагательных (если None - случайная)
            count: Количество карточек

        Returns:
            dict: {"nouns": [...], "adjectives": [...]}
        """
        data = self.load_data()

        # Выбираем категории
        if not noun_category:
            noun_category = random.choice(list(data["nouns"].keys()))
        if not adjective_category:
            adjective_category = random.choice(list(data["adjectives"].keys()))

        # Получаем списки слов
        nouns_list = data["nouns"].get(noun_category, [])
        adjectives_list = data["adjectives"].get(adjective_category, [])

        # Проверяем, что есть достаточно карточек
        if len(nouns_list) < count or len(adjectives_list) < count:
            # Если в категории недостаточно слов, берем из всех категорий
            all_nouns = []
            all_adjectives = []

            for cat_nouns in data["nouns"].values():
                all_nouns.extend(cat_nouns)
            for cat_adjs in data["adjectives"].values():
                all_adjectives.extend(cat_adjs)

            nouns_list = all_nouns
            adjectives_list = all_adjectives

        # Выбираем случайные карточки
        selected_nouns = random.sample(nouns_list, min(count, len(nouns_list)))
        selected_adjectives = random.sample(adjectives_list, min(count, len(adjectives_list)))

        return {
            "nouns": selected_nouns,
            "adjectives": selected_adjectives,
            "noun_category": noun_category,
            "adjective_category": adjective_category
        }

    def add_custom_word(self, word_type, category, word):
        """Добавляет пользовательское слово в категорию."""
        data = self.load_data()

        if word_type not in ["nouns", "adjectives"]:
            return False

        if category not in data[word_type]:
            data[word_type][category] = []

        if word not in data[word_type][category]:
            data[word_type][category].append(word)
            return self.save_data(data)

        return True

    def remove_word(self, word_type, category, word):
        """Удаляет слово из категории."""
        data = self.load_data()

        if word_type not in ["nouns", "adjectives"]:
            return False

        if category in data[word_type] and word in data[word_type][category]:
            data[word_type][category].remove(word)
            return self.save_data(data)

        return False