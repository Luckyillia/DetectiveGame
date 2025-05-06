from itertools import count

from nicegui import ui, app

class GameDialog:
    def __init__(self, game_ui):
        self.game_ui = game_ui

    def show_spravochnik_dialog(self, game_data, section, game_id=None, game_ui=None):
        """Показать справочник по выбранному разделу (люди, госструктуры, общественные места)"""

        section_names = {
            'people': 'Справочник жителей',
            'gosplace': 'Справочник госструктур',
            'obplace': 'Справочник общественных мест'
        }

        data = game_data.get('spravochnik', {}).get(section, {})

        with ui.dialog() as dialog, ui.card().classes('p-6 w-[700px] max-w-full'):
            ui.label(section_names.get(section, 'Справочник')).classes('text-xl font-bold mb-4')
            count = 0
            if data:
                if isinstance(data, dict):
                    for code, description in data.items():
                        count += 1
                        with ui.row().classes('w-full justify-between'):
                            ui.markdown(f"**{count}**: {description}").classes('text-base mb-2')
                            def create_click_handler_for_travel(id, loc_id):
                                return lambda: game_ui.travel_to_location(id, loc_id)
                            ui.button('Поехать', on_click=create_click_handler_for_travel(game_id, code)).classes('bg-blue-500')
                            if section == 'people':
                                def create_click_handler_for_accuse_suspect(id, loc_id):
                                    return lambda: game_ui.accuse_suspect(id, loc_id)
                                ui.button('Обвинить', on_click=create_click_handler_for_accuse_suspect(game_id, code)).classes('bg-blue-500')
                else:
                    ui.markdown(str(data)).classes('text-base')
            else:
                ui.label('Информация пока отсутствует.').classes('text-gray-500 italic')

            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-gray-300')

        dialog.open()

    def show_newspaper_dialog(self, game_data):
        with ui.dialog() as dialog, ui.card().classes('p-0 w-[600px] max-w-full overflow-hidden rounded-xl'):
            # Add paper texture background
            with ui.element('div').classes('relative w-full'):
                ui.element('div').style(
                    'position: absolute; inset: 0; background-image: url(https://i.imgur.com/fBWGcCC.jpg); '
                    'background-size: cover; opacity: 0.2; filter: sepia(0.2);'
                )

                # Content overlay
                with ui.element('div').classes('relative z-10 p-6'):
                    # Add newspaper image with animation
                    ui.image("https://i.imgur.com/WWuaQDn.png").classes('w-full mb-4 animate-fadeIn')

                    ui.label('Газета').classes('text-xl font-bold mb-4')

                    # Create styled container for newspaper text
                    with ui.element('div').classes(
                            'bg-white/70 dark:bg-gray-800/70 p-4 rounded-lg shadow-inner border border-gray-300'):
                        newspaper_text = game_data.get('gazeta', 'Газета пока пуста.')
                        ui.markdown(newspaper_text).classes('whitespace-pre-wrap text-base')

                    ui.button('Закрыть', on_click=dialog.close).classes(
                        'mt-4 bg-amber-700 hover:bg-amber-800 text-white')

        dialog.open()

    def show_document(self, additional_document):
        with ui.dialog() as dialog, ui.card().classes('p-6 w-[600px] max-w-full'):
            # Add case file background image
            ui.image("https://i.imgur.com/VrYJI87.jpeg").classes('w-full rounded-lg mb-4')

            ui.label('Вложение').classes('text-xl font-bold mb-4')
            ui.markdown(additional_document).classes('whitespace-pre-wrap text-base')
            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-gray-300')
        dialog.open()

    def show_travel_dialog(self):
        """Shows enhanced travel dialog with themed background"""
        current_room_id = app.storage.user.get('game_state_id')
        if not current_room_id:
            ui.notify('Нет активной игры', color='negative')
            return

        # Create dialog with enhanced styling
        with ui.dialog() as dialog, ui.card().classes('p-0 w-96 overflow-hidden rounded-xl'):
            # Add background image as a container with overlay
            with ui.element('div').classes('relative w-full'):
                # Background image with darkened overlay
                ui.element('div').classes('absolute inset-0 bg-black bg-opacity-60')
                ui.image("https://i.imgur.com/bSO5mPH.png").classes('w-full object-cover opacity-40')

                # Content overlay
                with ui.element('div').classes('relative z-10 p-6'):
                    ui.label('Куда хотите пойти?').classes('text-xl font-bold mb-4 text-white')

                    place_input = ui.input('Введите ID места').classes(
                        'w-full mb-4 bg-white/30 text-white placeholder-gray-300')
                    place_input.props('dark outlined')

                    def try_travel():
                        self.game_ui.travel_to_location(current_room_id, place_input.value)
                        dialog.close()

                    # Attach Enter key event
                    place_input.on('keydown.enter', try_travel)

                    with ui.row().classes('w-full justify-between'):
                        ui.button('Отмена', on_click=dialog.close).classes('bg-gray-600 text-white')
                        ui.button('Пойти', on_click=try_travel).classes('bg-blue-600 text-white')

        dialog.open()

    def show_accuse_dialog(self):
        current_room_id = app.storage.user.get('game_state_id')
        with ui.dialog() as dialog, ui.card().classes('p-0 w-96 overflow-hidden rounded-xl'):
            # Add dramatic background with detective theme
            with ui.element('div').classes('relative w-full'):
                # Background image with darkened overlay
                ui.element('div').classes('absolute inset-0 bg-black bg-opacity-70')
                ui.image("https://i.imgur.com/BLJ94Ls.jpg").classes('w-full object-cover opacity-30')

                # Content overlay
                with ui.element('div').classes('relative z-10 p-6'):
                    # Add warning icon
                    with ui.element('div').classes('flex justify-center mb-4'):
                        ui.icon('report_problem').classes('text-4xl text-red-500')

                    ui.label('Кого вы подозреваете?').classes('text-xl font-bold mb-4 text-white text-center')

                    # Add explanation text
                    ui.label('Для обвинения нескольких людей введите их ID через пробел').classes(
                        'text-sm text-gray-300 mb-2')

                    suspect_input = ui.input('Введите ID жителя').classes('w-full mb-4 bg-white/20 text-white')
                    suspect_input.props('dark outlined')
                    status_label = ui.label('').classes('text-red-500 mt-2')

                    def accuse():
                        suspect_id = suspect_input.value.strip()
                        if not suspect_id:
                            status_label.text = 'Введите ID жителя.'
                            return
                        self.game_ui.accuse_suspect(current_room_id, suspect_id)
                        dialog.close()

                    with ui.row().classes('w-full justify-between'):
                        ui.button('Отмена', on_click=dialog.close).classes('bg-gray-600 text-white')
                        ui.button('Обвинить', on_click=accuse).classes('bg-purple-600 text-white')

        dialog.open()
