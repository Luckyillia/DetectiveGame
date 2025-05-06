class User:
    def __init__(self, user_id, name, surname, username, password, avatar, email=None):
        self.id = user_id
        self.name = name
        self.surname = surname
        self.username = username
        self.password = password
        self.avatar = avatar
        self.email = email  # Добавляем поле email

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "username": self.username,
            "password": self.password,
            "avatar": self.avatar,
            "email": self.email,  # Включаем email в словарь
            "gameState": None,
            "color": None
        }