from typing import Optional
import time
import json

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.services.user_service import UserService
from src.services.auth_service import AuthService
from src.services.login_security import LoginSecurity
from src.services.password_service import PasswordService
from src.services.log_services import LogService
from src.services.registration import Registration
from src.services.email_service import EmailService

from nicegui import app, ui

UNRESTRICTED_PAGE_ROUTES = {'/login', '/register', '/reset-password', '/confirm-reset'}

log_service = LogService()
auth_service = AuthService(UserService())
login_security = LoginSecurity()
password_service = PasswordService()

# Временное хранилище для кодов восстановления
# В продакшене заменить на базу данных
reset_codes = {}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Проверка сессии
        if not app.storage.user.get('authenticated', False):
            # Проверка токена в cookies
            token = request.cookies.get('auth_token')
            if token:
                user_id = auth_service.validate_token(token)
                if user_id:
                    user = UserService().get_user_by_id(user_id)
                    if user:
                        app.storage.user.update({
                            'username': user['username'],
                            'user_id': user['id'],
                            'authenticated': True,
                            'game_state_id': user.get('gameState'),
                            'dark_mode': user.get('dark_mode', True),
                            'token': token
                        })

        # Перенаправление на логин при необходимости
        if not app.storage.user.get('authenticated', False):
            if not request.url.path.startswith('/_nicegui') and request.url.path not in UNRESTRICTED_PAGE_ROUTES:
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        return await call_next(request)


@ui.page('/login')
def login(redirect_to: str = '/', error: str = None) -> Optional[RedirectResponse]:
    def try_login() -> None:
        entered_username = username.value
        entered_password = password.value
        remember = remember_me.value

        # Получаем IP клиента (для демонстрации используем локальный IP)
        client_ip = "127.0.0.1"

        # Проверяем, не заблокирован ли аккаунт
        if login_security.is_account_locked(entered_username):
            unlock_time = login_security.get_unlock_time(entered_username)
            minutes = unlock_time // 60
            seconds = unlock_time % 60
            ui.notify(
                f'Аккаунт временно заблокирован. Повторите попытку через {minutes} мин. {seconds} сек.',
                color='negative',
                timeout=5000
            )
            return

        # Поиск пользователя
        user = UserService().get_user_by_username(entered_username)

        # Проверка пароля
        if user and password_service.verify_password(user['password'], entered_password):
            # Успешный вход
            login_security.record_attempt(entered_username, client_ip, True)

            # Генерируем токен
            token = auth_service.generate_token(user['id'], remember_me=remember)

            # Обновляем сессию
            app.storage.user.update({
                'username': user['username'],
                'user_id': user['id'],
                'authenticated': True,
                'game_state_id': user.get('gameState'),
                'dark_mode': user.get('dark_mode', True),
                'token': token
            })

            # Логируем успешный вход
            log_service.add_user_action_log(
                user_id=user['id'],
                action='LOGIN_SUCCESS',
                message=f"Пользователь {entered_username} успешно вошёл в систему"
            )

            # Устанавливаем cookie с токеном, если нужно запомнить пользователя
            if remember:
                response = RedirectResponse(redirect_to)
                response.set_cookie(
                    key="auth_token",
                    value=token,
                    max_age=60 * 60 * 24 * 30,  # 30 дней
                    httponly=True
                )
                ui.navigate.to(redirect_to)
                return response

            ui.navigate.to(redirect_to)
            return
        else:
            # Неудачная попытка входа
            login_security.record_attempt(entered_username, client_ip, False)

            remaining_attempts = login_security.get_remaining_attempts(entered_username)
            if remaining_attempts > 0:
                ui.notify(f'Неверный логин или пароль. Осталось попыток: {remaining_attempts}',
                          color='negative')
            else:
                ui.notify('Аккаунт временно заблокирован из-за большого количества неудачных попыток входа.',
                          color='negative', timeout=5000)

            log_service.add_error_log(
                error_message=f"Неудачная попытка входа для логина: {entered_username}",
                action="LOGIN_FAILED",
                metadata={"entered_username": entered_username}
            )


    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')

    with ui.card().classes('absolute-center w-96'):
        ui.image("https://i.imgur.com/NyTjp3u.png").classes('w-64 mb-4')
        ui.label('Вход в систему').classes('text-xl font-bold text-center w-full my-4')

        if error:
            ui.label(error).classes('text-red-500 w-full text-center mb-4')

        username = ui.input('Логин', validation={'Введите логин': lambda val: val != ''}).classes('w-full mb-2').on(
            'keydown.enter', try_login)
        password = ui.input('Пароль', password=True, password_toggle_button=True,
                            validation={'Введите пароль': lambda val: val != ''}).classes('w-full mb-4').on(
            'keydown.enter', try_login)

        with ui.row().classes('w-full items-center justify-between mb-4'):
            remember_me = ui.checkbox('Запомнить меня').classes('ml-2')
            ui.button('Забыли пароль?', on_click=lambda: ui.navigate.to('/reset-password')).props('flat dense').classes(
                'text-blue-500')

        with ui.row().classes('w-full justify-center gap-4'):
            ui.button('Войти', on_click=try_login).props('color=primary').classes('px-6')
            ui.button('Регистрация', on_click=lambda: ui.navigate.to('/register')).props('outline').classes('px-4')

    return None


@ui.page('/logout')
def logout():
    if app.storage.user.get('authenticated', False) and app.storage.user.get('token'):
        # Отзываем токен
        auth_service.revoke_token(app.storage.user.get('token'))

        # Логируем выход
        log_service.add_user_action_log(
            user_id=app.storage.user.get('user_id'),
            action='LOGOUT',
            message=f"Пользователь {app.storage.user.get('username')} вышел из системы"
        )

    # Очищаем сессию
    app.storage.user.clear()

    # Создаем ответ с редиректом
    response = RedirectResponse('/login')

    # Удаляем cookie с токеном
    response.delete_cookie(key="auth_token")

    return response


@ui.page('/reset-password')
def reset_password():
    """Страница восстановления пароля"""
    reset_container = ui.element('div').classes('w-full max-w-md mx-auto mt-10')
    email_service = EmailService()

    def send_reset_link():
        username = reset_input.value

        if not username:
            ui.notify('Введите имя пользователя', type='warning')
            return

        # Поиск пользователя
        user = UserService().get_user_by_username(username)

        if user:
            # Проверяем наличие email
            user_email = user.get('email')
            if not user_email:
                ui.notify('Для этого аккаунта не указан email. Обратитесь к администратору.', type='negative')
                log_service.add_error_log(
                    error_message=f"Невозможно восстановить пароль: отсутствует email",
                    metadata={"username": username}
                )
                return

            # Генерируем временный код восстановления
            reset_code = password_service.generate_reset_code(6)

            # Сохраняем код в временное хранилище
            reset_codes[username] = {
                'code': reset_code,
                'expires': time.time() + 15 * 60,  # Код действителен 15 минут
                'user_id': user['id']
            }

            # Отправляем код по электронной почте
            email_sent = email_service.send_password_reset_code(user_email, username, reset_code)

            if email_sent:
                # Для тестирования можно временно оставить вывод кода
                # ui.notify(f'Для тестирования - код: {reset_code}', type='info', timeout=5000)

                # Переход к экрану ввода кода
                ui.navigate.to(f'/confirm-reset?username={username}')
            else:
                ui.notify('Ошибка отправки письма. Попробуйте позже или обратитесь к администратору.', type='negative')
        else:
            ui.notify('Пользователь не найден', type='negative')

    with reset_container:
        ui.label('Восстановление пароля').classes('text-xl font-bold text-center')
        ui.label('Введите имя пользователя для получения кода восстановления').classes('text-gray-600 mb-4 text-center')

        reset_input = ui.input('Имя пользователя').classes('w-full mb-4')

        with ui.row().classes('w-full justify-center gap-4'):
            ui.button('Отправить код', on_click=send_reset_link).classes('bg-blue-500 text-white')
            ui.button('Вернуться к входу', on_click=lambda: ui.navigate.to('/login')).classes('bg-gray-300')

@ui.page('/confirm-reset')
def confirm_reset(username: str = ''):
    ui.notify(f'Код для восстановления пароля отправлен на email', type='positive')
    reset_container = ui.element('div').classes('w-full max-w-md mx-auto mt-10')

    def confirm_reset_code():
        if not username or username not in reset_codes:
            ui.notify('Недействительный запрос восстановления', type='negative')
            ui.navigate.to('/reset-password')
            return

        reset_data = reset_codes[username]

        # Проверяем срок действия кода
        if time.time() > reset_data['expires']:
            ui.notify('Код восстановления истек. Запросите новый код.', type='negative')
            del reset_codes[username]
            ui.navigate.to('/reset-password')
            return

        # Проверяем код
        if code_input.value != reset_data['code']:
            ui.notify('Неверный код восстановления', type='negative')
            return

        # Проверяем пароль
        if len(new_password.value) < 8:
            ui.notify('Пароль должен быть не менее 8 символов', type='negative')
            return

        if new_password.value != confirm_password.value:
            ui.notify('Пароли не совпадают', type='negative')
            return

        # Проверяем сложность пароля
        password_check = password_service.check_password_strength(new_password.value)
        if not password_check["valid"]:
            ui.notify('\n'.join(password_check["errors"]), type='negative')
            return

        # Хешируем и сохраняем новый пароль
        user_id = reset_data['user_id']
        hashed_password = password_service.hash_password(new_password.value)
        UserService().edit_user(user_id, {'password': hashed_password})

        # Удаляем использованный код
        del reset_codes[username]

        # Логируем сброс пароля
        log_service.add_log(
            level="INFO",
            message=f"Пароль пользователя {username} был сброшен через процедуру восстановления",
            user_id=user_id,
            action="PASSWORD_RESET"
        )

        ui.notify('Пароль успешно изменен', type='positive')
        ui.navigate.to('/login')

    with reset_container:
        ui.label('Сброс пароля').classes('text-xl font-bold text-center')
        ui.label(f'Введите код восстановления, отправленный для пользователя {username}').classes(
            'text-gray-600 mb-4 text-center')

        code_input = ui.input('Код восстановления').classes('w-full mb-4')
        new_password = ui.input('Новый пароль', password=True).classes('w-full mb-4')
        confirm_password = ui.input('Подтвердите пароль', password=True).classes('w-full mb-4')

        with ui.row().classes('w-full justify-center gap-4'):
            ui.button('Сбросить пароль', on_click=confirm_reset_code).classes('bg-blue-500 text-white')
            ui.button('Отмена', on_click=lambda: ui.navigate.to('/login')).classes('bg-gray-300')


@ui.page('/register')
def register() -> None:
    Registration()