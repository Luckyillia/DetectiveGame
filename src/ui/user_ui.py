from venv import create

from nicegui import app, ui

from src.game.game_state_service import GameStateService
from src.game.game_ui import GameUI
from src.ui.components.user_table import UserTable
from src.services.registration import Registration
from src.services.user_service import UserService
from src.game.game import Game


class UserUI:
    def __init__(self):
        # Initialize user service and user table
        self.user_service = UserService()
        self.game_state_service = GameStateService()
        self.user_table = UserTable(self.user_service)
        self.game_ui = GameUI(self.game_state_service)
        self.menu = None
        self.chess = None
        self.game_data = {}  # Store game data at class level
        self.setup_ui()

    def setup_ui(self):
        # Create UI tabs
        with ui.tabs().classes('w-full') as tabs:
            if (app.storage.user.get('username') == 'lucky_illia'):
                one = ui.tab('Добавить пользователя')
                two = ui.tab('Список пользователей')
                three = ui.tab('Создать игру')
            four = ui.tab('Игра')

        # User info and logout button
        with ui.row().classes('w-full items-center px-4 py-2 rounded-lg flex justify-center'):
            ui.switch('Dark mode', on_change=self.switch).classes('flex-grow')
            result = ui.label().classes('mr-auto')
            ui.label(f'Привет, {app.storage.user.get("username", "")}').classes(
                'text-xl font-semibold text-primary text-center')
            ui.button(on_click=self.logout, icon='logout').props('outline round')

        # Define content for each tab
        with ui.tab_panels(tabs, value=four).classes('w-full flex justify-center items-center'):
            if app.storage.user.get('username') == 'lucky_illia':
                with ui.tab_panel(one):
                    reg = Registration(self.user_table)

                with ui.tab_panel(two):
                    self.user_table.init_table()

                with ui.tab_panel(three):
                    self.game_ui.table_game()

            else:
                ui.notify('Ты вошел не как админ', color='red')

            with ui.tab_panel(four):
                game = Game()

    def switch(self, event):
        # Toggle dark mode based on switch
        if event.value:
            ui.dark_mode().enable()
        else:
            ui.dark_mode().disable()

    def logout(self) -> None:
        app.storage.user.clear()
        ui.navigate.to('/login')