from nicegui import ui, app
import time
from datetime import datetime

from src.minigame.best_pairs.best_pairs_data_service import BestPairsDataService
from src.minigame.best_pairs.best_pairs_room_service import BestPairsRoomService
from src.services.log.log_services import LogService
from src.minigame.best_pairs.best_pairs_components_ui import BestPairsComponents


class BestPairsGameUI:
    """
    Класс для управления интерфейсом игры Лучшие Пары.
    Игра на ассоциативное мышление с угадыванием пар.
    """

    def __init__(self):
        self.log_service = LogService()
        self.data_service = BestPairsDataService()
        self.room_service = BestPairsRoomService()
        self.components = BestPairsComponents()

        self.current_room_id = None
        self.player_name = ""
        self.player_id = None
        self.game_container = None
        self.last_update_time = 0
        self.update_timer = None
        self.rooms_update_timer = None

        # Для хранения выбранных пар
        self.selected_pairings = {}

        # Контейнеры для обновляемых элементов - инициализируем как None
        self.players_table_container = None
        self.rooms_list_container = None
        self.guessing_status_container = None
        self.last_round = None
        self.status_container = None
        self.pairs_container = None
        self.button_container = None

    def _ensure_player_id(self):
        """Гарантирует, что у нас есть правильный ID игрока"""
        if not self.player_id:
            self.player_id = app.storage.user.get('user_id')
        return self.player_id

    def show_main_menu(self, container=None):
        """Показывает главное меню игры."""
        # Восстанавливаем сохраненный ID комнаты при перезагрузке
        saved_room_id = app.storage.user.get('best_pairs_room_id')
        if saved_room_id and not self.current_room_id:
            self.current_room_id = saved_room_id
            # Проверяем существование комнаты
            if self.room_service.room_exists(saved_room_id):
                # Восстанавливаем участие в комнате
                self.player_name = app.storage.user.get('username', '')
                self._ensure_player_id()
                success = self.room_service.add_player(
                    saved_room_id,
                    self.player_id,
                    self.player_name
                )
                if success:
                    # Проверяем состояние игры
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
        self._ensure_player_id()

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Лучшие Пары"',
                    'Игра на ассоциативное мышление: угадай, как ведущий сочетал прилагательные с существительными!',
                    'psychology'
                )

                # Правила игры в отдельной карточке
                with ui.card().classes('w-full p-4 mb-4 bg-purple-50 dark:bg-purple-900 rounded-lg'):
                    with ui.expansion('Правила игры', icon='help_outline').classes('w-full'):
                        ui.markdown("""
                    ### Правила игры "Лучшие Пары":

                    1. **Участники**: 2-8 игроков, каждый по очереди становится ведущим
                    2. **Карточки**: Система случайно выбирает 5 существительных и 5 прилагательных

                    **Процесс раунда:**
                    1. **Ведущий**:
                       - Видит 5 открытых существительных
                       - Получает 5 прилагательных (скрыты от других)
                       - Мысленно сочетает каждое прилагательное с подходящим существительным
                       - Раскладывает прилагательные рубашкой вверх

                    2. **Остальные игроки**:
                       - Видят те же существительные
                       - Получают копии тех же прилагательных
                       - Думают, как ведущий мог их разложить
                       - Записывают свои предположения

                    3. **Подсчет очков**:
                       - За каждое совпадение: 2 очка
                       - Бонус ведущему: +1 очко за каждого игрока, угадавшего ≥3 пары
                    """)

                # Кнопки действий
                with ui.row().classes('w-full justify-center gap-4 mb-4'):
                    ui.button('Создать комнату',
                              icon='add_circle',
                              on_click=self.create_room).classes('bg-purple-600 hover:bg-purple-700 text-white')

                    ui.button('Присоединиться',
                              icon='group_add',
                              on_click=self.show_join_dialog).classes('bg-green-600 hover:bg-green-700 text-white')

                # Список доступных комнат
                self.show_available_rooms()

    def show_available_rooms(self):
        """Creates and displays a list of available rooms using consistent styling"""
        with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
            ui.label('Доступные комнаты:').classes('text-xl font-bold mb-4 text-indigo-600 dark:text-indigo-400')
            rooms_list_container = ui.element('div').classes('w-full')

            # Function to update the rooms list
            def update_rooms_list():
                rooms_list_container.clear()
                with rooms_list_container:
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
                        table.on('join', lambda e: self.join_room(e.args))
                    else:
                        with ui.card().classes('w-full p-4 bg-gray-200 dark:bg-gray-700 rounded-lg'):
                            with ui.row().classes('items-center justify-center text-gray-500 dark:text-gray-400'):
                                ui.icon('info').classes('text-xl mr-2')
                                ui.label('Нет доступных комнат').classes('text-center')

            # Update the rooms list
            update_rooms_list()
            self._cancel_timers()
            # Start timer to update the rooms list (every 5 seconds)
            self.rooms_update_timer = ui.timer(3.0, update_rooms_list)

    def create_room(self):
        """Создает новую комнату"""
        # Отменяем таймеры перед созданием комнаты
        self._cancel_timers()

        self._ensure_player_id()
        room_id = self.room_service.create_room(self.player_id, self.player_name)

        if room_id:
            self.current_room_id = room_id
            app.storage.user.update({'best_pairs_room_id': room_id})
            ui.notify(f'Комната {room_id} создана!', type='positive')
            # Добавляем небольшую задержку перед показом комнаты ожидания
            ui.timer(0.1, lambda: self.show_waiting_room(), once=True)
        else:
            ui.notify('Ошибка создания комнаты', type='negative')

    def show_join_dialog(self):
        """Показывает диалог для ввода ID комнаты"""
        # Отменяем таймеры на время диалога
        self._cancel_timers()

        dialog = ui.dialog()

        with dialog, ui.card().classes('p-4'):
            ui.label('Введите ID комнаты').classes('text-lg font-bold mb-2')
            room_input = ui.input('ID комнаты', placeholder='pairs_1234').classes('w-full mb-4')

            def join_and_close():
                if self.join_room(room_input.value):
                    dialog.close()

            def cancel_and_restore():
                dialog.close()
                # Восстанавливаем таймер обновления списка комнат
                self.show_available_rooms()

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Отмена', on_click=cancel_and_restore).classes('bg-gray-300')
                ui.button('Присоединиться', on_click=join_and_close).classes('bg-purple-600 text-white')

        dialog.open()

    def join_room(self, room_id):
        """Присоединяется к существующей комнате"""
        if not room_id:
            ui.notify('Введите ID комнаты', type='warning')
            return False

        if not self.room_service.room_exists(room_id):
            ui.notify('Комната не найдена', type='negative')
            return False

        self._ensure_player_id()
        success = self.room_service.add_player(room_id, self.player_id, self.player_name)

        if success:
            self.current_room_id = room_id
            app.storage.user.update({'best_pairs_room_id': room_id})
            ui.notify('Вы присоединились к комнате!', type='positive')
            self.show_waiting_room()
            return True
        else:
            ui.notify('Ошибка присоединения к комнате', type='negative')
            return False

    def show_waiting_room(self):
        """Показывает комнату ожидания"""
        if not self.current_room_id:
            self.show_main_menu()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'best_pairs_room_id': None})
            self.show_main_menu()
            return

        # ОЧИЩАЕМ КОНТЕЙНЕРЫ ПРИ СМЕНЕ ЭКРАНА
        self._clear_ui_containers()

        self.game_container.clear()

        # Запускаем таймер обновления
        self._cancel_timers()
        self.update_timer = ui.timer(1.0, lambda: self.update_waiting_room())

        # Получаем данные текущего игрока
        self._ensure_player_id()
        current_player = next((p for p in room_data["players"] if p["id"] == self.player_id), None)
        is_host = current_player and current_player.get("is_host", False)

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Лучшие Пары"',
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
                        ).classes('bg-blue-600 hover:bg-blue-700 text-white')

                    # Список игроков
                    ui.label('Игроки в комнате:').classes('text-lg font-bold mb-2')
                    # Создаем контейнер для таблицы игроков, который можно обновлять отдельно
                    self.players_table_container = ui.element('div').classes('w-full')
                    with self.players_table_container:
                        self.components.create_player_table(room_data["players"], self.player_id, is_waiting=True)

                    # Кнопки управления
                    with ui.row().classes('w-full justify-center gap-4 mt-4'):
                        if is_host:
                            ui.button(
                                'Начать игру',
                                icon='play_arrow',
                                on_click=self.start_game
                            ).classes(
                                'bg-green-600 hover:bg-green-700 text-white'
                            )

                        # Кнопка готовности для всех игроков
                        is_ready = current_player.get("is_ready", False) if current_player else False
                        ui.button(
                            'Не готов' if is_ready else 'Готов',
                            icon='check_circle' if is_ready else 'radio_button_unchecked',
                            on_click=lambda: self.toggle_ready()
                        ).classes(
                            'bg-green-600 hover:bg-green-700 text-white' if is_ready
                            else 'bg-amber-600 hover:bg-amber-700 text-white'
                        )

                        ui.button(
                            'Покинуть комнату',
                            icon='exit_to_app',
                            on_click=self.leave_room
                        ).classes('bg-red-600 hover:bg-red-700 text-white')

    def update_waiting_room(self):
        """Обновляет комнату ожидания"""
        room_data = self.room_service.get_room(self.current_room_id)

        if not room_data:
            self._cancel_timers()
            self.current_room_id = None
            app.storage.user.update({'best_pairs_room_id': None})
            self.show_main_menu()
            return

        # Если игра началась, переходим к игровому экрану
        if room_data["status"] == "playing":
            self._cancel_timers()
            self.show_game_screen()
            return

        # НЕ перерисовываем весь интерфейс, только обновляем таблицу игроков
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)

            # Обновляем только таблицу игроков, если есть контейнер И он не None
            if (hasattr(self, 'players_table_container') and
                    self.players_table_container is not None):  # ← ДОБАВЛЕНА ПРОВЕРКА НА None

                try:
                    self.players_table_container.clear()
                    with self.players_table_container:
                        self._ensure_player_id()
                        self.components.create_player_table(room_data["players"], self.player_id, is_waiting=True)
                except Exception as e:
                    # Если контейнер недоступен, просто игнорируем обновление
                    # Интерфейс будет обновлен при следующем полном перерисовывании
                    pass

    def toggle_ready(self):
        """Переключает статус готовности игрока"""
        if not self.current_room_id:
            return

        self._ensure_player_id()

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            return

        current_player = next((p for p in room_data["players"] if p["id"] == self.player_id), None)

        if not current_player:
            return

        new_ready_status = not current_player.get("is_ready", False)
        success = self.room_service.set_player_ready(self.current_room_id, self.player_id, new_ready_status)

        if success:
            # Обновляем только таблицу игроков
            ui.notify(f'Вы {"готовы" if new_ready_status else "не готовы"} к игре!', type='positive')
            self.show_waiting_room()
            self.last_update_time = time.time()

    def start_game(self):
        """Начинает игру (только для хоста)"""

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'best_pairs_room_id': None})
            self.show_main_menu()
            return

        all_ready = False
        if (len(room_data['players']) > 1):
            all_ready = self.room_service.all_players_ready(self.current_room_id)

        if not all_ready:
            ui.notify('Ошибка не все готовы', type='warning')
            return
        # Получаем случайные карточки
        cards = self.data_service.get_random_cards(count=5)

        # Начинаем раунд
        success = self.room_service.start_round(
            self.current_room_id,
            cards["nouns"],
            cards["adjectives"]
        )

        if success:
            ui.notify('Игра началась!', type='positive')
            self.show_game_screen()
        else:
            ui.notify('Ошибка начала игры', type='negative')

    def show_game_screen(self):
        """Показывает экран игры"""
        if not self.current_room_id:
            self.show_main_menu()
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            ui.notify('Комната не найдена', type='negative')
            self.current_room_id = None
            app.storage.user.update({'best_pairs_room_id': None})
            self.show_main_menu()
            return

        # Проверяем, что игра запущена
        if room_data["status"] != "playing":
            self.show_waiting_room()
            return

        # ОЧИЩАЕМ КОНТЕЙНЕРЫ ПРИ СМЕНЕ ЭКРАНА
        self._clear_ui_containers()

        self.game_container.clear()

        # Запускаем таймер обновления
        self._cancel_timers()
        self.last_round = room_data["game_data"]["round"]  # Сохраняем текущий раунд
        self.update_timer = ui.timer(1.0, lambda: self.update_game_screen())

        # Получаем данные текущего игрока
        self._ensure_player_id()
        current_player = next((p for p in room_data["players"] if p["id"] == self.player_id), None)
        is_host_of_round = self.player_id == room_data["game_data"]["current_round_host"]

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-gray-100 dark:bg-gray-800 mb-4'):
                self.components.create_header('Игра "Лучшие Пары"')

                # Показываем текущий этап
                current_round = room_data["game_data"]["round"]
                self.components.create_round_indicator(current_round)

                # В зависимости от этапа показываем разный интерфейс
                if current_round == 1:  # Ведущий раскладывает пары
                    if is_host_of_round:
                        self.show_host_pairing_interface(room_data)
                    else:
                        self.show_waiting_for_host(room_data)

                elif current_round == 2:  # Игроки угадывают
                    if is_host_of_round:
                        self.show_host_waiting_interface(room_data)
                    else:
                        self.show_player_guessing_interface(room_data)

                elif current_round == 3:  # Результаты
                    self.show_results_interface(room_data)

                elif current_round == 4:  # Конец раунда
                    self.show_round_end_interface(room_data)

    def update_pairing(self, noun_idx, adjective):
        """Обновляет выбранную пару с проверкой уникальности и поддержкой сброса"""
        if adjective and adjective != "":  # Если выбрано что-то кроме пустого значения
            # Проверяем, не использован ли уже этот прилагательный
            for existing_noun_idx, existing_adj in list(self.selected_pairings.items()):
                if existing_adj == adjective and existing_noun_idx != noun_idx:
                    # Удаляем предыдущее назначение этого прилагательного
                    del self.selected_pairings[existing_noun_idx]
                    ui.notify(f'Прилагательное "{adjective}" перенесено с предыдущей позиции', type='info')
                    break

            self.selected_pairings[noun_idx] = adjective
        else:  # Если выбрано пустое значение или None - сбрасываем
            if noun_idx in self.selected_pairings:
                removed_adj = self.selected_pairings[noun_idx]
                del self.selected_pairings[noun_idx]
                ui.notify(f'Прилагательное "{removed_adj}" удалено', type='info')

    def validate_pairings(self, adjectives):
        """Проверяет корректность выбранных пар"""
        # Проверяем, что выбраны все 5 пар
        if len(self.selected_pairings) != 5:
            return False, f'Выбрано {len(self.selected_pairings)}/5 пар'

        # Проверяем, что все прилагательные из допустимого списка
        for adj in self.selected_pairings.values():
            if adj not in adjectives:
                return False, f'Прилагательное "{adj}" не найдено в списке!'

        # Проверяем уникальность прилагательных
        used_adjectives = list(self.selected_pairings.values())
        if len(used_adjectives) != len(set(used_adjectives)):
            # Находим дублирующиеся прилагательные
            duplicates = []
            for adj in used_adjectives:
                if used_adjectives.count(adj) > 1 and adj not in duplicates:
                    duplicates.append(adj)

            return False, f'Прилагательные используются повторно: {", ".join(duplicates)}'

        return True, 'Все пары корректны'

    def create_pairing_options(self, adjectives, current_selection=None):
        """Создает список опций для выпадающего списка с пустым вариантом"""
        options = [""]  # Пустой вариант для сброса

        # Добавляем текущий выбор, если он есть
        if current_selection and current_selection not in options:
            options.append(current_selection)

        # Добавляем доступные прилагательные
        used_adjectives = set(self.selected_pairings.values())
        for adj in adjectives:
            if adj not in used_adjectives and adj not in options:
                options.append(adj)

        return options

    def reset_all_pairings(self):
        """Сбрасывает все выбранные пары"""
        if self.selected_pairings:
            count = len(self.selected_pairings)
            self.selected_pairings = {}
            ui.notify(f'Сброшено {count} пар', type='info')
            return True
        else:
            ui.notify('Нет пар для сброса', type='warning')
            return False

    def show_unified_pairing_interface(self, room_data, is_host=True):
        """Унифицированный интерфейс для выбора пар (хост и игроки)"""
        nouns = room_data["game_data"]["nouns"]
        adjectives = room_data["game_data"]["adjectives"]

        # Разные заголовки для хоста и игроков
        if is_host:
            title = 'Составьте пары: Существительное + Прилагательное'
            subtitle = 'Разложите прилагательные к подходящим существительным'
            button_text = 'Подтвердить расклад'
            button_icon = 'check'
            submit_function = self.submit_host_pairings
        else:
            title = 'Угадайте, как ведущий разложил пары!'
            subtitle = 'Попробуйте понять логику ведущего'
            button_text = 'Отправить догадки'
            button_icon = 'send'
            submit_function = self.submit_player_guesses

        ui.label(title).classes('text-xl font-bold text-purple-700 dark:text-purple-300 mb-2')
        ui.label(subtitle).classes('text-gray-600 dark:text-gray-300 mb-2')
        ui.label('Каждый прилагательный можно использовать только один раз!').classes(
            'text-orange-600 dark:text-orange-300 mb-4 font-medium')

        # Инициализируем выбранные пары
        if not self.selected_pairings:
            self.selected_pairings = {}

        # Контейнеры для динамического обновления
        self.status_container = ui.element('div').classes('w-full mb-4')
        self.pairs_container = ui.element('div').classes('w-full')
        self.controls_container = ui.element('div').classes('w-full mt-4')

        # Функция для обновления интерфейса
        def refresh_interface():
            self.update_status_display(adjectives)
            self.update_pairs_display(nouns, adjectives, submit_function)
            self.update_controls(adjectives, button_text, button_icon, submit_function)

        # Первоначальное отображение
        refresh_interface()

    def update_status_display(self, adjectives):
        """Обновляет отображение статуса использования прилагательных"""
        self.status_container.clear()
        with self.status_container:
            used_adjectives = set(self.selected_pairings.values())
            available_adjectives = [adj for adj in adjectives if adj not in used_adjectives]

            # Прогресс-бар
            progress = len(used_adjectives) / 5 * 100
            with ui.row().classes('w-full items-center gap-4 mb-3'):
                ui.label(f'Прогресс: {len(used_adjectives)}/5').classes('text-sm font-medium min-w-[100px]')
                with ui.element('div').classes('flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-3'):
                    ui.element('div').classes(f'bg-purple-600 h-3 rounded-full transition-all duration-300').style(
                        f'width: {progress}%')
                ui.label(f'{progress:.0f}%').classes('text-sm font-medium min-w-[40px]')

            # Статус по цветам в две колонки
            with ui.row().classes('w-full gap-4 mb-2'):
                # Использованные прилагательные
                with ui.column().classes('flex-1'):
                    ui.label('✅ Использованные:').classes('text-sm font-bold text-green-600')
                    if used_adjectives:
                        ui.label(', '.join(sorted(used_adjectives))).classes(
                            'text-xs text-green-700 dark:text-green-300 break-words')
                    else:
                        ui.label('Пока нет').classes('text-xs text-gray-500 italic')

                # Доступные прилагательные
                with ui.column().classes('flex-1'):
                    ui.label('⭕ Доступные:').classes('text-sm font-bold text-blue-600')
                    if available_adjectives:
                        # Показываем только первые 8, если их много
                        display_available = available_adjectives[:8]
                        remaining = len(available_adjectives) - 8
                        display_text = ', '.join(display_available)
                        if remaining > 0:
                            display_text += f' ... (+{remaining})'
                        ui.label(display_text).classes('text-xs text-blue-700 dark:text-blue-300 break-words')
                    else:
                        ui.label('Все использованы').classes('text-xs text-gray-500 italic')

    def update_pairs_display(self, nouns, adjectives, submit_function):
        """Обновляет отображение пар с выпадающими списками"""
        self.pairs_container.clear()
        with self.pairs_container:
            with ui.column().classes('w-full gap-3'):
                for idx, noun in enumerate(nouns):
                    with ui.card().classes('p-4 shadow-md hover:shadow-lg transition-shadow'):
                        with ui.row().classes('w-full items-center gap-4'):
                            # Номер и существительное
                            ui.label(f"{idx + 1}. {noun}").classes(
                                'text-lg font-bold min-w-[150px] text-gray-800 dark:text-gray-200')

                            # Стрелка
                            ui.icon('arrow_forward').classes('text-purple-500 text-xl')

                            # Выпадающий список с пустым вариантом
                            current_adj = self.selected_pairings.get(idx, None)
                            options = self.create_pairing_options(adjectives, current_adj)

                            adj_select = ui.select(
                                options,
                                label='Выберите прилагательное',
                                value=current_adj if current_adj else "",
                                on_change=lambda e, i=idx: self.handle_pairing_change(i, e.value, nouns, adjectives,
                                                                                      submit_function)
                            ).classes('flex-1')

                            # Настраиваем placeholder для пустого варианта
                            adj_select.props('clearable outlined dense')

                            # Индикатор статуса
                            if current_adj:
                                ui.icon('check_circle', color='green').classes('text-green-500 text-xl')
                            else:
                                ui.icon('radio_button_unchecked', color='gray').classes('text-gray-400 text-xl')

    def handle_pairing_change(self, noun_idx, adjective, nouns, adjectives, submit_function):
        """Обрабатывает изменение пары с обновлением интерфейса"""
        # Обновляем пару
        self.update_pairing(noun_idx, adjective)

        # Обновляем интерфейс
        self.refresh_unified_interface(nouns, adjectives, submit_function)

    def refresh_unified_interface(self, nouns, adjectives, submit_function):
        """Обновляет весь унифицированный интерфейс"""
        self.update_status_display(adjectives)
        self.update_pairs_display(nouns, adjectives, submit_function)

        # Определяем тип кнопки по функции
        if submit_function == self.submit_host_pairings:
            button_text = 'Подтвердить расклад'
            button_icon = 'check'
        else:
            button_text = 'Отправить догадки'
            button_icon = 'send'

        self.update_controls(adjectives, button_text, button_icon, submit_function)

    def update_controls(self, adjectives, button_text, button_icon, submit_function):
        """Обновляет элементы управления (кнопки)"""
        self.controls_container.clear()
        with self.controls_container:
            is_complete = len(self.selected_pairings) == 5
            is_valid, error_message = self.validate_pairings(adjectives) if is_complete else (False,
                                                                                              f'Выбрано {len(self.selected_pairings)}/5 пар')

            # Основные кнопки
            with ui.row().classes('w-full gap-4 justify-center'):
                # Кнопка сброса всех пар
                reset_button = ui.button(
                    '🗑️ Сбросить все',
                    icon='clear_all',
                    on_click=lambda: self.handle_reset_all(adjectives, submit_function)
                ).classes('bg-red-500 hover:bg-red-600 text-white')

                if not self.selected_pairings:
                    reset_button.disable()

                # Основная кнопка отправки
                if is_valid:
                    submit_button_class = 'bg-green-600 hover:bg-green-700 text-white px-8'
                    submit_button_text = f'✅ {button_text}'
                    enabled = True
                elif is_complete:
                    submit_button_class = 'bg-red-600 hover:bg-red-700 text-white px-8'
                    submit_button_text = f'❌ Исправить ошибки'
                    enabled = False
                else:
                    submit_button_class = 'bg-gray-400 text-gray-600 cursor-not-allowed px-8'
                    submit_button_text = f'⏳ {error_message}'
                    enabled = False

                submit_button = ui.button(
                    submit_button_text,
                    icon=button_icon if is_valid else 'warning',
                    on_click=lambda: submit_function(adjectives) if enabled else None
                ).classes(submit_button_class)

                if not enabled:
                    submit_button.disable()

            # Сообщение об ошибке
            if not is_valid and is_complete:
                ui.label(f'⚠️ {error_message}').classes('text-red-600 text-sm mt-2 text-center font-medium')

    def handle_reset_all(self, adjectives, submit_function):
        """Обработчик сброса всех пар"""
        if self.reset_all_pairings():
            # Получаем nouns из контекста (нужно передать или сохранить)
            # Для этого добавим их как атрибут класса
            if hasattr(self, 'current_nouns'):
                self.refresh_unified_interface(self.current_nouns, adjectives, submit_function)

    # ОБНОВЛЕННЫЕ ОСНОВНЫЕ ФУНКЦИИ ИНТЕРФЕЙСА

    def show_host_pairing_interface(self, room_data):
        """Интерфейс для ведущего - составление пар"""
        # Сохраняем существительные для использования в других функциях
        self.current_nouns = room_data["game_data"]["nouns"]
        self.show_unified_pairing_interface(room_data, is_host=True)

    def show_player_guessing_interface(self, room_data):
        """Интерфейс для игроков - угадывание пар"""
        nouns = room_data["game_data"]["nouns"]
        adjectives = room_data["game_data"]["adjectives"]

        # Проверяем, не отправил ли игрок уже свои догадки
        self._ensure_player_id()
        already_guessed = self.player_id in room_data["game_data"]["player_guesses"]

        if already_guessed:
            self.components.create_status_indicator('Вы уже отправили свои догадки', 'success')
            ui.label('Ожидаем остальных игроков...').classes('text-center mt-4')
            return

        # Сохраняем существительные и используем унифицированный интерфейс
        self.current_nouns = nouns
        self.show_unified_pairing_interface(room_data, is_host=False)

    # ОБНОВЛЕННЫЕ ФУНКЦИИ ОТПРАВКИ

    def submit_host_pairings(self, adjectives):
        """Отправляет выбранные пары с проверкой уникальности"""
        # Валидируем пары
        is_valid, error_message = self.validate_pairings(adjectives)

        if not is_valid:
            ui.notify(error_message, type='warning')
            return

        self._ensure_player_id()
        success = self.room_service.set_host_pairings(
            self.current_room_id,
            self.player_id,
            self.selected_pairings
        )

        if success:
            ui.notify('Пары разложены!', type='positive')
            self.selected_pairings = {}
        else:
            ui.notify('Ошибка сохранения пар', type='negative')

    def submit_player_guesses(self, adjectives):
        """Отправляет догадки игрока с проверкой уникальности"""
        # Валидируем догадки
        is_valid, error_message = self.validate_pairings(adjectives)

        if not is_valid:
            ui.notify(error_message, type='warning')
            return

        self._ensure_player_id()
        success = self.room_service.submit_player_guess(
            self.current_room_id,
            self.player_id,
            self.selected_pairings
        )

        if success:
            ui.notify('Догадки отправлены!', type='positive')
            self.selected_pairings = {}
        else:
            ui.notify('Ошибка отправки догадок', type='negative')

    def show_waiting_for_host(self, room_data):
        """Интерфейс ожидания для игроков пока ведущий раскладывает"""
        host_id = room_data["game_data"]["current_round_host"]
        host = next((p for p in room_data["players"] if p["id"] == host_id), None)
        host_name = host["name"] if host else "Ведущий"

        self.components.create_status_indicator(f'{host_name} раскладывает пары...', 'waiting')

        # Показываем существительные
        nouns = room_data["game_data"]["nouns"]
        ui.label('Существительные в этом раунде:').classes('text-lg font-bold mb-2 mt-4')

        with ui.column().classes('w-full gap-2'):
            for idx, noun in enumerate(nouns):
                with ui.row().classes('w-full items-center p-3 bg-gray-100 dark:bg-gray-800 rounded'):
                    ui.label(f"{idx + 1}. {noun}").classes('text-lg font-medium')

    def show_host_waiting_interface(self, room_data):
        """Интерфейс ожидания для ведущего пока игроки угадывают"""
        self.components.create_status_indicator('Игроки делают свои предположения...', 'waiting')

        # Показываем прогресс
        players_count = len(room_data["players"]) - 1  # Минус ведущий
        guesses_count = len(room_data["game_data"]["player_guesses"])

        # Создаем контейнер для обновляемого статуса
        self.guessing_status_container = ui.element('div').classes('w-full mt-4')
        with self.guessing_status_container:
            ui.label(f'Ответили: {guesses_count}/{players_count}').classes('text-lg text-center')

        # Показываем, как ведущий разложил пары
        ui.label('Ваш расклад:').classes('text-lg font-bold mb-2 mt-4')

        nouns = room_data["game_data"]["nouns"]
        adjectives = room_data["game_data"]["adjectives"]
        pairings = room_data["game_data"]["host_pairings"]

        with ui.column().classes('w-full gap-2'):
            for noun_idx_str, adj in pairings.items():
                noun = nouns[int(noun_idx_str)]
                with ui.row().classes('w-full items-center gap-4 p-2 bg-purple-100 dark:bg-purple-900 rounded'):
                    ui.label(f"{int(noun_idx_str) + 1}. {noun}").classes('text-lg font-medium min-w-[150px]')
                    ui.icon('arrow_forward').classes('text-purple-500')
                    ui.label(adj).classes('text-lg font-bold text-purple-700 dark:text-purple-300')

    def show_results_interface(self, room_data):
        """Показывает результаты раунда"""
        nouns = room_data["game_data"]["nouns"]
        host_pairings = room_data["game_data"]["host_pairings"]
        player_guesses = room_data["game_data"]["player_guesses"]

        # Применяем очки
        self.room_service.apply_round_scores(self.current_room_id)

        # Показываем правильные пары
        ui.label('Результаты раунда').classes('text-xl font-bold mb-4 text-center')

        # Создаем словарь правильных пар с именами существительных
        correct_pairings = {}
        for noun_idx_str, adj in host_pairings.items():
            noun = nouns[int(noun_idx_str)]
            correct_pairings[noun] = adj

        # Показываем результаты для текущего игрока
        self._ensure_player_id()
        if self.player_id in player_guesses:
            # Создаем словарь догадок игрока с именами существительных
            my_guesses = {}
            for noun_idx_str, adj in player_guesses[self.player_id].items():
                noun = nouns[int(noun_idx_str)]
                my_guesses[noun] = adj

            # Подсчитываем очки
            correct_count = 0
            for noun_idx_str, adj in player_guesses[self.player_id].items():
                if host_pairings.get(noun_idx_str) == adj:
                    correct_count += 1

            score = correct_count

            self.components.create_result_card(correct_pairings, my_guesses, score)

        else:
            # Для ведущего показываем его бонусные очки
            host_bonus = 0
            for player_id, guesses in player_guesses.items():
                correct_count = 0
                for noun_idx, adj in guesses.items():
                    if host_pairings.get(str(noun_idx)) == adj:
                        correct_count += 1
                if correct_count >= 3:
                    host_bonus += 1

            with ui.card().classes('w-full p-6 bg-purple-100 dark:bg-purple-900 rounded-lg'):
                ui.label(f'Вы заработали {host_bonus} бонусных очков как ведущий!').classes(
                    'text-xl font-bold text-purple-700 dark:text-purple-300 text-center'
                )

                # Показываем свой расклад
                ui.label('Ваш расклад был:').classes('text-lg font-bold mb-2 mt-4')
                with ui.column().classes('w-full gap-2'):
                    for noun_idx_str, adj in host_pairings.items():
                        noun = nouns[int(noun_idx_str)]
                        with ui.row().classes('w-full items-center gap-4 p-2 bg-purple rounded'):
                            ui.label(f"{int(noun_idx_str) + 1}. {noun}").classes('text-lg font-medium min-w-[150px]')
                            ui.icon('arrow_forward').classes('text-purple-500')
                            ui.label(adj).classes('text-lg font-bold text-purple-700 dark:text-purple-300')

        # ДОБАВЛЯЕМ КНОПКУ ДЛЯ ПЕРЕХОДА К ОКОНЧАНИЮ РАУНДА
        with ui.row().classes('w-full justify-center mt-6'):
            ui.button(
                'Продолжить',
                icon='navigate_next',
                on_click=self.proceed_to_round_end
            ).classes('bg-purple-600 hover:bg-purple-700 text-white text-lg px-6 py-3')

    def proceed_to_round_end(self):
        """Переходит к экрану окончания раунда"""
        success = self.room_service.end_round(self.current_room_id)

        if success:
            ui.notify('Переход к результатам!', type='positive')
        else:
            ui.notify('Ошибка перехода', type='negative')
    def show_round_end_interface(self, room_data):
        """Показывает интерфейс конца раунда"""
        # Показываем общий счет
        scores = {}
        for player in room_data["players"]:
            scores[player["name"]] = player["score"]

        self.components.create_score_display(scores)

        # Информация о следующем раунде
        next_host_idx = (room_data["current_host_index"] + 1) % len(room_data["players"])
        next_host = room_data["players"][next_host_idx]

        ui.label(f'Следующий ведущий: {next_host["name"]}').classes(
            'text-lg text-center mt-4 text-purple-700 dark:text-purple-300'
        )

        # Кнопка для перехода к следующему раунду
        self._ensure_player_id()
        is_current_host = next(
            (p for p in room_data["players"] if p["id"] == self.player_id and p.get("is_host", False)),
            None) is not None

        if is_current_host:
            ui.button(
                'Следующий раунд',
                icon='navigate_next',
                on_click=self.next_round
            ).classes('bg-purple-600 hover:bg-purple-700 text-white mt-4')

    def next_round(self):
        """Переходит к следующему раунду"""
        success = self.room_service.next_round(self.current_room_id)

        if success:
            ui.notify('Переход к следующему раунду!', type='positive')
            self.show_waiting_room()
        else:
            ui.notify('Ошибка перехода к следующему раунду', type='negative')

    def update_game_screen(self):
        """Обновляет игровой экран"""
        room_data = self.room_service.get_room(self.current_room_id)

        if not room_data:
            self._cancel_timers()
            self.current_room_id = None
            app.storage.user.update({'best_pairs_room_id': None})
            self.show_main_menu()
            return

        # Если игра завершена, возвращаемся в комнату ожидания
        if room_data["status"] != "playing":
            self._cancel_timers()
            self.show_waiting_room()
            return

        # Проверяем изменение раунда или других важных данных
        current_round = room_data["game_data"]["round"]
        if hasattr(self, 'last_round') and self.last_round != current_round:
            # Раунд изменился - нужно перерисовать интерфейс
            self.last_round = current_round
            self.show_game_screen()
        elif room_data.get("last_activity", 0) > self.last_update_time:
            # Есть обновления, но раунд тот же - обновляем только необходимые части
            self.last_update_time = room_data.get("last_activity", 0)

            # В зависимости от раунда обновляем разные элементы
            if (current_round == 2 and
                    hasattr(self, 'guessing_status_container') and
                    self.guessing_status_container is not None):  # ← ДОБАВЛЕНА ПРОВЕРКА НА None

                try:
                    # Обновляем статус угадывания
                    players_count = len(room_data["players"]) - 1
                    guesses_count = len(room_data["game_data"]["player_guesses"])

                    self.guessing_status_container.clear()
                    with self.guessing_status_container:
                        ui.label(f'Ответили: {guesses_count}/{players_count}').classes('text-lg text-center')
                except Exception as e:
                    # Если контейнер недоступен, просто игнорируем обновление
                    # Интерфейс будет обновлен при следующем полном перерисовывании
                    pass


    def validate_current_selection(self, adjectives):
        """Быстрая валидация текущего выбора без требования полноты"""
        # Проверяем уникальность среди выбранных
        used_adjectives = list(self.selected_pairings.values())
        used_set = set(used_adjectives)

        if len(used_adjectives) != len(used_set):
            duplicates = [adj for adj in used_set if used_adjectives.count(adj) > 1]
            return False, f'Дублирующиеся прилагательные: {", ".join(duplicates)}'

        # Проверяем, что все из допустимого списка
        for adj in used_adjectives:
            if adj not in adjectives:
                return False, f'Недопустимое прилагательное: {adj}'

        return True, 'OK'

    def update_submit_button(self, adjectives):
        """Обновляет кнопку отправки с индикацией готовности"""
        self.button_container.clear()
        with self.button_container:
            is_complete = len(self.selected_pairings) == 5
            is_valid, error_message = self.validate_pairings(adjectives) if is_complete else (False,
                                                                                              'Не все пары выбраны')

            # Кнопка с соответствующим цветом и состоянием
            if is_valid:
                button_class = 'bg-green-600 hover:bg-green-700 text-white'
                button_text = '✅ Подтвердить расклад'
                enabled = True
            elif is_complete:
                button_class = 'bg-red-600 hover:bg-red-700 text-white'
                button_text = '❌ Исправить ошибки'
                enabled = False
            else:
                button_class = 'bg-gray-400 text-gray-600 cursor-not-allowed'
                button_text = f'⏳ Выбрано {len(self.selected_pairings)}/5 пар'
                enabled = False

            button = ui.button(
                button_text,
                icon='check' if is_valid else 'warning',
                on_click=lambda: self.submit_host_pairings(adjectives) if enabled else None
            ).classes(button_class)

            if not enabled:
                button.disable()

            # Показываем подсказку с ошибкой
            if not is_valid and error_message != 'Не все пары выбраны':
                ui.label(f'⚠️ {error_message}').classes('text-red-600 text-sm mt-2')

    def refresh_pairing_interface(self, nouns, adjectives):
        """Обновляет весь интерфейс после изменений"""
        self.update_status_display(adjectives)
        self.update_pairs_display(nouns, adjectives)
        self.update_submit_button(adjectives)



    def leave_room(self):
        """Покидает текущую комнату"""
        self._ensure_player_id()
        self.room_service.remove_player(self.current_room_id, self.player_id)

        self.current_room_id = None
        app.storage.user.update({'best_pairs_room_id': None})

        self._cancel_timers()
        ui.notify('Вы покинули комнату', type='info')
        self.show_main_menu()

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

    def _clear_ui_containers(self):
        """Очищает все UI контейнеры"""
        self.players_table_container = None
        self.rooms_list_container = None
        self.guessing_status_container = None