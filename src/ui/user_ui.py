from nicegui import app, ui

from src.game.game_room_management import GameRoomManagement
from src.game.admin_game_ui import AdminGameUI
from src.game.game_room_management_ui import GameRoomManagementUI
from src.game.game_ui import GameUI
from src.minigame.mini_game_ui import MiniGamesUI
from src.services.log.log_services import LogService
from src.services.user.user_profile import UserProfile
from src.ui.components.user_table import UserTable
from src.services.registration import Registration
from src.services.user.user_service import UserService


class UserUI:
    def __init__(self):
        # Initialize user service and user table
        self.user_service = UserService()
        self.user_table = UserTable(self.user_service)
        self.user_profile = UserProfile()
        self.admin_game_ui = AdminGameUI()
        self.game_ui = GameUI()
        self.log_services = LogService()
        self.game_room_management = GameRoomManagement(game_ui=self.game_ui)
        self.game_room_management_ui = GameRoomManagementUI()
        self.mini_games_ui = MiniGamesUI()
        self.game_data = {}  # Store game data at class level
        self.switch_dark_mode(app.storage.user.get('dark_mode'))
        self.setup_ui()

    def setup_ui(self):
        # Добавить фоновое изображение для всего приложения
        ui.element('div').style(
            'position: fixed; top: 0; left: 0; width: 100%; height: 100%; '
            'background-image: url("https://i.imgur.com/wXW6uo7.png"); '
            'background-size: cover; background-position: center; z-index: -1;'
        )

        with ui.tabs().classes('w-full') as tabs:
            if (app.storage.user.get('username') == 'lucky_illia'):
                one = ui.tab('Добавить пользователя')
                two = ui.tab('Список пользователей')
                three = ui.tab('Логи')
                four = ui.tab('Управление играми')
                five = ui.tab('Управление комнатами')
            six = ui.tab('Детектив')
            eight = ui.tab('Мини игры')
            seven = ui.tab('Профиль')

        # User info and logout button
        with ui.row().classes('w-full items-center px-4 py-2 rounded-lg flex justify-center'):
            self.dark_mode = ui.switch('Dark mode', value=app.storage.user.get('dark_mode'), on_change=lambda e: self.switch_dark_mode(e.value)).classes('flex-grow')
            ui.label(f'Привет, {app.storage.user.get("username", "")}').classes('text-xl font-semibold text-primary text-center')
            ui.button(on_click=self.logout, icon='logout').props('outline round')

        # Define content for each tab
        with ui.tab_panels(tabs, value=six).classes('flex justify-center items-center'):
            if app.storage.user.get('username') == 'lucky_illia':
                with ui.tab_panel(one):
                    reg = Registration(self.user_table)
                with ui.tab_panel(two):
                    self.user_table.init_table()
                with ui.tab_panel(three):
                    self.log_services.log_interface()
                with ui.tab_panel(four):
                    self.admin_game_ui.create_ui()
                with ui.tab_panel(five):
                    self.game_room_management_ui.create_ui()

            with ui.tab_panel(six):
                self.game_ui.show_game_interface
            with ui.tab_panel(eight):
                self.mini_games_ui.create_mini_games_ui()
            with ui.tab_panel(seven):
                self.user_profile.show_profile_ui(app.storage.user.get('user_id'))
        self.check_and_request_email()


    def switch_dark_mode(self, arg):
        app.storage.user.update({'dark_mode': arg})
        if arg:
            ui.dark_mode().enable()
        else:
            ui.dark_mode().disable()

    def logout(self) -> None:
        app.storage.user.clear()
        ui.navigate.to('/login')

    def check_and_request_email(self):
        """Проверяет наличие email у пользователя и при необходимости запрашивает его"""
        user_id = app.storage.user.get('user_id')
        if not user_id:
            return  # Пользователь не авторизован

        # Получаем данные пользователя
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return  # Пользователь не найден

        # Проверяем наличие email
        if not user.get('email'):
            # Создаем диалог для запроса email
            with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
                ui.label('Добавьте email для безопасности аккаунта').classes('text-xl font-bold mb-4')
                ui.label('Email позволит восстановить доступ к аккаунту при утере пароля').classes('mb-4 text-gray-600')

                email_input = ui.input('Email').classes('w-full mb-4')
                status_label = ui.label('').classes('text-red-500 my-2')

                def validate_email(email):
                    """Проверяет корректность email"""
                    import re
                    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    return re.match(pattern, email) is not None

                def save_email():
                    email = email_input.value.strip()
                    if not email:
                        status_label.text = 'Поле email не может быть пустым'
                        return

                    if not validate_email(email):
                        status_label.text = 'Введите корректный email адрес'
                        return

                    # Сохраняем email в профиле пользователя
                    result = self.user_service.edit_user(user_id, {'email': email})
                    if result:
                        self.log_services.add_user_action_log(
                            user_id=user_id,
                            action="EMAIL_ADDED",
                            message=f"Пользователь добавил email в свой профиль",
                            metadata={"email": email}
                        )
                        ui.notify('Email успешно сохранен', type='positive')
                        dialog.close()
                    else:
                        status_label.text = 'Ошибка при сохранении email'

                with ui.row().classes('w-full justify-between mt-4'):
                    ui.button('Сделать позже', on_click=dialog.close).classes('bg-gray-300')
                    ui.button('Сохранить', on_click=save_email).classes('bg-blue-500 text-white')

            dialog.open()