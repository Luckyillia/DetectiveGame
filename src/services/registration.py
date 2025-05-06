from nicegui import ui
from src.services.user_service import UserService
from src.services.log_services import LogService
from src.services.password_service import PasswordService
import random
import string


class Registration:
    def __init__(self, user_table=None):
        # Initialize services
        self.user_service = UserService()
        self.log_service = LogService()
        self.password_service = PasswordService()
        self.user_table = user_table
        self.avatar_url = self.generate_avatar()

        # Determine if this is an admin adding a user or regular registration
        self.is_admin_mode = user_table is not None

        # Main container with a card
        with ui.card().classes('w-full max-w-lg mx-auto p-6 shadow-xl rounded-xl'):
            # Different title based on context
            if self.is_admin_mode:
                ui.label('Добавление пользователя').classes('text-2xl font-bold text-center w-full mb-4')
            else:
                ui.label('Регистрация аккаунта').classes('text-2xl font-bold text-center w-full mb-4')

            # Avatar section with refresh button
            with ui.column().classes('w-full items-center mb-6'):
                self.avatar_image = ui.image(self.avatar_url).classes('w-32 h-32 rounded-full object-cover mb-2')
                ui.button('Сгенерировать новую аватарку', icon='refresh', on_click=self.refresh_avatar).props(
                    'outline size=sm').classes('mb-4')

            # Form divided into two columns for name and surname
            with ui.row().classes('w-full gap-4 mb-2'):
                with ui.column().classes('flex-1'):
                    ui.label('Имя').classes('text-sm font-medium text-gray-700 dark:text-gray-300')
                    self.name_input = ui.input().classes('w-full').props('outlined')

                with ui.column().classes('flex-1'):
                    ui.label('Фамилия').classes('text-sm font-medium text-gray-700 dark:text-gray-300')
                    self.surname_input = ui.input().classes('w-full').props('outlined')

            # Username field
            ui.label('Имя пользователя').classes('text-sm font-medium text-gray-700 dark:text-gray-300 mt-2')
            self.username_input = ui.input().classes('w-full mb-2').props('outlined')

            # Password field with visibility toggle and strength indicator
            ui.label('Пароль').classes('text-sm font-medium text-gray-700 dark:text-gray-300 mt-2')
            with ui.row().classes('w-full items-center'):
                self.password_input = ui.input(password=True, password_toggle_button=True).classes('w-full').props(
                    'outlined')

            # Password strength indicator (initially hidden)
            self.password_strength_container = ui.row().classes('w-full mt-1 mb-3')

            # Password requirements in an expansion panel - similar to your game locations
            self.req_container = ui.expansion('Требования к паролю', icon='shield', group='registration').classes(
                'w-full mb-4')
            with self.req_container:
                # Initialize requirement check icons
                with ui.row().classes('items-center mt-2'):
                    self.req_length = ui.icon('close', color='red').classes('text-sm')
                    ui.label('Минимум 8 символов').classes('text-sm ml-1')
                with ui.row().classes('items-center'):
                    self.req_upper = ui.icon('close', color='red').classes('text-sm')
                    ui.label('Минимум 1 заглавная буква').classes('text-sm ml-1')
                with ui.row().classes('items-center'):
                    self.req_digit = ui.icon('close', color='red').classes('text-sm')
                    ui.label('Минимум 1 цифра').classes('text-sm ml-1')
                with ui.row().classes('items-center'):
                    self.req_special = ui.icon('close', color='red').classes('text-sm')
                    ui.label('Минимум 1 специальный символ').classes('text-sm ml-1')

            # Email field
            ui.label('Email (необязательно)').classes('text-sm font-medium text-gray-700 dark:text-gray-300')
            self.email_input = ui.input().classes('w-full mb-2').props('outlined type=email')
            ui.label('Нужен для восстановления пароля').classes('text-xs text-gray-500 italic mb-4')

            # Error message area
            self.error_label = ui.label().classes('text-red-500 text-sm mt-2 mb-2 hidden')

            # Different buttons based on whether this is admin mode or not
            with ui.row().classes('w-full justify-between mt-4'):
                if self.is_admin_mode:
                    # Admin adding a user - just needs an "Add User" button
                    ui.button('Добавить пользователя', on_click=self.add_user, icon='person_add').props(
                        'color=primary').classes('w-full')
                else:
                    # Regular user registering - needs Register and Return buttons
                    ui.button('Вернуться', on_click=lambda: ui.navigate.to('/login')).props('flat color=grey')
                    ui.button('Зарегистрироваться', on_click=self.add_user).props('color=primary').classes('px-6')

            # Setup password validation
            self.password_input.on('input', self.validate_password)

    def generate_avatar(self):
        # Generate a random avatar URL
        chars = string.ascii_uppercase + string.digits
        avatar_url = f'https://robohash.org/{"".join(random.choice(chars) for _ in range(5))}'
        return avatar_url

    def refresh_avatar(self):
        # Refresh the avatar image
        old_avatar = self.avatar_url
        self.avatar_url = self.generate_avatar()
        self.avatar_image.set_source(self.avatar_url)
        self.log_service.add_system_log(f'Аватар обновлен: {old_avatar} → {self.avatar_url}')

    def validate_password(self, e):
        """Validate password strength and update UI indicators"""
        password = e.value

        # Clear the strength indicator container
        self.password_strength_container.clear()

        if not password:
            return

        # Check password requirements
        has_min_length = len(password) >= 8
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        # Update requirement icons
        self.req_length.props(
            f'color={"green" if has_min_length else "red"} name={"check" if has_min_length else "close"}')
        self.req_upper.props(f'color={"green" if has_upper else "red"} name={"check" if has_upper else "close"}')
        self.req_digit.props(f'color={"green" if has_digit else "red"} name={"check" if has_digit else "close"}')
        self.req_special.props(f'color={"green" if has_special else "red"} name={"check" if has_special else "close"}')

        # Auto-open the requirements expansion when typing password
        self.req_container.value = True

        # Calculate strength (0-4)
        strength = sum([has_min_length, has_upper, has_digit, has_special])

        # Display strength meter
        with self.password_strength_container:
            strength_text = ""
            strength_color = ""

            if strength == 0:
                strength_text = "Очень слабый"
                strength_color = "red"
            elif strength == 1:
                strength_text = "Слабый"
                strength_color = "orange"
            elif strength == 2:
                strength_text = "Средний"
                strength_color = "yellow"
            elif strength == 3:
                strength_text = "Хороший"
                strength_color = "blue"
            else:
                strength_text = "Отличный"
                strength_color = "green"

            ui.label("Надежность: ").classes('text-xs')
            ui.label(strength_text).classes(f'text-xs font-medium text-{strength_color}-600')

            # Strength bar
            with ui.row().classes('w-full gap-1 ml-2'):
                for i in range(4):
                    if i < strength:
                        ui.icon('fiber_manual_record', color=strength_color).classes('text-xs')
                    else:
                        ui.icon('fiber_manual_record', color='grey').classes('text-xs')

    def show_error(self, message):
        """Display error message"""
        self.error_label.text = message
        self.error_label.classes('text-red-500 text-sm mt-2 mb-2')
        self.error_label.classes.remove('hidden')

    def hide_error(self):
        """Hide error message"""
        self.error_label.classes.add('hidden')

    def add_user(self, redirect_to: str = '/'):
        # Hide previous error if any
        self.hide_error()

        # Validate input fields
        if not self.name_input.value or not self.surname_input.value or not self.username_input.value or not self.password_input.value:
            self.show_error('Все обязательные поля должны быть заполнены')
            self.log_service.add_log(
                message="Ошибка регистрации: незаполненные поля",
                level="ERROR",
                action="USER_REGISTRATION"
            )
            return

        # Validate password
        if len(self.password_input.value) < 8:
            self.show_error('Пароль должен быть не менее 8 символов')
            self.log_service.add_log(
                message=f"Ошибка регистрации: короткий пароль для пользователя {self.username_input.value}",
                level="ERROR",
                action="USER_REGISTRATION",
                metadata={"username": self.username_input.value, "password_length": len(self.password_input.value)}
            )
            return

        # Check password strength
        password_check = self.password_service.check_password_strength(self.password_input.value)
        if not password_check["valid"]:
            self.show_error('\n'.join(password_check["errors"]))
            self.log_service.add_log(
                message=f"Ошибка регистрации: пароль не соответствует требованиям для пользователя {self.username_input.value}",
                level="ERROR",
                action="USER_REGISTRATION",
                metadata={"username": self.username_input.value, "password_errors": password_check["errors"]}
            )
            return

        # Try to add the user
        if not self.user_service.add_user(
                self.name_input.value.strip(),
                self.surname_input.value.strip(),
                self.username_input.value.strip(),
                self.password_input.value.strip(),
                self.avatar_url.strip(),
                self.email_input.value.strip() if self.email_input.value else None
        ):
            self.show_error('Пользователь с таким именем уже существует')
            self.log_service.add_log(
                message=f"Попытка регистрации с существующим логином: {self.username_input.value}",
                level="WARNING",
                action="USER_REGISTRATION",
                metadata={"username": self.username_input.value}
            )
            return

        # Different success messages and actions based on context
        if self.is_admin_mode:
            ui.notify('Пользователь успешно добавлен!', type='positive', position='top', close_button='OK')

            # Update the admin user table
            if self.user_table:
                self.user_table.update_table()
        else:
            ui.notify('Регистрация успешна! Пожалуйста, войдите в систему.', type='positive', position='top',
                      close_button='OK')

            # Redirect to login after successful self-registration
            ui.navigate.to(redirect_to or '/login')

        # Clear inputs and reset avatar in both cases
        self.name_input.value = ''
        self.surname_input.value = ''
        self.username_input.value = ''
        self.password_input.value = ''
        self.email_input.value = ''
        self.avatar_url = self.generate_avatar()
        self.avatar_image.set_source(self.avatar_url)