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
            "nouns": [
                "Кот", "Собака", "Слон", "Тигр", "Медведь", "Лиса", "Волк", "Заяц",
                "Лев", "Обезьяна", "Жираф", "Зебра", "Крокодил", "Дельфин", "Орел",
                "Торт", "Пицца", "Суп", "Салат", "Мороженое", "Хлеб", "Сыр", "Яблоко",
                "Банан", "Шоколад", "Кофе", "Чай", "Молоко", "Мясо", "Рыба",
                "Стол", "Стул", "Книга", "Телефон", "Компьютер", "Машина", "Велосипед",
                "Дом", "Окно", "Дверь", "Часы", "Сумка", "Ключ", "Зеркало", "Лампа",
                "Дерево", "Цветок", "Гора", "Река", "Море", "Озеро", "Лес", "Поле",
                "Небо", "Облако", "Солнце", "Луна", "Звезда", "Дождь", "Снег",
                "Учитель", "Врач", "Художник", "Музыкант", "Спортсмен", "Ребенок", "Студент",
                "Родитель", "Друг", "Сосед", "Начальник", "Коллега", "Клиент", "Продавец",
                "Водитель", "Пилот", "Повар", "Официант", "Программист", "Дизайнер", "Менеджер",
                "Город", "Деревня", "Страна", "Планета", "Космос", "Вселенная", "Галактика",
                "Корабль", "Самолет", "Поезд", "Автобус", "Метро", "Трамвай", "Такси",
                "Магазин", "Рынок", "Кафе", "Ресторан", "Театр", "Кино", "Музей",
                "Школа", "Университет", "Библиотека", "Больница", "Аптека", "Банк", "Почта",
                "Парк", "Сад", "Площадь", "Улица", "Мост", "Тоннель", "Башня",
                "Игра", "Спорт", "Музыка", "Танец", "Песня", "Фильм", "Картина",
                "Праздник", "День", "Ночь", "Утро", "Вечер", "Лето", "Зима",
                "Весна", "Осень", "Год", "Месяц", "Неделя", "Час", "Минута"
            ],
            "adjectives": [
                "Заброшенный", "Способный", "Абсолютный", "Академический", "Приемлемый", "Признанный", "Точный",
                "Кислый", "Акробатический", "Авантюрный", "Младенческий", "Плохой", "Мешковатый", "Токсичный",
                "Добрый", "Голый", "Бесплодный", "Основной", "Прекрасный", "Запоздалый", "Любимый",
                "Откровенный", "Собачий", "Беззаботный", "Осторожный", "Небрежный", "Кавернозный", "Очаровательный",
                "Сырой", "Опасный", "Щеголеватый", "Дерзкий", "Дорогой", "Ослепительный", "Смертельный",
                "Оглушительный", "Каждый", "Нетерпеливый", "Серьезный", "Восторженный", "Съедобный", "Образованный",
                "Сказочный", "Слабый", "Верный", "Известный", "Расплывчатый", "Гигантский", "Газообразный",
                "Щедрый", "Нежный", "Подлинный", "Волосатый", "Красивый", "Удобный", "Счастливый",
                "Жесткий", "Неприятный", "Ледяной", "Идеальный", "Идеалистический", "Идентичный", "Идиотский",
                "Праздный", "Невежественный", "Больной", "Незаконный", "Измученный", "Зазубренный", "Забитый",
                "Калейдоскопический", "Увлеченный", "Долговязый", "Большой", "Последний", "Прочный", "Законный",
                "Сумасшедший", "Великолепный", "Величественный", "Главный", "Мужской", "Чудесный", "Наивный",
                "Узкий", "Противный", "Естественный", "Непослушный", "Послушный", "Тучный", "Продолговатый",
                "Очевидный", "Случайный", "Маслянистый", "Вкусный", "Бледный", "Ничтожный", "Иссушенный",
                "Частичный", "Страстный", "Мирный", "Острый", "Ароматный", "Причудливый", "Квалифицированный",
                "Сияющий", "Оборванный", "Стремительный", "Редкий", "Недавний", "Безрассудный", "Прямоугольный"
            ]
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

    def get_word_counts(self):
        """Возвращает количество слов в каждом списке."""
        data = self.load_data()
        return {
            "nouns": len(data.get("nouns", [])),
            "adjectives": len(data.get("adjectives", []))
        }

    def get_random_cards(self, count=5):
        """
        Возвращает случайные карточки для игры.

        Args:
            count: Количество карточек

        Returns:
            dict: {"nouns": [...], "adjectives": [...]}
        """
        data = self.load_data()

        # Получаем списки слов
        nouns_list = data.get("nouns", [])
        adjectives_list = data.get("adjectives", [])

        # Проверяем, что есть достаточно карточек
        if len(nouns_list) < count or len(adjectives_list) < count:
            self.log_service.add_error_log(
                error_message=f"Недостаточно слов для игры. Существительных: {len(nouns_list)}, Прилагательных: {len(adjectives_list)}",
                action="BEST_PAIRS_GET_CARDS"
            )
            # Используем что есть
            count = min(count, len(nouns_list), len(adjectives_list))

        # Выбираем случайные карточки
        selected_nouns = random.sample(nouns_list, count)
        selected_adjectives = random.sample(adjectives_list, count)

        return {
            "nouns": selected_nouns,
            "adjectives": selected_adjectives
        }

    def add_custom_word(self, word_type, word):
        """Добавляет пользовательское слово в список."""
        data = self.load_data()

        if word_type not in ["nouns", "adjectives"]:
            return False

        if word not in data[word_type]:
            data[word_type].append(word)
            return self.save_data(data)

        return True

    def remove_word(self, word_type, word):
        """Удаляет слово из списка."""
        data = self.load_data()

        if word_type not in ["nouns", "adjectives"]:
            return False

        if word in data[word_type]:
            data[word_type].remove(word)
            return self.save_data(data)

        return False