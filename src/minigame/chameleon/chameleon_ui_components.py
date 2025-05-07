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
        Creates a player table with appropriate content

        Args:
            players: List of players
            current_round: Current game round (0-3)
            current_user_id: ID of the current user
            vote_handler: Handler for voting events
            votes: Dictionary of votes (key - player ID, value - ID of the player the vote was cast for)
            chameleon_index: Index of the chameleon player
        """
        # Create a container for the player cards
        container = ui.column().classes('w-full gap-2')

        # Count votes for each player
        vote_counts = {}
        if votes and current_round >= 2:
            for voted_id in votes.values():
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

        # Create a card for each player
        for i, player in enumerate(players):
            player_id = player.get('id', '')
            player_name = player.get('name', 'Неизвестный игрок')
            is_host = player.get('is_host', False)
            is_ready = player.get('is_ready', False)
            player_index = i + 1

            with ui.card().classes('w-full p-3 flex flex-col gap-2') as container:
                # Header with player number and name
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(f"{player_index}").classes(
                            'font-bold bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded-full')
                        ui.label(player_name).classes('font-bold text-lg')

                    # Status icons - shown in waiting room
                    if current_round == 0:
                        with ui.row().classes('gap-2'):
                            if is_host:
                                ui.label('👑').tooltip('Ведущий')
                            if is_ready:
                                ui.label('✅').tooltip('Готов')
                            else:
                                ui.label('⏳').tooltip('Не готов')

                # Second row with additional info based on game state
                with ui.row().classes('w-full items-center justify-between'):
                    # Last action time - only in waiting room
                    if current_round == 0:
                        last_action_time = player.get("last_action", player.get("joined_at", 0))
                        if last_action_time:
                            formatted_time = datetime.fromtimestamp(last_action_time).strftime("%H:%M:%S")
                            ui.label(f"Последнее действие: {formatted_time}").classes('text-sm text-gray-500')

                    # Vote count - in voting and results modes
                    if current_round >= 2:
                        vote_count = vote_counts.get(player_id, 0)
                        ui.label(f"Голосов: {vote_count}").classes('text-sm font-medium')

                    # Role - only in results mode
                    if current_round == 3 and chameleon_index is not None:
                        is_chameleon = (i == chameleon_index)
                        role_text = 'Хамелеон' if is_chameleon else 'Обычный игрок'
                        ui.label(role_text).classes(
                            'font-medium px-2 py-1 rounded-full ' +
                            (
                                'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' if is_chameleon else
                                'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200')
                        )

                # Voting buttons - only in voting mode
                if current_round == 2 and vote_handler:
                    # Check if current user has voted
                    has_voted = votes and current_user_id in votes

                    # Only show voting option for other players
                    if player_id != current_user_id:
                        # If user already voted, show who they voted for
                        if has_voted:
                            voted_for_id = votes.get(current_user_id)
                            if player_id == voted_for_id:
                                ui.label('Вы проголосовали за этого игрока ✓').classes(
                                    'text-green-600 font-medium text-center w-full')
                        # Otherwise show voting button
                        else:
                            ui.button('Голосовать', icon='how_to_vote',
                                      on_click=lambda pid=player_id: vote_handler(pid)).classes('w-full')
                    else:
                        ui.label('Вы не можете голосовать за себя').classes('text-gray-500 italic text-center w-full')

        return container

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
        """Creates a card with game results"""
        if chameleon_caught:
            with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4 rounded-lg'):
                ui.label(f'Хамелеон ({chameleon_name}) был пойман!').classes(
                    'text-center text-green-700 dark:text-green-300 font-bold text-lg mb-2')

                # The chameleon can still win if they correctly guess the word,
                # but this is shown separately in the UI via the guess form.
                # Here we only show that they were caught.
                ui.label('Хамелеон был идентифицирован! Теперь всё зависит от его догадки.').classes(
                    'text-center text-green-800 dark:text-green-200')
                ui.label(f'Загаданное слово было: {word}').classes('text-center mt-2')
        else:
            with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4 rounded-lg'):
                ui.label('Хамелеон не был пойман! Хамелеон побеждает!').classes(
                    'text-center text-yellow-700 dark:text-yellow-300 font-bold text-lg mb-2')
                ui.label(f'Хамелеоном был игрок {chameleon_name}').classes(
                    'text-center text-yellow-800 dark:text-yellow-200 mb-2')
                ui.label(f'Загаданное слово было: {word}').classes('text-center text-yellow-800 dark:text-yellow-200')