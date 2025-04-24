from nicegui import ui
from src.services.user_service import UserService
import random, string

from src.ui.components import user_table


class Registration:
    def __init__(self, user_table=None):
        # Initialize user service and other variables
        self.user_service = UserService()
        self.user_table = user_table
        self.avatar_url = self.generate_avatar()

        # Initialize input fields and their UI components
        self.name_input = ui.input('Имя').classes('m-auto w-64')
        self.surname_input = ui.input('Фамилия').classes('m-auto w-64')
        self.username_input = ui.input('Логин').classes('m-auto w-64')
        self.password_input = ui.input('Пароль', password=True, password_toggle_button=True).classes('m-auto w-64')

        # Initialize avatar image UI
        self.avatar_image = ui.image(self.avatar_url).classes('w-32 h-32 m-auto')

        # UI buttons
        ui.button('Сгенерировать новую аватарку', on_click=self.refresh_avatar).classes('m-auto w-64')

        # Navigation button if no user table is passed
        if not self.user_table:
            ui.button('Зарегестрироваться', on_click=self.add_user).classes('m-auto w-64')
            ui.button('Вернуться', on_click=lambda: ui.navigate.to('/login')).classes('m-auto w-64')
        else:
            ui.button('Добавить пользователя', on_click=self.add_user).classes('m-auto w-64')


    def generate_avatar(self):
        # Generate a random avatar URL using uppercase letters and digits
        chars = string.ascii_uppercase + string.digits
        return f'https://robohash.org/{"".join(random.choice(chars) for _ in range(5))}'

    def refresh_avatar(self):
        # Refresh the avatar image
        self.avatar_url = self.generate_avatar()
        self.avatar_image.set_source(self.avatar_url)

    def add_user(self, redirect_to: str = '/'):
        # Check if all required fields are filled
        if self.name_input.value and self.surname_input.value and self.username_input.value and self.password_input.value:
            # Validate the PESEL input (should be 11 digits)
            if len(self.password_input.value) >= 8:
                # Add the user using the user service
                if not self.user_service.add_user(self.name_input.value,self.surname_input.value,self.username_input.value,self.password_input.value,self.avatar_url):
                    ui.notify('Такой пользователь уже есть', color='red')
                    return

                # Clear input fields after user is added
                self.name_input.value = ''
                self.surname_input.value = ''
                self.username_input.value = ''
                self.password_input.value = ''
                self.avatar_url = self.generate_avatar()
                self.avatar_image.set_source(self.avatar_url)

                # Update user table or navigate based on the context
                if self.user_table:
                    self.user_table.update_table()
                else:
                    ui.navigate.to(redirect_to)

            else:
                # Notify if PESEL is invalid
                ui.notify('Пароль должен быть не меньше 8', color='red')
        else:
            # Notify if any required field is empty
            ui.notify('Все поля должны быть заполненые', color='red')
