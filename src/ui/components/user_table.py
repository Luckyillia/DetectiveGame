from nicegui import ui, events
from src.services.user.user_service import UserService
from src.services.password_service import PasswordService
from src.services.log.log_services import LogService


class UserTable:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.password_service = PasswordService()
        self.log_service = LogService()

    def init_table(self):
        self.columns = [
            {'name': 'name', 'label': 'Имя', 'field': 'name', 'align': 'center'},
            {'name': 'surname', 'label': 'Фамилия', 'field': 'surname', 'align': 'center'},
            {'name': 'username', 'label': 'Логин', 'field': 'username', 'align': 'center'},
            {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'center'},  # Added email column
            {'name': 'password', 'label': 'Пароль', 'field': 'password', 'align': 'center'},
            {'name': 'avatar', 'label': 'Аватар', 'field': 'avatar', 'align': 'center'},
            {'name': 'id', 'label': 'Действия', 'field': 'id', 'align': 'center'},
        ]
        self.table = ui.table(columns=self.columns, rows=[], row_key='id',
                              column_defaults={'align': 'center', 'headerClasses': 'uppercase text-primary',
                                               'justify-content': 'center'}).classes('w-full')
        self.table.add_slot('body', ''' 
                            <q-tr :props="props">
                                <q-td v-for="col in props.cols" :key="col.name" :props="props" 
                                      :style="col.name === 'id' ? 'width: 15%;' : 'width: 10%;'" class="text-center">

                                    <template v-if="col.name === 'avatar'">
                                        <div class="flex justify-center">
                                            <img :src="props.row.avatar" class="w-32 h-32 rounded-full">
                                        </div>
                                    </template>

                                    <template v-else-if="col.name === 'password'">
                                        <div class="flex justify-center">
                                            <q-btn color="blue" dense icon="key" size="md"
                                                @click="() => $parent.$emit('reset_password', props.row)">Сбросить пароль</q-btn>
                                        </div>
                                    </template>

                                    <template v-else-if="col.name === 'id'">
                                        <div class="flex justify-center items-center gap-4 p-2">
                                            <q-btn color="red" dense icon="delete" size="md"
                                                @click="() => $parent.$emit('delete', props.row)">Удалить</q-btn>

                                            <q-btn v-if="!props.row.editing" color="primary" dense icon="edit" size="md"
                                                @click="props.row.editing = true">Изменить</q-btn>

                                            <q-btn v-else color="green" dense icon="save" size="md"
                                                @click="() => { 
                                                    $parent.$emit('edit', props.row); 
                                                    props.row.editing = false;
                                                }">Сохранить</q-btn>
                                        </div>
                                    </template>

                                    <template v-else>
                                        <q-input v-if="props.row.editing" v-model="props.row[col.name]" dense outlined 
                                                 :label="col.label" class="w-full"/>
                                        <span v-else class="block text-center">{{ col.value }}</span>
                                    </template>

                                </q-td>
                            </q-tr>
                        ''')
        self.table.on('delete', self.delete_user)
        self.table.on('edit', self.edit_user)
        self.table.on('reset_password', self.show_reset_password_dialog)  # Add handler for password reset
        self.update_table()

    def update_table(self):
        users = self.user_service.load_data()
        self.table.rows.clear()
        for user in users:
            self.table.rows.append({
                'name': user["name"],
                'surname': user["surname"],
                'username': user["username"],
                'email': user.get("email", ""),  # Include email field with fallback to empty string
                'password': user["password"],
                'avatar': user["avatar"],
                'id': user['id']
            })
        self.table.update()

    def delete_user(self, e: events.GenericEventArguments):
        user_id = e.args.get('id')
        if self.user_service.delete_user(user_id):
            ui.notify("✅ Пользователь удален!", color="green")
        else:
            ui.notify("❌ Ошибка: Пользователь не найден!", color="red")
        self.update_table()

    def edit_user(self, e: events.GenericEventArguments):
        user_data = e.args.copy()
        user_id = user_data.pop('id')
        user_data.pop('editing')

        # Remove password from the data being updated
        if 'password' in user_data:
            user_data.pop('password')

        if self.user_service.edit_user(user_id, user_data):
            ui.notify("✅ Изменения сохранены!", color="green")
        else:
            ui.notify("❌ Ошибка: Пользователь не найден!", color="red")
        self.update_table()

    def show_reset_password_dialog(self, e: events.GenericEventArguments):
        """Show dialog for password reset"""
        user_id = e.args.get('id')
        user = self.user_service.get_user_by_id(user_id)

        if not user:
            ui.notify("❌ Пользователь не найден!", color="red")
            return

        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(f'Сброс пароля для {user["username"]}').classes('text-xl font-bold mb-4')

            # Password fields
            new_password = ui.input('Новый пароль', password=True, password_toggle_button=True).classes('w-full mb-4')
            confirm_password = ui.input('Подтвердите пароль', password=True, password_toggle_button=True).classes(
                'w-full mb-4')
            status_label = ui.label('').classes('text-red-500 mt-2')

            def reset_password():
                # Validate password
                if len(new_password.value) < 8:
                    status_label.text = 'Пароль должен содержать не менее 8 символов'
                    return

                if new_password.value != confirm_password.value:
                    status_label.text = 'Пароли не совпадают'
                    return

                # Check password strength
                password_check = self.password_service.check_password_strength(new_password.value)
                if not password_check["valid"]:
                    status_label.text = '\n'.join(password_check["errors"])
                    return

                # Hash and save new password
                hashed_password = self.password_service.hash_password(new_password.value)
                if self.user_service.edit_user(user_id, {'password': hashed_password}):
                    self.log_service.add_log(
                        level="INFO",
                        message=f"Пароль пользователя {user['username']} был сброшен администратором",
                        action="ADMIN_PASSWORD_RESET",
                        metadata={"username": user['username']}
                    )
                    ui.notify("✅ Пароль успешно сброшен!", color="green")
                    dialog.close()
                else:
                    status_label.text = 'Ошибка при сбросе пароля'

            with ui.row().classes('w-full justify-between mt-4'):
                ui.button('Отмена', on_click=dialog.close).classes('bg-gray-300')
                ui.button('Сохранить', on_click=reset_password).classes('bg-blue-500 text-white')

        dialog.open()