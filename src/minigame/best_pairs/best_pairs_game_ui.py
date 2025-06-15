from nicegui import ui, app
import random
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

                with ui.expansion('Правила игры', icon='help_outline').classes(
                        'w-full mb-4 bg-purple-50 dark:bg-purple-900 rounded-lg'):
                    ui.markdown("""
                    ### Правила игры "Лучшие Пары":

                    1. **Участники**: 2-8 игроков, каждый по очереди становится ведущим
                    2. **Карточки**: 5 существительных и 5 прилагательных

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
                    """).classes('p-3')

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
        """Показывает список доступных комнат"""
        rooms_list = self.room_service.get_rooms_list()

        if rooms_list:
            ui.label('Доступные комнаты:').classes('text-lg font-bold mb-2')

            with ui.column().classes('w-full gap-2'):
                for room in rooms_list:
                    with ui.card().classes('w-full p-3 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700').on(
                            'click', lambda r=room: self.join_room(r['room_id'])):
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label(f"Комната {room['room_id']}").classes('font-bold')
                            ui.label(f"Хост: {room['host_name']}").classes('text-sm')
                            ui.label(f"Игроков: {room['player_count']}").classes('text-sm')

        else:
            self.components.create_status_indicator('Нет доступных комнат', 'info')

        # Запускаем обновление списка комнат
        self._cancel_timers()
        self.rooms_update_timer = ui.timer(3.0, lambda: self.update_rooms_list())

    def update_rooms_list(self):
        """Обновляет список доступных комнат"""
        if self.game_container and not self.current_room_id:
            self.show_main_menu()

    def create_room(self):
        """Создает новую комнату"""
        self._ensure_player_id()
        room_id = self.room_service.create_room(self.player_id, self.player_name)

        if room_id:
            self.current_room_id = room_id
            app.storage.user.update({'best_pairs_room_id': room_id})
            ui.notify(f'Комната {room_id} создана!', type='positive')
            self.show_waiting_room()
        else:
            ui.notify('Ошибка создания комнаты', type='negative')

    def show_join_dialog(self):
        """Показывает диалог для ввода ID комнаты"""
        dialog = ui.dialog()

        with dialog, ui.card().classes('p-4'):
            ui.label('Введите ID комнаты').classes('text-lg font-bold mb-2')
            room_input = ui.input('ID комнаты', placeholder='pairs_1234').classes('w-full mb-4')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300')
                ui.button('Присоединиться',
                          on_click=lambda: self.join_room(room_input.value) or dialog.close()
                          ).classes('bg-purple-600 text-white')

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
                    self.components.create_player_table(room_data["players"], self.player_id, is_waiting=True)

                    # Кнопки управления
                    with ui.row().classes('w-full justify-center gap-4 mt-4'):
                        if is_host and len(room_data["players"]) >= 2:
                            # Хост может начать игру если все готовы
                            all_ready = self.room_service.all_players_ready(self.current_room_id)

                            ui.button(
                                'Начать игру',
                                icon='play_arrow',
                                on_click=self.start_game
                            ).classes(
                                'bg-green-600 hover:bg-green-700 text-white' if all_ready
                                else 'bg-gray-400 cursor-not-allowed'
                            ).props('disabled' if not all_ready else '')

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

        # Обновляем только если есть изменения
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)
            self.show_waiting_room()

    def toggle_ready(self):
        """Переключает статус готовности игрока"""
        self._ensure_player_id()
        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            return

        current_player = next((p for p in room_data["players"] if p["id"] == self.player_id), None)
        if not current_player:
            return

        new_ready_status = not current_player.get("is_ready", False)
        self.room_service.set_player_ready(self.current_room_id, self.player_id, new_ready_status)

    def start_game(self):
        """Начинает игру (только для хоста)"""
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

        self.game_container.clear()

        # Запускаем таймер обновления
        self._cancel_timers()
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

    def show_host_pairing_interface(self, room_data):
        """Интерфейс для ведущего - раскладывание пар"""
        nouns = room_data["game_data"]["nouns"]
        adjectives = room_data["game_data"]["adjectives"]

        ui.label('Вы - ведущий этого раунда!').classes('text-xl font-bold text-purple-700 dark:text-purple-300 mb-4')
        ui.label('Разложите прилагательные к подходящим существительным').classes(
            'text-gray-600 dark:text-gray-300 mb-4')

        # Инициализируем выбранные пары
        if not self.selected_pairings:
            self.selected_pairings = {}

        # Показываем существительные и места для прилагательных
        with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
            # Левая колонка - существительные
            with ui.column().classes('w-full'):
                ui.label('Существительные').classes('text-lg font-bold mb-2 text-center')
                for idx, noun in enumerate(nouns):
                    with ui.card().classes('p-4 bg-white dark:bg-gray-700 shadow-lg'):
                        ui.label(f"{idx + 1}. {noun}").classes('text-lg font-bold text-center')

                        # Выпадающий список для выбора прилагательного
                        current_adj = self.selected_pairings.get(idx, '')

                        adj_select = ui.select(
                            adjectives,
                            label='Выберите прилагательное',
                            value=current_adj,
                            on_change=lambda e, i=idx: self.update_pairing(i, e.value)
                        ).classes('w-full mt-2')

        # Показываем все доступные прилагательные
        ui.label('Доступные прилагательные:').classes('text-lg font-bold mb-2')
        ui.label(', '.join(adjectives)).classes('text-purple-700 dark:text-purple-300 mb-4')

        # Кнопка подтверждения
        all_paired = len(self.selected_pairings) == 5 and all(
            adj in adjectives for adj in self.selected_pairings.values())
        ui.button(
            'Подтвердить расклад',
            icon='check',
            on_click=self.submit_host_pairings
        ).classes(
            'bg-green-600 hover:bg-green-700 text-white' if all_paired
            else 'bg-gray-400 cursor-not-allowed'
        ).props('disabled' if not all_paired else '')

    def update_pairing(self, noun_idx, adjective):
        """Обновляет выбранную пару"""
        if adjective:
            self.selected_pairings[noun_idx] = adjective
        elif noun_idx in self.selected_pairings:
            del self.selected_pairings[noun_idx]

    def submit_host_pairings(self):
        """Отправляет выбранные пары"""
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

    def show_waiting_for_host(self, room_data):
        """Интерфейс ожидания для игроков пока ведущий раскладывает"""
        host_id = room_data["game_data"]["current_round_host"]
        host = next((p for p in room_data["players"] if p["id"] == host_id), None)
        host_name = host["name"] if host else "Ведущий"

        self.components.create_status_indicator(f'{host_name} раскладывает пары...', 'waiting')

        # Показываем существительные
        nouns = room_data["game_data"]["nouns"]
        ui.label('Существительные в этом раунде:').classes('text-lg font-bold mb-2 mt-4')

        with ui.row().classes('w-full gap-2 flex-wrap'):
            for idx, noun in enumerate(nouns):
                ui.chip(f"{idx + 1}. {noun}", icon='label').classes('text-lg')

    def show_host_waiting_interface(self, room_data):
        """Интерфейс ожидания для ведущего пока игроки угадывают"""
        self.components.create_status_indicator('Игроки делают свои предположения...', 'waiting')

        # Показываем прогресс
        players_count = len(room_data["players"]) - 1  # Минус ведущий
        guesses_count = len(room_data["game_data"]["player_guesses"])

        ui.label(f'Ответили: {guesses_count}/{players_count}').classes('text-lg text-center mt-4')

        # Показываем, как ведущий разложил пары
        ui.label('Ваш расклад:').classes('text-lg font-bold mb-2 mt-4')

        nouns = room_data["game_data"]["nouns"]
        adjectives = room_data["game_data"]["adjectives"]
        pairings = room_data["game_data"]["host_pairings"]

        with ui.column().classes('w-full'):
            for noun_idx, adj in pairings.items():
                noun = nouns[int(noun_idx)]
                with ui.row().classes('w-full justify-center mb-1'):
                    ui.label(f"{noun} — {adj}").classes('text-purple-700 dark:text-purple-300')

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

        ui.label('Угадайте, как ведущий разложил пары!').classes(
            'text-xl font-bold text-purple-700 dark:text-purple-300 mb-4')

        # Инициализируем выбранные пары
        if not self.selected_pairings:
            self.selected_pairings = {}

        # Показываем интерфейс для выбора
        with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
            # Левая колонка - существительные с выбором
            with ui.column().classes('w-full'):
                ui.label('Существительные').classes('text-lg font-bold mb-2 text-center')
                for idx, noun in enumerate(nouns):
                    with ui.card().classes('p-4 bg-white dark:bg-gray-700 shadow-lg'):
                        ui.label(f"{idx + 1}. {noun}").classes('text-lg font-bold text-center')

                        # Выпадающий список для выбора прилагательного
                        current_adj = self.selected_pairings.get(idx, '')

                        adj_select = ui.select(
                            adjectives,
                            label='Выберите прилагательное',
                            value=current_adj,
                            on_change=lambda e, i=idx: self.update_pairing(i, e.value)
                        ).classes('w-full mt-2')

        # Показываем все доступные прилагательные
        ui.label('Доступные прилагательные:').classes('text-lg font-bold mb-2')
        ui.label(', '.join(adjectives)).classes('text-purple-700 dark:text-purple-300 mb-4')

        # Кнопка отправки
        all_guessed = len(self.selected_pairings) == 5 and all(
            adj in adjectives for adj in self.selected_pairings.values())
        ui.button(
            'Отправить догадки',
            icon='send',
            on_click=self.submit_player_guesses
        ).classes(
            'bg-green-600 hover:bg-green-700 text-white' if all_guessed
            else 'bg-gray-400 cursor-not-allowed'
        ).props('disabled' if not all_guessed else '')

    def submit_player_guesses(self):
        """Отправляет догадки игрока"""
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

    def show_results_interface(self, room_data):
        """Показывает результаты раунда"""
        nouns = room_data["game_data"]["nouns"]
        host_pairings = room_data["game_data"]["host_pairings"]
        player_guesses = room_data["game_data"]["player_guesses"]

        # Сначала применяем очки
        self.room_service.apply_round_scores(self.current_room_id)

        # Показываем правильные пары
        ui.label('Правильные пары:').classes('text-xl font-bold mb-4')

        correct_pairings = {}
        for noun_idx_str, adj in host_pairings.items():
            noun = nouns[int(noun_idx_str)]
            correct_pairings[noun] = adj

        # Показываем результаты для текущего игрока
        self._ensure_player_id()
        if self.player_id in player_guesses:
            my_guesses = {}
            for noun_idx, adj in player_guesses[self.player_id].items():
                noun = nouns[int(noun_idx)]
                my_guesses[noun] = adj

            # Подсчитываем очки
            correct_count = 0
            for noun_idx, adj in player_guesses[self.player_id].items():
                if host_pairings.get(str(noun_idx)) == adj:
                    correct_count += 1

            score = correct_count * 2

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

            ui.label(f'Вы заработали {host_bonus} бонусных очков как ведущий!').classes(
                'text-xl font-bold text-purple-700 dark:text-purple-300 text-center'
            )

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

        # Обновляем только если есть изменения
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)
            self.show_game_screen()

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
            self.update_timer.cancel()
            self.update_timer = None

        if self.rooms_update_timer:
            self.rooms_update_timer.cancel()
            self.rooms_update_timer = None