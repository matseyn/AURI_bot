import logging
# import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BotBlocked, ChatNotFound
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey, DateTime
import config
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=10, filename="py_log.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")

engine = create_engine('sqlite:///Auri.db', echo=True)
Base = declarative_base()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

start_time = datetime.now()


# Определение класса User для БД
class User(Base):
    __tablename__ = 'Users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer)
    username = Column(String)
    first_name = Column(String)
    nickname = Column(String)
    hero_class = Column(String)
    account_id = Column(String, unique=True)
    mentor_id = Column(Integer, ForeignKey('Mentors.id'))
    guild = Column(String)
    date_registration = Column(DateTime)

    __table_args__ = (UniqueConstraint('account_id'),)  # Уникальность для account_id


# Определение класса Transfers для БД
class Transfers(Base):
    __tablename__ = 'Transfers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.id'))
    admin_id = Column(Integer, ForeignKey('Admins.id'))
    transfer_date = Column(DateTime)
    reason = Column(String)


# Определение класса Mentor для БД
class Mentor(Base):
    __tablename__ = 'Mentors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mentor_account_id = Column(String)  # равен Users.account_id
    mentor_nickname = Column(String)
    mentor_interest = Column(String)
    mentor_number_of_students = Column(Integer)
    mentor_time_online = Column(String)
    mentor_characteristic = Column(String)


# Определение класса Admin для БД
class Admin(Base):
    __tablename__ = 'Admins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_account_id = Column(String)  # равен Users.account_id
    admin_nickname = Column(String)
    admin_role = Column(String)
    admin_position = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


class Registration(StatesGroup):
    nickname = State()
    hero_class = State()
    account_id = State()
    guild = State()
    user_mentor_id = State()


'''СТАРТОВЫЕ КОМАНДЫ И ФУНКЦИИ'''


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    username = message.from_user.first_name
    buttons = [
        types.KeyboardButton('\U0001F464Мой профиль'),
        types.KeyboardButton('Регистрация'),
        types.KeyboardButton('\U0001F198Помощь')
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(*buttons)

    with open('image/start_message.jpg', 'rb') as start_mess_photo:
        await message.answer_photo(
            photo=start_mess_photo,
            caption="Здрям, " + f"<b>{username}</b>" + ' - я милый бот клана <b>AURI!</b>\n' + config.start_message,
            reply_markup=markup,
            parse_mode='HTML'
        )


@dp.message_handler(lambda message: message.text == 'Регистрация')
async def registration_start(message: types.Message):
    buttons = [
        types.KeyboardButton('/reg', description='Регистрация пользователя'),
        types.KeyboardButton('/reg_mentors', description='Регистрация как Наставник'),
        types.KeyboardButton('/reg_admins', description='Регистрация Админа'),
        types.KeyboardButton('\U0001F519Назад', description='Вернуться к предыдущему меню')
    ]

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder='Выберите тип регистрации:'
    )

    markup.add(*buttons)
    with open('image/reg_user_1.jpg', 'rb') as reg_user_1_photo:
        await message.answer_photo(
            photo=reg_user_1_photo,
            caption='Выберите тип регистрации:',
            reply_markup=markup,
        )
    # await message.answer('Выберите тип регистрации:', reply_markup=markup)


@dp.message_handler(lambda message: message.text.replace('\U0001F519', '') == 'Назад')
async def back_to_start(message: types.Message):
    buttons = [
        types.KeyboardButton('\U0001F464Мой профиль'),
        types.KeyboardButton('Регистрация'),
        types.KeyboardButton('\U0001F198Помощь')
    ]

    # Создание клавиатуры
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(*buttons)

    await message.answer('Выберите действие:', reply_markup=markup)


'''КОМАНДЫ ДЛЯ РЕГИСТРАЦИИ'''


# Команда регистрации Пользователей
@dp.message_handler(commands=['reg'], state=None)
async def registration_start(message: types.Message, state: FSMContext):
    # Автоматически получаем nickname и id из информации об аккаунте telegram user
    username = message.from_user.first_name

    with open('image/reg_user_2.jpg', 'rb') as reg_user_2_photo:
        await message.answer_photo(
            photo=reg_user_2_photo,
            caption=f'Привет! {username}. Давай зарегистрируем тебя.\n'
                    'Какой у тебя Ник в игре?'
        )
    await state.set_state(Registration.nickname.state)


@dp.message_handler(state=Registration.nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text

    # Проверка на запрещённый символ "/"
    if nickname.startswith('/') and nickname != '/cancel':
        await message.reply("Неверно. Ник не должен начинаться с символа /")
        return  # Выход из обработчика, если ник неверный

    if nickname != '/cancel':
        # Сохранение ника и переход к выбору класса
        async with state.proxy() as data:
            data['nickname'] = nickname

        await message.reply("Прекрасно! Теперь выбери класс, в котором ты играешь:",
                            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                                types.KeyboardButton("\U0001FA93Берсерк"),
                                types.KeyboardButton("\u2695Друид"),
                                types.KeyboardButton("\U0001F3F9Лучница")
                            ))
        await Registration.hero_class.set()
    elif nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")

    # Устанавливаем таймаут для ответа 5 минут
    # await asyncio.sleep(300)
    # await message.reply("Извини, но ты слишком долго не отвечал. Регистрация отменена.")
    # await state.finish()


@dp.message_handler(state=Registration.hero_class)
async def process_hero_class(message: types.Message, state: FSMContext):
    if message.text not in ['\U0001FA93Берсерк', '\u2695Друид', '\U0001F3F9Лучница'] and message.text != '/cancel':
        await message.reply("Выберите класс из предложенных кнопок!")
        return

    hero_class = message.text.replace('\U0001FA93', '').replace('\u2695', '').replace('\U0001F3F9', '')

    # Проверка на запрещённый символ "/"
    if hero_class.startswith('/') and hero_class != '/cancel':
        await message.reply("Неверно. Класс не должен начинаться с символа /")
        return  # Выход из обработчика, если класс неверный

    if hero_class != '/cancel':
        # Сохраняем данные в БД
        async with state.proxy() as data:
            data['hero_class'] = hero_class
        with open('image/reg_user_3.jpg', 'rb') as reg_user_3_photo:
            await message.answer_photo(
                photo=reg_user_3_photo,
                caption='Отлично! Теперь напиши свой ID в игре:'
            )
        await Registration.account_id.set()
    elif hero_class == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")

    # Устанавливаем таймаут для ответа 5 минут
    # await asyncio.sleep(300)
    # await message.reply("Извини, но ты слишком долго не отвечал. Регистрация отменена.")
    # await state.finish()


@dp.message_handler(state=Registration.account_id)
async def process_account_id(message: types.Message, state: FSMContext):
    account_id = message.text

    # Проверка на запрещённый символ "/"
    if account_id.startswith('/') and account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный

    if not (
            account_id.isdigit() and
            len(account_id) == 11 and
            account_id[-3:] == '160' and
            int(account_id) > 0 or  # Проверка на наличие лишних нулей
            account_id == '/cancel'
    ):
        await message.reply(
            "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
        return  # Выход из обработчика, если ID неверный

    # Проверка на уникальность account_id
    existing_user = session.query(User).filter_by(account_id=message.text).first()
    if existing_user:
        await message.reply(f"Пользователь с таким ID в игре уже зарегистрирован!\n"
                            f"Его имя: {existing_user.first_name}\n"
                            f"Его tg: @{existing_user.username}\n"
                            f"Ник: {existing_user.nickname}\n"
                            f"Класс: {existing_user.hero_class}"
                            f"\n\n Регистрация завершена. Для помощи обратитесь к Администратору!")
        await state.finish()
        return

    if account_id != '/cancel':
        async with state.proxy() as data:
            data['account_id'] = account_id
            data['guild'] = 'AcademAURI'  # Автоматически задаем гильдию
            mentors = session.query(Mentor).all()
            mentor_nicknames = [mentor.mentor_nickname for mentor in mentors]

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for nickname in mentor_nicknames:
                keyboard.add(types.KeyboardButton(nickname))

            await message.reply("Выберите наставника:", reply_markup=keyboard)
            await Registration.user_mentor_id.set()
    elif account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=Registration.user_mentor_id)
async def process_user_mentor_id(message: types.Message, state: FSMContext):
    mentor_nickname = message.text

    # Проверка на запрещённый символ "/"
    if mentor_nickname.startswith('/') and mentor_nickname != '/cancel':
        await message.reply("Неверно. Никнейм наставника не должен начинаться с символа /. "
                            "Воспользуйся кнопками для выбора Наставника")
        return  # Выход из обработчика, если никнейм неверный

    mentor = session.query(Mentor).filter_by(mentor_nickname=message.text).first()
    if not mentor and mentor_nickname != '/cancel':
        await message.reply(f"Наставник с таким никнеймом не найден.\n"
                            f"Выберите наставника из списка.")
        return

    if mentor_nickname != '/cancel':
        async with state.proxy() as data:
            data['user_mentor_id'] = mentor.id

            # Получаем old_students_count из таблицы Mentors
            old_students_count = session.query(Mentor).filter_by(id=mentor.id).first().mentor_number_of_students
            selected_mentor = mentor
            # logging.info(f"У {mentor_nickname} было - {old_students_count}")  # for Debug -> delete after

            try:
                # Получаем количество подопечных до обновления
                # old_students_count = session.query(User).filter_by(mentor_id=mentor.id).count()

                # сохраняем данные в БД
                user = User(
                    telegram_id=message.from_user.id,  # id пользователя tg
                    username=message.from_user.username,  # тег пользователя tg
                    first_name=message.from_user.first_name,  # Имя аккаунта tg
                    nickname=data['nickname'],
                    hero_class=data['hero_class'],
                    account_id=data['account_id'],  # id аккаунта в игре
                    guild=data['guild'],
                    mentor_id=data['user_mentor_id'],
                    date_registration=datetime.now()
                )
                session.add(user)
                session.commit()

                logging.info(
                    f"Пользователь {message.from_user.first_name} (username:{message.from_user.username}, "
                    f"ID: {message.from_user.id}) успешно завершил регистрацию."
                )

                await message.reply("Регистрация завершена! Спасибо за информацию!")
                await state.finish()
                from script_db import update_students  # Вызов скрипта для функции обновления данных в таблице Mentors
                await update_students()  # Обновление данных таблице Mentors

                # Получаем количество подопечных после обновления
                new_students_count = session.query(Mentor).filter_by(id=selected_mentor.id).first() \
                    .mentor_number_of_students
                logging.info("Функция update_students - успешно выполнена")
                # logging.info(f"У {mentor_nickname} стало - {new_students_count}")  # for Debug -> delete after
                session.close()  # Закрываем сеанс с БД после завершения регистрации
                # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
                #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
                change_students_member_text = f"Наставник {mentor_nickname} (ID: {mentor.id}) - " \
                                              f"Количество подопечных: {old_students_count} -> {new_students_count}"
                await bot.send_message(config.id_leader, change_students_member_text)
            except Exception as e:
                logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
                session.close()  # Закрываем сеанс с БД после завершения регистрации
    elif mentor_nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


class RegistrationMentors(StatesGroup):
    mentor_nickname = State()
    mentor_account_id = State()
    mentor_interest = State()
    mentor_time_online = State()
    mentor_characteristic = State()


# Команда регистрации Наставников
@dp.message_handler(commands=['reg_mentors'], state=None)
async def registration_mentors_start(message: types.Message):
    await message.reply("Введите свой никнейм:")
    await RegistrationMentors.mentor_nickname.set()


@dp.message_handler(state=RegistrationMentors.mentor_nickname)
async def process_mentor_nickname(message: types.Message, state: FSMContext):
    mentor_nickname = message.text
    # Проверка на запрещённый символ "/"
    if mentor_nickname.startswith('/'):
        await message.reply("Неверно. Никнейм наставника не должен начинаться с символа /."
                            "\nВоспользуйся кнопками для выбора Наставника")
        return  # Выход из обработчика, если никнейм неверный

    async with state.proxy() as data:
        data['mentor_nickname'] = message.text
    await message.reply("Теперь введите ID наставника в игре:")
    await RegistrationMentors.mentor_account_id.set()


@dp.message_handler(state=RegistrationMentors.mentor_account_id)
async def process_mentor_account_id(message: types.Message, state: FSMContext):
    mentor_account_id = message.text

    # Проверка на запрещённый символ "/"
    if mentor_account_id.startswith('/'):
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный

    if not (
            mentor_account_id.isdigit() and
            len(mentor_account_id) == 11 and
            mentor_account_id[-3:] == '160' and
            int(mentor_account_id) > 0  # Проверка на наличие лишних нулей
    ):
        await message.reply(
            "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
        return  # Выход из обработчика, если ID неверный

    # Проверка на уникальность account_id
    existing_mentor = session.query(Mentor).filter_by(mentor_account_id=message.text).first()
    if existing_mentor:
        await message.reply(f"Наставник с таким ID в игре уже зарегистрирован!\n"
                            f"Его Никнейм в игре {existing_mentor.nickname}"
                            f"Введите другой ID или используйте команду /cancel для выхода из регистрации.")
        return

    async with state.proxy() as data:
        data['mentor_account_id'] = message.text

        # Запрос данных о менторе
        await message.reply("Введите интересы ментора (через запятую):")
        await RegistrationMentors.mentor_interest.set()


@dp.message_handler(state=RegistrationMentors.mentor_interest)
async def process_mentor_interest(message: types.Message, state: FSMContext):
    mentor_interest = message.text
    # Проверка на запрещённый символ "/"
    if mentor_interest.startswith('/'):
        await message.reply("Неверно. Интересы ментора не должны начинаться с символа /."
                            "\nПожалуйста, введите интересы без символа /")
        return  # Выход из обработчика, если никнейм неверный

    async with state.proxy() as data:
        data['mentor_interest'] = mentor_interest
        await message.reply("Введите время онлайн ментора (пример: 18:00-22:00):")
        await RegistrationMentors.mentor_time_online.set()


@dp.message_handler(state=RegistrationMentors.mentor_time_online)
async def process_mentor_time_online(message: types.Message, state: FSMContext):
    mentor_time_online = message.text
    # Проверка на запрещённый символ "/"
    if mentor_time_online.startswith('/'):
        await message.reply("Неверно. Время онлайн ментора не должно начинаться с символа /."
                            "\nПожалуйста, введите время онлайн без символа /")
        return  # Выход из обработчика, если никнейм неверный

    async with state.proxy() as data:
        data['mentor_time_online'] = mentor_time_online
        await message.reply("Введите краткую характеристику ментора (максимум 100 символов):")
        await RegistrationMentors.mentor_characteristic.set()


@dp.message_handler(state=RegistrationMentors.mentor_characteristic)
async def process_mentor_characteristic(message: types.Message, state: FSMContext):
    mentor_characteristic = message.text
    # Проверка на запрещённый символ "/"
    if mentor_characteristic.startswith('/'):
        await message.reply("Неверно. Характеристика ментора не должна начинаться с символа /."
                            "\nПожалуйста, введите характеристику без символа /")
        return  # Выход из обработчика, если никнейм неверный

    async with state.proxy() as data:
        data['mentor_characteristic'] = mentor_characteristic

        # Сохраняем данные в БД
        mentor = Mentor(
            mentor_account_id=data['mentor_account_id'],
            mentor_nickname=data['mentor_nickname'],
            mentor_interest=data['mentor_interest'],
            mentor_number_of_students=0,
            mentor_time_online=data['mentor_time_online'],
            mentor_characteristic=data['mentor_characteristic']
        )
        session.add(mentor)
        session.commit()
        session.close()  # Закрываем сеанс с БД после завершения регистрации

        logging.info(
            f"Наставник {message.from_user.first_name} (username:{message.from_user.username}, "
            f"ID: {message.from_user.id}) успешно завершил регистрацию"
        )

        await message.reply("Ментор успешно зарегистрирован!")
        await state.finish()


class RegistrationAdmins(StatesGroup):
    admin_nickname = State()
    admin_account_id = State()
    admin_role = State()


# Команда регистрации Офицеров гильдии
@dp.message_handler(commands=['reg_admins'], state=None)
async def registration_admins_start(message: types.Message):
    await message.reply("Введите свой никнейм:")
    await RegistrationAdmins.admin_nickname.set()


@dp.message_handler(state=RegistrationAdmins.admin_nickname)
async def process_admin_nickname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['admin_nickname'] = message.text
    await message.reply("Введите ID администратора в игре:")
    await RegistrationAdmins.admin_account_id.set()


@dp.message_handler(state=RegistrationAdmins.admin_account_id)
async def process_admin_account_id(message: types.Message, state: FSMContext):
    admin_account_id = message.text

    # Проверка на запрещённый символ "/"
    if admin_account_id.startswith('/'):
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный
    # Проверка длины и окончания ID
    if not (
            admin_account_id.isdigit() and
            len(admin_account_id) == 11 and
            admin_account_id[-3:] == '160' and
            int(admin_account_id) > 0  # Проверка на наличие лишних нулей
    ):
        await message.reply(
            "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
        return  # Выход из обработчика, если ID неверный

    #  Проверка на уникальность account_id
    existing_admin = session.query(Admin).filter_by(admin_account_id=message.text).first()
    if existing_admin:
        await message.reply(f"Администратор с таким ID в игре уже зарегистрирован!\n"
                            f"Введите другой ID или используйте команду /cancel для выхода из регистрации.")
        return

    async with state.proxy() as data:
        data['admin_account_id'] = message.text
    await message.reply("Выберите роль администратора:",
                        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                            types.KeyboardButton("Управляющий"),
                            types.KeyboardButton("Заместитель"),
                            types.KeyboardButton("\U0001F451Глава")
                        ))
    await RegistrationAdmins.admin_role.set()


@dp.message_handler(state=RegistrationAdmins.admin_role)
async def process_admin_role(message: types.Message, state: FSMContext):
    if message.text not in ['Управляющий', 'Заместитель', '\U0001F451Глава']:
        await message.reply("Выберите роль из предложенных кнопок!")
        return

    admin_role = message.text.replace('\U0001F451', '')

    if admin_role.startswith('/'):
        await message.reply("Неверно. Класс не должен начинаться с символа /")
        return  # Выход из обработчика, если класс неверный

    async with state.proxy() as data:
        data['admin_role'] = admin_role

        # Проверка количества admin_role
        existing_roles = session.query(Admin).filter_by(admin_role='Глава').all()  # Изменили фильтр на 'Глава'
        if len(existing_roles) >= 2:
            await message.reply(f"Достигнут предел количества Администраторов с ролью 'Глава'. "
                                f"Введите другую роль или используйте команду /cancel для выхода из регистрации.")
            return

            # Сохраняем данные в БД
    admin = Admin(
        admin_account_id=data['admin_account_id'],
        admin_nickname=data['admin_nickname'],
        admin_role=data['admin_role']
    )
    session.add(admin)
    session.commit()
    session.close()  # Закрываем сеанс с БД после завершения регистрации

    logging.info(
        f"Администратор {message.from_user.first_name} (username:{message.from_user.username}, "
        f"ID: {message.from_user.id}) успешно завершил регистрацию"
    )

    await message.reply("Администратор успешно зарегистрирован!")
    await state.finish()

'''КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА'''


# Команда статус
@dp.message_handler(commands=['status'])
async def handle_status(message: types.Message):
    uptime = datetime.now() - start_time
    # Вычисляем время работы в часах
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    await message.answer(f"Бот запущен: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                         f"Время работы: {hours} часов {minutes} минут {seconds} секунд")


# Команда отправки лог файла в лс
@dp.message_handler(commands=['send_logs'])
async def handle_send_logs(message: types.Message):
    try:
        # Открываем файл 'bot.log' в бинарном режиме для чтения
        with open('py_log.log', 'rb') as f:
            await bot.send_document(chat_id=message.from_user.id, document=f)
            await message.answer("Логи отправлены!")
    except FileNotFoundError:
        await message.answer("Файл логов не найден!")
    except BotBlocked:
        await message.answer("Бот заблокирован в этом чате!")
    except ChatNotFound:
        await message.answer("Чат не найден!")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
