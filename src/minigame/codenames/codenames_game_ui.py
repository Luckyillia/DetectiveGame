from datetime import datetime

from nicegui import ui, app

from src.minigame.codenames.codenames_components_ui import CodenamesComponents
from src.minigame.codenames.codenames_data_service import CodenamesDataService
from src.minigame.codenames.codenames_room_service import CodenamesRoomService
from src.services.log.log_services import LogService


class CodenamesGameUI:
    """
    Класс для управления интерфейсом игры Codenames.
    Командная игра на угадывание слов по подсказкам капитанов.
    """

    def __init__(self):
        self.log_service = LogService()
        self.data_service = CodenamesDataService()
        self.room_service = CodenamesRoomService()
        self.components = CodenamesComponents()

        self.current_room_id = None
        self.player_name = ""
        self.game_container = None
        self.last_update_time = 0
        self.update_timer = None
        self.rooms_update_timer = None

    def show_main_menu(self, container=None):
        """Показывает главное меню игры."""
        # Восстанавливаем сохраненный ID комнаты при перезагрузке
        saved_room_id = app.storage.user.get('codenames_room_id')
        if saved_room_id and not self.current_room_id:
            self.current_room_id = saved_room_id
            # Проверяем существование комнаты
            if self.room_service.room_exists(saved_room_id):
                # Восстанавливаем участие в комнате
                self.player_name = app.storage.user.get('username', '')
                success = self.room_service.add_player(
                    saved_room_id,
                    app.storage.user.get('user_id'),
                    self.player_name
                )
                if success:
                    # Проверяем, начата ли игра
                    room_data = self.room_service.get_room(saved_room_id)
                    if room_data and room_data['status'] == 'playing':
                        if container:
                            self.game_container = container
                        self.show_game_screen()
                        return
                    else:
                        if container:
                            self.game_container = container
                        self.show_waiting_room()
                        return

        if container is not None:
            self.game_container = container

        if self.game_container is None:
            self.game_container = ui.element('div').classes('w-full')
        else:
            self.game_container.clear()

        self._cancel_timers()

        # Получаем имя пользователя
        self.player_name = app.storage.user.get('username', '')

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Codenames"',
                    'Командная игра на угадывание слов по подсказкам капитанов!',
                    'psychology'
                )

                with ui.expansion('Правила игры', icon='help_outline').classes(
                        'w-full mb-4 bg-blue-50 dark:bg-blue-900 rounded-lg'):
                    ui.markdown("""
                    ### Правила игры "Codenames":

                    1. **Команды**: Игроки делятся на команды (2-5 команд), в каждой есть капитан и участники.
                    2. **Поле**: На поле размещены карты с эмоджи, каждая принадлежит одной из команд или нейтральная.
                    3. **Цель**: Команда должна найти все свои карты раньше соперников.
                    4. **Подсказки**: Капитан дает подсказку - одно слово и число (количество карт).
                    5. **Угадывание**: Участники команды выбирают карты, основываясь на подсказке капитана.
                    6. **Ограничения**: 
                       - Капитан видит, какая карта какой команде принадлежит
                       - Участники видят только эмоджи
                       - Есть карта "убийца" - если её открыть, команда проигрывает
                    7. **Победа**: Команда, которая первой откроет все свои карты, побеждает.

                    **Роли:**
                    - **Капитан**: Видит принадлежность карт, дает подсказки
                    - **Участник**: Угадывает карты по подсказкам капитана

                    **Режимы подсказок:**
                    - **Письменные**: Капитан пишет подсказку в чат
                    - **Устные**: Капитан произносит подсказку вслух (для живого общения)
                    """).classes('p-3')

            with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                with ui.row().classes('w-full items-center mb-4'):
                    ui.icon('person').classes('text-blue-500 mr-2')
                    ui.label('Ваше имя:').classes('mr-2 font-medium text-gray-700 dark:text-gray-300')
                    player_name_input = ui.input(value=self.player_name).classes('flex-grow')
                    player_name_input.props('outlined rounded dense')

                    def update_player_name():
                        self.player_name = player_name_input.value.strip()
                        if not self.player_name:
                            self.player_name = app.storage.user.get('username', '')
                            player_name_input.value = self.player_name

                    player_name_input.on('blur', lambda: update_player_name())

                with ui.row().classes('w-full gap-2 mb-4'):
                    ui.button('Создать новую игру', icon='add_circle', on_click=self.create_new_game).classes(
                        'flex-grow bg-blue-600 hover:bg-blue-700 text-white')
                    ui.button('Присоединиться к игре', icon='login', on_click=self.show_join_menu).classes(
                        'flex-grow bg-green-600 hover:bg-green-700 text-white')
                    ui.button('Обновить список', icon='refresh', on_click=self.refresh_rooms_list).classes(
                        'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600')

            self._create_available_rooms_list()

    def _create_available_rooms_list(self):
        """Создает и отображает список доступных комнат"""
        with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
            ui.label('Доступные комнаты:').classes('text-xl font-bold mb-4 text-blue-600 dark:text-blue-400')
            rooms_container = ui.element('div').classes('w-full')

            def update_rooms_list():
                rooms_container.clear()
                with rooms_container:
                    available_rooms = self.room_service.get_rooms_list()

                    if available_rooms:
                        rows = []
                        for i, room in enumerate(available_rooms):
                            rows.append({
                                'id': room['room_id'],
                                'room_id': room['room_id'],
                                'host_name': room['host_name'],
                                'player_count': room['player_count'],
                                'team_count': room['team_count'],
                                'created_at': datetime.fromtimestamp(room['created_at']).strftime('%H:%M:%S')
                            })

                        columns = [
                            {'name': 'room_id', 'label': 'ID комнаты', 'field': 'room_id', 'align': 'center'},
                            {'name': 'host_name', 'label': 'Создатель', 'field': 'host_name', 'align': 'center'},
                            {'name': 'player_count', 'label': 'Игроков', 'field': 'player_count', 'align': 'center'},
                            {'name': 'team_count', 'label': 'Команд', 'field': 'team_count', 'align': 'center'},
                            {'name': 'created_at', 'label': 'Создана', 'field': 'created_at', 'align': 'center'},
                            {'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'},
                        ]

                        table = ui.table(
                            columns=columns,
                            rows=rows,
                            row_key='id',
                            column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary'}
                        ).classes('w-full')

                        table.add_slot('body', '''
                            <q-tr :props="props">
                                <q-td v-for="col in props.cols" :key="col.name" :props="props" class="text-center">
                                    <template v-if="col.name === 'action'">
                                        <div class="flex justify-center">
                                            <q-btn color="primary" dense icon="login" size="md"
                                                   @click="() => $parent.$emit('join', props.row.room_id)">
                                                Присоединиться
                                            </q-btn>
                                        </div>
                                    </template>
                                    <template v-else>
                                        <span>{{ col.value }}</span>
                                    </template>
                                </q-td>
                            </q-tr>
                        ''')

                        table.on('join', lambda e: self.join_game(e.args))
                    else:
                        with ui.card().classes('w-full p-4 bg-gray-200 dark:bg-gray-700 rounded-lg'):
                            with ui.row().classes('items-center justify-center text-gray-500 dark:text-gray-400'):
                                ui.icon('info').classes('text-xl mr-2')
                                ui.label('Нет доступных комнат').classes('text-center')

            update_rooms_list()
            self.rooms_update_timer = ui.timer(5.0, update_rooms_list)

    def _cancel_timers(self):
        """Отменяет все активные таймеры"""
        if self.update_timer:
            try:
                self.update_timer.cancel()
                self.update_timer = None
            except:
                pass

        if self.rooms_update_timer:
            try:
                self.rooms_update_timer.cancel()
                self.rooms_update_timer = None
            except:
                pass

    def refresh_rooms_list(self):
        """Обновляет список комнат вручную"""
        self.show_main_menu(self.game_container)
        ui.notify('Список комнат обновлен', type='positive')

    def create_new_game(self):
        """Создает новую игру."""
        if not self.player_name:
            ui.notify('Введите ваше имя', type='warning')
            return

        room_id = self.room_service.create_room(
            app.storage.user.get('user_id'),
            self.player_name
        )

        if not room_id:
            ui.notify('Ошибка при создании комнаты', type='negative')
            return

        self.current_room_id = room_id
        app.storage.user.update({'codenames_room_id': room_id})
        self.show_waiting_room()

    def show_join_menu(self):
        """Показывает меню для присоединения к игре."""
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
            ui.label('Присоединиться к игре').classes(
                'text-xl font-bold mb-4 text-center text-blue-600 dark:text-blue-400')

            room_id_input = ui.input('ID комнаты', placeholder='Введите ID комнаты').classes('w-full mb-4')
            room_id_input.props('outlined dense rounded')

            def join_room():
                room_id = room_id_input.value.strip()
                if not room_id:
                    ui.notify('Введите ID комнаты', type='warning')
                    return

                if not self.player_name:
                    ui.notify('Введите ваше имя', type='warning')
                    return

                if not self.room_service.room_exists(room_id):
                    ui.notify('Комната не найдена', type='negative')
                    return

                dialog.close()
                self.join_game(room_id)

            with ui.row().classes('w-full justify-between gap-4'):
                ui.button('Отмена', icon='close', on_click=dialog.close).classes(
                    'bg-gray-300 dark:bg-gray-700 hover:bg-gray-400')
                ui.button('Присоединиться', icon='login', on_click=join_room).classes(
                    'bg-blue-600 hover:bg-blue-700 text-white')

        dialog.open()

    def join_game(self, room_id):
        """Присоединяется к существующей игре."""
        if not self.player_name:
            ui.notify('Введите ваше имя', type='warning')
            return

        success = self.room_service.add_player(
            room_id,
            app.storage.user.get('user_id'),
            self.player_name
        )

        if not success:
            ui.notify('Ошибка при присоединении к комнате', type='negative')
            return

        self.current_room_id = room_id
        app.storage.user.update({'codenames_room_id': room_id})

        room_data = self.room_service.get_room(room_id)
        if room_data and room_data['status'] == 'playing':
            self.show_game_screen()
        else:
            self.show_waiting_room()

    def show_waiting_room(self):
        """Показывает комнату ожидания игры."""
        if not self.current_room_id:
            self.show_main_menu()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'codenames_room_id': None})
            self.show_main_menu()
            return

        # ИСПРАВЛЕНИЕ: Очищаем контейнер только при первом показе
        if not hasattr(self, '_waiting_room_shown'):
            self.game_container.clear()
            self._waiting_room_shown = True

        # Отменяем существующие таймеры и создаем новый
        self._cancel_timers()
        self.update_timer = ui.timer(2.0, lambda: self.update_waiting_room())  # Увеличиваем интервал

        current_user_id = app.storage.user.get('user_id')
        current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)
        is_host = current_player and current_player.get("is_host", False)

        # Создаем или обновляем контент
        self._render_waiting_room_content(room_data, current_user_id, is_host)

    def _render_waiting_room_content(self, room_data, current_user_id, is_host):
        """Рендерит содержимое комнаты ожидания"""
        # Очищаем контейнер каждый раз при рендеринге
        self.game_container.clear()

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Codenames"',
                    f'ID комнаты: {self.current_room_id}'
                )

                if room_data["status"] == "waiting":
                    self.components.create_status_indicator('Формирование команд...', 'waiting')

                    # Копировать ID комнаты
                    with ui.row().classes('w-full justify-center mb-4'):
                        ui.button(
                            'Копировать ID комнаты',
                            icon='content_copy',
                            on_click=lambda: ui.notify('ID скопирован', type='positive')
                        ).classes('bg-blue-600 hover:bg-blue-700 text-white')

                    # Показываем статистику команд
                    with ui.card().classes('w-full p-4 mb-4 bg-blue-50 dark:bg-blue-800 rounded-lg'):
                        teams_count = len(room_data["teams"])
                        max_teams = room_data["settings"]["team_count"]
                        ui.label(f'Команд создано: {teams_count}/{max_teams}').classes(
                            'text-lg font-bold text-blue-800 dark:text-blue-200 text-center')

                        # Показываем требования для начала игры
                        if teams_count >= 2:
                            # Проверяем, есть ли в каждой команде капитан
                            ready_teams = sum(1 for team in room_data["teams"].values() if team.get("captain"))
                            if ready_teams >= 2:
                                ui.label('✅ Готово к началу игры!').classes(
                                    'text-green-600 dark:text-green-400 text-center font-medium')
                            else:
                                ui.label('⏳ Нужны капитаны во всех командах').classes(
                                    'text-yellow-600 dark:text-yellow-400 text-center font-medium')
                        else:
                            ui.label('⏳ Нужно минимум 2 команды').classes(
                                'text-yellow-600 dark:text-yellow-400 text-center font-medium')

                    # Выбор команды
                    self.components.create_team_selection(
                        room_data["teams"],
                        room_data["settings"]["team_count"],
                        self.join_team_with_validation,
                        current_user_id
                    )

                    # Настройки игры (только для хоста)
                    if is_host:
                        try:
                            self.components.create_game_settings(
                                room_data["settings"],
                                self.update_settings,
                                is_host
                            )
                        except Exception as e:
                            ui.label(f'Ошибка настроек: {str(e)}').classes('text-red-500')

                    # Список игроков
                    with ui.card().classes('w-full p-4 mb-4 bg-gray-200 dark:bg-gray-700 rounded-lg shadow'):
                        ui.label('Игроки:').classes('font-bold mb-3 text-lg text-gray-800 dark:text-gray-200')
                        try:
                            self.components.create_player_table(
                                room_data["players"],
                                room_data["teams"],
                                current_user_id
                            )
                        except Exception as e:
                            ui.label(f'Ошибка таблицы игроков: {str(e)}').classes('text-red-500')

                    # Кнопка начала игры (только для хоста)
                    if is_host:
                        def start_game():
                            # Проверяем требования перед началом
                            teams_count = len(room_data["teams"])
                            if teams_count < 2:
                                ui.notify('Нужно минимум 2 команды для начала игры', type='warning')
                                return

                            # Проверяем, есть ли капитаны во всех командах
                            teams_without_captain = [team_id for team_id, team in room_data["teams"].items()
                                                     if not team.get("captain")]
                            if teams_without_captain:
                                ui.notify('Во всех командах должны быть капитаны', type='warning')
                                return

                            try:
                                field = self.data_service.generate_game_field(teams_count)
                                success = self.room_service.start_game(self.current_room_id, field)
                                if success:
                                    ui.notify('Игра началась!', type='positive')
                                    self._waiting_room_shown = False  # Сбрасываем флаг
                                    self.show_game_screen()
                                else:
                                    ui.notify('Ошибка при запуске игры', type='negative')
                            except Exception as e:
                                ui.notify(f'Ошибка при создании игры: {str(e)}', type='negative')

                        # Кнопка активна только при выполнении условий
                        teams_ready = len(room_data["teams"]) >= 2 and all(
                            team.get("captain") for team in room_data["teams"].values()
                        )

                        start_button = ui.button('Начать игру', icon='play_arrow', on_click=start_game)
                        if teams_ready:
                            start_button.classes('w-full bg-green-600 hover:bg-green-700 text-white mt-3')
                        else:
                            start_button.classes('w-full bg-gray-400 text-gray-600 mt-3')
                            start_button.props('disable')

            # Кнопка выхода из игры
            ui.button('Выйти из игры', icon='exit_to_app', on_click=self.leave_game).classes(
                'w-full bg-red-500 hover:bg-red-600 text-white mt-4')

    def update_waiting_room(self):
        """Обновляет данные в комнате ожидания."""
        if not self.current_room_id:
            self._cancel_timers()
            return

        try:
            room_data = self.room_service.get_room(self.current_room_id)
            if not room_data:
                self._cancel_timers()
                ui.notify('Комната была удалена', type='negative')
                self.current_room_id = None
                app.storage.user.update({'codenames_room_id': None})
                self.show_main_menu()
                return

            # Если статус изменился на playing, переходим на экран игры
            if room_data["status"] == "playing":
                self.last_update_time = room_data.get("last_activity", 0)
                self._waiting_room_shown = False  # Сбрасываем флаг
                self.show_game_screen()
                return

            # ИСПРАВЛЕНИЕ: Обновляем только при изменении данных
            if room_data.get("last_activity", 0) > self.last_update_time:
                self.last_update_time = room_data.get("last_activity", 0)

                current_user_id = app.storage.user.get('user_id')
                current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)
                is_host = current_player and current_player.get("is_host", False)

                # Перерисовываем только содержимое
                self._render_waiting_room_content(room_data, current_user_id, is_host)

        except Exception as e:
            # Логируем ошибку и продолжаем
            self.log_service.add_error_log(
                error_message=f"Ошибка обновления комнаты ожидания: {str(e)}",
                action="CODENAMES_UPDATE_ERROR",
                user_id=app.storage.user.get('user_id')
            )
            print(f"Ошибка обновления комнаты ожидания: {e}")

    def join_team_with_validation(self, team_id, role):
        """
        Присоединяется к команде с улучшенной валидацией и обработкой ошибок.
        """
        if not self.current_room_id:
            ui.notify('Ошибка: не выбрана комната', type='negative')
            return

        try:
            # Получаем актуальные данные комнаты
            room_data = self.room_service.get_room(self.current_room_id)
            if not room_data:
                ui.notify('Комната не найдена', type='negative')
                return

            current_user_id = app.storage.user.get('user_id')

            # Получаем доступные действия для валидации
            available_actions = self.room_service.get_available_team_actions(
                self.current_room_id,
                current_user_id
            )

            if "error" in available_actions:
                ui.notify(f'Ошибка валидации: {available_actions["error"]}', type='negative')
                return

            # Проверяем, можно ли выполнить запрошенное действие
            if role == "captain":
                if team_id in room_data["teams"] and room_data["teams"][team_id].get("captain"):
                    existing_captain_id = room_data["teams"][team_id]["captain"]
                    if existing_captain_id != current_user_id:
                        # Находим имя существующего капитана
                        captain_name = next(
                            (p["name"] for p in room_data["players"] if p["id"] == existing_captain_id),
                            "Неизвестный игрок"
                        )
                        team_name = room_data["teams"][team_id].get("name", f"команды {team_id}")
                        ui.notify(
                            f'У {team_name} уже есть капитан: {captain_name}',
                            type='warning'
                        )
                        return

                # Проверяем лимит команд
                if team_id not in room_data["teams"]:
                    max_teams = room_data["settings"].get("team_count", 2)
                    if int(team_id) > max_teams:
                        ui.notify(
                            f'Нельзя создать команду {team_id}. Максимум команд: {max_teams}',
                            type='warning'
                        )
                        return

            elif role == "member":
                if team_id not in room_data["teams"]:
                    ui.notify(f'Команда {team_id} не существует', type='warning')
                    return

                if not room_data["teams"][team_id].get("captain"):
                    ui.notify(f'У команды {team_id} нет капитана', type='warning')
                    return

                if current_user_id in room_data["teams"][team_id].get("members", []):
                    ui.notify('Вы уже участник этой команды', type='info')
                    return

            # Выполняем присоединение
            success = self.room_service.join_team(
                self.current_room_id,
                current_user_id,
                team_id,
                role
            )

            if success:
                # Определяем название команды и роль для уведомления
                role_text = "капитаном" if role == "captain" else "участником"
                team_colors = {
                    "1": "Красной", "2": "Синей", "3": "Зеленой",
                    "4": "Фиолетовой", "5": "Оранжевой"
                }
                team_name = team_colors.get(team_id, f"команды {team_id}")

                ui.notify(f'Вы стали {role_text} {team_name} команды!', type='positive')

                # Логируем успешное присоединение
                self.log_service.add_log(
                    level="GAME",
                    action="CODENAMES_JOIN_TEAM_SUCCESS",
                    message=f"Игрок успешно присоединился к команде {team_id} как {role}",
                    user_id=current_user_id,
                    metadata={
                        "room_id": self.current_room_id,
                        "team_id": team_id,
                        "role": role,
                        "team_name": team_name
                    }
                )

                # Принудительно обновляем данные
                self.last_update_time = 0
            else:
                ui.notify('Ошибка при присоединении к команде. Попробуйте еще раз.', type='negative')

                # Логируем неудачную попытку
                self.log_service.add_error_log(
                    error_message=f"Неудачная попытка присоединения к команде {team_id} как {role}",
                    action="CODENAMES_JOIN_TEAM_FAILED",
                    user_id=current_user_id,
                    metadata={"room_id": self.current_room_id, "team_id": team_id, "role": role}
                )

        except Exception as e:
            ui.notify(f'Произошла ошибка: {str(e)}', type='negative')
            self.log_service.add_error_log(
                error_message=f"Исключение при присоединении к команде: {str(e)}",
                action="CODENAMES_JOIN_TEAM_EXCEPTION",
                user_id=app.storage.user.get('user_id'),
                metadata={"team_id": team_id, "role": role}
            )

    def validate_game_start_conditions(self, room_data):
        """
        Валидирует условия для начала игры и возвращает детальную информацию.

        Returns:
            tuple: (bool можно_начать, list сообщения_об_ошибках)
        """
        errors = []

        # Проверяем количество команд
        teams_count = len(room_data["teams"])
        if teams_count < 2:
            errors.append(f"Нужно минимум 2 команды (сейчас: {teams_count})")

        # Проверяем капитанов
        teams_without_captain = []
        for team_id, team in room_data["teams"].items():
            if not team.get("captain"):
                team_name = team.get("name", f"Команда {team_id}")
                teams_without_captain.append(team_name)

        if teams_without_captain:
            errors.append(f"Команды без капитанов: {', '.join(teams_without_captain)}")

        # Проверяем общее количество игроков
        total_players = len(room_data["players"])
        if total_players < teams_count:
            errors.append(f"Недостаточно игроков: нужно минимум {teams_count}, есть {total_players}")

        # Проверяем, что все игроки в командах (опционально)
        players_without_teams = [
            p["name"] for p in room_data["players"]
            if not p.get("team")
        ]

        if players_without_teams:
            # Это предупреждение, а не ошибка
            ui.notify(
                f'Игроки вне команд: {", ".join(players_without_teams)}. Они не смогут участвовать в игре.',
                type='warning'
            )

        return len(errors) == 0, errors

    def update_settings(self, settings):
        """Обновляет настройки игры."""
        if not self.current_room_id:
            return

        try:
            success = self.room_service.update_settings(self.current_room_id, settings)
            if success:
                ui.notify('Настройки обновлены', type='positive')

                # Логируем изменение настроек
                self.log_service.add_log(
                    level="GAME",
                    action="CODENAMES_SETTINGS_UPDATE",
                    message=f"Обновлены настройки игры",
                    user_id=app.storage.user.get('user_id'),
                    metadata={"room_id": self.current_room_id, "new_settings": settings}
                )

                # Принудительно обновляем данные
                self.last_update_time = 0

            else:
                ui.notify('Ошибка при обновлении настроек', type='negative')

        except Exception as e:
            ui.notify(f'Ошибка: {str(e)}', type='negative')
            self.log_service.add_error_log(
                error_message=f"Ошибка обновления настроек: {str(e)}",
                action="CODENAMES_SETTINGS_ERROR"
            )

    def show_game_screen(self):
        """Показывает экран игры."""
        if not self.current_room_id:
            self.show_main_menu()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'codenames_room_id': None})
            self.show_main_menu()
            return

        if room_data["status"] != "playing":
            self.show_waiting_room()
            return

        self.game_container.clear()

        self._cancel_timers()
        self.update_timer = ui.timer(1.0, lambda: self.update_game_screen())

        current_user_id = app.storage.user.get('user_id')
        current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)

        if not current_player:
            ui.notify('Игрок не найден в комнате', type='negative')
            return

        player_team = current_player.get("team")
        player_role = current_player.get("role")
        current_team_id = str(room_data["game_data"]["current_team"])

        is_captain = player_role == "captain"
        is_current_team_captain = is_captain and player_team == current_team_id
        is_current_team_member = player_team == current_team_id and not is_captain

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                self.components.create_header('Игра "Codenames"')

                # Индикатор статуса игры
                current_team_name = room_data["teams"].get(current_team_id, {}).get("name",
                                                                                    f"Команда {current_team_id}")
                self.components.create_round_indicator("playing", current_team_name)

            # Панель подсказок
            self.components.create_hint_panel(
                room_data["game_data"].get("current_hint"),
                current_team_name,
                is_current_team_captain,
                is_current_team_member,
                room_data["settings"]["hint_mode"],
                self.set_hint,
                self.end_turn
            )

            # Игровое поле
            field = room_data["game_data"]["field"]
            grid_size = self.data_service.get_grid_size(len(room_data["teams"]))

            self.components.create_game_field(
                field,
                grid_size,
                is_captain,
                self.make_guess if not is_captain else None
            )

            # Статус команд
            self.components.create_team_status(room_data["teams"], field)

            # Список игроков
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                ui.label('Игроки:').classes('text-lg font-bold mb-3 text-gray-800 dark:text-gray-200')
                self.components.create_player_table(
                    room_data["players"],
                    room_data["teams"],
                    current_user_id
                )

            # Проверяем, не завершена ли игра
            if room_data["status"] == "finished":
                winner = room_data["game_data"].get("winner")
                self.components.create_game_result_card(winner, room_data["teams"])

            # Кнопка выхода
            ui.button('Выйти из игры', icon='exit_to_app', on_click=self.leave_game).classes(
                'w-full bg-red-500 hover:bg-red-600 text-white mt-4')

    def update_game_screen(self):
        """Обновляет данные на экране игры."""
        if not self.current_room_id:
            self._cancel_timers()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            self._cancel_timers()
            ui.notify('Комната была удалена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'codenames_room_id': None})
            self.show_main_menu()
            return

        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)

            if room_data["status"] == "finished":
                self.show_game_over(room_data["game_data"].get("winner"), room_data["teams"])
                return

            self.show_game_screen()

    def set_hint(self, hint_text, hint_count):
        """Устанавливает подсказку от капитана."""
        if not self.current_room_id:
            return

        success = self.room_service.set_hint(
            self.current_room_id,
            app.storage.user.get('user_id'),
            hint_text,
            hint_count
        )

        if success:
            ui.notify('Подсказка дана команде!', type='positive')
            self.show_game_screen()
        else:
            ui.notify('Ошибка при даче подсказки', type='negative')

    def make_guess(self, card_index):
        """Делает попытку угадать карту."""
        if not self.current_room_id:
            return

        success = self.room_service.make_guess(
            self.current_room_id,
            app.storage.user.get('user_id'),
            card_index
        )

        if success:
            self.show_game_screen()
        else:
            ui.notify('Ошибка при выборе карты', type='negative')

    def end_turn(self):
        """Заканчивает ход команды."""
        if not self.current_room_id:
            return

        success = self.room_service.end_turn(
            self.current_room_id,
            app.storage.user.get('user_id')
        )

        if success:
            ui.notify('Ход завершен', type='positive')
            self.show_game_screen()
        else:
            ui.notify('Ошибка при завершении хода', type='negative')

    def show_game_over(self, winner, teams):
        """Показывает экран завершения игры."""
        self._cancel_timers()
        self.game_container.clear()

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 text-center'):
                ui.label('Игра завершена!').classes('text-2xl font-bold mb-4 text-blue-600 dark:text-blue-400')

                self.components.create_game_result_card(winner, teams)

                with ui.row().classes('w-full justify-center gap-4 mt-6'):
                    ui.button('Играть снова', icon='replay', on_click=self.reset_game).classes(
                        'bg-blue-600 hover:bg-blue-700 text-white')
                    ui.button('Выйти в меню', icon='home', on_click=self.return_to_menu).classes(
                        'bg-gray-500 hover:bg-gray-600 text-white')

    def reset_game(self):
        """Сбрасывает игру для повторной игры."""
        if not self.current_room_id:
            return

        success = self.room_service.reset_game(self.current_room_id)
        if success:
            ui.notify('Игра сброшена', type='positive')
            self.show_waiting_room()
        else:
            ui.notify('Ошибка при сбросе игры', type='negative')

    def return_to_menu(self):
        """Возвращает в главное меню."""
        if self.current_room_id:
            self.leave_game()
        else:
            self.show_main_menu()

    def leave_game(self):
        """Выходит из текущей игры."""
        if not self.current_room_id:
            return

        self._cancel_timers()

        success = self.room_service.remove_player(
            self.current_room_id,
            app.storage.user.get('user_id')
        )

        if success:
            ui.notify('Вы покинули игру', type='positive')
        else:
            ui.notify('Ошибка при выходе из игры', type='warning')

        self.current_room_id = None
        app.storage.user.update({'codenames_room_id': None})
        self.show_main_menu()