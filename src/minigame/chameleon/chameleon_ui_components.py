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
        Creates a player table similar to the UserTable implementation

        Args:
            players: List of players
            current_round: Current game round (0-3)
            current_user_id: ID of the current user
            vote_handler: Handler for voting events
            votes: Dictionary of votes (key - player ID, value - ID of the player the vote was cast for)
            chameleon_index: Index of the chameleon player
        """
        # Define columns for the table based on current round
        columns = [
            {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
            {'name': 'name', 'label': 'Имя игрока', 'field': 'name', 'align': 'center'}
        ]

        # Add status column for waiting room
        if current_round == 0:
            columns.append({'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'})
            columns.append(
                {'name': 'last_action', 'label': 'Последнее действие', 'field': 'last_action', 'align': 'center'})

        # Add vote count column for voting and results
        if current_round >= 2:
            columns.append({'name': 'votes', 'label': 'Голосов', 'field': 'votes', 'align': 'center'})

        # Add role column for results
        if current_round == 3:
            columns.append({'name': 'role', 'label': 'Роль', 'field': 'role', 'align': 'center'})

        # Add action column for voting
        if current_round == 2:
            columns.append({'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'})

        # Create rows array
        rows = []

        # Count votes for each player
        vote_counts = {}
        if votes and current_round >= 2:
            for voted_id in votes.values():
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

        # Prepare rows with all necessary data
        for i, player in enumerate(players):
            player_id = player.get('id', '')
            player_name = player.get('name', 'Неизвестный игрок')
            is_host = player.get('is_host', False)
            is_ready = player.get('is_ready', False)

            row = {
                'id': player_id,
                'index': i + 1,
                'name': player_name
            }

            # Add status information for waiting room
            if current_round == 0:
                # Status icons
                status = []
                if is_host:
                    status.append('👑 Ведущий')
                if is_ready:
                    status.append('✅ Готов')
                else:
                    status.append('⏳ Не готов')
                row['status'] = ', '.join(status)

                # Last action time
                last_action_time = player.get('last_action', player.get('joined_at', 0))
                row['last_action'] = datetime.fromtimestamp(last_action_time).strftime(
                    '%H:%M:%S') if last_action_time else '—'

            # Add vote count for voting and results
            if current_round >= 2:
                row['votes'] = vote_counts.get(player_id, 0)

            # Add role for results
            if current_round == 3 and chameleon_index is not None:
                is_chameleon = (i == chameleon_index)
                row['role'] = 'Хамелеон' if is_chameleon else 'Обычный игрок'
                row['is_chameleon'] = is_chameleon  # Used in template

            # Add to rows
            rows.append(row)

        # Create table with row_key for proper row tracking
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary'}
        ).classes('w-full')

        # Add custom body slot for conditional rendering
        body_template = '''
        <q-tr :props="props">
            <q-td v-for="col in props.cols" :key="col.name" :props="props" class="text-center">
                <!-- Status display -->
                <template v-if="col.name === 'status'">
                    <div class="flex justify-center items-center gap-2">
                        <span>{{ col.value }}</span>
                    </div>
                </template>

                <!-- Vote count display -->
                <template v-else-if="col.name === 'votes'">
                    <div class="font-medium">
                        {{ col.value }}
                    </div>
                </template>

                <!-- Role display with proper styling -->
                <template v-else-if="col.name === 'role'">
                    <div :class="[
                        props.row.is_chameleon 
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' 
                            : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                        'px-2 py-1 rounded-full font-medium inline-block'
                    ]">
                        {{ col.value }}
                    </div>
                </template>

                <!-- Action buttons for voting -->
                <template v-else-if="col.name === 'action'">
                    <div class="flex justify-center">
                        <div v-if="props.row.id === '%s'">
                            <span class="text-gray-500 dark:text-gray-400 text-sm">Нельзя голосовать за себя</span>
                        </div>
                        <div v-else>
                            <q-btn v-if="!%s" color="primary" dense icon="how_to_vote" size="md"
                                   @click="() => $parent.$emit('vote', props.row.id)">Голосовать</q-btn>
                            <span v-else-if="props.row.id === '%s'" class="text-green-600 dark:text-green-400 font-medium">
                                Вы проголосовали ✓
                            </span>
                        </div>
                    </div>
                </template>

                <!-- Default column display -->
                <template v-else>
                    <span>{{ col.value }}</span>
                </template>
            </q-td>
        </q-tr>
        ''' % (
            current_user_id or '',  # Current user ID for self-vote check
            str(bool(votes and current_user_id in votes)).lower(),  # Has voted check
            votes.get(current_user_id, '') if votes and current_user_id in votes else ''  # Voted for ID
        )

        table.add_slot('body', body_template)

        # Add handler for vote event
        if current_round == 2 and vote_handler:
            table.on('vote', lambda e: vote_handler(e.args))

        return table

    @staticmethod
    def create_word_grid(category, words):
        """
        Создает сетку слов для указанной категории

        Args:
            category: Название категории
            words: Список слов для отображения
        """
        # Создаем копию списка слов, чтобы не изменять оригинал
        grid_words = words.copy() if words else []

        # НЕ перемешиваем слова здесь! Используем те, что пришли

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
                            word = grid_words[word_index] if word_index < len(grid_words) else "---"

                            # Используем простой контейнер вместо карточки с эффектами наведения
                            with ui.element('div').classes(
                                    'p-2 min-h-12 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-md'):
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