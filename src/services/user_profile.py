from nicegui import ui
from src.services.user_service import UserService
from src.services.log_services import LogService
from src.services.password_service import PasswordService


class UserProfile:
    def __init__(self):
        self.user_service = UserService()
        self.log_service = LogService()
        self.password_service = PasswordService()
        self.current_user_id = None

        self.name = None
        self.surname = None
        self.username = None
        self.password_button = None  # Кнопка для сброса пароля вместо поля ввода
        self.avatar_image = None
        self.avatar = None
        self.button = None
        self.is_editing = False

    def show_profile_ui(self, user_id):
        self.current_user_id = user_id
        user = self.get_user_by_id(user_id)
        if not user:
            ui.label('Пользователь не найден').classes('text-center text-2xl mt-10')
            self.log_service.add_error_log(f"Попытка просмотра несуществующего профиля: {user_id}")
            return

        with ui.row().classes('w-full justify-center'):
            with ui.card().classes('p-8 shadow-xl w-96 flex flex-col items-center gap-4 bg-gray-100 dark:bg-gray-800'):
                self.avatar_image = ui.image(user['avatar']).classes('rounded-full w-32 h-32 object-cover')
                self.display_view_mode(user_id)

    def toggle_edit_mode(self, user_id):
        # Если мы находимся в режиме редактирования и пытаемся выйти из него
        if self.is_editing:
            # Проверяем валидность данных перед выходом из режима редактирования
            if not self.validate_and_save():
                # Если валидация не прошла, остаемся в режиме редактирования
                return

        # Переключаем режим только если валидация прошла успешно или мы входим в режим редактирования
        self.is_editing = not self.is_editing

        # Логируем переключение режима
        action = "EDIT_MODE_ENTER" if self.is_editing else "EDIT_MODE_EXIT"
        message = "Пользователь вошел в режим редактирования профиля" if self.is_editing else "Пользователь вышел из режима редактирования профиля"
        self.log_service.add_user_action_log(
            user_id=user_id,
            action=action,
            message=message
        )

        # Очищаем текущие элементы UI
        if hasattr(self, 'name') and self.name:
            self.name.delete()
        if hasattr(self, 'surname') and self.surname:
            self.surname.delete()
        if hasattr(self, 'username') and self.username:
            self.username.delete()
        if hasattr(self, 'password_button') and self.password_button:
            self.password_button.delete()
        if hasattr(self, 'avatar') and self.avatar:
            self.avatar.delete()
        if hasattr(self, 'button') and self.button:
            self.button.delete()

        # Создаем элементы в соответствии с режимом
        if self.is_editing:
            self.display_edit_mode(user_id)
        else:
            self.display_view_mode(user_id)

    def display_view_mode(self, user_id):
        user = self.get_user_by_id(user_id)
        if not user:
            ui.label('Пользователь не найден').classes('text-center text-2xl mt-10')
            self.log_service.add_error_log(f"Ошибка при отображении пользователя: {user_id} не найден")
            return
        self.avatar = ui.label(f"Аватар: {user['avatar']}").classes('w-full overflow-hidden')
        self.name = ui.label(f"Имя: {user['name']}").classes('w-full')
        self.surname = ui.label(f"Фамилия: {user['surname']}").classes('w-full')
        self.username = ui.label(f"Логин: {user['username']}").classes('w-full')

        # Добавляем email, если он есть
        if 'email' in user and user['email']:
            ui.label(f"Email: {user['email']}").classes('w-full')

        # Вместо поля пароля - кнопка для сброса пароля
        self.password_button = ui.button('Сбросить пароль',
                                         on_click=lambda: self.show_reset_password_dialog(user_id)).classes(
            'w-full bg-blue-500 text-white mb-2')

        self.button = ui.button('Изменить профиль', on_click=lambda: self.toggle_edit_mode(user_id)).classes('w-full')

    def display_edit_mode(self, user_id):
        user = self.get_user_by_id(user_id)
        if not user:
            ui.label('Пользователь не найден').classes('text-center text-2xl mt-10')
            self.log_service.add_error_log(f"Ошибка при отображении формы редактирования: {user_id} не найден")
            return
        self.avatar = ui.input('Ссылка на аватар', value=user['avatar']).classes('w-full')
        self.name = ui.input('Имя', value=user['name']).classes('w-full')
        self.surname = ui.input('Фамилия', value=user['surname']).classes('w-full')
        self.username = ui.input('Логин', value=user['username']).classes('w-full')

        # Добавляем поле для email
        self.email = ui.input('Email', value=user.get('email', '')).classes('w-full')

        # Вместо поля для пароля - кнопка сброса пароля
        self.password_button = ui.button('Сбросить пароль',
                                         on_click=lambda: self.show_reset_password_dialog(user_id)).classes(
            'w-full bg-blue-500 text-white mb-2')

        self.button = ui.button('Сохранить', color='green', on_click=lambda: self.toggle_edit_mode(user_id)).classes(
            'w-full')

    def show_reset_password_dialog(self, user_id):
        """Показывает диалог для сброса пароля"""
        user = self.get_user_by_id(user_id)

        if not user:
            ui.notify("❌ Пользователь не найден!", color="red")
            return

        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(f'Сброс пароля для {user["username"]}').classes('text-xl font-bold mb-4')

            # Поля для паролей
            new_password = ui.input('Новый пароль', password=True, password_toggle_button=True).classes('w-full mb-4')
            confirm_password = ui.input('Подтвердите пароль', password=True, password_toggle_button=True).classes(
                'w-full mb-4')
            status_label = ui.label('').classes('text-red-500 mt-2')

            def reset_password():
                # Валидация пароля
                if len(new_password.value) < 8:
                    status_label.text = 'Пароль должен содержать не менее 8 символов'
                    return

                if new_password.value != confirm_password.value:
                    status_label.text = 'Пароли не совпадают'
                    return

                # Проверка сложности пароля
                password_check = self.password_service.check_password_strength(new_password.value)
                if not password_check["valid"]:
                    status_label.text = '\n'.join(password_check["errors"])
                    return

                # Хешируем и сохраняем новый пароль
                hashed_password = self.password_service.hash_password(new_password.value)
                if self.user_service.edit_user(user_id, {'password': hashed_password}):
                    self.log_service.add_log(
                        level="INFO",
                        message=f"Пароль пользователя {user['username']} был сброшен",
                        user_id=user_id,
                        action="PASSWORD_RESET"
                    )
                    ui.notify("✅ Пароль успешно сброшен!", color="green")
                    dialog.close()
                else:
                    status_label.text = 'Ошибка при сбросе пароля'

            with ui.row().classes('w-full justify-between mt-4'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300')
                ui.button('Сохранить', on_click=reset_password).classes('bg-blue-500 text-white')

        dialog.open()

    def validate_and_save(self):
        """Проверяет данные и сохраняет их, если они валидны.
        Возвращает True, если данные валидны и сохранены, иначе False."""
        if not hasattr(self, 'name') or not hasattr(self.name, 'value'):
            self.log_service.add_error_log("Ошибка валидации: отсутствуют обязательные поля",
                                           user_id=self.current_user_id)
            return False

        new_data = {
            'name': self.name.value.strip(),
            'surname': self.surname.value.strip(),
            'username': self.username.value.strip(),
            'avatar': self.avatar.value.strip(),
            'email': self.email.value.strip() if hasattr(self, 'email') else ''
        }

        # Проверяем обязательные поля на заполненность
        if not new_data['name'] or not new_data['surname'] or not new_data['username']:
            ui.notify("Пожалуйста заполните все обязательные поля", color='red')
            self.log_service.add_error_log(
                "Ошибка валидации: не все поля заполнены",
                user_id=self.current_user_id,
                metadata={"empty_fields": [k for k, v in new_data.items() if not v and k != 'email']}
            )
            return False

        # Проверяем уникальность имени пользователя
        # Нужно проверить, что имя пользователя не занято другими пользователями
        current_user = self.get_user_by_id(self.current_user_id)
        if new_data['username'] != current_user['username'] and not self.user_service.is_username_available(
                new_data['username']):
            ui.notify("Такое имя пользователя уже занято", color='red')
            self.log_service.add_error_log(
                "Ошибка валидации: имя пользователя уже занято",
                user_id=self.current_user_id,
                metadata={"attempted_username": new_data['username']}
            )
            return False

        # Определяем, какие поля изменились для логирования
        changed_fields = {
            field: new_data[field]
            for field in new_data
            if field != 'password' and new_data[field] != current_user.get(field, '')
        }

        # Если все проверки пройдены, сохраняем данные
        success = self.user_service.edit_user(self.current_user_id, new_data)
        if success:
            ui.notify('Профиль успешно обновлён!', color='green')
            self.avatar_image.source = self.avatar.value

            # Логируем успешное обновление
            self.log_service.add_user_action_log(
                user_id=self.current_user_id,
                action="PROFILE_UPDATE",
                message=f"Пользователь успешно обновил свой профиль",
                metadata={
                    "changed_fields": list(changed_fields.keys()),
                    "changes": changed_fields
                }
            )
            return True
        else:
            ui.notify('Ошибка при обновлении профиля', color='negative')
            self.log_service.add_error_log(
                "Ошибка сохранения профиля",
                user_id=self.current_user_id
            )
            return False

    def get_user_by_id(self, user_id):
        users = self.user_service.load_data()
        for user in users:
            if user['id'] == user_id:
                return user

        # Логируем попытку получения несуществующего пользователя
        self.log_service.add_error_log(
            f"Попытка получения данных несуществующего пользователя с ID: {user_id}"
        )
        return None