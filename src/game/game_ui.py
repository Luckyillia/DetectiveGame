from nicegui import ui, app

from src.services.user.user_service import UserService
from src.game.game_state_service import GameStateService
from src.game.game_dialog import GameDialog
from src.game.game_room_management import GameRoomManagement
from src.services.log.log_services import LogService


class GameUI:
    def __init__(self):
        self.last_update = 0
        self.timer = None
        # Инициализируем сервисы - GameStateService теперь работает с отдельными файлами для каждой игры
        self.log_service = LogService()
        self.user_service = UserService()
        self.game_state_service = GameStateService()
        self.game_dialog = GameDialog(self)
        self.game_room_management = GameRoomManagement(game_ui=self)

    def check_updates_safely(self):
        """Упрощенная и оптимизированная версия проверки обновлений"""
        try:
            # Выполняем обычную проверку обновлений
            self.game_room_management.check_for_updates()
        except Exception as e:
            # Логируем ошибку, но не выполняем сложных проверок и операций
            self.log_service.add_error_log(
                error_message=f"Ошибка при проверке обновлений: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
            # Если таймер существует и произошла ошибка, отменяем его
            # Это предотвращает накопление ошибок и сообщений в консоли
            if self.timer:
                try:
                    self.timer.cancel()
                except:
                    pass
                self.timer = None

    def refresh_game_data(self, room_id):
        """Обновляет данные игры и комнаты, используя обновленные сервисы"""
        self.log_service.add_log(
            level='GAME',
            message=f"Обновление данных игры для комнаты: {room_id}",
            action="REFRESH_GAME",
            metadata={"room_id": room_id}
        )

        # Получаем данные комнаты из GameRoomManagement
        room_data = self.game_room_management.get_game_state(room_id)

        if not room_data or 'game_id' not in room_data:
            self.log_service.add_error_log(
                error_message=f"Не удалось получить данные комнаты или game_id отсутствует",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id}
            )
            return {}, {}

        # Получаем данные игры из GameStateService по game_id
        game_id = room_data.get('game_id')
        game_data = self.game_state_service.load(game_id)

        if not game_data:
            self.log_service.add_error_log(
                error_message=f"Не удалось получить данные игры",
                user_id=app.storage.user.get('user_id'),
                metadata={"room_id": room_id, "game_id": game_id}
            )
            return room_data, {}

        ui.update()
        return room_data, game_data

    @property
    def show_game_interface(self):
        """Показывает игровой интерфейс на основе текущего состояния игры"""
        if self.timer:
            self.timer.cancel()
            self.timer = None

        current_room_id = app.storage.user.get('game_state_id')
        user_id = app.storage.user.get('user_id')

        # Создаем или получаем контейнер для игрового интерфейса
        if hasattr(self, 'game_container'):
            self.game_container.clear()
        else:
            self.game_container = ui.element('div').classes('w-full')

        # В методе show_game_interface, для случая, когда нет активной игры:
        # В методе show_game_interface, для случая, когда нет активной игры:
        if not current_room_id:
            with self.game_container:
                # Центрирующий контейнер
                with ui.column().classes('items-center justify-center'):
                    # Увеличиваем максимальную ширину карточки и убираем отступы сверху и снизу
                    with ui.card().classes('w-full max-w-3xl mx-auto mt-4 p-0 shadow-xl rounded-xl overflow-hidden'):
                        # Увеличиваем высоту баннера для лучшей видимости
                        ui.image("https://i.imgur.com/TvSrC1A.png").classes(
                            'w-full h-64 object-cover object-center')

                        # Содержимое карточки с увеличенными отступами для лучшего баланса
                        with ui.card_section().classes('w-full p-8 bg-gray-100 dark:bg-gray-800 text-center'):
                            ui.label('У вас нет активной игры').classes(
                                'text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4')

                            ui.label('Пожалуйста, войдите в существующую игру или создайте новую.').classes(
                                'text-lg text-gray-600 dark:text-gray-300 mb-6')

                            # Добавляем контейнер для кнопки, чтобы центрировать её и ограничить ширину
                            with ui.element('div').classes('max-w-md mx-auto w-full'):
                                ui.button('Войти в игру',
                                          on_click=lambda: self.game_room_management.show_join_game_dialog(
                                              self)).classes(
                                    'bg-blue-500 hover:bg-blue-600 text-white text-lg w-full rounded-lg py-3 transition')

            self.log_service.add_log(
                level='GAME',
                message="Показывание интерфейса без игры",
                user_id=user_id,
                action="NO_GAME"
            )
            return

        # Проверяем существование комнаты через GameRoomManagement
        if not self.game_id_exists(current_room_id):
            self.log_service.add_log(
                level='GAME',
                action='ERROR',
                message=f"Комната не найдена: {current_room_id}",
                user_id=user_id,
                metadata={"room_id": current_room_id}
            )

            with self.game_container:
                with ui.card().classes(
                        'w-full max-w-lg mx-auto mt-6 p-6 shadow-lg bg-gray-100 dark:bg-gray-800 rounded-2xl'):
                    ui.label(f'⚠️ Комната с ID "{current_room_id}" не найдена.').classes(
                        'text-xl font-semibold text-center text-gray-800 dark:text-gray-100 mb-2')

                    ui.label('Проверьте правильность ID или выберите другую игру.').classes(
                        'text-center text-gray-600 dark:text-gray-300 mb-4')

                    self.game_room_management.update_user_game_state(app.storage.user.get('user_id'), None)
                    app.storage.user.update({'game_state_id': None})

                    ui.button("Вернуться назад", on_click=lambda: self.show_game_interface).classes(
                        'mt-6 bg-blue-600 hover:bg-blue-700 text-white text-lg w-full rounded-lg py-2')
            return

        # Получаем данные игры и комнаты
        room_data, game_data = self.refresh_game_data(current_room_id)

        # Проверяем наличие данных
        if not room_data or not game_data:
            with self.game_container:
                with ui.card().classes(
                        'w-full max-w-lg mx-auto mt-6 p-6 shadow-lg bg-gray-100 dark:bg-gray-800 rounded-2xl'):
                    ui.label(f'⚠️ Не удалось загрузить данные игры для комнаты {current_room_id}').classes(
                        'text-xl font-semibold text-center text-gray-800 dark:text-gray-100 mb-2')

                    self.game_room_management.update_user_game_state(app.storage.user.get('user_id'), None)
                    self.game_room_management.remove_user_from_room(app.storage.user.get('user_id'), current_room_id)
                    app.storage.user.update({'game_state_id': None})

                    ui.button("Вернуться назад", on_click=lambda: self.show_game_interface).classes(
                        'mt-6 bg-blue-600 hover:bg-blue-700 text-white text-lg w-full rounded-lg py-2')
            return

        if room_data.get('status') != 'finished':
            self.timer = ui.timer(interval=1.0, callback=self.check_updates_safely)
            self.log_service.add_log(
                level='GAME',
                message=f"Показывание активной игры для пользователя",
                user_id=user_id,
                action="SHOW_GAME",
                metadata={"room_id": current_room_id, "game_id": room_data.get('game_id'),
                          "move": room_data.get("move", 0)}
            )
            with self.game_container:
                with ui.card().classes('w-full p-6 bg-gray-50 dark:bg-gray-800'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Игровой интерфейс').classes('text-xl font-bold')
                        ui.label(f'Ходов: {room_data.get("move", 0)}').classes('text-right text-sm text-gray-600')

                    # Получаем историю локаций через game_room_management
                    location_history = self.game_room_management.get_location_history(current_room_id)
                    current_location = self.game_room_management.get_current_location(current_room_id, self)

                    # Если есть история локаций, показываем последнюю
                    if location_history:
                        for i, location in enumerate(location_history):
                            location_id = location["id"]
                            visited_at = location["visited_at"]
                            is_tooltip = location.get("is_tooltip", False)
                            visited = location.get('open', False)

                            spravochnik = game_data.get('spravochnik', {})
                            gosplace = spravochnik.get('gosplace', {})
                            people = spravochnik.get('people', {})
                            obplace = spravochnik.get('obplace', {})
                            extplace = spravochnik.get('extplace', {})

                            # Определяем название локации
                            if location_id in gosplace:
                                location_name = gosplace[location_id]
                            elif location_id in people:
                                location_name = people[location_id]
                            elif location_id in obplace:
                                location_name = obplace[location_id]
                            elif location_id in extplace:
                                location_name = extplace[location_id]
                            elif location_id == "start":
                                location_name = 'Вводные данные'
                            else:
                                location_name = 'Неизвестная локация'

                            location_text = None
                            additional_document = None

                            if location_id == '112102':  # Полиция
                                location_text = game_data.get('112102', {}).get('text',
                                                                                'Информация о полиции отсутствует')
                                additional_document = game_data.get('112102', {}).get('delo', None)
                            elif location_id == '440321':  # Морг
                                location_text = game_data.get('440321', {}).get('text',
                                                                                'Информация о морге отсутствует')
                                additional_document = game_data.get('440321', {}).get('vskrytie', None)
                            elif location_id == '220123':  # ЗАГС
                                location_text = game_data.get('220123', {}).get('text',
                                                                                'Информация о ЗАГСе отсутствует')
                                additional_document = game_data.get('220123', {}).get('otchet', None)
                            elif location_id == 'start':
                                location_text = game_data.get('start', 'Для этой игры не задан начальный текст.')
                            elif location_id in game_data.get('place', {}):
                                location_text = game_data.get('place', {}).get(location_id,
                                                                               'Информация о месте отсутствует')
                            else:
                                location_text = 'По данному делу информации нет'

                            label_text = f'Шаг {i + 1}: {location_name}'
                            icon = 'lightbulb' if is_tooltip else 'ads_click'  # Different icon for tooltips
                            expansion_classes = 'w-full' + (' bg-yellow-50 dark:bg-yellow-900' if is_tooltip else '')

                            if is_tooltip:
                                label_text = f'💡 Подсказка: {location_name}'

                            with ui.expansion(label_text, icon=icon, group='location', value=visited).classes(
                                    expansion_classes):
                                # Создаем контейнер с фоновым изображением для соответствующих локаций
                                if location_id in ['112102', '440321', '220123', 'start']:
                                    # Выбираем правильное изображение для локации
                                    bg_image = {
                                        '112102': 'https://i.imgur.com/bhJnYcl.png',  # Полиция
                                        '440321': 'https://i.imgur.com/BTb7IZI.png',  # Морг
                                        '220123': 'https://i.imgur.com/1r9oLZV.png',  # ЗАГС
                                        'start': 'https://i.imgur.com/exZCuJn.png'  # Начальная локация
                                    }.get(location_id)

                                    # Создаем контейнер с фоновым изображением
                                    with ui.element('div').classes('relative rounded-lg mb-4 overflow-hidden'):
                                        # Устанавливаем минимальную высоту для контейнера
                                        ui.element('div').classes('min-h-[200px]')

                                        # Добавляем фоновое изображение
                                        ui.element('div').style(
                                            f'position: absolute; inset: 0; background-image: url("{bg_image}"); '
                                            f'background-size: cover; background-position: center; opacity: 0.5;'
                                        )

                                        # Контент поверх фона
                                        with ui.element('div').classes('relative z-10 p-4'):
                                            # Показываем подсказку, если это нужно
                                            if is_tooltip:
                                                ui.label('Это подсказка для текущего хода').classes(
                                                    'text-amber-600 text-sm italic mb-2')

                                            # Текст локации
                                            ui.markdown(location_text).classes('whitespace-pre-wrap')
                                else:
                                    # Для остальных локаций - стандартное отображение
                                    if is_tooltip:
                                        ui.label('Это подсказка для текущего хода').classes(
                                            'text-amber-600 text-sm italic mb-2')
                                    ui.markdown(location_text).classes('whitespace-pre-wrap')

                                # Кнопка для дополнительного документа
                                if additional_document:
                                    def create_click_handler(doc):
                                        return lambda: self.game_dialog.show_document(doc)

                                    ui.button('Посмотреть вложение', icon='folder_open',
                                              on_click=create_click_handler(additional_document)).classes('mt-2')
                            self.game_room_management.location_visited(current_room_id, location_id, status=False)

                    # Иначе показываем начальный текст
                    elif game_data.get('start'):
                        # При первом запуске игры добавляем начальный текст как первую локацию
                        if not location_history:
                            self.log_service.add_log(
                                level='GAME',
                                message=f"Первый запуск игры для комнаты {current_room_id}, добавление начальной локации",
                                user_id=user_id,
                                action="ADD_START_LOCATION",
                                metadata={"room_id": current_room_id, "game_id": room_data.get('game_id')}
                            )
                            # Используем метод из game_room_management
                            self.game_room_management.add_location_to_history(current_room_id, 'start')
                        ui.markdown(game_data['start']).classes('whitespace-pre-wrap mb-6 text-lg')
                    else:
                        ui.label('Для этой игры не задан начальный текст.').classes('italic text-gray-500 mb-6')

                    with ui.row().classes('w-full justify-between items-center gap-2 mt-4'):
                        # Кнопка перемещения
                        ui.button('Куда хотите пойти?', icon='directions_walk',
                                  on_click=self.game_dialog.show_travel_dialog).classes(
                            'text-lg bg-blue-500 text-white')

                        # Кнопка открытия газеты
                        ui.button('Открыть Газету', icon='description',
                                  on_click=lambda: self.game_dialog.show_newspaper_dialog(game_data)).classes(
                            'text-lg bg-yellow-500 text-white')

                        # Кнопка: Справочник жителей
                        ui.button('Справочник жителей', icon='people',
                                  on_click=lambda: self.game_dialog.show_spravochnik_dialog(game_data, 'people',
                                                                                            game_ui=self,
                                                                                            game_id=current_room_id)).classes(
                            'text-lg bg-blue-500 text-white')

                        # Кнопка: Справочник госструктур
                        ui.button('Справочник госструктур', icon='gavel',
                                  on_click=lambda: self.game_dialog.show_spravochnik_dialog(game_data,
                                                                                            'gosplace', game_ui=self,
                                                                                            game_id=current_room_id)).classes(
                            'text-lg bg-blue-500 text-white')

                        # Кнопка: Справочник общественных мест
                        ui.button('Справочник общественных мест', icon='map',
                                  on_click=lambda: self.game_dialog.show_spravochnik_dialog(game_data,
                                                                                            'obplace', game_ui=self,
                                                                                            game_id=current_room_id)).classes(
                            'text-lg bg-blue-500 text-white')

                        # Кнопка: Обвинить жителя
                        ui.button('Обвинить жителя', icon='report_problem',
                                  on_click=self.game_dialog.show_accuse_dialog).classes(
                            'text-lg bg-purple-600 text-white')

                        # Кнопка выхода из игры (красная)
                        ui.button('Выйти из игры', icon='exit_to_app',
                                  on_click=lambda: self.game_room_management.leave_game(self)).classes(
                            'text-lg bg-red-500 text-white')
        else:
            if self.timer:
                self.timer.cancel()
                self.timer = None

            # Проверяем наличие необходимых данных для отображения завершенной игры
            if not game_data.get('isCulprit') or not game_data['isCulprit'].get('name') or not game_data[
                'isCulprit'].get('endText'):
                with self.game_container:
                    with ui.card().classes(
                            'w-full max-w-lg mx-auto mt-6 p-6 shadow-lg bg-gray-100 dark:bg-gray-800 rounded-2xl'):
                        ui.label(f'🎉 Игра с ID "{current_room_id}" завершена!').classes(
                            'text-center text-green-600 dark:text-green-400 text-lg font-semibold')

                        ui.label(f'Данные о виновном отсутствуют').classes(
                            'text-center text-gray-800 dark:text-white text-base font-medium mt-4')

                        self.game_room_management.update_user_game_state(app.storage.user.get('user_id'), None)
                        self.game_room_management.remove_user_from_room(app.storage.user.get('user_id'),
                                                                        current_room_id)
                        app.storage.user.update({'game_state_id': None})

                        ui.button("Вернуться назад", on_click=lambda: self.show_game_interface).classes(
                            'mt-6 bg-blue-600 hover:bg-blue-700 text-white text-lg w-full rounded-lg py-2')
                return

            self.log_service.add_log(
                level='GAME',
                message=f"Показывание интерфейса для законченной игры",
                user_id=user_id,
                action="SHOW_FINISHED_GAME",
                metadata={
                    "room_id": current_room_id,
                    "game_id": room_data.get('game_id'),
                    "culprit": game_data['isCulprit']['name'],
                    "moves": room_data['move']
                }
            )

            with self.game_container:
                with ui.card().classes(
                        'w-full max-w-lg mx-auto mt-6 p-6 shadow-lg bg-gray-100 dark:bg-gray-800 rounded-2xl'):
                    ui.label(f'🎉 Игра с ID "{current_room_id}" завершена!').classes(
                        'text-center text-green-600 dark:text-green-400 text-lg font-semibold')

                    # Получаем данные о виновном и количестве ходов
                    culprit_name = game_data['isCulprit']['name']
                    turns_taken = room_data['move']
                    endText = game_data['isCulprit']['endText']

                    ui.label(f'🔍 Виновный: {culprit_name}').classes(
                        'text-center text-gray-800 dark:text-white text-base font-medium mt-4')

                    ui.markdown(endText).classes(
                        'whitespace-pre-wrap text-center text-gray-600 dark:text-gray-300 mb-6'
                    )

                    ui.label(f'⏱ Количество ходов: {turns_taken}').classes(
                        'text-center text-gray-700 dark:text-gray-300 text-base mt-1')

                    self.game_room_management.update_user_game_state(app.storage.user.get('user_id'), None)
                    self.game_room_management.remove_user_from_room(app.storage.user.get('user_id'), current_room_id)
                    app.storage.user.update({'game_state_id': None})

                    ui.button("Вернуться назад", on_click=lambda: self.show_game_interface).classes(
                        'mt-6 bg-blue-600 hover:bg-blue-700 text-white text-lg w-full rounded-lg py-2')
            return

    def check_tooltip(self, room_id):
        """Проверяет и добавляет подсказку, если она доступна для текущего хода"""
        room_data = self.game_room_management.get_game_state(room_id)
        if not room_data or 'game_id' not in room_data:
            return

        game_data = self.game_state_service.get_game_state(room_data['game_id'])
        if not game_data:
            return

        tooltip = game_data.get('tooltip', {})

        # Важно: преобразуем номер хода в строку для сравнения с ключами
        current_move = str(room_data.get('move', 0))

        # Проверяем, есть ли подсказка для текущего хода
        if current_move in tooltip:
            # Получаем ID локации подсказки
            tooltip_location_id = tooltip[current_move]

            # Проверяем, не добавлена ли уже эта подсказка
            location_history = room_data.get('location_history', [])
            tooltip_already_added = any(
                loc.get('id') == tooltip_location_id and loc.get('is_tooltip', False)
                for loc in location_history
            )

            if not tooltip_already_added:
                # Добавляем подсказку в историю, указывая что это tooltip (важно!)
                success = self.game_room_management.add_location_to_history(room_id, tooltip_location_id, tooltip=True)

                if success:
                    self.log_service.add_log(
                        level='GAME',
                        message=f"Подсказка была добавлена для хода {current_move}",
                        user_id=app.storage.user.get('user_id'),
                        action="TOOLTIP_ADDED",
                        metadata={"room_id": room_id, "move": current_move, "tooltip_location": tooltip_location_id}
                    )

                    # Обновляем интерфейс для отображения подсказки
                    self.refresh_game_data(room_id)
                    self.show_game_interface

    def travel_to_location(self, room_id, location_id):
        """Логика перемещения в новую локацию"""
        user_id = app.storage.user.get('user_id')

        if not location_id:
            ui.notify('Укажите ID места', color='warning')
            self.log_service.add_log(
                level='GAME',
                action='ERROR',
                message="Попытка поездки с пустым Айди места",
                user_id=user_id,
                metadata={"room_id": room_id}
            )
            return

        room_data = self.game_room_management.get_game_state(room_id)
        if not room_data or 'game_id' not in room_data:
            ui.notify('Ошибка: данные комнаты недоступны', color='negative')
            return

        game_data = self.game_state_service.get_game_state(room_data['game_id'])
        if not game_data:
            ui.notify('Ошибка: данные игры недоступны', color='negative')
            return

        spravochnik = game_data.get('spravochnik', {})

        # Проверяем, существует ли место
        if (location_id not in game_data.get('place', {})
                and location_id not in ['112102', '440321', '220123']
                and location_id not in spravochnik.get('obplace', {})
                and location_id not in spravochnik.get('gosplace', {})
                and location_id not in spravochnik.get('people', {})
                and location_id not in spravochnik.get('extplace', {})):
            # Используем increment_move из game_room_management вместо прямого обновления
            ui.notify(f'Место с ID {location_id} не найдено', color='negative')

            self.log_service.add_log(
                level='GAME',
                action='ERROR',
                message=f"Локация не найдена: {location_id}",
                user_id=user_id,
                metadata={"room_id": room_id, "game_id": room_data.get('game_id')}
            )
            return
        for location in room_data.get('location_history'):
            if location_id == location['id']:
                self.game_room_management.location_visited(room_id, location_id, status=True)
                ui.notify('Вы уже посещали это место ранее. Локация открыта в истории перемещений.',
                          color='warning',
                          icon='history')
                self.log_service.add_log(
                    level='GAME',
                    action='LOCATION_REVISIT',
                    message=f"Пользователь повторно открыл ранее посещенную локацию: {location_id}",
                    user_id=user_id,
                    metadata={
                        "room_id": room_id,
                        "game_id": room_data.get('game_id'),
                        "location_id": location_id
                    }
                )
                self.show_game_interface
                return
        # Используем метод из game_room_management
        success = self.game_room_management.add_location_to_history(room_id, location_id)

        if success:
            ui.notify(f'Вы переместились в локацию {location_id}', color='positive')
            self.log_service.add_log(
                level='GAME',
                message=f"Пользователь успешно переместился в локацию: {location_id}",
                user_id=user_id,
                action="TRAVEL_SUCCESS",
                metadata={"room_id": room_id, "game_id": room_data.get('game_id'), "location_id": location_id}
            )

            # Обновляем данные игры
            self.refresh_game_data(room_id)
            self.user_service.increment_user_moves(user_id)
            # Обновляем только игровой интерфейс
            self.show_game_interface
        else:
            ui.notify('Ошибка при перемещении', color='negative')

            self.log_service.add_error_log(
                error_message="Ошибка при перемещении",
                user_id=user_id,
                metadata={"room_id": room_id, "location_id": location_id}
            )
        self.check_tooltip(room_id)

    def accuse_suspect(self, room_id, suspect_id):
        """Обвинить подозреваемого"""
        user_id = app.storage.user.get('user_id')

        room_data = self.game_room_management.get_game_state(room_id)
        if not room_data or 'game_id' not in room_data:
            ui.notify('Ошибка: данные комнаты недоступны', color='negative')
            return

        game_data = self.game_state_service.get_game_state(room_data['game_id'])
        if not game_data:
            ui.notify('Ошибка: данные игры недоступны', color='negative')
            return

        culprit = game_data.get('isCulprit', {})
        culprit_id = culprit.get('id', '')
        culprit_parts = [part.strip() for part in culprit_id.split() if part.strip()]

        # Используем метод из game_room_management
        if self.game_room_management.accuse_suspect(room_id, suspect_id):
            # Используем метод из game_room_management для завершения игры
            self.game_room_management.finishing_game(room_id)

            # Корректируем сообщение об успехе в зависимости от количества виновных
            if len(culprit_parts) > 1:
                ui.notify('✅ Отличная работа! Вы раскрыли дело и нашли всех виновных!', color='emerald')
            else:
                ui.notify('✅ Отличная работа! Вы раскрыли дело и нашли виновного!', color='emerald')
            self.user_service.increment_users_completed_games(room_data)
            self.log_service.add_log(
                level='GAME',
                message=f"Пользователь раскрыл дело и нашел виновных: {culprit.get('name', 'Неизвестно')}",
                user_id=user_id,
                action="ACCUSE_CORRECT",
                metadata={
                    "room_id": room_id,
                    "game_id": room_data['game_id'],
                    "suspect_id": suspect_id,
                    "moves": room_data.get('move', 0) + 1
                }
            )
        else:
            # Проверяем, указал ли пользователь правильное количество подозреваемых
            suspect_parts = [part.strip() for part in suspect_id.split() if part.strip()]

            if len(suspect_parts) < len(culprit_parts):
                ui.notify('❌ Увы, вы нашли не всех виновных! Попробуйте ещё раз.', color='rose')
            elif len(suspect_parts) > len(culprit_parts):
                ui.notify('❌ Увы, вы обвинили слишком много людей! Попробуйте ещё раз.', color='rose')
            else:
                ui.notify('❌ Увы, это не те люди! Попробуйте ещё раз.', color='rose')

            self.log_service.add_log(
                level='GAME',
                message=f"Пользователь неправильно предположил {suspect_id}",
                user_id=user_id,
                action="ACCUSE_INCORRECT",
                metadata={
                    "room_id": room_id,
                    "game_id": room_data['game_id'],
                    "suspect_id": suspect_id,
                    "actual_culprit": culprit.get('id', 'Неизвестно')
                }
            )

        # Используем метод из game_room_management
        self.game_room_management.increment_move(room_id)
        self.check_tooltip(room_id)
        self.show_game_interface

    # Вспомогательная функция для проверки существования игры
    def game_id_exists(self, room_id):
        """Проверяет существование комнаты по ID через GameRoomManagement"""
        if not room_id:
            return False

        # Используем метод room_exists из GameRoomManagement
        return self.game_room_management.room_exists(room_id)