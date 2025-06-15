from nicegui import ui
from datetime import datetime


class BestPairsComponents:
    """Компоненты пользовательского интерфейса для игры Лучшие Пары"""

    @staticmethod
    def create_header(title, subtitle=None, icon_name=None):
        """Создает заголовок с иконкой и подзаголовком"""
        with ui.column().classes('w-full items-center'):
            if icon_name:
                ui.icon(icon_name).classes('text-3xl text-purple-500 dark:text-purple-400 mb-2')

            ui.label(title).classes('text-2xl font-bold text-center text-purple-600 dark:text-purple-400')

            if subtitle:
                ui.label(subtitle).classes('text-center text-gray-600 dark:text-gray-300')

    @staticmethod
    def create_status_indicator(text, status_type="info"):
        """Создает индикатор статуса с соответствующим цветом и иконкой"""
        status_configs = {
            "info": {"icon": "info", "bg": "bg-purple-100 dark:bg-purple-900",
                     "text": "text-purple-700 dark:text-purple-300"},
            "waiting": {"icon": "hourglass_empty", "bg": "bg-amber-100 dark:bg-amber-900",
                        "text": "text-amber-700 dark:text-amber-300"},
            "success": {"icon": "check_circle", "bg": "bg-green-100 dark:bg-green-900",
                        "text": "text-green-700 dark:text-green-300"},
            "error": {"icon": "error", "bg": "bg-red-100 dark:bg-red-900",
                      "text": "text-red-700 dark:text-red-300"},
            "warning": {"icon": "warning", "bg": "bg-yellow-100 dark:bg-yellow-900",
                        "text": "text-yellow-700 dark:text-yellow-300"}
        }

        config = status_configs.get(status_type, status_configs["info"])

        with ui.row().classes(f'items-center justify-center {config["bg"]} rounded-lg p-3 w-full'):
            ui.icon(config["icon"]).classes(f'{config["text"]} text-2xl mr-2')
            ui.label(text).classes(f'text-lg font-medium {config["text"]}')

    @staticmethod
    def create_player_table(players, current_player_id=None, is_waiting=True):
        """Создает таблицу игроков"""
        columns = [
            {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
            {'name': 'name', 'label': 'Имя игрока', 'field': 'name', 'align': 'center'},
            {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'},
        ]

        if not is_waiting:
            columns.append({'name': 'score', 'label': 'Очки', 'field': 'score', 'align': 'center'})
            columns.append({'name': 'guesses', 'label': 'Угадано пар', 'field': 'guesses', 'align': 'center'})

        rows = []
        for idx, player in enumerate(players):
            row = {
                'index': idx + 1,
                'name': player['name'],
                'status': '✅ Готов' if player.get('is_ready', False) else '⏳ Ожидает',
                'score': player.get('score', 0),
                'guesses': player.get('guesses', 0)
            }

            # Подсветка текущего игрока
            if player['id'] == current_player_id:
                row['name'] = f"🎮 {row['name']}"

            # Подсветка хоста
            if player.get('is_host', False):
                row['name'] = f"👑 {row['name']}"

            rows.append(row)

        ui.table(columns=columns, rows=rows, row_key='index').classes('w-full')

    @staticmethod
    def create_noun_card(noun, index):
        """Создает карточку существительного"""
        with ui.card().classes(
                'p-4 bg-white dark:bg-gray-700 shadow-lg hover:shadow-xl transition-shadow cursor-pointer'):
            ui.label(f"{index + 1}").classes('text-sm text-gray-500 dark:text-gray-400 mb-1')
            ui.label(noun).classes('text-lg font-bold text-center text-gray-800 dark:text-gray-200')

    @staticmethod
    def create_adjective_card(adjective, is_revealed=False):
        """Создает карточку прилагательного"""
        with ui.card().classes('p-4 shadow-lg hover:shadow-xl transition-shadow'):
            if is_revealed:
                ui.label(adjective).classes('text-lg font-bold text-center text-purple-700 dark:text-purple-300')
            else:
                ui.icon('help_outline').classes('text-2xl text-gray-400 mx-auto')
                ui.label('?').classes('text-lg font-bold text-center text-gray-400')

    @staticmethod
    def create_pairing_display(nouns, adjectives, pairings=None, is_host_view=False):
        """Создает отображение пар существительных и прилагательных"""
        with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
            # Левая колонка - существительные
            with ui.column().classes('w-full'):
                ui.label('Существительные').classes('text-lg font-bold mb-2 text-center')
                for idx, noun in enumerate(nouns):
                    BestPairsComponents.create_noun_card(noun, idx)

            # Правая колонка - прилагательные
            with ui.column().classes('w-full'):
                ui.label('Прилагательные').classes('text-lg font-bold mb-2 text-center')
                if is_host_view and pairings:
                    # Для ведущего показываем расставленные прилагательные
                    for noun_idx in range(len(nouns)):
                        adj = pairings.get(noun_idx, '?')
                        BestPairsComponents.create_adjective_card(adj, is_revealed=True)
                else:
                    # Для игроков показываем скрытые карточки
                    for _ in range(len(adjectives)):
                        BestPairsComponents.create_adjective_card('?', is_revealed=False)

    @staticmethod
    def create_round_indicator(current_round):
        """Создает индикатор текущего раунда"""
        round_info = {
            1: ("Ведущий раскладывает пары", "psychology"),
            2: ("Игроки делают предположения", "group"),
            3: ("Проверка результатов", "fact_check"),
            4: ("Конец раунда", "emoji_events")
        }

        text, icon = round_info.get(current_round, ("Неизвестный этап", "help"))

        with ui.row().classes('items-center justify-center bg-purple-100 dark:bg-purple-900 rounded-lg p-3 w-full'):
            ui.icon(icon).classes('text-purple-500 dark:text-purple-400 text-2xl mr-2')
            ui.label(f"Этап {current_round}: {text}").classes(
                'text-lg font-medium text-purple-700 dark:text-purple-300')

    @staticmethod
    def create_score_display(scores):
        """Создает отображение счета"""
        with ui.card().classes('w-full p-4 bg-purple-50 dark:bg-purple-900 rounded-lg'):
            ui.label('Счёт игры').classes('text-lg font-bold mb-2 text-center text-purple-700 dark:text-purple-300')

            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            for idx, (player_name, score) in enumerate(sorted_scores):
                medal = ""
                if idx == 0:
                    medal = "🥇"
                elif idx == 1:
                    medal = "🥈"
                elif idx == 2:
                    medal = "🥉"

                with ui.row().classes('w-full justify-between items-center py-1'):
                    ui.label(f"{medal} {player_name}").classes('text-purple-700 dark:text-purple-300')
                    ui.label(f"{score} очков").classes('font-bold text-purple-800 dark:text-purple-200')

    @staticmethod
    def create_result_card(correct_pairings, player_guesses, score):
        """Создает карточку с результатами раунда"""
        with ui.card().classes('w-full p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg'):
            ui.label('Результаты раунда').classes(
                'text-xl font-bold mb-4 text-center text-purple-700 dark:text-purple-300')

            # Показываем правильные пары
            ui.label('Правильные пары:').classes('font-bold mb-2')
            with ui.column().classes('w-full mb-4'):
                for noun, adj in correct_pairings.items():
                    with ui.row().classes('w-full justify-center mb-1'):
                        ui.label(f"{noun} — {adj}").classes('text-gray-700 dark:text-gray-300')

            # Показываем догадки игрока
            ui.label('Ваши догадки:').classes('font-bold mb-2')
            correct_count = 0
            with ui.column().classes('w-full mb-4'):
                for noun, adj in player_guesses.items():
                    is_correct = correct_pairings.get(noun) == adj
                    if is_correct:
                        correct_count += 1

                    icon = "✅" if is_correct else "❌"
                    color = "text-green-600" if is_correct else "text-red-600"

                    with ui.row().classes('w-full justify-center mb-1'):
                        ui.label(f"{icon} {noun} — {adj}").classes(f'{color} dark:{color}')

            # Показываем счет
            ui.label(f'Угадано пар: {correct_count}/5').classes('text-center text-lg font-bold mb-2')
            ui.label(f'Заработано очков: {score}').classes(
                'text-center text-xl font-bold text-purple-700 dark:text-purple-300')