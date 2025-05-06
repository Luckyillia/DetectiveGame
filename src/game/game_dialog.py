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
        with ui.dialog() as dialog, ui.card().classes('p-6 w-[600px] max-w-full'):
            # Add newspaper image
            ui.image("https://i.imgur.com/WWuaQDn.png").classes('w-full mb-4')

            ui.label('Газета').classes('text-xl font-bold mb-4')

            newspaper_text = game_data.get('gazeta', 'Газета пока пуста.')
            ui.markdown(newspaper_text).classes('whitespace-pre-wrap text-base')

            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-gray-300')
        dialog.open()


    def show_document(self, additional_document):
        with ui.dialog() as dialog, ui.card().classes('p-6 w-[600px] max-w-full'):
            ui.label('Вложение').classes('text-xl font-bold mb-4')
            ui.markdown(additional_document).classes('whitespace-pre-wrap text-base')
            ui.button('Закрыть', on_click=dialog.close).classes('mt-4 bg-gray-300')
        dialog.open()

    def show_travel_dialog(self):
        """Показывает диалоговое окно для перемещения"""
        current_room_id = app.storage.user.get('game_state_id')
        if not current_room_id:
            ui.notify('Нет активной игры', color='negative')
            return

        # Создаем диалоговое окно
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            # Add a thematic image for travel
            ui.image("https://i.imgur.com/bSO5mPH.png").classes('w-full rounded-lg mb-4')

            ui.label('Куда хотите пойти?').classes('text-xl font-bold mb-4')

            place_input = ui.input('Введите ID места').classes('w-full mb-4')

            def try_travel():
                self.game_ui.travel_to_location(current_room_id, place_input.value)
                dialog.close()

            # Attach Enter key event to the input field
            place_input.on('keydown.enter', try_travel)

            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300 dark:bg-gray-700')
                ui.button('Пойти', on_click=try_travel).classes('bg-blue-500 text-white')

        dialog.open()

    def show_accuse_dialog(self):
        current_room_id = app.storage.user.get('game_state_id')
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label('Кого вы подозреваете?').classes('text-xl font-bold mb-4')

            # Добавим пояснение о вводе нескольких подозреваемых
            ui.label('Для обвинения нескольких людей введите их ID через пробел').classes('text-sm text-gray-500 mb-2')

            suspect_input = ui.input('Введите ID жителя').classes('w-full mb-4')
            status_label = ui.label('').classes('text-red-500 mt-2')

            def accuse():
                suspect_id = suspect_input.value.strip()
                if not suspect_id:
                    status_label.text = 'Введите ID жителя.'
                    return
                self.game_ui.accuse_suspect(current_room_id, suspect_id)
                dialog.close()

            with ui.row().classes('w-full justify-between'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300 dark:bg-gray-700')
                ui.button('Обвинить', on_click=accuse).classes('bg-purple-600 text-white')

        dialog.open()
