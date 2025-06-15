from nicegui import ui
from datetime import datetime


class CodenamesComponents:
    """Компоненты пользовательского интерфейса для игры Codenames"""

    @staticmethod
    def create_header(title, subtitle=None, icon_name=None):
        """Создает заголовок с иконкой и подзаголовком"""
        with ui.column().classes('w-full items-center'):
            if icon_name:
                ui.icon(icon_name).classes('text-3xl text-blue-500 dark:text-blue-400 mb-2')

            ui.label(title).classes('text-2xl font-bold text-center text-blue-600 dark:text-blue-400')

            if subtitle:
                ui.label(subtitle).classes('text-center text-gray-600 dark:text-gray-300')

    @staticmethod
    def create_status_indicator(text, status_type="info"):
        """Создает индикатор статуса с соответствующим цветом и иконкой"""
        status_configs = {
            "info": {"icon": "info", "bg": "bg-blue-100 dark:bg-blue-900",
                     "text": "text-blue-700 dark:text-blue-300"},
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
    def create_player_table(players, teams, current_user_id=None):
        """
        Создает таблицу игроков для игры Codenames

        Args:
            players: Список игроков
            teams: Словарь команд
            current_user_id: ID текущего пользователя
        """
        columns = [
            {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
            {'name': 'name', 'label': 'Имя игрока', 'field': 'name', 'align': 'center'},
            {'name': 'team', 'label': 'Команда', 'field': 'team', 'align': 'center'},
            {'name': 'role', 'label': 'Роль', 'field': 'role', 'align': 'center'},
            {'name': 'last_action', 'label': 'Последнее действие', 'field': 'last_action', 'align': 'center'}
        ]

        rows = []

        for i, player in enumerate(players):
            player_id = player.get('id', '')
            player_name = player.get('name', 'Неизвестный игрок')
            team_id = player.get('team')
            role = player.get('role')

            # Определяем информацию о команде с цветом
            team_info = "Не в команде"
            team_color_class = "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"

            if team_id and team_id in teams:
                team = teams[team_id]
                team_info = team["name"]
                # Получаем цветовой класс для команды
                team_color_class = {
                    '1': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
                    '2': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
                    '3': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                    '4': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
                    '5': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                }.get(team_id, team_color_class)

            # Определяем роль с улучшенным отображением
            role_info = "Не назначена"
            role_color_class = "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"

            if role == "captain":
                role_info = "👑 Капитан"
                role_color_class = "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
            elif role == "member":
                role_info = "👤 Участник"
                role_color_class = "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"

            # Время последнего действия - исправляем логику
            last_action_time = player.get('last_action', 0)
            if last_action_time == 0:
                last_action_time = player.get('joined_at', 0)

            if last_action_time > 0:
                try:
                    last_action_str = datetime.fromtimestamp(last_action_time).strftime('%H:%M:%S')
                except (ValueError, OSError):
                    last_action_str = '—'
            else:
                last_action_str = '—'

            row = {
                'id': player_id,
                'index': i + 1,
                'name': player_name,
                'team': team_info,
                'role': role_info,
                'last_action': last_action_str,
                'team_id': team_id,
                'player_role': role,
                'team_color_class': team_color_class,
                'role_color_class': role_color_class
            }

            rows.append(row)

        # Создаем таблицу
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary'}
        ).classes('w-full')

        # Добавляем пользовательский слот для стилизации команд и ролей
        body_template = '''
        <q-tr :props="props">
            <q-td v-for="col in props.cols" :key="col.name" :props="props" class="text-center">
                <template v-if="col.name === 'team' && props.row.team_id">
                    <div :class="props.row.team_color_class" class="px-2 py-1 rounded-full font-medium inline-block">
                        {{ col.value }}
                    </div>
                </template>
                <template v-else-if="col.name === 'role' && props.row.player_role">
                    <div :class="props.row.role_color_class" class="px-2 py-1 rounded-full font-medium inline-block">
                        {{ col.value }}
                    </div>
                </template>
                <template v-else-if="col.name === 'team' && !props.row.team_id">
                    <div class="bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 px-2 py-1 rounded-full font-medium inline-block italic">
                        {{ col.value }}
                    </div>
                </template>
                <template v-else-if="col.name === 'role' && !props.row.player_role">
                    <div class="bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 px-2 py-1 rounded-full font-medium inline-block italic">
                        {{ col.value }}
                    </div>
                </template>
                <template v-else>
                    <span>{{ col.value }}</span>
                </template>
            </q-td>
        </q-tr>
        '''

        table.add_slot('body', body_template)
        return table

    @staticmethod
    def create_team_selection(teams, max_teams, join_team_handler, current_user_id):
        """Создает интерфейс выбора команды"""
        with ui.card().classes('w-full p-4 mb-4 bg-blue-50 dark:bg-blue-900 rounded-lg shadow'):
            ui.label('Выбор команды').classes('font-bold mb-3 text-lg text-blue-800 dark:text-blue-200')

            # Показываем текущую команду игрока
            current_team = None
            current_role = None

            # Находим текущую команду игрока
            for team_id, team in teams.items():
                if team.get('captain') == current_user_id:
                    current_team = team_id
                    current_role = 'captain'
                    break
                elif current_user_id in team.get('members', []):
                    current_team = team_id
                    current_role = 'member'
                    break

            # Отображаем текущий статус игрока
            if current_team:
                team_name = teams[current_team].get('name', f'Команда {current_team}')
                role_text = 'Капитан' if current_role == 'captain' else 'Участник'
                with ui.card().classes('w-full p-3 mb-4 bg-green-100 dark:bg-green-800 rounded-lg'):
                    ui.label(f'Ваша команда: {team_name} ({role_text})').classes(
                        'font-bold text-green-800 dark:text-green-200 text-center')
            else:
                with ui.card().classes('w-full p-3 mb-4 bg-yellow-100 dark:bg-yellow-800 rounded-lg'):
                    ui.label('Вы не в команде. Выберите или создайте команду.').classes(
                        'font-bold text-yellow-800 dark:text-yellow-200 text-center')

            # Показываем существующие команды
            if teams:
                ui.label('Существующие команды:').classes('font-medium mb-2')
                for team_id, team in teams.items():
                    team_color = team.get('color', 'bg-gray-500')
                    team_name = team.get('name', f'Команда {team_id}')
                    captain_id = team.get('captain')
                    members = team.get('members', [])

                    with ui.row().classes('w-full items-center mb-2 p-3 bg-white dark:bg-gray-800 rounded-lg border'):
                        # Индикатор цвета команды
                        ui.element('div').classes(f'{team_color} w-6 h-6 rounded mr-3')

                        # Информация о команде
                        with ui.column().classes('flex-grow'):
                            ui.label(f'{team_name}').classes('font-bold text-lg')
                            ui.label(f'Участников: {1 + len(members)} (капитан + {len(members)} участников)').classes(
                                'text-sm text-gray-600 dark:text-gray-400')

                        # Кнопки действий - ИСПРАВЛЕНО
                        with ui.column().classes('gap-1'):
                            # Если есть капитан, можно присоединиться как участник
                            if captain_id and captain_id != current_user_id:
                                if current_user_id not in members:
                                    ui.button('Присоединиться',
                                              on_click=lambda tid=team_id: join_team_handler(tid, 'member')).classes(
                                        'bg-blue-500 text-white text-sm')
                                else:
                                    ui.label('Вы участник').classes('text-green-600 text-sm font-medium')

                            # ИСПРАВЛЕНИЕ: Логика для капитанства
                            if not captain_id:
                                # Если нет капитана - любой может стать капитаном
                                ui.button('Стать капитаном',
                                          on_click=lambda tid=team_id: join_team_handler(tid, 'captain')).classes(
                                    'bg-green-500 text-white text-sm')
                            elif captain_id == current_user_id:
                                # Если игрок уже капитан этой команды
                                ui.label('Вы капитан').classes('text-yellow-600 text-sm font-bold')
                            else:
                                # ИСПРАВЛЕНИЕ: Убираем кнопку "Сменить капитана" для других игроков
                                # Вместо этого показываем информацию о том, что у команды есть капитан
                                ui.label('Есть капитан').classes('text-gray-500 text-sm')

            # Кнопки для создания новых команд (показываем все доступные)
            ui.label('Создать новую команду:').classes('font-medium mb-2 mt-4')

            available_teams = []
            for team_id in range(1, max_teams + 1):
                if str(team_id) not in teams:
                    available_teams.append(team_id)

            if available_teams:
                with ui.row().classes('flex-wrap gap-2'):
                    for team_id in available_teams:
                        team_colors_names = {
                            1: "Красная", 2: "Синяя", 3: "Зеленая",
                            4: "Фиолетовая", 5: "Оранжевая"
                        }
                        team_name = team_colors_names.get(team_id, f"Команда {team_id}")
                        ui.button(f'Создать {team_name}',
                                  on_click=lambda tid=str(team_id): join_team_handler(tid, 'captain')).classes(
                            'mb-1 bg-purple-500 text-white')
            else:
                ui.label('Все команды созданы').classes('text-gray-500 italic')

    @staticmethod
    def create_game_settings(current_settings, update_handler, is_host=False):
        """Создает панель настроек игры"""
        if not is_host:
            return

        # Проверяем, что current_settings не None
        if current_settings is None:
            current_settings = {"team_count": 2, "hint_mode": "written"}

        with ui.card().classes('w-full p-4 mb-4 bg-green-50 dark:bg-green-900 rounded-lg shadow'):
            ui.label('Настройки игры (только для ведущего)').classes(
                'font-bold mb-3 text-lg text-green-800 dark:text-green-200')

            with ui.row().classes('w-full items-center mb-2'):
                ui.label('Количество команд:').classes('font-medium mr-2')
                team_count_select = ui.select(
                    options=[2, 3, 4, 5],
                    value=current_settings.get('team_count', 2)
                ).classes('mr-4')
                team_count_select.props('outlined dense')

            with ui.row().classes('w-full items-center mb-4'):
                ui.label('Режим подсказок:').classes('font-medium mr-2')

                # ИСПРАВЛЕНИЕ: Используем простые строки вместо словарей
                hint_mode_options = ['written', 'verbal']
                hint_mode_select = ui.select(
                    options=hint_mode_options,
                    value=current_settings.get('hint_mode', 'written')
                ).classes('mr-4')
                hint_mode_select.props('outlined dense')

                # Добавляем подписи рядом с селектом
                ui.label('(written = письменные, verbal = устные)').classes('text-xs text-gray-500 ml-2')

            def update_settings():
                if update_handler:
                    new_settings = {
                        'team_count': team_count_select.value,
                        'hint_mode': hint_mode_select.value
                    }
                    update_handler(new_settings)

            ui.button('Применить настройки', on_click=update_settings).classes(
                'bg-green-600 hover:bg-green-700 text-white')

            # Показываем текущие настройки
            with ui.card().classes('w-full p-2 mt-2 bg-gray-100 dark:bg-gray-700'):
                ui.label('Текущие настройки:').classes('font-medium mb-1')
                ui.label(f"• Команд: {current_settings.get('team_count', 2)}").classes('text-sm')
                hint_mode_text = 'Письменные' if current_settings.get('hint_mode', 'written') == 'written' else 'Устные'
                ui.label(f"• Режим подсказок: {hint_mode_text}").classes('text-sm')

    @staticmethod
    def create_game_field(field, grid_size, is_captain=False, card_click_handler=None):
        """Создает игровое поле"""
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label('Игровое поле').classes('text-lg font-bold mb-3 text-center')

            # Создаем сетку
            with ui.element('div').classes('w-full overflow-x-auto'):
                with ui.element('div').classes(f'grid grid-cols-{grid_size} gap-2 mx-auto max-w-4xl'):
                    for i, card in enumerate(field):
                        emoji = card['emoji']
                        team = card['team']
                        revealed = card['revealed']

                        # Определяем стиль карты
                        if revealed:
                            # Карта открыта - показываем цвет команды
                            if team == -1:  # Убийца
                                card_class = 'bg-black text-white'
                            elif team == 0:  # Нейтральная
                                card_class = 'bg-gray-300 dark:bg-gray-600 text-black dark:text-white'
                            else:  # Команда
                                team_colors = {
                                    1: 'bg-red-500 text-white',
                                    2: 'bg-blue-500 text-white',
                                    3: 'bg-green-500 text-white',
                                    4: 'bg-purple-500 text-white',
                                    5: 'bg-orange-500 text-white'
                                }
                                card_class = team_colors.get(team, 'bg-gray-500 text-white')
                        elif is_captain:
                            # Капитан видит цвета до открытия
                            if team == -1:  # Убийца
                                card_class = 'bg-black text-white border-2 border-red-400'
                            elif team == 0:  # Нейтральная
                                card_class = 'bg-gray-300 dark:bg-gray-600 text-black dark:text-white border-2 border-gray-400'
                            else:  # Команда
                                team_colors = {
                                    1: 'bg-red-500 text-white border-2 border-red-700',
                                    2: 'bg-blue-500 text-white border-2 border-blue-700',
                                    3: 'bg-green-500 text-white border-2 border-green-700',
                                    4: 'bg-purple-500 text-white border-2 border-purple-700',
                                    5: 'bg-orange-500 text-white border-2 border-orange-700'
                                }
                                card_class = team_colors.get(team, 'bg-gray-500 text-white')
                        else:
                            # Обычные игроки видят только эмоджи
                            card_class = 'bg-white dark:bg-gray-700 text-black dark:text-white border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'

                        # Создаем карту
                        if card_click_handler and not revealed and not is_captain:
                            # Кликабельная карта для обычных игроков
                            card_button = ui.button(emoji, on_click=lambda idx=i: card_click_handler(idx))
                            card_button.classes(f'{card_class} w-16 h-16 text-2xl cursor-pointer transition-colors')
                        else:
                            # Некликабельная карта или карта для капитана
                            with ui.element('div').classes(
                                    f'{card_class} w-16 h-16 flex items-center justify-center text-2xl'):
                                ui.label(emoji)

    @staticmethod
    def create_hint_panel(current_hint, current_team_name, is_current_team_captain=False,
                          is_current_team_member=False, hint_mode="written", set_hint_handler=None,
                          end_turn_handler=None):
        """Создает панель подсказок"""
        with ui.card().classes('w-full p-4 mb-4 bg-yellow-50 dark:bg-yellow-900 rounded-lg'):
            ui.label(f'Ходит команда: {current_team_name}').classes(
                'text-lg font-bold mb-3 text-yellow-800 dark:text-yellow-200')

            if current_hint:
                # Показываем текущую подсказку
                hint_text = current_hint.get('text', '')
                hint_count = current_hint.get('count', 0)
                guesses_made = current_hint.get('guesses_made', 0)

                ui.label(f'Подсказка: "{hint_text}" - {hint_count}').classes(
                    'text-xl font-bold mb-2 text-yellow-900 dark:text-yellow-100')
                ui.label(f'Попыток сделано: {guesses_made}/{hint_count + 1}').classes(
                    'text-lg mb-3 text-yellow-800 dark:text-yellow-200')

                if is_current_team_member and end_turn_handler:
                    ui.button('Закончить ход', on_click=end_turn_handler).classes(
                        'bg-red-500 hover:bg-red-600 text-white')

            elif is_current_team_captain and set_hint_handler:
                # Форма для ввода подсказки капитаном
                ui.label('Дайте подсказку своей команде:').classes(
                    'font-medium mb-2 text-yellow-800 dark:text-yellow-200')

                if hint_mode == "written":
                    with ui.row().classes('w-full items-end gap-2 mb-2'):
                        hint_input = ui.input('Подсказка (макс. 2 слова)').classes('flex-grow')
                        hint_input.props('outlined dense')

                        count_input = ui.number('Количество', value=1, min=1, max=10).classes('w-24')
                        count_input.props('outlined dense')

                    def submit_hint():
                        if not hint_input.value or not hint_input.value.strip():
                            ui.notify('Введите подсказку', type='warning')
                            return

                        words = hint_input.value.strip().split()
                        if len(words) > 2:
                            ui.notify('Подсказка должна содержать максимум 2 слова', type='warning')
                            return

                        if count_input.value < 1:
                            ui.notify('Количество должно быть больше 0', type='warning')
                            return

                        set_hint_handler(hint_input.value.strip(), int(count_input.value))

                    ui.button('Дать подсказку', on_click=submit_hint).classes(
                        'bg-blue-600 hover:bg-blue-700 text-white')

                else:  # verbal mode
                    ui.label('Произнесите подсказку вслух и нажмите "Готово"').classes(
                        'mb-2 text-yellow-800 dark:text-yellow-200')

                    count_input = ui.number('Количество карт', value=1, min=1, max=10).classes('w-32 mb-2')
                    count_input.props('outlined dense')

                    def submit_verbal_hint():
                        if count_input.value < 1:
                            ui.notify('Количество должно быть больше 0', type='warning')
                            return
                        set_hint_handler("(устная подсказка)", int(count_input.value))

                    ui.button('Готово', on_click=submit_verbal_hint).classes(
                        'bg-blue-600 hover:bg-blue-700 text-white')

            elif is_current_team_member:
                ui.label('Ожидайте подсказку от капитана...').classes(
                    'italic text-yellow-700 dark:text-yellow-300')
            else:
                ui.label('Ходит другая команда').classes(
                    'italic text-yellow-700 dark:text-yellow-300')

    @staticmethod
    def create_team_status(teams, field):
        """Создает панель статуса команд"""
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label('Статус команд').classes('text-lg font-bold mb-3')

            for team_id, team in teams.items():
                team_name = team.get('name', f'Команда {team_id}')
                team_color = team.get('color', 'bg-gray-500')

                # Подсчитываем карты команды
                team_cards = [card for card in field if card['team'] == int(team_id)]
                revealed_cards = [card for card in team_cards if card['revealed']]

                remaining = len(team_cards) - len(revealed_cards)

                with ui.row().classes('w-full items-center mb-2'):
                    ui.element('div').classes(f'{team_color} w-4 h-4 rounded mr-2')
                    ui.label(f'{team_name}:').classes('font-medium mr-2')
                    ui.label(f'{remaining} карт осталось').classes('flex-grow')

                    # Прогресс-бар
                    progress = (len(revealed_cards) / len(team_cards)) * 100 if team_cards else 0
                    with ui.element('div').classes('w-24 bg-gray-200 rounded-full h-2'):
                        ui.element('div').classes(f'{team_color} h-2 rounded-full transition-all').style(
                            f'width: {progress}%')

    @staticmethod
    def create_game_result_card(winner, teams, current_team_data=None):
        """Создает карточку с результатами игры - ИСПРАВЛЕНО"""
        with ui.card().classes('w-full p-6 mb-4 rounded-lg'):
            if winner == "assassin":
                ui.label('Игра окончена!').classes(
                    'text-2xl font-bold mb-2 text-center text-red-600 dark:text-red-400')
                ui.label('Команда наткнулась на убийцу! 💀').classes(
                    'text-xl text-center text-red-700 dark:text-red-300 mb-2')

                # ИСПРАВЛЕНИЕ: Показываем какая именно команда проиграла
                losing_team_id = None
                if current_team_data:
                    # Приоритет: специально сохраненная losing_team, затем current_team
                    losing_team_id = current_team_data.get('losing_team') or current_team_data.get('current_team')

                if losing_team_id:
                    losing_team_id = str(losing_team_id)
                    losing_team = teams.get(losing_team_id)
                    if losing_team:
                        losing_team_name = losing_team.get('name', f'Команда {losing_team_id}')
                        ui.label(f'Команда "{losing_team_name}" проиграла, открыв карту убийцы!').classes(
                            'text-lg text-center text-red-600 dark:text-red-400 mb-2')

                # Показываем победившие команды
                winning_teams = []
                for tid, team in teams.items():
                    if tid != losing_team_id:
                        team_name = team.get('name', f'Команда {tid}')
                        winning_teams.append(team_name)

                if winning_teams:
                    if len(winning_teams) == 1:
                        ui.label(f'Команда "{winning_teams[0]}" побеждает!').classes(
                            'text-lg text-center text-green-600 dark:text-green-400')
                    else:
                        teams_list = '", "'.join(winning_teams[:-1]) + f'" и "{winning_teams[-1]}'
                        ui.label(f'Команды "{teams_list}" побеждают!').classes(
                            'text-lg text-center text-green-600 dark:text-green-400')
                else:
                    ui.label('Все остальные команды побеждают!').classes(
                        'text-lg text-center text-green-600 dark:text-green-400')
            else:
                winning_team = teams.get(str(winner))
                if winning_team:
                    team_name = winning_team.get('name', f'Команда {winner}')
                    ui.label('Победа!').classes(
                        'text-2xl font-bold mb-2 text-center text-green-600 dark:text-green-400')
                    ui.label(f'Команда "{team_name}" открыла все свои карты! 🎉').classes(
                        'text-xl text-center text-green-700 dark:text-green-300 mb-2')

                    # Показываем проигравшие команды
                    losing_teams = []
                    for tid, team in teams.items():
                        if tid != str(winner):
                            team_name = team.get('name', f'Команда {tid}')
                            losing_teams.append(team_name)

                    if losing_teams:
                        if len(losing_teams) == 1:
                            ui.label(f'Команда "{losing_teams[0]}" проиграла.').classes(
                                'text-md text-center text-gray-600 dark:text-gray-400')
                        else:
                            teams_list = '", "'.join(losing_teams[:-1]) + f'" и "{losing_teams[-1]}'
                            ui.label(f'Команды "{teams_list}" проиграли.').classes(
                                'text-md text-center text-gray-600 dark:text-gray-400')

    @staticmethod
    def create_round_indicator(status, current_team_name=None):
        """Создает индикатор текущего статуса игры"""
        status_text = {
            "waiting": "Ожидание начала игры",
            "playing": f"Игра в процессе - ходит {current_team_name or 'команда'}",
            "finished": "Игра завершена"
        }

        text = status_text.get(status, "Неизвестный статус")
        color = "text-blue-600" if status == "playing" else "text-gray-600"

        with ui.row().classes('items-center justify-center bg-blue-100 dark:bg-blue-900 rounded-lg p-3 mt-2 w-full'):
            ui.icon('info').classes(f'{color} dark:text-blue-400 text-2xl mr-2')
            ui.label(f"Статус: {text}").classes(f'text-lg font-medium {color} dark:text-blue-300')