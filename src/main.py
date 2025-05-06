from nicegui import app, ui
from src.services.login import AuthMiddleware
from src.ui.user_ui import UserUI
from dotenv import load_dotenv
#from src.services.registration import Registration
#from src.services.user_service import UserService


if __name__ in {"__main__", "__mp_main__"}:
    app.add_middleware(AuthMiddleware)
    load_dotenv()

@ui.page('/')
def main_page() -> None:
    UserUI()

ui.add_body_html("""
<style>
body {
    background-image: url('https://i.imgur.com/6jHnBoh.jpeg');
    background-size: cover;
    background-attachment: fixed;
    background-position: center;
    background-repeat: no-repeat;
}
</style>
""")
ui.run(storage_secret='natka.zajk79', on_air='Exb5blKCa7JaTEOd', port=1234)
