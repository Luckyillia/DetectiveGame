from nicegui import ui
import random
import string
import time
from datetime import datetime

from src.services.user_service import UserService
from src.services.log_services import LogService
from src.services.password_service import PasswordService
from src.game.game_room_management import GameRoomManagement


class UserProfile:
    """Улучшенный профиль пользователя с расширенной функциональностью и современным интерфейсом."""

    def __init__(self):
        # Инициализация сервисов
        self.user_service = UserService()
        self.log_service = LogService()
        self.password_service = PasswordService()
        self.game_room_management = GameRoomManagement()

        # Данные пользователя
        self.current_user_id = None
        self.current_user = None

        # Компоненты интерфейса
        self.profile_container = None
        self.form_elements = {}
        self.stat_cards = {}
        self.is_editing = False

    def show_profile_ui(self, user_id):
        """Главная точка входа для отображения интерфейса профиля пользователя."""
        self.current_user_id = user_id
        self.current_user = self.get_user_by_id(user_id)

        if not self.current_user:
            ui.label('Пользователь не найден').classes('text-center text-2xl mt-10 text-red-500')
            self.log_service.add_error_log(f"Попытка просмотра несуществующего профиля: {user_id}")
            return

        # Создаем основной контейнер
        self.profile_container = ui.card().classes('w-full max-w-4xl mx-auto p-0 shadow-xl rounded-xl overflow-hidden')

        with self.profile_container:
            # Заголовок с фоном - увеличенная высота
            with ui.element('div').classes('relative w-full h-40 bg-blue-600 dark:bg-blue-800'):
                # Фоновый узор
                ui.element('div').style(
                    'position: absolute; inset: 0; background-image: url(https://www.transparenttextures.com/patterns/cubes.png); opacity: 0.2')

                # Информация о пользователе - перемещена выше в заголовке
                with ui.element('div').classes('absolute top-4 left-4 p-4'):
                    ui.label(f'{self.current_user["name"]} {self.current_user["surname"]}').classes(
                        'text-2xl font-bold text-white')

            # Контейнер для аватара и кнопки действия
            with ui.row().classes('w-full justify-between px-6'):
                # Контейнер аватара - позиционирован с перекрытием заголовка
                with ui.element('div').classes('relative -mt-16'):
                    with ui.card().classes('h-32 w-32 overflow-hidden p-0 shadow-lg'):
                        self.avatar_image = ui.image(self.current_user['avatar']).classes('h-full w-full object-cover')

                # Кнопка редактирования/сохранения - позиционирована вверху справа, без перекрытия
                self.action_button = ui.button(
                    'Редактировать',
                    on_click=lambda: self.toggle_edit_mode()
                ).props('icon=edit outline').classes('mt-2')

            # Создаем вкладки для разных разделов
            with ui.tabs().classes('w-full') as tabs:
                profile_tab = ui.tab('Профиль')
                activity_tab = ui.tab('Активность')
                stats_tab = ui.tab('Статистика')

            # Контейнер для панелей вкладок
            with ui.tab_panels(tabs, value=profile_tab).classes('w-full p-4 pt-0'):
                # Вкладка профиля
                with ui.tab_panel(profile_tab):
                    self.create_profile_panel()

                # Вкладка активности
                with ui.tab_panel(activity_tab):
                    self.create_activity_panel()

                # Вкладка статистики
                with ui.tab_panel(stats_tab):
                    self.create_stats_panel()

    def create_profile_panel(self):
        """Создает панель основной информации профиля."""
        # Форма профиля
        with ui.card().classes('w-full p-4'):
            ui.label('Информация профиля').classes('text-lg font-bold mb-2')

            # Создаем группу полей формы
            with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 gap-4'):
                # Поля информации пользователя - используем словарь для хранения ссылок
                self.form_elements['username'] = self.create_form_field(
                    'Имя пользователя',
                    self.current_user['username'],
                    icon='person'
                )

                self.form_elements['name'] = self.create_form_field(
                    'Имя',
                    self.current_user['name'],
                    icon='badge'
                )

                self.form_elements['surname'] = self.create_form_field(
                    'Фамилия',
                    self.current_user['surname'],
                    icon='family_restroom'
                )

                self.form_elements['email'] = self.create_form_field(
                    'Email',
                    self.current_user.get('email', ''),
                    icon='email',
                    placeholder='Не указан'
                )

            # URL аватара как отдельное поле
            with ui.element('div').classes('mt-4'):
                self.form_elements['avatar'] = self.create_form_field(
                    'URL аватара',
                    self.current_user['avatar'],
                    icon='image',
                    full_width=True
                )

                # Кнопка генератора аватара (видима только в режиме редактирования)
                self.form_elements['avatar_generator'] = ui.button(
                    'Сгенерировать новый аватар',
                    on_click=self.generate_new_avatar,
                    icon='autorenew'
                ).props('outline size=sm').classes('mt-2 hidden')

            # Раздел сброса пароля
            with ui.card().classes('w-full mt-4 p-4 bg-gray-50 dark:bg-gray-800'):
                ui.label('Безопасность').classes('text-lg font-bold mb-2')

                ui.button(
                    'Сбросить пароль',
                    on_click=lambda: self.show_reset_password_dialog(self.current_user_id),
                    icon='lock_reset'
                ).props('color=primary').classes('mt-2')

    def create_activity_panel(self):
        """Создает панель активности пользователя с историей входов."""
        with ui.card().classes('w-full p-4'):
            ui.label('История активности').classes('text-lg font-bold mb-2')

            # Получаем логи активности пользователя
            activities = self.get_user_activity(self.current_user_id)

            if not activities:
                ui.label('История активности пуста').classes('text-gray-500 italic my-4')
                return

            # Создаем список логов
            with ui.scroll_area().classes('max-h-96 w-full'):
                for activity in activities:
                    action = activity.get('action', 'ACTION')
                    timestamp = activity.get('datetime', 'UNKNOWN TIME')
                    message = activity.get('message', 'Нет подробностей')

                    # Получаем соответствующие иконку и цвет для типа активности
                    icon, color = self.get_activity_icon_and_color(action)

                    with ui.card().classes(f'mb-2 border-l-4 {color}'):
                        with ui.row().classes('items-center p-2'):
                            ui.icon(icon).classes(f'text-lg {color.replace("border", "text")}')
                            with ui.column().classes('ml-2'):
                                ui.label(message).classes('font-medium')
                                ui.label(timestamp).classes('text-xs text-gray-500')

    def create_stats_panel(self):
        """Создает панель статистики с игровыми показателями пользователя."""
        with ui.card().classes('w-full p-4'):
            # Заголовок и кнопка обновления в одной строке
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Игровая статистика').classes('text-lg font-bold')

                # Кнопка обновления статистики
                refresh_button = ui.button('Обновить', icon='refresh', on_click=self.refresh_stats_panel)
                refresh_button.props('flat color=primary size=sm')

            # Контейнер для карточек статистики, который будем обновлять
            self.stats_container = ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4')

            # Контейнер для таблицы недавних игр
            self.recent_games_container = ui.element('div').classes('w-full')

            # Первичное заполнение данными
            self.refresh_stats_panel()

    def refresh_stats_panel(self):
        """Обновляет данные на панели статистики."""
        # Получаем актуальную статистику из user_service
        user_stats = self.user_service.get_user_stats(self.current_user_id)

        # Очищаем контейнеры перед обновлением
        self.stats_container.clear()
        self.recent_games_container.clear()

        if not user_stats:
            with self.stats_container:
                ui.label('Статистика недоступна').classes('text-gray-500 italic my-4')
            return

        # Создаем карточки статистики
        with self.stats_container:
            # Количество посещенных комнат
            rooms_visited = user_stats.get('rooms_visited', 0)
            self.create_stat_card('Игр сыграно', rooms_visited, 'casino', 'blue')

            # Общее количество ходов
            total_moves = user_stats.get('total_moves', 0)
            self.create_stat_card('Сделано ходов', total_moves, 'directions_walk', 'green')

            # Завершенные дела
            games_completed = user_stats.get('games_completed', 0)
            self.create_stat_card('Дел раскрыто', games_completed, 'psychology', 'purple')

            # Последняя активность
            last_active = self.get_last_active_time(self.current_user_id)
            self.create_stat_card('Последняя активность', last_active, 'schedule', 'amber')

        # Обновляем раздел недавних игр
        with self.recent_games_container:
            ui.separator().classes('my-4')
            ui.label('Недавние игры').classes('text-lg font-bold mb-2')

            # Получаем список недавних игр на основе данных пользователя
            recent_games = self.get_recent_games_from_stats(user_stats)

            if recent_games:
                # Создаем таблицу для недавних игр
                columns = [
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                    {'name': 'date', 'label': 'Дата', 'field': 'date', 'align': 'left'},
                    {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center'},
                    {'name': 'moves', 'label': 'Ходов', 'field': 'moves', 'align': 'center'},
                ]

                ui.table(columns=columns, rows=recent_games).classes('w-full')
            else:
                ui.label('Нет данных о недавних играх').classes('text-gray-500 italic my-4')

    def create_form_field(self, label, value, icon=None, placeholder='', full_width=False):
        """Вспомогательная функция для создания согласованных полей форм, поддерживающих режимы просмотра/редактирования."""
        with ui.element('div').classes('w-full'):
            # Строка метки с иконкой
            with ui.row().classes('items-center'):
                if icon:
                    ui.icon(icon).classes('text-blue-500 mr-2')
                ui.label(label).classes('text-sm font-medium text-gray-600 dark:text-gray-400')

            # Для режима просмотра (статический текст)
            field_view = ui.label(value if value else placeholder).classes(
                f'text-md {" text-gray-500 italic" if not value else ""} pb-1 border-b border-gray-200 dark:border-gray-700 w-full'
            )

            # Для режима редактирования (поле ввода)
            field_edit = ui.input(
                label='',
                value=value,
                placeholder=placeholder
            ).classes('w-full hidden')

            if full_width:
                field_view.classes(add='block')
                field_edit.classes(add='block')

            # Возвращаем словарь со ссылками на оба элемента для удобного переключения
            return {
                'view': field_view,
                'edit': field_edit,
                'value': value
            }

    def create_stat_card(self, title, value, icon, color):
        """Создает карточку статистики с согласованным стилем."""
        color_classes = {
            'blue': 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300',
            'green': 'bg-green-50 dark:bg-green-900 text-green-700 dark:text-green-300',
            'purple': 'bg-purple-50 dark:bg-purple-900 text-purple-700 dark:text-purple-300',
            'amber': 'bg-amber-50 dark:bg-amber-900 text-amber-700 dark:text-amber-300',
        }

        with ui.card().classes(f'p-4 {color_classes.get(color, "")}'):
            with ui.row().classes('justify-between items-center'):
                ui.label(title).classes('text-sm font-medium')
                ui.icon(icon).classes('text-xl')
            ui.label(str(value)).classes('text-2xl font-bold mt-2')

    def toggle_edit_mode(self):
        """Переключение между режимами просмотра и редактирования без пересоздания элементов."""
        self.is_editing = not self.is_editing

        # Обновляем текст и иконку кнопки
        if self.is_editing:
            self.action_button.text = 'Сохранить'
            self.action_button.props('icon=save color=primary')

            # Записываем в лог вход в режим редактирования
            self.log_service.add_user_action_log(
                user_id=self.current_user_id,
                action="EDIT_MODE_ENTER",
                message="Пользователь вошел в режим редактирования профиля"
            )

            # Показываем кнопку генератора аватара
            if 'avatar_generator' in self.form_elements:
                self.form_elements['avatar_generator'].classes(remove='hidden')
        else:
            # Если сохраняем, проверяем и обновляем
            if self.is_editing and not self.validate_and_save():
                # Если проверка не прошла, остаемся в режиме редактирования
                return

            self.action_button.text = 'Редактировать'
            self.action_button.props('icon=edit outline')

            # Записываем в лог выход из режима редактирования
            self.log_service.add_user_action_log(
                user_id=self.current_user_id,
                action="EDIT_MODE_EXIT",
                message="Пользователь вышел из режима редактирования профиля"
            )

            # Скрываем кнопку генератора аватара
            if 'avatar_generator' in self.form_elements:
                self.form_elements['avatar_generator'].classes(add='hidden')

        # Переключаем видимость полей просмотра/редактирования
        for field_name, elements in self.form_elements.items():
            if isinstance(elements, dict) and 'view' in elements and 'edit' in elements:
                view_element = elements['view']
                edit_element = elements['edit']

                if self.is_editing:
                    view_element.classes(add='hidden')
                    edit_element.classes(remove='hidden')
                else:
                    view_element.classes(remove='hidden')
                    edit_element.classes(add='hidden')

                    # Обновляем значение просмотра после редактирования (только для не-кнопок)
                    if hasattr(edit_element, 'value'):
                        if edit_element.value:
                            view_element.text = edit_element.value
                        else:
                            view_element.text = edit_element._props.get('placeholder', '')
                            view_element.classes(add='text-gray-500 italic')

    def generate_new_avatar(self):
        """Генерирует новый случайный аватар и обновляет предпросмотр."""
        chars = string.ascii_uppercase + string.digits
        new_avatar_url = f'https://robohash.org/{"".join(random.choice(chars) for _ in range(5))}'

        # Обновляем URL аватара в форме
        if 'avatar' in self.form_elements and hasattr(self.form_elements['avatar']['edit'], 'value'):
            self.form_elements['avatar']['edit'].value = new_avatar_url

        # Обновляем изображение предпросмотра аватара
        if hasattr(self, 'avatar_image'):
            self.avatar_image.source = new_avatar_url

        # Записываем обновление аватара в лог
        self.log_service.add_user_action_log(
            user_id=self.current_user_id,
            action="AVATAR_GENERATED",
            message="Пользователь сгенерировал новый аватар",
            metadata={"new_avatar_url": new_avatar_url}
        )

        # Показываем уведомление
        ui.notify('Аватар обновлен', type='positive')

    def validate_and_save(self):
        """Проверяет данные формы и сохраняет, если они действительны."""
        # Собираем обновленные данные
        new_data = {
            'name': self.form_elements['name']['edit'].value.strip(),
            'surname': self.form_elements['surname']['edit'].value.strip(),
            'username': self.form_elements['username']['edit'].value.strip(),
            'avatar': self.form_elements['avatar']['edit'].value.strip(),
            'email': self.form_elements['email']['edit'].value.strip()
        }

        # Проверка: Проверяем обязательные поля
        required_fields = ['name', 'surname', 'username']
        for field in required_fields:
            if not new_data[field]:
                ui.notify(f'Поле "{field}" не может быть пустым', type='negative')
                return False

        # Проверяем, уникально ли имя пользователя (если изменено)
        if new_data['username'] != self.current_user['username']:
            if not self.user_service.is_username_available(new_data['username']):
                ui.notify('Такое имя пользователя уже занято', type='negative')
                return False

        # Проверка email
        if new_data['email'] and not self.validate_email(new_data['email']):
            ui.notify('Некорректный формат email', type='negative')
            return False

        # Если проверка пройдена, сохраняем данные
        success = self.user_service.edit_user(self.current_user_id, new_data)

        if success:
            # Обновляем изображение аватара немедленно
            self.avatar_image.source = new_data['avatar']

            # Обновляем сохраненные данные пользователя
            self.current_user = self.get_user_by_id(self.current_user_id)

            # Определяем, какие поля были изменены для записи в лог
            changed_fields = {
                field: new_data[field]
                for field in new_data
                if new_data[field] != self.current_user.get(field, '')
            }

            # Записываем успешное обновление в лог
            self.log_service.add_user_action_log(
                user_id=self.current_user_id,
                action="PROFILE_UPDATE_SUCCESS",
                message="Профиль успешно обновлен",
                metadata={"changed_fields": list(changed_fields.keys())}
            )

            ui.notify('Профиль успешно обновлен', type='positive')
            return True
        else:
            ui.notify('Ошибка при обновлении профиля', type='negative')

            # Записываем ошибку в лог
            self.log_service.add_error_log(
                error_message="Ошибка при сохранении профиля",
                user_id=self.current_user_id
            )
            return False

    def show_reset_password_dialog(self, user_id):
        """Улучшенный диалог сброса пароля с лучшей проверкой."""
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label('Сбросить пароль').classes('text-xl font-bold mb-4')

            # Поля пароля с индикатором сложности в реальном времени
            new_password = ui.input('Новый пароль', password=True, password_toggle_button=True).classes('w-full mb-2')

            # Индикатор сложности пароля
            strength_container = ui.row().classes('w-full items-center mb-4')

            # Обновляем индикатор сложности при вводе
            def update_strength_indicator(e):
                password = e.value
                strength_container.clear()

                if not password:
                    return

                with strength_container:
                    # Получаем проверку сложности пароля
                    check = self.password_service.check_password_strength(password)
                    strength = check["strength"]

                    # Сопоставление текста сложности
                    strength_text = ["Очень слабый", "Слабый", "Средний", "Хороший", "Отличный", "Превосходный"][
                        min(5, strength)]

                    # Сопоставление цветов
                    strength_colors = ["red", "orange", "yellow", "blue", "green", "purple"]
                    color = strength_colors[min(5, strength)]

                    ui.label("Надежность: ").classes('text-xs')
                    ui.label(strength_text).classes(f'text-xs font-medium text-{color}-600')

                    # Шкала сложности
                    with ui.row().classes('w-full gap-1 ml-2'):
                        for i in range(5):
                            if i < strength:
                                ui.icon('fiber_manual_record', color=color).classes('text-xs')
                            else:
                                ui.icon('fiber_manual_record', color='grey').classes('text-xs')

            new_password.on('input', update_strength_indicator)

            confirm_password = ui.input('Подтвердите пароль', password=True, password_toggle_button=True).classes(
                'w-full mb-4')

            # Раздел требований
            with ui.expansion('Требования к паролю', icon='shield').classes('w-full mb-4'):
                with ui.element('div').classes('text-sm text-gray-600 dark:text-gray-300 pl-2 mt-2'):
                    ui.label('• Минимум 8 символов')
                    ui.label('• Содержит буквы и цифры')
                    ui.label('• Желательно специальные символы (!@#$%)')

            status_label = ui.label('').classes('text-red-500 mt-2 mb-2')

            def reset_password():
                if len(new_password.value) < 8:
                    status_label.text = 'Пароль должен содержать не менее 8 символов'
                    return

                if new_password.value != confirm_password.value:
                    status_label.text = 'Пароли не совпадают'
                    return

                # Проверяем сложность пароля
                password_check = self.password_service.check_password_strength(new_password.value)
                if not password_check["valid"]:
                    status_label.text = '\n'.join(password_check["errors"])
                    return

                # Хешируем и сохраняем новый пароль
                hashed_password = self.password_service.hash_password(new_password.value)
                if self.user_service.edit_user(user_id, {'password': hashed_password}):
                    self.log_service.add_log(
                        level="INFO",
                        message=f"Пароль успешно сброшен",
                        user_id=user_id,
                        action="PASSWORD_RESET_SUCCESS"
                    )
                    ui.notify("Пароль успешно сброшен!", type='positive')
                    dialog.close()
                else:
                    status_label.text = 'Ошибка при сбросе пароля'

            with ui.row().classes('w-full justify-between mt-4'):
                ui.button('Отмена', on_click=dialog.close).props('flat color=grey')
                ui.button('Сохранить', on_click=reset_password).props('color=primary')

        dialog.open()

    # Вспомогательные методы
    def get_user_by_id(self, user_id):
        """Получение данных пользователя по ID."""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            self.log_service.add_error_log(
                f"Попытка получения данных несуществующего пользователя с ID: {user_id}"
            )
        return user

    def validate_email(self, email):
        """Проверка формата email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_user_activity(self, user_id, limit=10):
        """Получение недавней активности пользователя из логов."""
        try:
            # Используем LogService для получения логов активности пользователя
            logs = self.log_service.db.get_logs(
                user_id=user_id,
                page=1,
                page_size=limit
            )
            return logs
        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка при получении логов активности: {str(e)}",
                user_id=user_id
            )
            return []

    def get_activity_icon_and_color(self, action):
        """Получение соответствующей иконки и цвета для типа активности."""
        action_mapping = {
            'LOGIN': ('login', 'border-green-500'),
            'LOGOUT': ('logout', 'border-gray-500'),
            'PROFILE_UPDATE': ('edit', 'border-blue-500'),
            'PASSWORD_RESET': ('lock_reset', 'border-orange-500'),
            'TRAVEL_SUCCESS': ('directions_walk', 'border-indigo-500'),
            'ACCUSE_CORRECT': ('check_circle', 'border-green-500'),
            'ACCUSE_INCORRECT': ('cancel', 'border-red-500'),
            'EDIT_MODE_ENTER': ('edit', 'border-blue-500'),
            'EDIT_MODE_EXIT': ('save', 'border-blue-500'),
        }

        return action_mapping.get(action, ('info', 'border-gray-500'))

    def get_recent_games_from_stats(self, user_stats, limit=5):
        """
        Получает список недавних игр на основе статистики пользователя.

        Args:
            user_stats (dict): Статистика пользователя
            limit (int): Максимальное количество игр для отображения

        Returns:
            list: Список недавних игр
        """
        recent_games = []

        # Используем список завершенных игр из статистики
        completed_games = user_stats.get('completed_games_list', [])

        # Получаем данные комнат для дополнительной информации
        room_data = self.game_room_management.load()

        # Собираем информацию о завершенных играх
        for game_id in completed_games:
            if game_id in room_data:
                room = room_data[game_id]
                recent_games.append({
                    'id': game_id,
                    'date': datetime.fromtimestamp(room.get('last_visited_at', 0)).strftime("%d.%m.%Y"),
                    'status': 'Завершена',
                    'moves': room.get('move', 0)
                })

        # Проверяем активные комнаты, где пользователь участвует
        rooms_list = user_stats.get('rooms_list', [])

        for room_id in rooms_list:
            # Пропускаем комнаты, которые уже есть в списке завершенных
            if room_id in completed_games:
                continue

            if room_id in room_data:
                room = room_data[room_id]
                # Добавляем только если пользователь все еще в комнате
                if self.current_user_id in room.get('users', []):
                    recent_games.append({
                        'id': room_id,
                        'date': datetime.fromtimestamp(room.get('last_visited_at', 0)).strftime("%d.%m.%Y"),
                        'status': 'В процессе',
                        'moves': room.get('move', 0)
                    })

        # Сортируем по дате (самые недавние сверху)
        recent_games.sort(key=lambda x: x['date'], reverse=True)

        # Ограничиваем количество
        return recent_games[:limit]

    def get_last_active_time(self, user_id):
        """Получение форматированного времени последней активности на основе логов."""
        try:
            logs = self.log_service.db.get_logs(
                user_id=user_id,
                page=1,
                page_size=1
            )

            if logs and logs[0].get('timestamp'):
                # Форматируем время последней активности
                last_time = datetime.fromtimestamp(logs[0].get('timestamp'))
                now = datetime.now()

                # Вычисляем разницу во времени
                diff = now - last_time

                if diff.days == 0:
                    if diff.seconds < 3600:
                        return f"{diff.seconds // 60} мин. назад"
                    else:
                        return f"{diff.seconds // 3600} ч. назад"
                elif diff.days == 1:
                    return "Вчера"
                elif diff.days < 7:
                    return f"{diff.days} дн. назад"
                else:
                    return last_time.strftime("%d.%m.%Y")

            return "Никогда"
        except Exception:
            return "Неизвестно"