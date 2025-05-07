from nicegui import ui
import random
import string
from datetime import datetime


class ChameleonComponents:
    """Компоненты пользовательского интерфейса для игры Хамелеон"""

    @staticmethod
    def create_header(title, subtitle=None, icon_name=None):
        """Создает заголовок с иконкой и подзаголовком"""
        with ui.column().classes('w-full items-center'):
            if icon_name:
                ui.icon(icon_name).classes('text-3xl text-indigo-500 dark:text-indigo-400 mb-2')

            ui.label(title).classes('text-2xl font-bold text-center text-indigo-600 dark:text-indigo-400')

            if subtitle:
                ui.label(subtitle).classes('text-center text-gray-600 dark:text-gray-300')

    @staticmethod
    def create_status_indicator(text, status_type="info"):
        """Создает индикатор статуса с соответствующим цветом и иконкой"""
        status_configs = {
            "info": {"icon": "info", "bg": "bg-indigo-100 dark:bg-indigo-900",
                     "text": "text-indigo-700 dark:text-indigo-300"},
            "waiting": {"icon": "hourglass_empty", "bg": "bg-amber-100 dark:bg-amber-900",
                        "text": "text-amber-700 dark:text-amber-300"},
            "success": {"icon": "check_circle", "bg": "bg-green-100 dark:bg-green-900",
                        "text": "text-green-700 dark:text-green-300"},
            "error": {"icon": "error", "bg": "bg-red-100 dark:bg-red-900", "text": "text-red-700 dark:text-red-300"},
            "warning": {"icon": "warning", "bg": "bg-yellow-100 dark:bg-yellow-900",
                        "text": "text-yellow-700 dark:text-yellow-300"}
        }

        config = status_configs.get(status_type, status_configs["info"])

        with ui.row().classes(f'items-center justify-center {config["bg"]} rounded-lg p-3 w-full'):
            ui.icon(config["icon"]).classes(f'{config["text"]} text-2xl mr-2')
            ui.label(text).classes(f'text-lg font-medium {config["text"]}')

    @staticmethod
    def create_player_table(players, current_round=0, current_user_id=None, vote_handler=None, votes=None,
                            chameleon_index=None):
        """
        Создает таблицу игроков с соответствующим содержимым в зависимости от этапа игры

        Args:
            players: Список игроков
            current_round: Текущий раунд игры (0-3)
            current_user_id: ID текущего пользователя
            vote_handler: Обработчик событий голосования
            votes: Словарь голосов (ключ - ID игрока, значение - ID игрока, за которого отдан голос)
            chameleon_index: Индекс игрока-Хамелеона
        """
        # Определяем колонки для таблицы
        columns = [
            {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
            {'name': 'name', 'label': 'Имя', 'field': 'name', 'align': 'left'},
        ]

        # Добавляем колонку со статусом для комнаты ожидания
        if current_round == 0:
            columns.append({'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'})
            columns.append(
                {'name': 'last_action', 'label': 'Последнее действие', 'field': 'last_action', 'align': 'center'})

        # Добавляем колонку голосов для режима голосования и результатов
        if current_round >= 2:
            columns.append({'name': 'votes', 'label': 'Голосов', 'field': 'votes', 'align': 'center'})

        # Добавляем колонку для роли в режиме результатов
        if current_round == 3:
            columns.append({'name': 'role', 'label': 'Роль', 'field': 'role', 'align': 'center'})

        # Если в режиме голосования, добавляем колонку для кнопок голосования
        if current_round == 2:
            columns.append({'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'})

        # Создаем строки данных
        rows = []

        # Подсчитываем голоса для каждого игрока
        vote_counts = {}
        if votes and current_round >= 2:
            for voted_id in votes.values():
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

        # Формируем строки данных
        for i, player in enumerate(players):
            # Базовая информация о игроке
            row = {
                'id': player.get('id', ''),  # Нужно для логики голосования
                'index': str(i + 1),
                'name': player.get('name', 'Неизвестный игрок'),
            }

            # Добавляем статус для комнаты ожидания
            if current_round == 0:
                status_items = []
                if player.get("is_host", False):
                    status_items.append("👑 Ведущий")
                if player.get("is_ready", False):
                    status_items.append("✅ Готов")
                else:
                    status_items.append("⏳ Не готов")
                row['status'] = ", ".join(status_items)

                # Добавляем время последнего действия
                last_action_time = player.get("last_action", player.get("joined_at", 0))
                if last_action_time:
                    formatted_time = datetime.fromtimestamp(last_action_time).strftime("%H:%M:%S")
                    row['last_action'] = formatted_time
                else:
                    row['last_action'] = "—"

            # Добавляем количество голосов для режимов голосования и результатов
            if current_round >= 2:
                row['votes'] = str(vote_counts.get(player.get('id', ''), 0))

            # Добавляем роль для режима результатов
            if current_round == 3 and chameleon_index is not None:
                is_chameleon = (i == chameleon_index)
                row['role'] = 'Хамелеон' if is_chameleon else 'Обычный игрок'

            rows.append(row)

        # Создаем таблицу
        table = ui.table(columns=columns, rows=rows).classes('w-full').props('flat bordered')

        # Если в режиме голосования, добавляем кнопки голосования
        if current_round == 2 and vote_handler and current_user_id:
            # Проверяем, голосовал ли уже текущий пользователь
            has_voted = current_user_id in (votes or {})

            if has_voted:
                voted_for_id = votes.get(current_user_id)

                # Показываем ячейки с информацией о голосовании
                for i, player in enumerate(players):
                    player_id = player.get('id', '')
                    with table.add_slot('body-cell-action',
                                        f"{{row: {{index: '{i + 1}', name: '{player['name']}', votes: '{vote_counts.get(player_id, 0)}'}}}}"):
                        if player_id == voted_for_id:
                            ui.label('Вы проголосовали ✓').classes('text-green-600 dark:text-green-400 font-medium')
                        else:
                            ui.label('')
            else:
                # Показываем кнопки для голосования
                for i, player in enumerate(players):
                    player_id = player.get('id', '')
                    with table.add_slot('body-cell-action',
                                        f"{{row: {{index: '{i + 1}', name: '{player['name']}', votes: '{vote_counts.get(player_id, 0)}'}}}}"):
                        if player_id != current_user_id:
                            ui.button(
                                'Голосовать',
                                icon='how_to_vote',
                                on_click=lambda pid=player_id: vote_handler(pid)
                            ).props('size=sm color=primary')
                        else:
                            ui.label('Нельзя голосовать за себя').classes('text-gray-500 dark:text-gray-400 text-sm')

        return table

    @staticmethod
    def create_word_grid(category, words):
        """
        Создает сетку слов для указанной категории

        Args:
            category: Название категории
            words: Список слов для отображения
        """
        # Убеждаемся, что у нас достаточно слов для сетки 4x4
        while len(words) < 16:
            words.append("")

        # Перемешиваем слова для случайного распределения
        random.shuffle(words)

        # Создаем список букв и цифр для сетки
        letters = list(string.ascii_uppercase)[:4]  # A-D
        numbers = [str(i) for i in range(1, 5)]  # 1-4

        with ui.card().classes('w-full p-4 rounded-lg dark:bg-gray-800 mb-4'):
            ui.label(f'Слова для категории "{category}":').classes(
                'text-lg font-bold mb-3 text-gray-800 dark:text-gray-200')

            with ui.element('div').classes('w-full overflow-x-auto'):
                with ui.element('div').classes('grid grid-cols-5 gap-2 min-w-md mx-auto'):
                    # Пустая ячейка в верхнем левом углу
                    ui.label('').classes('p-2 text-center font-bold')

                    # Заголовки столбцов (буквы)
                    for letter in letters:
                        ui.label(letter).classes(
                            'p-2 text-center font-bold bg-indigo-100 dark:bg-indigo-900 rounded-md')

                    # Строки
                    for row, number in enumerate(numbers):
                        # Заголовок строки (число)
                        ui.label(number).classes(
                            'p-2 text-center font-bold bg-indigo-100 dark:bg-indigo-900 rounded-md')

                        # Ячейки в строке
                        for col in range(4):
                            # Вычисляем индекс слова в нашем списке
                            word_index = row * 4 + col
                            cell_id = f"{letters[col]}{number}"

                            # Берем слово из списка
                            word = words[word_index] if word_index < len(words) else ""

                            with ui.card().classes(
                                    'p-2 min-h-12 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-md shadow hover:shadow-md transition-shadow'):
                                ui.label(word).classes(
                                    'text-sm font-medium text-center text-gray-800 dark:text-gray-200')

    @staticmethod
    def create_round_indicator(current_round):
        """Создает индикатор текущего раунда игры"""
        round_text = {
            0: "Подготовка к игре",
            1: "Игроки обсуждают слово",
            2: "Время голосования",
            3: "Оглашение результатов"
        }

        text = round_text.get(current_round, "Неизвестный этап")

        with ui.row().classes(
                'items-center justify-center bg-indigo-100 dark:bg-indigo-900 rounded-lg p-3 mt-2 w-full'):
            ui.icon('info').classes('text-indigo-500 dark:text-indigo-400 text-2xl mr-2')
            ui.label(f"Текущий этап: {text}").classes('text-lg font-medium text-indigo-700 dark:text-indigo-300')

    @staticmethod
    def create_role_card(is_chameleon, word=None):
        """Создает карточку с информацией о роли игрока"""
        if is_chameleon:
            with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4 rounded-lg shadow-inner'):
                ui.label('Вы - Хамелеон!').classes('text-center mb-2 text-yellow-700 dark:text-yellow-300 font-bold')
                ui.label('Вы не знаете секретное слово. Притворитесь, что знаете!').classes(
                    'text-center text-yellow-800 dark:text-yellow-200')
        else:
            with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4 rounded-lg shadow-inner'):
                ui.label('Вы знаете секретное слово:').classes('text-center mb-2 text-green-700 dark:text-green-300')
                ui.label(word).classes('text-2xl font-bold text-center text-green-800 dark:text-green-200')

    @staticmethod
    def create_game_result_card(chameleon_caught, chameleon_name, word):
        """Создает карточку с результатами игры"""
        if chameleon_caught:
            with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4 rounded-lg'):
                ui.label(f'Хамелеон ({chameleon_name}) был пойман!').classes(
                    'text-center text-green-700 dark:text-green-300 font-bold text-lg mb-2')
                ui.label('Поздравляем! Команда игроков победила.').classes(
                    'text-center text-green-800 dark:text-green-200')
                ui.label(f'Загаданное слово было: {word}').classes('text-center mt-2')
        else:
            with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4 rounded-lg'):
                ui.label('Хамелеон не был пойман! Хамелеон побеждает!').classes(
                    'text-center text-yellow-700 dark:text-yellow-300 font-bold text-lg mb-2')
                ui.label(f'Хамелеоном был игрок {chameleon_name}').classes(
                    'text-center text-yellow-800 dark:text-yellow-200 mb-2')
                ui.label(f'Загаданное слово было: {word}').classes('text-center text-yellow-800 dark:text-yellow-200')