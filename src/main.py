from nicegui import app, ui
from src.services.login import AuthMiddleware
from src.ui.user_ui import UserUI
#from src.services.registration import Registration

if __name__ in {"__main__", "__mp_main__"}:
    # registration = Registration()
    app.add_middleware(AuthMiddleware)


    @ui.page('/')
    def main_page() -> None:
        UserUI()

    ui.run(storage_secret='natka.zajk79', on_air='Exb5blKCa7JaTEOd', port=1234)