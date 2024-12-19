from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

# Инициализация приложения
app = Flask(__name__)
app.secret_key = 'mysecretkey'

# Подключение к базе данных MySQL
db_config = {
    'user': 'root',
    'password': '25102004',
    'host': 'localhost',
    'database': 'pitomnik'
}
db_connection = mysql.connector.connect(**db_config)
cursor = db_connection.cursor()

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Функция user_loader для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user_id=user[0], name_=user[1], email=user[2], role=user[4], password_hash=user[3])
    return None

# Класс пользователя
class User(UserMixin):
    def __init__(self, user_id, name_, email, role, password_hash):
        self.user_id = user_id
        self.name_ = name_
        self.email = email
        self.role = role
        self.password_hash = password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)

# Главная страница
@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cursor.execute("SELECT * FROM user WHERE name_ = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):  # Проверяем пароль
            if user[4] == role:  # Проверка роли
                user_obj = User(user_id=user[0], name_=user[1], email=user[2], role=user[4], password_hash=user[3])
                login_user(user_obj)
                if user[4] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Роль не совпадает с данными пользователя', 'danger')
                return redirect(url_for('login'))

        else:
            flash('Неверный логин или пароль', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        role = request.form['role']

        if password != password_confirm:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))

        cursor.execute("SELECT * FROM user WHERE name_ = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Пользователь с таким именем уже существует!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO user (name_, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                       (username, email, hashed_password, role))
        db_connection.commit()

        flash('Вы успешно зарегистрировались! Теперь можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Страница для пользователей
@app.route('/user/dashboard', methods=['GET'])
@login_required
def user_dashboard():
    # Получаем параметры фильтрации из GET-запроса
    age = request.args.get('age', type=int)
    age_status = request.args.get('age_status')

    # Строим базовый SQL запрос
    query = "SELECT * FROM pet WHERE adoption_status = 'Не усыновлен'"
    params = []

    # Добавляем условия фильтрации
    if age:
        query += " AND age = %s"
        params.append(age)

    if age_status:
        query += " AND age_status = %s"
        params.append(age_status)

    # Выполняем запрос с фильтрами
    cursor.execute(query, tuple(params))
    pets = cursor.fetchall()

    return render_template('user_dashboard.html', pets=pets)


@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    # Получаем все заявки пользователя с информацией о питомце
    cursor.execute("""
        SELECT bid.bid_id, bid.bid_info, bid.user_id, bid.pet_id, pet.adoption_status 
        FROM bid 
        JOIN pet ON bid.pet_id = pet.pet_id
        WHERE bid.user_id = %s
    """, (current_user.user_id,))
    bids = cursor.fetchall()

    if request.method == 'POST':
        # Обработка кнопки "Одобрить"
        if 'approve_bid' in request.form:
            bid_id = request.form.get('approve_bid')

            # Получаем pet_id из заявки
            cursor.execute("SELECT pet_id FROM bid WHERE bid_id = %s", (bid_id,))
            pet_id_row = cursor.fetchone()
            if pet_id_row:
                pet_id = pet_id_row[0]
                try:
                    # Меняем статус питомца на "Усыновлен"
                    cursor.execute("UPDATE pet SET adoption_status = 'Усыновлен' WHERE pet_id = %s", (pet_id,))
                    db_connection.commit()
                    flash('Заявка успешно одобрена!', 'success')
                except Exception as e:
                    db_connection.rollback()
                    flash(f'Ошибка при одобрении заявки: {e}', 'danger')

        # Обработка отмены заявки
        if 'bid_id' in request.form:
            bid_id = request.form.get('bid_id')

            # Получаем pet_id из заявки
            cursor.execute("SELECT pet_id FROM bid WHERE bid_id = %s", (bid_id,))
            pet_id_row = cursor.fetchone()
            if pet_id_row:
                pet_id = pet_id_row[0]
                try:
                    # Удаляем заявку
                    cursor.execute("DELETE FROM bid WHERE bid_id = %s", (bid_id,))
                    # Возвращаем статус питомца на "Не усыновлен"
                    cursor.execute("UPDATE pet SET adoption_status = 'Не усыновлен' WHERE pet_id = %s", (pet_id,))
                    db_connection.commit()
                    flash('Заявка успешно отменена!', 'success')
                except Exception as e:
                    db_connection.rollback()
                    flash(f'Ошибка при отмене заявки: {e}', 'danger')

        return redirect('/user/profile')

    return render_template('user_profile.html', bids=bids)




@app.route('/admin/dashboard')
def admin_dashboard():
    # Подключаемся к базе данных
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Получаем список питомцев
    cursor.execute("SELECT * FROM pet")
    pets = cursor.fetchall()

    # Логирование полученных данных
    print(pets)

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html', pets=pets)


# Удаление питомца
@app.route('/admin/delete_pet/<int:pet_id>', methods=['POST'])
@login_required
def delete_pet(pet_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('index'))

    try:
        # 1. Удаляем все заявки на питомца из таблицы bid
        cursor.execute("DELETE FROM bid WHERE pet_id = %s", (pet_id,))
        db_connection.commit()
        print(f"Удалено заявок для питомца с pet_id {pet_id}")

        # 2. Теперь удаляем питомца из таблицы pet
        cursor.execute("DELETE FROM pet WHERE pet_id = %s", (pet_id,))
        db_connection.commit()
        flash('Питомец успешно удалён!', 'success')
        print(f"Питомец с pet_id {pet_id} удалён.")

    except Exception as e:
        db_connection.rollback()  # Откат транзакции в случае ошибки
        flash(f'Ошибка при удалении питомца: {e}', 'danger')
        print(f"Ошибка при удалении питомца с pet_id {pet_id}: {e}")

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add_pet', methods=['GET', 'POST'])
@login_required
def add_pet():
    if request.method == 'POST':
        # Получаем данные из формы
        pet_info = request.form['pet_info']
        age = request.form['age']
        age_status = request.form['age_status']
        medical_record = request.form['medical_record']
        adoption_status = request.form['adoption_status']

        # Подключение к базе данных и добавление нового питомца
        try:
            cursor.execute(
                """
                INSERT INTO pet (pet_info, age, age_status, medical_record, adoption_status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (pet_info, age, age_status, medical_record, adoption_status)
            )
            db_connection.commit()

            # Получаем ID добавленного питомца
            pet_id = cursor.lastrowid

            # Информация о документе
            pet_doc_info = "Первичный документ о питомце"

            # Устанавливаем doctor_id = 1
            doctor_id = 1

            # Вызов процедуры для добавления документа
            cursor.execute(
                "CALL add_pet_document(%s, %s, %s, %s)",
                (pet_id, current_user.user_id, doctor_id, pet_doc_info)
            )
            db_connection.commit()

            flash('Питомец и документ успешно добавлены!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f"Ошибка при добавлении данных: {e}", "danger")

    return render_template('add_pet.html')






# Редактирование питомца
@app.route('/admin/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM pet WHERE pet_id = %s", (pet_id,))
    pet = cursor.fetchone()

    if request.method == 'POST':
        pet_info = request.form['pet_info']
        medical_record = request.form['medical_record']
        adoption_status = request.form['adoption_status']

        cursor.execute("UPDATE pet SET pet_info = %s, medical_record = %s, adoption_status = %s WHERE pet_id = %s",
                       (pet_info, medical_record, adoption_status, pet_id))
        db_connection.commit()
        flash('Информация о питомце успешно обновлена!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_pet.html', pet=pet)


@app.route('/pet/document/<int:pet_id>')
@login_required
def view_pet_document(pet_id):
    try:
        # Получение данных о питомце
        cursor.execute("SELECT * FROM pet WHERE pet_id = %s", (pet_id,))
        pet = cursor.fetchone()

        # Проверяем, существует ли питомец
        if pet is None:
            flash('Питомец не найден!', 'danger')
            return redirect(url_for('user_dashboard'))

        # Получение данных о документе питомца
        cursor.execute("SELECT * FROM pet_document WHERE pet_id = %s", (pet_id,))
        pet_document = cursor.fetchone()

        # Передаем данные питомца и его документа в шаблон
        return render_template('view_pet_document.html', pet=pet, pet_document=pet_document)

    except Exception as e:
        flash(f'Ошибка при просмотре документа: {e}', 'danger')
        return redirect(url_for('user_dashboard'))


# Маршрут для усыновления питомца
# Маршрут для подачи заявки на усыновление питомца
@app.route('/adopt_pet/<int:pet_id>', methods=['POST'])
@login_required
def adopt_pet(pet_id):
    # Проверка доступности питомца
    cursor.execute("SELECT adoption_status FROM pet WHERE pet_id = %s", (pet_id,))
    result = cursor.fetchall()

    # Если результат пустой, питомец не найден
    if not result:
        flash('Питомец не найден!', 'danger')
        return redirect(url_for('user_dashboard'))

    # Если найдено несколько записей с одинаковым pet_id
    if len(result) > 1:
        flash('Ошибка: найдено несколько питомцев с одинаковым ID!', 'danger')
        return redirect(url_for('user_dashboard'))

    # Получаем статус питомца
    pet_status = result[0][0]

    # Проверка, если питомец уже усыновлен
    if pet_status == 'Усыновлен':
        flash('Этот питомец уже усыновлен!', 'danger')
        return redirect(url_for('user_dashboard'))

    # Если питомец доступен, отправляем заявку
    try:
        cursor.execute(
            "INSERT INTO bid (bid_info, user_id, pet_id) VALUES (%s, %s, %s)",
            (f"Заявление на усыновление питомца ID {pet_id}", current_user.user_id, pet_id)
        )
        cursor.execute(
            "UPDATE pet SET adoption_status = 'Заявка подана' WHERE pet_id = %s",
            (pet_id,)
        )
        db_connection.commit()
        flash('Заявка на усыновление успешно подана!', 'success')
    except mysql.connector.Error as e:
        db_connection.rollback()
        flash(f"Ошибка при подаче заявки: {e}", 'danger')

    return redirect(url_for('user_dashboard'))



def is_pet_available(pet_id):
    try:
        # Запрос для получения статуса питомца
        cursor.execute("SELECT adoption_status FROM pet WHERE pet_id = %s", (pet_id,))
        result = cursor.fetchone()

        # Проверяем, если питомец найден и его статус
        if result is not None:
            adoption_status = result[0]
            if adoption_status == "Усыновлен":
                return False
            else:
                return True
        else:
            print(f"Питомец с ID {pet_id} не найден.")
            return False

    except mysql.connector.Error as err:
        print(f"Ошибка: {err}")
        return False




@app.route('/admin/bids', methods=['GET'])
def view_bids():
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM bid")
    bids = cursor.fetchall()
    cursor.close()
    return render_template('bids.html', bids=bids)


@app.route('/admin/bids', methods=['POST'])
def consider_bid():
    bid_id = request.form['bid_id']
    pet_id = request.form['pet_id']
    action = request.form['action']
    print(bid_id, pet_id, action) # не забыть удалить

    if action == 'accept':
        status = 'Усыновлен'
    else:
        status = 'Не усыновлен'

    cursor.execute("UPDATE pet SET adoption_status = %s WHERE pet_id = %s", (status, pet_id))
    cursor.execute("DELETE FROM adoption_document WHERE bid_id = %s", (bid_id,))
    cursor.execute("DELETE FROM bid WHERE bid_id = %s", (bid_id,))
    db_connection.commit()

    return redirect('/admin/bids')


@app.route('/admin/supplies')
def view_supplies():
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM supply")
    supplies = cursor.fetchall()
    cursor.close()
    return render_template('supplies.html', supplies=supplies)


@app.route('/admin/add_supply', methods=['GET', 'POST'])
@login_required
def add_supply():
    if request.method == 'POST':
        medicines_id = request.form['medicines_id']
        count = request.form['count']
        supply_info = request.form['supply_info']
        type_of_supply = request.form['type_of_supply']
        date_ = request.form['date_']
        supplier_id = request.form['supplier_id']

        # Добавление новой поставки
        try:
            cursor.execute("""
                INSERT INTO supply (supplier_id, medicines_id, supply_info, type_of_supply, date_, count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (supplier_id, medicines_id, supply_info, type_of_supply, date_, count))
            db_connection.commit()
            flash("Поставка успешно добавлена!", "success")
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f"Ошибка при добавлении поставки: {e}", "danger")

        return redirect(url_for('view_medicines'))

    # Получение списка лекарств для выбора
    cursor.execute("SELECT medicines_id, purpose FROM medicines")
    medicines = cursor.fetchall()
    return render_template('add_supply.html', medicines=medicines)


@app.route('/admin/add_procedure', methods=['GET', 'POST'])
@login_required
def add_procedure():
    if request.method == 'POST':
        pet_id = request.form['pet_id']
        medicines_id = request.form['medicines_id']
        date_ = request.form['date_']
        info_procedure = request.form['info_procedure']

        # Adding a new procedure
        try:
            cursor.execute("""
                INSERT INTO procedures (pet_id, medicines_id, date_, info_procedure)
                VALUES (%s, %s, %s, %s)
            """, (pet_id, medicines_id, date_, info_procedure))
            db_connection.commit()
            flash("Процедура успешно добавлена!", "success")
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f"Ошибка при добавлении процедуры: {e}", "danger")

        return redirect(url_for('view_procedures'))

    # Fetch the list of medicines for the form
    cursor.execute("SELECT medicines_id, purpose FROM medicines")
    medicines = cursor.fetchall()
    return render_template('add_procedure.html', medicines=medicines)



@app.route('/admin/medicines')
def view_medicines():
    # Подключение к базе данных для получения списка лекарств
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM medicines")
    medicines = cursor.fetchall()
    cursor.close()
    return render_template('medicines.html', medicines=medicines)


@app.route('/admin/procedures')
def view_procedures():
    # Подключение к базе данных для получения списка процедур
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM procedures")
    procedures = cursor.fetchall()
    cursor.close()
    return render_template('procedures.html', procedures=procedures)

@app.route('/admin/edit_procedure/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_procedure(id):
    cursor = db_connection.cursor()

    if request.method == 'POST':
        pet_id = request.form['pet_id']
        medicines_id = request.form['medicines_id']
        date_ = request.form['date_']
        info_procedure = request.form['info_procedure']

        # Update the procedure
        try:
            cursor.execute("""
                UPDATE procedures
                SET pet_id = %s, medicines_id = %s, date_ = %s, info_procedure = %s
                WHERE procedure_id = %s  -- Using the correct primary key column
            """, (pet_id, medicines_id, date_, info_procedure, id))
            db_connection.commit()
            flash("Процедура успешно обновлена!", "success")
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f"Ошибка при обновлении процедуры: {e}", "danger")

        return redirect(url_for('view_procedures'))

    # Fetch the procedure data based on the correct column name (procedure_id)
    cursor.execute("SELECT * FROM procedures WHERE procedure_id = %s", (id,))
    procedure = cursor.fetchone()

    # Fetch the list of medicines for selection
    cursor.execute("SELECT medicines_id, purpose FROM medicines")
    medicines = cursor.fetchall()

    return render_template('edit_procedure.html', procedure=procedure, medicines=medicines)


@app.route('/admin/delete_procedure/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_procedure(id):
    cursor = db_connection.cursor()

    try:
        # Use the correct column name 'procedure_id' instead of 'id'
        cursor.execute("DELETE FROM procedures WHERE procedure_id = %s", (id,))
        db_connection.commit()
        flash("Процедура успешно удалена!", "success")
    except mysql.connector.Error as e:
        db_connection.rollback()
        flash(f"Ошибка при удалении процедуры: {e}", "danger")

    return redirect(url_for('view_procedures'))


@app.route('/admin/edit_medicine/<int:medicine_id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(medicine_id):
    # Получение текущих данных о лекарстве
    cursor.execute("SELECT * FROM medicines WHERE medicines_id = %s", (medicine_id,))
    medicine = cursor.fetchone()

    if not medicine:
        flash('Лекарство не найдено', 'danger')
        return redirect(url_for('view_medicines'))

    if request.method == 'POST':
        # Получение новых данных из формы
        new_count = request.form['count']
        new_purpose = request.form['purpose']

        try:
            # Обновление данных в таблице medicines
            cursor.execute("""
                UPDATE medicines
                SET count = %s, purpose = %s
                WHERE medicines_id = %s
            """, (new_count, new_purpose, medicine_id))
            db_connection.commit()
            flash('Лекарство успешно обновлено!', 'success')
            return redirect(url_for('view_medicines'))
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f'Ошибка при обновлении лекарства: {e}', 'danger')

    return render_template('edit_medicine.html', medicine=medicine)


@app.route('/admin/delete_medicine/<int:medicine_id>', methods=['GET'])
@login_required
def delete_medicine(medicine_id):
    cursor = db_connection.cursor()

    try:
        # Проверяем, сколько единиц лекарства осталось перед удалением
        cursor.execute("SELECT count FROM medicines WHERE medicines_id = %s", (medicine_id,))
        result = cursor.fetchone()

        # Debugging: Print out the result to check the count of the medicine
        print(f"Данные перед удалением: {result}")

        if result is None:
            flash("Лекарство не найдено!", "danger")
            return redirect(url_for('view_medicines'))

        # Удаление всех записей из таблицы supply, связанных с данным лекарством
        cursor.execute("DELETE FROM supply WHERE medicines_id = %s", (medicine_id,))
        db_connection.commit()

        # Check how many rows were deleted
        print(f"Rows deleted from supply: {cursor.rowcount}")

        # Попытка удалить лекарство
        cursor.execute("DELETE FROM medicines WHERE medicines_id = %s", (medicine_id,))
        db_connection.commit()

        # Check how many rows were deleted
        print(f"Rows deleted from medicines: {cursor.rowcount}")

        flash('Лекарство успешно удалено!', 'success')
    except mysql.connector.Error as e:
        db_connection.rollback()
        flash(f'Ошибка при удалении лекарства: {e}', 'danger')
        print(f"Ошибка: {e}")

    # Перенаправляем пользователя назад
    return redirect(url_for('view_medicines'))




@app.route('/admin/edit_supply/<int:supply_id>', methods=['GET', 'POST'])
@login_required
def edit_supply(supply_id):
    if request.method == 'GET':
        # Получаем текущую информацию о поставке
        cursor.execute("SELECT * FROM supply WHERE supply_id = %s", (supply_id,))
        supply = cursor.fetchone()

        # Если поставка не найдена, перенаправляем
        if not supply:
            flash('Поставка не найдена.', 'danger')
            return redirect(url_for('view_supplies'))

        # Передаем данные в форму
        return render_template('edit_supply.html', supply=supply)

    elif request.method == 'POST':
        # Получаем данные из формы
        supplier_id = request.form['supplier_id']
        medicines_id = request.form['medicines_id']
        supply_info = request.form['supply_info']
        type_of_supply = request.form['type_of_supply']
        date_ = request.form['date_']
        count = request.form['count']

        try:
            # Обновляем запись в базе данных
            cursor.execute("""
                UPDATE supply
                SET supplier_id = %s, medicines_id = %s, supply_info = %s, type_of_supply = %s, date_ = %s, count = %s
                WHERE supply_id = %s
            """, (supplier_id, medicines_id, supply_info, type_of_supply, date_, count, supply_id))
            db_connection.commit()
            flash('Поставка успешно обновлена!', 'success')
            return redirect(url_for('view_supplies'))
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f'Ошибка при обновлении поставки: {e}', 'danger')
            return redirect(url_for('view_supplies'))


@app.route('/admin/delete_supply/<int:supply_id>', methods=['GET'])
@login_required
def delete_supply(supply_id):
    try:
        # Удаляем поставку из базы данных по ID
        cursor.execute("DELETE FROM supply WHERE supply_id = %s", (supply_id,))
        db_connection.commit()
        flash('Поставка успешно удалена!', 'success')
    except mysql.connector.Error as e:
        db_connection.rollback()
        flash(f'Ошибка при удалении поставки: {e}', 'danger')

    # Перенаправляем на страницу со списком поставок после удаления
    return redirect(url_for('view_supplies'))

@app.route('/admin/documents', methods=['GET', 'POST'])
@login_required
def manage_documents():
    # Получаем все документы из базы данных
    try:
        cursor.execute("SELECT * FROM pet_document")
        documents = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Ошибка при получении данных: {e}", "danger")
        documents = []

    return render_template('document_management.html', documents=documents)


@app.route('/admin/delete_document/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    try:
        # Получаем ID питомца, связанного с документом
        cursor.execute("SELECT pet_id FROM pet_document WHERE pet_document_id = %s", (document_id,))
        result = cursor.fetchone()
        if result:
            pet_id = result[0]

            # Удаляем документ
            cursor.execute("DELETE FROM pet_document WHERE pet_document_id = %s", (document_id,))
            # Удаляем питомца
            cursor.execute("DELETE FROM pet WHERE id = %s", (pet_id,))
            db_connection.commit()

            flash('Документ и питомец успешно удалены!', 'success')
        else:
            flash('Документ не найден.', 'danger')
    except mysql.connector.Error as e:
        db_connection.rollback()
        flash(f"Ошибка при удалении данных: {e}", "danger")

    return redirect(url_for('manage_documents'))


@app.route('/admin/edit_document/<int:document_id>', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    # Получаем документ по ID из базы данных
    cursor.execute("SELECT * FROM pet_document WHERE pet_document_id = %s", (document_id,))
    document = cursor.fetchone()
    if not document:
        flash("Документ не найден", "danger")
        return redirect(url_for('manage_documents'))

    if request.method == 'POST':
        # Получаем новые данные из формы
        new_admin_id = request.form['admin_id']
        new_doctor_id = request.form['doctor_id']
        new_pet_doc_info = request.form['pet_doc_info']
        new_pet_id = request.form['pet_id']

        # Обновляем данные в БД
        try:
            cursor.execute(
                """
                UPDATE pet_document 
                SET admin_id = %s, doctor_id = %s, pet_doc_info = %s, pet_id = %s 
                WHERE pet_document_id = %s
                """,
                (new_admin_id, new_doctor_id, new_pet_doc_info, new_pet_id, document_id)
            )
            db_connection.commit()
            flash('Документ успешно обновлен!', 'success')
            return redirect(url_for('manage_documents'))
        except mysql.connector.Error as e:
            db_connection.rollback()
            flash(f"Ошибка при обновлении данных: {e}", "danger")

    # Если метод GET, отобразим форму редактирования с текущими данными
    return render_template(
        'edit_document.html',
        document=document
    )


# Страница выхода
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
