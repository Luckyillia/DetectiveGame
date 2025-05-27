from nicegui import ui
from datetime import datetime


class SpyComponents:
    """Компоненты пользовательского интерфейса для игры Шпион"""

    @staticmethod
    def create_header(title, subtitle=None, icon_name=None):
        """Создает заголовок с иконкой и подзаголовком"""
        with ui.column().classes('w-full items-center'):
            if icon_name:
                ui.icon(icon_name).classes('text-3xl text-red-500 dark:text-red-400 mb-2')

            ui.label(title).classes('text-2xl font-bold text-center text-red-600 dark:text-red-400')

            if subtitle:
                ui.label(subtitle).classes('text-center text-gray-600 dark:text-gray-300')

    @staticmethod
    def create_status_indicator(text, status_type="info"):
        """Создает индикатор статуса с соответствующим цветом и иконкой"""
        status_configs = {
            "info": {"icon": "info", "bg": "bg-red-100 dark:bg-red-900",
                     "text": "text-red-700 dark:text-red-300"},
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
                            spy_index=None):
        """
        Создает таблицу игроков для игры Шпион

        Args:
            players: Список игроков
            current_round: Текущий раунд игры (0-3)
            current_user_id: ID текущего пользователя
            vote_handler: Обработчик голосования
            votes: Словарь голосов (ключ - ID игрока, значение - ID игрока, за которого проголосовали)
            spy_index: Индекс игрока-шпиона
        """
        # Определяем колонки таблицы в зависимости от текущего раунда
        columns = [
            {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
            {'name': 'name', 'label': 'Имя игрока', 'field': 'name', 'align': 'center'}
        ]

        # Добавляем колонку статуса для комнаты ожидания
        if current_round == 0:
            columns.append({'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'})
            columns.append(
                {'name': 'last_action', 'label': 'Последнее действие', 'field': 'last_action', 'align': 'center'})

        # Добавляем колонку роли для игры
        if current_round == 1:
            columns.append({'name': 'role', 'label': 'Роль', 'field': 'role', 'align': 'center'})

        # Добавляем колонку голосов для голосования и результатов
        if current_round >= 2:
            columns.append({'name': 'votes', 'label': 'Голосов', 'field': 'votes', 'align': 'center'})

        # Добавляем колонку роли для результатов
        if current_round == 3:
            columns.append({'name': 'final_role', 'label': 'Роль', 'field': 'final_role', 'align': 'center'})

        # Добавляем колонку действий для голосования
        if current_round == 2:
            columns.append({'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'})

        # Создаем массив строк
        rows = []

        # Подсчитываем голоса для каждого игрока
        vote_counts = {}
        if votes and current_round >= 2:
            for voted_id in votes.values():
                vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

        # Подготавливаем строки со всеми необходимыми данными
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

            # Добавляем информацию о статусе для комнаты ожидания
            if current_round == 0:
                # Иконки статуса
                status = []
                if is_host:
                    status.append('👑 Ведущий')
                if is_ready:
                    status.append('✅ Готов')
                else:
                    status.append('⏳ Не готов')
                row['status'] = ', '.join(status)

                # Время последнего действия
                last_action_time = player.get('last_action', player.get('joined_at', 0))
                row['last_action'] = datetime.fromtimestamp(last_action_time).strftime(
                    '%H:%M:%S') if last_action_time else '—'

            # Добавляем роль для игры (раунд 1)
            if current_round == 1:
                # Роль видна только самому игроку
                is_current_player = (player_id == current_user_id)
                is_spy = (i == spy_index)

                if is_current_player:
                    if is_spy:
                        row['role'] = 'Шпион'
                    else:
                        # Роль обычного игрока - показываем его роль
                        row['role'] = '🎭 Ваша роль'  # Роль будет показана отдельно
                else:
                    row['role'] = '???'

            # Добавляем количество голосов для голосования и результатов
            if current_round >= 2:
                row['votes'] = vote_counts.get(player_id, 0)

            # Добавляем финальную роль для результатов
            if current_round == 3 and spy_index is not None:
                is_spy = (i == spy_index)
                row['final_role'] = 'Шпион' if is_spy else 'Обычный игрок'
                row['is_spy'] = is_spy  # Используется в шаблоне

            # Добавляем в строки
            rows.append(row)

        # Создаем таблицу с ключом строки для правильного отслеживания строк
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary'}
        ).classes('w-full')

        # Добавляем пользовательский слот body для условного рендеринга
        body_template = '''
        <q-tr :props="props">
            <q-td v-for="col in props.cols" :key="col.name" :props="props" class="text-center">
                <!-- Отображение статуса -->
                <template v-if="col.name === 'status'">
                    <div class="flex justify-center items-center gap-2">
                        <span>{{ col.value }}</span>
                    </div>
                </template>

                <!-- Отображение количества голосов -->
                <template v-else-if="col.name === 'votes'">
                    <div class="font-medium">
                        {{ col.value }}
                    </div>
                </template>

                <!-- Отображение роли с правильным стилем -->
                <template v-else-if="col.name === 'final_role'">
                    <div :class="[
                        props.row.is_spy 
                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' 
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
                        'px-2 py-1 rounded-full font-medium inline-block'
                    ]">
                        {{ col.value }}
                    </div>
                </template>

                <!-- Кнопки действий для голосования -->
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

                <!-- Отображение колонки по умолчанию -->
                <template v-else>
                    <span>{{ col.value }}</span>
                </template>
            </q-td>
        </q-tr>
        ''' % (
            current_user_id or '',  # ID текущего пользователя для проверки голосования за себя
            str(bool(votes and current_user_id in votes)).lower(),  # Проверка, проголосовал ли
            votes.get(current_user_id, '') if votes and current_user_id in votes else ''
        # ID того, за кого проголосовали
        )

        table.add_slot('body', body_template)

        # Добавляем обработчик для события голосования
        if current_round == 2 and vote_handler:
            table.on('vote', lambda e: vote_handler(e.args))

        return table

    @staticmethod
    def create_location_display(category, location, is_spy):
        """Создает отображение категории и локации"""
        if is_spy:
            with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg shadow-inner'):
                ui.label('Вы - Шпион!').classes('text-center mb-2 text-red-700 dark:text-red-300 font-bold text-xl')
                ui.label(f'Категория: {category}').classes('text-center mb-2 text-red-800 dark:text-red-200 text-lg')
                ui.label('Вы не знаете локацию. Выясните её через живое общение, не выдав себя!').classes(
                    'text-center text-red-800 dark:text-red-200')
        else:
            with ui.card().classes('bg-blue-100 dark:bg-blue-900 p-4 mb-4 rounded-lg shadow-inner'):
                ui.label(f'Категория: {category}').classes('text-center mb-2 text-blue-700 dark:text-blue-300 text-lg')
                ui.label('Локация:').classes('text-center mb-2 text-blue-700 dark:text-blue-300')
                ui.label(location).classes('text-3xl font-bold text-center text-blue-800 dark:text-blue-200 mb-2')
                ui.label('Найдите Шпиона через живое общение!').classes('text-center text-blue-700 dark:text-blue-300')

    @staticmethod
    def create_round_indicator(current_round):
        """Создает индикатор текущего раунда игры"""
        round_text = {
            0: "Подготовка к игре",
            1: "Обсуждение (в реальном времени)",
            2: "Время голосования",
            3: "Оглашение результатов"
        }

        text = round_text.get(current_round, "Неизвестный этап")

        with ui.row().classes(
                'items-center justify-center bg-red-100 dark:bg-red-900 rounded-lg p-3 mt-2 w-full'):
            ui.icon('info').classes('text-red-500 dark:text-red-400 text-2xl mr-2')
            ui.label(f"Текущий этап: {text}").classes('text-lg font-medium text-red-700 dark:text-red-300')

    @staticmethod
    def create_game_result_card(spy_caught, spy_name, location, spy_won=False):
        """Создает карточку с результатами игры"""
        if spy_won:
            with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg'):
                ui.label(f'Шпион ({spy_name}) победил!').classes(
                    'text-center text-red-700 dark:text-red-300 font-bold text-lg mb-2')
                ui.label('Шпион правильно угадал локацию!').classes(
                    'text-center text-red-800 dark:text-red-200')
                ui.label(f'Локация была: {location}').classes('text-center mt-2')
        elif spy_caught:
            with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4 rounded-lg'):
                ui.label(f'Шпион ({spy_name}) был пойман!').classes(
                    'text-center text-green-700 dark:text-green-300 font-bold text-lg mb-2')
                ui.label('Обычные игроки победили!').classes(
                    'text-center text-green-800 dark:text-green-200')
                ui.label(f'Локация была: {location}').classes('text-center mt-2')
        else:
            with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg'):
                ui.label('Шпион не был пойман! Шпион побеждает!').classes(
                    'text-center text-red-700 dark:text-red-300 font-bold text-lg mb-2')
                ui.label(f'Шпионом был игрок {spy_name}').classes(
                    'text-center text-red-800 dark:text-red-200 mb-2')
                ui.label(f'Локация была: {location}').classes('text-center text-red-800 dark:text-red-200')

    @staticmethod
    def create_timer_display(start_time, duration, title="Время раунда"):
        """Создает отображение таймера"""
        import time

        elapsed = int(time.time() - start_time)
        remaining = max(0, duration - elapsed)

        minutes = remaining // 60
        seconds = remaining % 60

        color_class = "text-green-600" if remaining > 60 else "text-red-600"

        with ui.card().classes('p-3 bg-gray-100 dark:bg-gray-800 rounded-lg mb-4'):
            with ui.row().classes('items-center justify-center'):
                ui.icon('timer').classes(f'{color_class} text-xl mr-2')
                ui.label(title).classes('font-medium mr-4')
                ui.label(f'{minutes:02d}:{seconds:02d}').classes(f'{color_class} font-bold text-xl')