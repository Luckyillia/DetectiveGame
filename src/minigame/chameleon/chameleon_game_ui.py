from nicegui import ui, app
import random
import string
import time
from datetime import datetime

from src.minigame.chameleon.chameleon_data_service import ChameleonDataService
from src.minigame.chameleon.chameleon_room_service import ChameleonRoomService
from src.services.log_services import LogService


class ChameleonGameUI:
    """
    Класс для управления интерфейсом игры Хамелеон.
    Гибридный режим: обсуждение происходит вживую, а интерфейс онлайн.
    """

    def __init__(self):
        self.log_service = LogService()
        self.data_service = ChameleonDataService()
        self.room_service = ChameleonRoomService()

        self.current_room_id = None
        self.player_name = ""
        self.game_container = None
        self.word_grid = None
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

        # Получаем имя пользователя
        self.player_name = app.storage.user.get('username', '')

        with self.game_container:
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Игра "Хамелеон"').classes('text-2xl font-bold mb-2 text-center')
                ui.label('Социальная игра-детектив: найди, кто из игроков не знает секретное слово!').classes(
                    'text-center mb-4')

                with ui.expansion('Правила игры', icon='help_outline').classes('w-full mb-4'):
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
                    """)

            with ui.row().classes('w-full items-center mb-4'):
                ui.label('Ваше имя:').classes('mr-2')
                player_name_input = ui.input(value=self.player_name).classes('flex-grow')

                def update_player_name():
                    self.player_name = player_name_input.value.strip()
                    if not self.player_name:
                        self.player_name = app.storage.user.get('username', '')
                        player_name_input.value = self.player_name

                player_name_input.on('blur', lambda: update_player_name())

            with ui.row().classes('w-full gap-2 mb-4'):
                ui.button('Создать новую игру', on_click=self.create_new_game).classes(
                    'flex-grow bg-green-500 text-white')
                ui.button('Присоединиться к игре', on_click=self.show_join_menu).classes(
                    'flex-grow bg-blue-500 text-white')
                ui.button('Обновить список комнат', on_click=self.refresh_rooms_list, icon='refresh').classes(
                    'bg-gray-200 dark:bg-gray-700')

            # Список доступных комнат
            rooms_container = ui.element('div').classes('w-full')

            # Функция для обновления списка комнат
            def update_rooms_list():
                rooms_container.clear()

                with rooms_container:
                    with ui.card().classes('w-full p-4'):
                        ui.label('Доступные комнаты:').classes('text-xl font-bold mb-2')

                        available_rooms = self.room_service.get_rooms_list()

                        if available_rooms:
                            # Определяем столбцы для таблицы
                            columns = [
                                {'name': 'room_id', 'label': 'ID комнаты', 'field': 'room_id', 'align': 'center'},
                                {'name': 'host_name', 'label': 'Создатель', 'field': 'host_name', 'align': 'center'},
                                {'name': 'player_count', 'label': 'Игроков', 'field': 'player_count',
                                 'align': 'center'},
                                {'name': 'actions', 'label': 'Действия', 'field': 'actions', 'align': 'center'},
                            ]

                            # Подготавливаем данные для строк
                            rows = []
                            for room in available_rooms:
                                rows.append({
                                    'room_id': room['room_id'],
                                    'host_name': room['host_name'],
                                    'player_count': str(room['player_count']),
                                    'actions': ''  # Действия добавим с помощью ячейки с кнопкой
                                })

                            # Создаем таблицу с колонками и пустыми строками
                            with ui.table(columns=columns, rows=rows).classes('w-full').props('bordered') as table:
                                # Добавляем кнопки в колонку actions
                                for i, room in enumerate(available_rooms):
                                    with table.add_slot('body-cell-actions', f"{{'row': {rows[i]}}}"):
                                        ui.button('Присоединиться',
                                                  on_click=lambda r=room['room_id']: self.join_game(r)).props(
                                            'size=sm color=primary')
                        else:
                            ui.label('Нет доступных комнат').classes('text-gray-500 italic text-center p-4')

            # Обновляем список комнат
            update_rooms_list()

            # Запускаем таймер обновления списка комнат (каждые 5 секунд)
            self.rooms_update_timer = ui.timer(5.0, update_rooms_list)

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
        with ui.dialog() as dialog, ui.card().classes('p-4 w-96'):
            ui.label('Присоединиться к игре').classes('text-xl font-bold mb-4')

            room_id_input = ui.input('ID комнаты').classes('w-full mb-2')

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

            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300')
                ui.button('Присоединиться', on_click=join_room).classes('bg-blue-500 text-white')

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
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = ui.timer(1.0, lambda: self.update_waiting_room())

        with self.game_container:
            with ui.card().classes('w-full p-4'):
                ui.label(f'Игра "Хамелеон" (ID: {self.current_room_id})').classes('text-xl font-bold mb-2 text-center')

                # Проверяем, является ли текущий пользователь хостом
                current_user_id = app.storage.user.get('user_id')
                current_player = next((p for p in room_data["players"] if p["id"] == current_user_id), None)
                is_host = current_player and current_player.get("is_host", False)

                if room_data["status"] == "waiting":
                    ui.label('Ожидание игроков...').classes('text-center mb-4')

                    # Копировать ID комнаты
                    with ui.row().classes('w-full justify-center mb-4'):
                        ui.label('ID комнаты:').classes('mr-2')
                        ui.label(self.current_room_id).classes('font-bold mr-2')
                        ui.button('Копировать', icon='content_copy', on_click=lambda: ui.notify('ID скопирован')).props(
                            'dense flat')

                    # Список игроков
                    with ui.card().classes('w-full p-4 mb-4'):
                        ui.label('Игроки:').classes('font-bold mb-2')

                        # Таблица игроков
                        columns = [
                            {'name': 'name', 'label': 'Имя', 'field': 'name', 'align': 'left'},
                            {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'},
                        ]

                        rows = []
                        for player in room_data["players"]:
                            status = []
                            if player.get("is_host", False):
                                status.append("Ведущий")
                            if player.get("is_ready", False):
                                status.append("Готов ✓")
                            else:
                                status.append("Не готов ✗")

                            rows.append({
                                'name': player["name"],
                                'status': ", ".join(status)
                            })

                        ui.table(columns=columns, rows=rows).classes('w-full')

                    # Если хост, показываем кнопку выбора категории и начала игры
                    if is_host:
                        # Выбор категории
                        with ui.card().classes('w-full p-4 mb-4'):
                            ui.label('Выберите категорию:').classes('font-bold mb-2')

                            category_select = ui.select(
                                options=self.data_service.get_all_categories(),
                                value=self.data_service.get_random_category()
                            ).classes('w-full mb-2')

                            word = None  # Переменная для хранения выбранного слова

                            def update_category():
                                nonlocal word
                                category = category_select.value
                                words = self.data_service.get_words_for_category(category)
                                word = random.choice(words) if words else None
                                if word:
                                    selected_word.text = f'Выбранное слово: {word}'
                                else:
                                    selected_word.text = 'Не удалось выбрать слово для категории'

                            selected_word = ui.label().classes('font-bold')
                            update_category()  # Инициализация

                            category_select.on('change', lambda: update_category())

                            # Кнопка начала игры
                            def start_game():
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

                            ui.button('Начать игру', on_click=start_game).classes('bg-green-500 text-white w-full mt-2')
                    else:
                        # Для обычных игроков - кнопка готовности
                        is_ready = current_player and current_player.get("is_ready", False)

                        ready_button = ui.button(
                            'Я готов!' if not is_ready else 'Отменить готовность',
                            on_click=lambda: self.toggle_ready()
                        ).classes(f'w-full {"bg-green-500 text-white" if not is_ready else "bg-red-500 text-white"}')

                # Кнопка выхода из игры
                ui.button('Выйти из игры', on_click=self.leave_game).classes('w-full bg-red-500 text-white mt-4')

    def update_waiting_room(self):
        """Обновляет данные в комнате ожидания."""
        if not self.current_room_id:
            if self.update_timer:
                self.update_timer.cancel()
                self.update_timer = None
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            if self.update_timer:
                self.update_timer.cancel()
                self.update_timer = None
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
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = ui.timer(1.0, lambda: self.update_game_screen())

        # Получаем данные текущего игрока
        current_user_id = app.storage.user.get('user_id')
        current_player_index = next((i for i, p in enumerate(room_data["players"]) if p["id"] == current_user_id), -1)
        is_chameleon = current_player_index == room_data["game_data"]["chameleon_index"]

        with self.game_container:
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Игра "Хамелеон"').classes('text-2xl font-bold mb-2 text-center')

                # Показываем категорию всем игрокам
                category = room_data["game_data"]["category"]
                ui.label(f'Категория: {category}').classes('text-xl text-center mb-4')

                # Показываем секретное слово не-Хамелеону
                if not is_chameleon:
                    with ui.card().classes('bg-green-100 dark:bg-green-900 p-4 mb-4'):
                        ui.label('Вы знаете секретное слово:').classes('text-center mb-2')
                        ui.label(room_data["game_data"]["word"]).classes('text-2xl font-bold text-center')
                else:
                    with ui.card().classes('bg-yellow-100 dark:bg-yellow-900 p-4 mb-4'):
                        ui.label('Вы - Хамелеон!').classes('text-center mb-2')
                        ui.label('Вы не знаете секретное слово. Притворитесь, что знаете!').classes('text-center')

                # Показываем сетку с буквами и цифрами для слов
                self.create_word_grid()

                # Список игроков
                with ui.card().classes('w-full p-4 mb-4'):
                    ui.label('Игроки:').classes('font-bold mb-2')

                    # Таблица игроков
                    columns = [
                        {'name': 'index', 'label': '№', 'field': 'index', 'align': 'center', 'width': '50px'},
                        {'name': 'name', 'label': 'Имя', 'field': 'name', 'align': 'left'},
                    ]

                    rows = []
                    for i, player in enumerate(room_data["players"]):
                        rows.append({
                            'index': str(i + 1),
                            'name': player["name"]
                        })

                    ui.table(columns=columns, rows=rows).classes('w-full')

                # Добавляем информацию о текущем этапе игры
                round_text = {
                    0: "Подготовка к игре",
                    1: "Игроки обсуждают слово",
                    2: "Время голосования",
                    3: "Оглашение результатов"
                }

                current_round = room_data["game_data"]["round"]

                ui.label(f"Текущий этап: {round_text.get(current_round, 'Неизвестно')}").classes(
                    'text-center my-4 font-bold text-lg')

                # Раунд голосования (только в раунде 2)
                if current_round == 2:
                    with ui.card().classes('w-full p-4 mb-4'):
                        ui.label('Время голосования! Кто, по вашему мнению, Хамелеон?').classes('font-bold mb-2')

                        # Проверяем, проголосовал ли уже текущий игрок
                        has_voted = current_user_id in room_data["game_data"]["votes"]

                        if has_voted:
                            voted_id = room_data["game_data"]["votes"][current_user_id]
                            voted_player = next((p for p in room_data["players"] if p["id"] == voted_id), None)
                            voted_name = voted_player["name"] if voted_player else "Неизвестный игрок"

                            ui.label(
                                f'Вы проголосовали за {voted_name}. Ожидайте, пока все игроки проголосуют.').classes(
                                'text-center p-4')
                        else:
                            for player in room_data["players"]:
                                if player["id"] != current_user_id:  # Нельзя голосовать за себя
                                    ui.button(
                                        f"Проголосовать за {player['name']}",
                                        on_click=lambda p=player: self.vote_for_player(p["id"])
                                    ).classes('w-full mb-2 bg-purple-500 text-white')

                # Раунд результатов (только в раунде 3)
                elif current_round == 3:
                    with ui.card().classes('w-full p-4 mb-4'):
                        ui.label('Результаты голосования:').classes('font-bold mb-2')

                        results = self.room_service.get_vote_results(self.current_room_id)
                        if not results:
                            ui.label('Ошибка получения результатов').classes('text-center p-4')
                        else:
                            # Таблица результатов голосования
                            columns = [
                                {'name': 'name', 'label': 'Имя', 'field': 'name', 'align': 'left'},
                                {'name': 'votes', 'label': 'Голосов', 'field': 'votes', 'align': 'center'},
                            ]

                            rows = []
                            for player in room_data["players"]:
                                vote_count = results["votes"].get(player["id"], 0)
                                rows.append({
                                    'name': player["name"],
                                    'votes': vote_count
                                })

                            ui.table(columns=columns, rows=rows).classes('w-full mb-4')

                            # Определяем, кто победил
                            chameleon_player = room_data["players"][room_data["game_data"]["chameleon_index"]] if 0 <= \
                                                                                                                  room_data[
                                                                                                                      "game_data"][
                                                                                                                      "chameleon_index"] < len(
                                room_data["players"]) else None

                            if results["chameleon_caught"]:
                                ui.label(f'Хамелеон ({chameleon_player["name"]}) был пойман!').classes(
                                    'text-center text-green-600 font-bold mb-2')

                                # Если текущий игрок - Хамелеон, показываем ему форму для угадывания
                                if is_chameleon:
                                    ui.label('Теперь вы можете попытаться угадать секретное слово:').classes(
                                        'text-center mb-2')

                                    with ui.row().classes('w-full items-center mb-2'):
                                        guess_input = ui.input(placeholder='Введите ваше предположение...').classes(
                                            'flex-grow mr-2')

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

                                        ui.button('Отправить догадку', on_click=check_guess).classes(
                                            'bg-blue-500 text-white')
                                else:
                                    ui.label('Ожидание, пока Хамелеон сделает предположение...').classes(
                                        'text-center p-4')
                            else:
                                ui.label('Хамелеон не был пойман! Хамелеон побеждает!').classes(
                                    'text-center text-red-600 font-bold mb-2')
                                ui.label(f'Хамелеоном был игрок {chameleon_player["name"]}').classes('text-center mb-2')
                                ui.label(f'Загаданное слово было: {room_data["game_data"]["word"]}').classes(
                                    'text-center')

                                ui.button('Завершить игру', on_click=lambda: self.finish_game()).classes(
                                    'w-full mt-4 bg-blue-500 text-white')

                # Кнопка выхода
                ui.button('Выйти из игры', on_click=self.leave_game).classes('w-full bg-red-500 text-white mt-4')

    def create_word_grid(self):
        """Создает игровое поле с буквами, цифрами и словами из выбранной категории."""
        if not self.current_room_id:
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            return

        # Получаем категорию игры
        category = room_data["game_data"]["category"]

        # Получаем список слов для этой категории
        category_words = self.data_service.get_words_for_category(category)

        # Если слов недостаточно, дополняем список
        while len(category_words) < 25:
            category_words.append("")

        # Перемешиваем слова для случайного распределения
        random.shuffle(category_words)

        # Создаем список букв и цифр для сетки
        letters = list(string.ascii_uppercase)
        numbers = [str(i) for i in range(1, 5)]  # 1-5

        # Создаем карточку для сетки
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label(f'Игровое поле для категории "{category}":').classes('font-bold mb-2')

            # Создаем сетку
            with ui.element('div').classes('grid grid-cols-6 gap-2'):
                # Пустая ячейка в верхнем левом углу
                ui.label('').classes('p-2 text-center font-bold')

                # Заголовки столбцов (буквы)
                for letter in letters[:4]:
                    ui.label(letter).classes('p-2 text-center font-bold bg-gray-100 dark:bg-gray-700')

                # Строки
                for row, number in enumerate(numbers):
                    # Заголовок строки (число)
                    ui.label(number).classes('p-2 text-center font-bold bg-gray-100 dark:bg-gray-700')

                    # Ячейки в строке
                    for col in range(4):
                        # Вычисляем индекс слова в нашем списке
                        word_index = row * 4 + col
                        cell_id = f"{letters[col]}{number}"

                        # Берем слово из списка
                        word = category_words[word_index] if word_index < len(category_words) else ""

                        # Создаем кнопку со словом
                        ui.button(
                            word,
                            on_click=lambda c=cell_id, w=word: ui.notify(f'Выбрана ячейка {c}: {w}')
                        ).classes(
                            'p-2 min-h-10 text-xs')

    def update_game_screen(self):
        """Обновляет данные на экране игры."""
        if not self.current_room_id:
            if self.update_timer:
                self.update_timer.cancel()
                self.update_timer = None
            return

        room_data = self.room_service.get_room(self.current_room_id)
        if not room_data:
            if self.update_timer:
                self.update_timer.cancel()
                self.update_timer = None
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
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

        self.game_container.clear()

        with self.game_container:
            with ui.card().classes('w-full p-6 text-center'):
                ui.label('Игра завершена!').classes('text-2xl font-bold mb-4')

                if chameleon_won:
                    ui.label('Хамелеон победил, угадав секретное слово!').classes(
                        'text-xl text-yellow-600 dark:text-yellow-400 mb-4')
                else:
                    ui.label('Обычные игроки победили!').classes('text-xl text-green-600 dark:text-green-400 mb-4')

                ui.label(f'Загаданное слово было: {actual_word}').classes('text-lg mb-6')

                with ui.row().classes('w-full justify-center gap-4'):
                    ui.button('Играть снова', on_click=self.reset_game).classes('bg-blue-500 text-white')
                    ui.button('Выйти в меню', on_click=self.return_to_menu).classes('bg-gray-500 text-white')

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

        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

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