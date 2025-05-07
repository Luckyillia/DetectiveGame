from nicegui import ui, app
import random
import time
from datetime import datetime

from src.minigame.chameleon.chameleon_data_service import ChameleonDataService
from src.minigame.chameleon.chameleon_room_service import ChameleonRoomService
from src.services.log_services import LogService
from src.minigame.chameleon.chameleon_ui_components import ChameleonComponents


class ChameleonGameUI:
    """
    Класс для управления интерфейсом игры Хамелеон.
    Гибридный режим: обсуждение происходит вживую, а интерфейс онлайн.
    """

    def __init__(self):
        self.log_service = LogService()
        self.data_service = ChameleonDataService()
        self.room_service = ChameleonRoomService()
        self.components = ChameleonComponents()

        self.current_room_id = None
        self.player_name = ""
        self.game_container = None
        self.last_update_time = 0
        self.update_timer = None
        self.rooms_update_timer = None

    def show_main_menu(self, container=None):
        """Показывает главное меню игры."""
        # Восстанавливаем сохраненный ID комнаты при перезагрузке
        saved_room_id = app.storage.user.get('chameleon_room_id')
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
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Хамелеон"',
                    'Социальная игра-детектив: найди, кто из игроков не знает секретное слово!',
                    'psychology'
                )

                with ui.expansion('Правила игры', icon='help_outline').classes(
                        'w-full mb-4 bg-indigo-50 dark:bg-indigo-900 rounded-lg'):
                    ui.markdown("""
                    ### Правила игры "Хамелеон":

                    1. Каждый игрок получает категорию и секретное слово из неё, кроме одного - Хамелеона.
                    2. Хамелеон знает только категорию, но не знает секретное слово.
                    3. По очереди каждый игрок говорит одно слово, описывающее секретное слово (в реальном общении).
                    4. Хамелеон должен притвориться, что знает слово, и не выдать себя.
                    5. После круга описаний все игроки голосуют, кто, по их мнению, Хамелеон.
                    6. Если Хамелеон не раскрыт, он выигрывает. Если раскрыт, но угадывает секретное слово, игроки проигрывают.

                    Цель обычных игроков: выявить Хамелеона.
                    Цель Хамелеона: остаться незамеченным или угадать секретное слово.

                    В этой версии игры обсуждение происходит вживую, а интерфейс служит для отображения информации.
                    """).classes('p-3')

            with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-white dark:bg-gray-800'):
                with ui.row().classes('w-full items-center mb-4'):
                    ui.icon('person').classes('text-indigo-500 mr-2')
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
                        'flex-grow bg-green-600 hover:bg-green-700 text-white')
                    ui.button('Присоединиться к игре', icon='login', on_click=self.show_join_menu).classes(
                        'flex-grow bg-blue-600 hover:bg-blue-700 text-white')
                    ui.button('Обновить список', icon='refresh', on_click=self.refresh_rooms_list).classes(
                        'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600')

            self._create_available_rooms_list()

    def _create_available_rooms_list(self):
        """Создает и отображает список доступных комнат"""
        with ui.card().classes('w-full p-6 mt-4 rounded-xl shadow-lg bg-white dark:bg-gray-800'):
            ui.label('Доступные комнаты:').classes('text-xl font-bold mb-4 text-indigo-600 dark:text-indigo-400')
            rooms_container = ui.element('div').classes('w-full')

            # Функция для обновления списка комнат
            def update_rooms_list():
                rooms_container.clear()

                with rooms_container:
                    available_rooms = self.room_service.get_rooms_list()

                    if available_rooms:
                        # Создаем таблицу комнат
                        columns = [
                            {'name': 'room_id', 'label': 'ID комнаты', 'field': 'room_id', 'align': 'center'},
                            {'name': 'host_name', 'label': 'Создатель', 'field': 'host_name', 'align': 'center'},
                            {'name': 'player_count', 'label': 'Игроков', 'field': 'player_count', 'align': 'center'},
                            {'name': 'action', 'label': 'Действие', 'field': 'action', 'align': 'center'},
                        ]

                        # Подготавливаем данные для строк
                        rows = []
                        for room in available_rooms:
                            rows.append({
                                'room_id': room['room_id'],
                                'host_name': room['host_name'],
                                'player_count': str(room['player_count']),
                                'action': ''  # Будем добавлять кнопку через слот
                            })

                        # Создаем таблицу
                        with ui.table(columns=columns, rows=rows).classes('w-full').props(
                                'flat bordered card-container') as table:
                            # Добавляем кнопки через слот
                            for i, room in enumerate(available_rooms):
                                room_id = room['room_id']
                                with table.add_slot('body-cell-action',
                                                    f"{{row: {{room_id: '{room_id}', host_name: '{room['host_name']}', player_count: '{room['player_count']}' }}}}"):
                                    ui.button(
                                        'Присоединиться',
                                        icon='login',
                                        on_click=lambda r=room_id: self.join_game(r)
                                    ).props('size=sm color=primary')
                    else:
                        with ui.card().classes('w-full p-4 bg-gray-50 dark:bg-gray-700 rounded-lg'):
                            with ui.row().classes('items-center justify-center text-gray-500 dark:text-gray-400'):
                                ui.icon('info').classes('text-xl mr-2')
                                ui.label('Нет доступных комнат').classes('text-center')

            # Обновляем список комнат
            update_rooms_list()

            # Запускаем таймер обновления списка комнат (каждые 5 секунд)
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
        app.storage.user.update({'chameleon_room_id': room_id})
        self.show_waiting_room()

    def show_join_menu(self):
        """Показывает меню для присоединения к игре."""
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96 rounded-xl shadow-lg bg-white dark:bg-gray-800'):
            ui.label('Присоединиться к игре').classes(
                'text-xl font-bold mb-4 text-center text-indigo-600 dark:text-indigo-400')

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
        app.storage.user.update({'chameleon_room_id': room_id})

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
            app.storage.user.update({'chameleon_room_id': None})
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
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800'):
                self.components.create_header(
                    'Игра "Хамелеон"',
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
                    with ui.card().classes('w-full p-4 mb-4 bg-white dark:bg-gray-700 rounded-lg shadow'):
                        ui.label('Игроки:').classes('font-bold mb-3 text-lg text-gray-800 dark:text-gray-200')

                        # Создаем таблицу игроков
                        self.components.create_player_table(
                            players=room_data["players"],
                            current_round=0
                        )

                    # Если хост, показываем кнопку выбора категории и начала игры
                    if is_host:
                        # Выбор категории
                        with ui.card().classes('w-full p-4 mb-4 bg-green-50 dark:bg-green-900 rounded-lg shadow'):
                            ui.label('Настройки игры (только для ведущего)').classes(
                                'font-bold mb-3 text-lg text-green-800 dark:text-green-200')

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

                                # Получаем случайное слово из выбранной категории
                                word = random.choice(self.data_service.get_words_for_category(category_select.value))
                                if not word:
                                    ui.notify('Не удалось выбрать слово', type='negative')
                                    return

                                # Проверяем, достаточно ли игроков
                                if len(room_data["players"]) < 3:
                                    ui.notify('Для игры нужно минимум 3 игрока', type='warning')
                                    return

                                # Начинаем игру
                                success = self.room_service.start_game(
                                    self.current_room_id,
                                    category_select.value,
                                    word
                                )

                                if success:
                                    ui.notify('Игра началась!', type='positive')
                                    self.show_game_screen()
                                else:
                                    ui.notify('Ошибка при запуске игры', type='negative')

                            ui.button('Начать игру', icon='play_arrow', on_click=start_game).classes(
                                'w-full bg-green-600 hover:bg-green-700 text-white mt-3')
                    else:
                        # Для обычных игроков - кнопка готовности
                        is_ready = current_player and current_player.get("is_ready", False)

                        ready_button = ui.button(
                            'Я готов!' if not is_ready else 'Отменить готовность',
                            icon='check_circle' if not is_ready else 'cancel',
                            on_click=lambda: self.toggle_ready()
                        ).classes(
                            f'w-full {"bg-green-600 hover:bg-green-700 text-white" if not is_ready else "bg-red-500 hover:bg-red-600 text-white"}')

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
            app.storage.user.update({'chameleon_room_id': None})
            self.show_main_menu()
            return

        # Если статус изменился, обновляем экран
        if room_data["status"] == "playing" and room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)
            self.show_game_screen()
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
            app.storage.user.update({'chameleon_room_id': None})
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
        is_chameleon = current_player_index == room_data["game_data"]["chameleon_index"]
        is_host = next((p for p in room_data["players"] if p["id"] == current_user_id and p.get("is_host", False)),
                       None) is not None

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800 mb-4'):
                self.components.create_header('Игра "Хамелеон"')

                # Показываем категорию всем игрокам
                category = room_data["game_data"]["category"]
                ui.label(f'Категория: {category}').classes(
                    'text-xl text-center mb-4 font-medium text-indigo-700 dark:text-indigo-300')

                # Показываем секретное слово не-Хамелеону
                self.components.create_role_card(is_chameleon,
                                                 room_data["game_data"]["word"] if not is_chameleon else None)

                # Показываем индикатор текущего раунда
                current_round = room_data["game_data"].get("round", 1)
                self.components.create_round_indicator(current_round)

                # Кнопка для перехода к голосованию (только для хоста и только в раунде 1)
                if is_host and current_round == 1:
                    def start_voting():
                        # Копируем данные комнаты и изменяем номер раунда
                        updated_room = dict(room_data)
                        updated_room["game_data"]["round"] = 2
                        updated_room["last_activity"] = int(time.time())

                        # Сохраняем обновленные данные
                        rooms = self.room_service.load_rooms()
                        rooms[self.current_room_id] = updated_room
                        success = self.room_service.save_rooms(rooms)

                        if success:
                            ui.notify('Переход к этапу голосования', type='positive')
                            self.show_game_screen()
                        else:
                            ui.notify('Ошибка при переходе к голосованию', type='negative')

                    ui.button('Перейти к голосованию', icon='how_to_vote', on_click=start_voting).classes(
                        'w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white')

            # Показываем сетку с буквами и цифрами для слов
            words = self.data_service.get_words_for_category(category)
            self.components.create_word_grid(category, words)

            # Список игроков с голосованием
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800 mb-4'):
                ui.label('Игроки:').classes('text-lg font-bold mb-3 text-gray-800 dark:text-gray-200')

                # Создаем таблицу игроков с учетом текущего раунда
                self.components.create_player_table(
                    players=room_data["players"],
                    current_round=current_round,
                    current_user_id=current_user_id,
                    vote_handler=self.vote_for_player,
                    votes=room_data["game_data"].get("votes", {}),
                    chameleon_index=room_data["game_data"].get("chameleon_index") if current_round == 3 else None
                )

            # Раунд результатов (только в раунде 3)
            if current_round == 3:
                vote_results = self.room_service.get_vote_results(self.current_room_id)

                with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800 mb-4'):
                    ui.label('Результаты игры').classes(
                        'text-xl font-bold mb-3 text-center text-indigo-600 dark:text-indigo-400')

                    if not vote_results:
                        ui.label('Ошибка получения результатов').classes('text-center p-4 text-red-500')
                    else:
                        # Определяем, кто победил
                        chameleon_index = room_data["game_data"]["chameleon_index"]
                        chameleon_player = room_data["players"][chameleon_index] if 0 <= chameleon_index < len(
                            room_data["players"]) else None

                        if vote_results["chameleon_caught"]:
                            self.components.create_game_result_card(
                                True,
                                chameleon_player["name"],
                                room_data["game_data"]["word"]
                            )

                            # Если текущий игрок - Хамелеон, показываем ему форму для угадывания
                            if is_chameleon:
                                with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4 rounded-lg'):
                                    ui.label('Вас поймали, но у вас есть шанс на победу!').classes(
                                        'text-center font-bold mb-2 text-yellow-700 dark:text-yellow-300')
                                    ui.label('Попытайтесь угадать секретное слово:').classes(
                                        'text-center mb-3 text-yellow-800 dark:text-yellow-200')

                                    with ui.row().classes('w-full items-center justify-center mb-2'):
                                        guess_input = ui.input(placeholder='Введите ваше предположение...').classes(
                                            'w-full max-w-md')
                                        guess_input.props('outlined rounded dense')

                                        def check_guess():
                                            guess = guess_input.value.strip()
                                            if not guess:
                                                ui.notify('Введите предположение', type='warning')
                                                return

                                            result = self.room_service.check_chameleon_guess(
                                                self.current_room_id,
                                                current_user_id,
                                                guess
                                            )

                                            if result:
                                                if result["is_correct"]:
                                                    ui.notify('Вы правильно угадали слово! Вы победили!',
                                                              type='positive')
                                                else:
                                                    ui.notify(f'Неверно! Загаданное слово: {result["actual_word"]}',
                                                              type='negative')

                                                self.show_game_over(result["is_correct"], result["actual_word"])

                                    ui.button('Отправить догадку', icon='send', on_click=check_guess).classes(
                                        'bg-yellow-600 hover:bg-yellow-700 text-white w-full max-w-md mx-auto mt-2')
                            else:
                                ui.label('Ожидайте, пока Хамелеон попытается угадать слово...').classes(
                                    'text-center mt-2 italic')
                        else:
                            self.components.create_game_result_card(
                                False,
                                chameleon_player["name"],
                                room_data["game_data"]["word"]
                            )

                            ui.button('Завершить игру', icon='check_circle',
                                      on_click=lambda: self.finish_game()).classes(
                                'w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white')

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
            app.storage.user.update({'chameleon_room_id': None})
            self.show_main_menu()
            return

        # Если статус изменился или были обновления, обновляем экран
        if room_data.get("last_activity", 0) > self.last_update_time:
            self.last_update_time = room_data.get("last_activity", 0)

            # Если игра завершена, показываем экран завершения
            if room_data["status"] == "finished":
                self.show_game_over(False, room_data["game_data"]["word"])
                return

            # В остальных случаях просто обновляем экран игры
            self.show_game_screen()

    def vote_for_player(self, player_id):
        """Голосует за игрока как за Хамелеона."""
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

    def show_game_over(self, chameleon_won, actual_word):
        """Показывает экран завершения игры."""
        self._cancel_timers()
        self.game_container.clear()

        with self.game_container:
            with ui.card().classes('w-full p-6 rounded-xl shadow-lg bg-white dark:bg-gray-800 text-center'):
                ui.label('Игра завершена!').classes('text-2xl font-bold mb-4 text-indigo-600 dark:text-indigo-400')

                if chameleon_won:
                    with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4 rounded-lg'):
                        ui.label('Хамелеон победил, угадав секретное слово!').classes(
                            'text-xl text-yellow-700 dark:text-yellow-300 font-bold mb-2')
                        ui.label(f'Загаданное слово было: {actual_word}').classes(
                            'text-lg text-yellow-800 dark:text-yellow-200')
                else:
                    with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4 rounded-lg'):
                        ui.label('Обычные игроки победили!').classes(
                            'text-xl text-green-700 dark:text-green-300 font-bold mb-2')
                        ui.label(f'Загаданное слово было: {actual_word}').classes(
                            'text-lg text-green-800 dark:text-green-200')

                with ui.row().classes('w-full justify-center gap-4 mt-6'):
                    ui.button('Играть снова', icon='replay', on_click=self.reset_game).classes(
                        'bg-blue-600 hover:bg-blue-700 text-white')
                    ui.button('Выйти в меню', icon='home', on_click=self.return_to_menu).classes(
                        'bg-gray-500 hover:bg-gray-600 text-white')

    def finish_game(self):
        """Завершает текущую игру."""
        if not self.current_room_id:
            return

        success = self.room_service.finish_game(self.current_room_id)
        if success:
            ui.notify('Игра завершена', type='positive')
            self.show_game_over(False, self.room_service.get_room(self.current_room_id)["game_data"]["word"])
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
        app.storage.user.update({'chameleon_room_id': None})
        self.show_main_menu()