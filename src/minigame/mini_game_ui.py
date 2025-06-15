from nicegui import ui, app

from src.minigame.chameleon.chameleon_game_ui import ChameleonGameUI
from src.minigame.codenames.codenames_game_ui import CodenamesGameUI
from src.minigame.spy.spy_game_ui import SpyGameUI
from src.minigame.best_pairs.best_pairs_game_ui import BestPairsGameUI
from src.services.log.log_services import LogService


class MiniGamesUI:
    """
    UI для раздела мини-игр, включающего различные социальные и командные игры.
    """

    def __init__(self):
        self.log_service = LogService()
        self.chameleon_game_ui = ChameleonGameUI()
        self.spy_game_ui = SpyGameUI()
        self.codenames_game_ui = CodenamesGameUI()
        self.best_pairs_game_ui = BestPairsGameUI()
        self.games_container = None

    def create_mini_games_ui(self):
        """Создает главный интерфейс выбора мини-игр"""
        if hasattr(self, 'games_container') and self.games_container is not None:
            self.games_container.clear()
        else:
            self.games_container = ui.element('div').classes('w-full')

        with self.games_container:
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Мини-игры').classes('text-2xl font-bold mb-2 text-center')
                ui.label('Выберите игру из списка доступных мини-игр').classes('text-center mb-4')

                # Сетка выбора игр
                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Карточка игры "Хамелеон"
                    with ui.card().classes(
                            'p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors').on('click',
                                                                                                                self.show_chameleon_game):
                        ui.image('https://game.city/static/media/theChameleon.419b43690de24a8b2287.png').classes(
                            'w-full h-50 object-cover rounded-lg mb-2')
                        ui.label('Хамелеон (Chameleon)').classes('text-xl font-bold mb-1')
                        ui.label('Социальная игра-детектив: найди кто из игроков не знает секретное слово!').classes(
                            'text-sm')

                    # Карточка игры "Шпион"
                    with ui.card().classes(
                            'p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors').on('click',
                                                                                                                self.show_spy_game):
                        ui.image('https://i.imgur.com/hpUdvjj.png').classes('w-full h-50 object-cover rounded-lg mb-2')
                        ui.label('Шпион (Spy)').classes('text-xl font-bold mb-1')
                        ui.label('Социальная игра-детектив: найди шпиона, который не знает локацию!').classes(
                            'text-sm')

                    # Карточка игры "Кодовые имена"
                    with ui.card().classes(
                            'p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors').on(
                        'click',
                        self.show_codenames_game):
                        ui.image('https://i.imgur.com/rkXBo4O.png').classes(
                            'w-full h-50 object-cover rounded-lg mb-2')
                        ui.label('Кодовые имена (Codenames)').classes('text-xl font-bold mb-1')
                        ui.label('Командная игра на угадывание слов по подсказкам капитанов!').classes(
                            'text-sm')

                    # Карточка игры "Лучшие Пары"
                    with ui.card().classes(
                            'p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors').on(
                        'click',
                        self.show_best_pairs_game):
                        ui.image('https://i.imgur.com/wZSvkKR.png').classes(
                            'w-full h-50 object-cover rounded-lg mb-2')
                        ui.label('Лучшие Пары (Best Pairs)').classes('text-xl font-bold mb-1')
                        ui.label('Угадай, как ведущий сочетал прилагательные с существительными!').classes(
                            'text-sm')

    def show_chameleon_game(self):
        """Показывает интерфейс игры "Хамелеон" """
        # Очищаем контейнер
        if self.games_container is None:
            self.games_container = ui.element('div').classes('w-full')
        else:
            self.games_container.clear()

        # Добавляем кнопку возврата
        with self.games_container:
            with ui.row().classes('w-full mb-4'):
                ui.button('← Назад к списку игр', on_click=self.create_mini_games_ui).classes(
                    'bg-gray-200 dark:bg-gray-700')

            # Логируем выбор игры "Хамелеон"
            self.log_service.add_log(
                level="GAME",
                action="MINI_GAME_SELECT",
                message=f"Игрок выбрал мини-игру 'Хамелеон'",
                user_id=app.storage.user.get('user_id')
            )

            # Создаем контейнер для интерфейса игры
            game_content = ui.element('div').classes('w-full')

            # Показываем интерфейс игры "Хамелеон", передавая контейнер
            self.chameleon_game_ui.show_main_menu(game_content)

    def show_spy_game(self):
        """Показывает интерфейс игры "Шпион" """
        # Очищаем контейнер
        if self.games_container is None:
            self.games_container = ui.element('div').classes('w-full')
        else:
            self.games_container.clear()

        # Добавляем кнопку возврата
        with self.games_container:
            with ui.row().classes('w-full mb-4'):
                ui.button('← Назад к списку игр', on_click=self.create_mini_games_ui).classes(
                    'bg-gray-200 dark:bg-gray-700')

            # Логируем выбор игры "Шпион"
            self.log_service.add_log(
                level="GAME",
                action="MINI_GAME_SELECT",
                message=f"Игрок выбрал мини-игру 'Шпион'",
                user_id=app.storage.user.get('user_id')
            )

            # Создаем контейнер для интерфейса игры
            game_content = ui.element('div').classes('w-full')

            # Показываем интерфейс игры "Шпион", передавая контейнер
            self.spy_game_ui.show_main_menu(game_content)

    def show_codenames_game(self):
        # Очищаем контейнер
        if self.games_container is None:
            self.games_container = ui.element('div').classes('w-full')
        else:
            self.games_container.clear()
        with self.games_container:
            with ui.row().classes('w-full mb-4'):
                ui.button('← Назад к списку игр', on_click=self.create_mini_games_ui).classes(
                    'bg-gray-200 dark:bg-gray-700')

            # Логируем выбор игры "Кодовые имена"
            self.log_service.add_log(
                level="GAME",
                action="MINI_GAME_SELECT",
                message=f"Игрок выбрал мини-игру 'Кодовые имена'",
                user_id=app.storage.user.get('user_id')
            )
            game_content = ui.element('div').classes('w-full')
            self.codenames_game_ui.show_main_menu(game_content)

    def show_best_pairs_game(self):
        """Показывает интерфейс игры "Лучшие Пары" """
        # Очищаем контейнер
        if self.games_container is None:
            self.games_container = ui.element('div').classes('w-full')
        else:
            self.games_container.clear()

        # Добавляем кнопку возврата
        with self.games_container:
            with ui.row().classes('w-full mb-4'):
                ui.button('← Назад к списку игр', on_click=self.create_mini_games_ui).classes(
                    'bg-gray-200 dark:bg-gray-700')

            # Логируем выбор игры "Лучшие Пары"
            self.log_service.add_log(
                level="GAME",
                action="MINI_GAME_SELECT",
                message=f"Игрок выбрал мини-игру 'Лучшие Пары'",
                user_id=app.storage.user.get('user_id')
            )

            # Создаем контейнер для интерфейса игры
            game_content = ui.element('div').classes('w-full')

            # Показываем интерфейс игры "Лучшие Пары", передавая контейнер
            self.best_pairs_game_ui.show_main_menu(game_content)