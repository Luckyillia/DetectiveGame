from nicegui import ui, app
import random
import time
from datetime import datetime

from src.minigame.spy.spy_data_service import SpyDataService
from src.minigame.spy.spy_room_service import SpyRoomService
from src.services.log.log_services import LogService
from src.minigame.spy.spy_ui_components import SpyComponents


class SpyGameUI:
    """
    Класс для управления интерфейсом игры Шпион.
    Гибридный режим: обсуждение происходит вживую, а интерфейс онлайн.
    """

    def __init__(self):
        self.log_service = LogService()
        self.data_service = SpyDataService()
        self.room_service = SpyRoomService()
        self.components = SpyComponents()

        self.current_room_id = None
        self.player_name = ""
        self.game_container = None
        self.last_update_time = 0
        self.update_timer = None
        self.rooms_update_timer = None

    def show_main_menu(self, container=None):
        """Показывает главное меню игры."""
        # Восстанавливаем сохраненный ID комнаты при перезагрузке
        saved_room_id = app.storage.user.get('spy_room_id')
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
                    'Игра "Шпион"',
                    'Социальная игра-детектив: найди шпиона, который не знает локацию!',
                    'person_search'
                )

                with ui.expansion('Правила игры', icon='help_outline').classes(
                        'w-full mb-4 bg-red-50 dark:bg-red-900 rounded-lg'):
                    ui.markdown("""
                    ### Правила игры "Шпион":

                    1. Выбирается **категория** (например, "Украина") и **локация** из неё (например, "Аэропорт Борисполь").
                    2. Все игроки знают категорию и локацию, кроме одного - **Шпиона**.
                    3. **Шпион** знает только категорию, но не знает конкретную локацию.
                    4. Игроки общаются **вживую** (голосом/дискорд/лично) и задают вопросы друг другу о локации.
                    5. Шпион должен выяснить локацию через общение, не выдав себя.
                    6. Обычные игроки должны найти Шпиона, не выдав при этом локацию.
                    7. После обсуждения все игроки голосуют, кто, по их мнению, Шпион.
                    8. Если Шпион пойман, он может попытаться угадать локацию из данной категории.
                    9. Если Шпион угадал локацию или не был пойман - он выигрывает.

                    **Цель обычных игроков**: выявить Шпиона.
                    **Цель Шпиона**: остаться незамеченным или угадать локацию.

                    **Общение происходит в реальном времени**, интерфейс служит только для отображения информации и голосования.
                    """).classes('p-3')

            with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                with ui.row().classes('w-full items-center mb-4'):
                    ui.icon('person').classes('text-red-500 mr-2')
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
                        'flex-grow bg-red-600 hover:bg-red-700 text-white')
                    ui.button('Присоединиться к игре', icon='login', on_click=self.show_join_menu).classes(
                        'flex-grow bg-blue-600 hover:bg-blue-700 text-white')
                    ui.button('Обновить список', icon='refresh', on_click=self.refresh_rooms_list).classes(
                        'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600')

            self._create_available_rooms_list()

    def _create_available_rooms_list(self):
        """Creates and displays a list of available rooms using consistent styling"""
        with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
            ui.label('Доступные комнаты:').classes('text-xl font-bold mb-4 text-red-600 dark:text-red-400')
            rooms_container = ui.element('div').classes('w-full')

            # Function to update the rooms list
            def update_rooms_list():
                rooms_container.clear()
                with rooms_container:
                    available_rooms = self.room_service.get_rooms_list()

                    if available_rooms:
                        # Create rows for the table
                        rows = []
                        for i, room in enumerate(available_rooms):
                            rows.append({
                                'id': room['room_id'],
                                'room_id': room['room_id'],
                                'host_name': room['host_name'],
                                'player_count': room['player_count'],
                                'created_at': datetime.fromtimestamp(room['created_at']).strftime('%H:%M:%S')
                            })

                        # Define columns in the same style as player table
                        columns = [
                            {'name': 'room_id', 'label': 'ID комнаты', 'field': 'room_id', 'align': 'center'},
                            {'name': 'host_name', 'label': 'Создатель', 'field': 'host_name', 'align': 'center'},
                            {'name': 'player_count', 'label': 'Игроков', 'field': 'player_count', 'align': 'center'},
                            {'name': 'created_at', 'label': 'Создана', 'field': 'created_at', 'align': 'center'},
                            {'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'},
                        ]

                        # Create the table with unified styling
                        table = ui.table(
                            columns=columns,
                            rows=rows,
                            row_key='id',
                            column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary'}
                        ).classes('w-full')

                        # Add custom body slot for action buttons
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

                        # Add handler for join event
                        table.on('join', lambda e: self.join_game(e.args))
                    else:
                        with ui.card().classes('w-full p-4 bg-gray-200 dark:bg-gray-700 rounded-lg'):
                            with ui.row().classes('items-center justify-center text-gray-500 dark:text-gray-400'):
                                ui.icon('info').classes('text-xl mr-2')
                                ui.label('Нет доступных комнат').classes('text-center')

            # Update the rooms list
            update_rooms_list()

            # Start timer to update the rooms list (every 5 seconds)
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

        # Создаем новую комнату
        room_id = self.room_service.create_room(
            app.storage.user.get('user_id'),
            self.player_name
        )

        if not room_id:
            ui.notify('Ошибка при создании комнаты', type='negative')
            return

        self.current_room_id = room_id
        # Сохраняем ID комнаты в хранилище пользователя
        app.storage.user.update({'spy_room_id': room_id})
        self.show_waiting_room()

    def show_join_menu(self):
        """Показывает меню для присоединения к игре."""
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
            ui.label('Присоединиться к игре').classes(
                'text-xl font-bold mb-4 text-center text-red-600 dark:text-red-400')

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
                    'bg-red-600 hover:bg-red-700 text-white')

        dialog.open()

    def join_game(self, room_id):
        """Присоединяется к существующей игре."""
        if not self.player_name:
            ui.notify('Введите ваше имя', type='warning')
            return

        # Присоединяемся к комнате
        success = self.room_service.add_player(
            room_id,
            app.storage.user.get('user_id'),
            self.player_name
        )

        if not success:
            ui.notify('Ошибка при присоединении к комнате', type='negative')
            return

        self.current_room_id = room_id
        # Сохраняем ID комнаты в хранилище пользователя
        app.storage.user.update({'spy_room_id': room_id})

        # Проверяем, не началась ли уже игра
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
            app.storage.user.update({'spy_room_id': None})
            self.show_main_menu()
            return

        self.game_container.clear()

        # Запускаем таймер обновления
        self._cancel_timers()
        self.update_timer = ui.timer(1.0, lambda: self.update_waiting_room())

        # Получаем данные текущего игрока
        current_user_id = app.storage.user.get('user_id')
        current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)
        is_host = current_player and current_player.get("is_host", False)

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Шпион"',
                    f'ID комнаты: {self.current_room_id}'
                )

                if room_data["status"] == "waiting":
                    self.components.create_status_indicator('Ожидание игроков...', 'waiting')

                    # Копировать ID комнаты
                    with ui.row().classes('w-full justify-center mb-4'):
                        ui.button(
                            'Копировать ID комнаты',
                            icon='content_copy',
                            on_click=lambda: ui.notify('ID скопирован', type='positive')
                        ).classes('bg-red-600 hover:bg-red-700 text-white')

                    # Список игроков
                    with ui.card().classes('w-full p-4 mb-4 bg-gray-200 dark:bg-gray-700 rounded-lg shadow'):
                        ui.label('Игроки:').classes('font-bold mb-3 text-lg text-gray-800 dark:text-gray-200')

                        # Создаем таблицу игроков
                        self.components.create_player_table(
                            players=room_data["players"],
                            current_round=0
                        )

                    # Если хост, показываем кнопку выбора локации и начала игры
                    if is_host:
                        # Выбор локации
                        with ui.card().classes('w-full p-4 mb-4 bg-red-50 dark:bg-red-900 rounded-lg shadow'):
                            ui.label('Настройки игры (только для ведущего)').classes(
                                'font-bold mb-3 text-lg text-red-800 dark:text-red-200')

                            with ui.row().classes('items-center mb-2'):
                                ui.label('Выберите категорию:').classes('font-medium mr-2')
                                category_select = ui.select(
                                    options=self.data_service.get_all_categories(),
                                    value=self.data_service.get_random_category()
                                ).classes('flex-grow')
                                category_select.props('outlined dense')

                            # Кнопка начала игры
                            def start_game():
                                if not category_select.value:
                                    ui.notify('Выберите категорию', type='negative')
                                    return

                                # Получаем случайную локацию из категории
                                location = self.data_service.get_random_location_from_category(category_select.value)
                                if not location:
                                    ui.notify('Не удалось получить локацию для категории', type='negative')
                                    return

                                # Проверяем, достаточно ли игроков
                                if len(room_data["players"]) < 3:
                                    ui.notify('Для игры нужно минимум 3 игрока', type='warning')
                                    return

                                # Начинаем игру
                                success = self.room_service.start_game(
                                    self.current_room_id,
                                    category_select.value,
                                    location
                                )

                                if success:
                                    ui.notify('Игра началась!', type='positive')
                                    self.show_game_screen()
                                else:
                                    ui.notify('Ошибка при запуске игры', type='negative')

                            ui.button('Начать игру', icon='play_arrow', on_click=start_game).classes(
                                'w-full bg-red-600 hover:bg-red-700 text-white mt-3')
                    else:
                        # Для обычных игроков - кнопка готовности
                        is_ready = current_player and current_player.get("is_ready", False)

                        ready_button = ui.button(
                            'Я готов!' if not is_ready else 'Отменить готовность',
                            icon='check_circle' if not is_ready else 'cancel',
                            on_click=lambda: self.toggle_ready()
                        ).classes(
                            f'w-full {"bg-red-600 hover:bg-red-700 text-white" if not is_ready else "bg-red-500 hover:bg-red-600 text-white"}')

                # Кнопка выхода из игры
                ui.button('Выйти из игры', icon='exit_to_app', on_click=self.leave_game).classes(
                    'w-full bg-red-500 hover:bg-red-600 text-white mt-4')

    def update_waiting_room(self):
        """Обновляет данные в комнате ожидания."""
        if not self.current_room_id:
            self._cancel_timers()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            self._cancel_timers()
            ui.notify('Комната была удалена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'spy_room_id': None})
            self.show_main_menu()
            return

        # Если статус изменился на playing, переходим на экран игры
        if room_data["status"] == "playing":
            self.last_update_time = room_data.get("last_activity", 0)
            self.show_game_screen()
            return

        # Проверяем, было ли обновление данных комнаты
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)
            self.show_waiting_room()
            return

    def toggle_ready(self):
        """Переключает статус готовности игрока."""
        if not self.current_room_id:
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            return

        current_user_id = app.storage.user.get('user_id')
        current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)

        if not current_player:
            return

        is_ready = current_player.get("is_ready", False)
        success = self.room_service.set_player_ready(self.current_room_id, current_user_id, not is_ready)

        if success:
            ui.notify(f'Вы {"готовы" if not is_ready else "не готовы"} к игре!', type='positive')
            self.show_waiting_room()

    def show_game_screen(self):
        """Показывает экран игры."""
        if not self.current_room_id:
            self.show_main_menu()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'spy_room_id': None})
            self.show_main_menu()
            return

        # Проверяем, что игра запущена
        if room_data["status"] != "playing":
            self.show_waiting_room()
            return

        self.game_container.clear()

        # Запускаем таймер обновления
        self._cancel_timers()
        self.update_timer = ui.timer(1.0, lambda: self.update_game_screen())

        # Получаем данные текущего игрока
        current_user_id = app.storage.user.get('user_id')
        current_player_index = next((i for i, p in enumerate(room_data["players"]) if p["id"] == current_user_id), -1)
        is_spy = current_player_index == room_data["game_data"]["spy_index"]
        is_host = next((p for p in room_data["players"] if p["id"] == current_user_id and p.get("is_host", False)),
                       None) is not None

        # Получаем игровые данные
        category = room_data["game_data"]["category"]
        location = room_data["game_data"]["location"]

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                self.components.create_header('Игра "Шпион"')

                # Показываем категорию и локацию игрока
                self.components.create_location_display(category, location, is_spy)

                # Показываем индикатор текущего раунда
                current_round = room_data["game_data"].get("round", 1)
                self.components.create_round_indicator(current_round)

                # Информация для обсуждения в реальном времени
                if current_round == 1:
                    with ui.card().classes('w-full p-4 mb-4 bg-yellow-50 dark:bg-yellow-900 rounded-lg'):
                        ui.label('💬 Живое общение').classes('text-lg font-bold mb-2 text-yellow-800 dark:text-yellow-200')
                        ui.label('Сейчас происходит обсуждение в реальном времени (голосом/дискорд/живое общение).').classes('text-yellow-700 dark:text-yellow-300 mb-2')
                        ui.label('Задавайте вопросы друг другу, чтобы найти Шпиона!').classes('text-yellow-700 dark:text-yellow-300')

                # Кнопки для управления игрой (только для хоста)
                if is_host and current_round == 1:
                    with ui.row().classes('w-full gap-2 mb-4'):
                        def start_voting():
                            success = self.room_service.start_voting_round(self.current_room_id)
                            if success:
                                ui.notify('Переход к этапу голосования', type='positive')
                                self.show_game_screen()
                            else:
                                ui.notify('Ошибка при переходе к голосованию', type='negative')

                        ui.button('Перейти к голосованию', icon='how_to_vote', on_click=start_voting).classes(
                            'bg-red-600 hover:bg-red-700 text-white')

            # Список игроков с голосованием
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                ui.label('Игроки:').classes('text-lg font-bold mb-3 text-gray-800 dark:text-gray-200')

                # Создаем таблицу игроков с учетом текущего раунда
                self.components.create_player_table(
                    players=room_data["players"],
                    current_round=current_round,
                    current_user_id=current_user_id,
                    vote_handler=self.vote_for_player,
                    votes=room_data["game_data"].get("votes", {}),
                    spy_index=room_data["game_data"].get("spy_index") if current_round == 3 else None
                )

            # Отображаем результаты голосования в раунде 3
            if current_round == 3:
                vote_results = self.room_service.get_vote_results(self.current_room_id)

                with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                    ui.label('Результаты голосования').classes(
                        'text-xl font-bold mb-3 text-center text-red-600 dark:text-red-400')

                    if not vote_results:
                        ui.label('Ошибка получения результатов').classes('text-center p-4 text-red-500')
                    else:
                        # Получаем данные о Шпионе
                        spy_index = room_data["game_data"]["spy_index"]
                        spy_player = room_data["players"][spy_index] if 0 <= spy_index < len(
                            room_data["players"]) else None
                        spy_name = spy_player["name"] if spy_player else "Unknown"

                        # Показываем результаты голосования
                        if vote_results["spy_caught"]:
                            with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg'):
                                ui.label(f'Игрок {spy_name} получил больше всего голосов!').classes(
                                    'text-center font-bold mb-2 text-red-700 dark:text-red-300')
                                ui.label('Шпион пойман! Теперь он должен попытаться угадать локацию.').classes(
                                    'text-center text-red-800 dark:text-red-200')

                            # Если текущий игрок - Шпион, показываем ему форму для угадывания
                            if is_spy:
                                with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg'):
                                    ui.label('Вас поймали, но у вас есть шанс на победу!').classes(
                                        'text-center font-bold mb-2 text-red-700 dark:text-red-300')
                                    ui.label('Попытайтесь угадать локацию:').classes(
                                        'text-center mb-3 text-red-800 dark:text-red-200')

                                    with ui.row().classes('w-full items-center justify-center mb-2'):
                                        # Получаем локации только из данной категории
                                        category = room_data["game_data"]["category"]
                                        location_options = self.data_service.get_locations_for_category(category)
                                        guess_select = ui.select(
                                            options=location_options,
                                            label='Выберите локацию'
                                        ).classes('w-full max-w-md')
                                        guess_select.props('outlined rounded dense')

                                        def check_guess():
                                            guess = guess_select.value
                                            if not guess:
                                                ui.notify('Выберите локацию', type='warning')
                                                return

                                            result = self.room_service.check_spy_guess(
                                                self.current_room_id,
                                                current_user_id,
                                                guess
                                            )

                                            if result:
                                                if result["is_correct"]:
                                                    ui.notify('Вы правильно угадали локацию! Вы победили!',
                                                              type='positive')
                                                else:
                                                    ui.notify(f'Неверно! Локация: {result["actual_location"]}',
                                                              type='negative')

                                                self.show_game_over(result["is_correct"], result["actual_location"])

                                    ui.button('Отправить догадку', icon='send', on_click=check_guess).classes(
                                        'bg-red-600 hover:bg-red-700 text-white w-full max-w-md mx-auto mt-2')
                            else:
                                ui.label('Ожидайте, пока Шпион попытается угадать локацию...').classes(
                                    'text-center mt-2 italic')
                        else:
                            # Шпион не пойман - он побеждает
                            self.components.create_game_result_card(False, spy_name, location)

                            # Кнопка показа финальных результатов
                            ui.button('Показать итоги игры', icon='check_circle',
                                      on_click=lambda: self.show_game_over(True, location)).classes(
                                'w-full mt-4 bg-red-600 hover:bg-red-700 text-white')

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
            app.storage.user.update({'spy_room_id': None})
            self.show_main_menu()
            return

        # Если статус изменился или были обновления, обновляем экран
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)

            # Если игра завершена, показываем экран завершения
            if room_data["status"] == "finished":
                self.show_game_over(False, room_data["game_data"]["location"])
                return

            # В остальных случаях просто обновляем экран игры
            self.show_game_screen()

    def vote_for_player(self, player_id):
        """Голосует за игрока как за Шпиона."""
        if not self.current_room_id:
            return

        success = self.room_service.add_vote(
            self.current_room_id,
            app.storage.user.get('user_id'),
            player_id
        )

        if success:
            ui.notify('Голос учтен', type='positive')
            self.show_game_screen()
        else:
            ui.notify('Ошибка при голосовании', type='negative')

    def show_game_over(self, spy_won, actual_location):
        """Показывает экран завершения игры."""
        self._cancel_timers()
        self.game_container.clear()

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 text-center'):
                ui.label('Игра завершена!').classes('text-2xl font-bold mb-4 text-red-600 dark:text-red-400')

                if spy_won:
                    with ui.card().classes('bg-red-100 dark:bg-red-900 p-4 mb-4 rounded-lg'):
                        ui.label('Шпион победил!').classes(
                            'text-xl text-red-700 dark:text-red-300 font-bold mb-2')
                        ui.label(f'Локация была: {actual_location}').classes(
                            'text-lg text-red-800 dark:text-red-200')
                else:
                    with ui.card().classes('bg-blue-100 dark:bg-blue-900 p-4 mb-4 rounded-lg'):
                        ui.label('Обычные игроки победили!').classes(
                            'text-xl text-blue-700 dark:text-blue-300 font-bold mb-2')
                        ui.label(f'Локация была: {actual_location}').classes(
                            'text-lg text-blue-800 dark:text-blue-200')

                with ui.row().classes('w-full justify-center gap-4 mt-6'):
                    ui.button('Играть снова', icon='replay', on_click=self.reset_game).classes(
                        'bg-red-600 hover:bg-red-700 text-white')
                    ui.button('Выйти в меню', icon='home', on_click=self.return_to_menu).classes(
                        'bg-gray-500 hover:bg-gray-600 text-white')

    def finish_game(self):
        """Завершает текущую игру."""
        if not self.current_room_id:
            return

        success = self.room_service.finish_game(self.current_room_id)
        if success:
            ui.notify('Игра завершена', type='positive')
            room_data = self.room_service.get_room(self.current_room_id)
            location = room_data["game_data"]["location"] if room_data else "Неизвестная локация"
            self.show_game_over(False, location)
        else:
            ui.notify('Ошибка при завершении игры', type='negative')

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
        # Удаляем ID комнаты из хранилища пользователя
        app.storage.user.update({'spy_room_id': None})
        self.show_main_menu()