import os
from pathlib import Path
from nicegui import app, ui
from src.services.login import AuthMiddleware
from src.ui.user_ui import UserUI
from dotenv import load_dotenv
#from src.services.registration import Registration
#from src.services.user_service import UserService


if __name__ in {"__main__", "__mp_main__"}:
    # Set up static files directory
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)

    img_dir = static_dir / 'img'
    img_dir.mkdir(exist_ok=True)

    app.add_static_files('/static', str(static_dir))

    # Rest of your existing code
    app.add_middleware(AuthMiddleware)
    load_dotenv()

@ui.page('/')
def main_page() -> None:
    UserUI()

ui.add_body_html("""
            <style>
            body {
                background-image: url('https://i.imgur.com/bhI92Pw.png');
                background-size: cover;
                background-attachment: fixed;
                background-position: center;
            }
            </style>
            """)
ui.run(storage_secret='natka.zajk79', on_air='Exb5blKCa7JaTEOd', port=1234)
