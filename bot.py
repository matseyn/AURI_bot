import logging
# import asyncio
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, Message, CallbackQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton, Update
from aiogram.utils.callback_data import CallbackData
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
from aiogram.utils.exceptions import MessageNotModified
import os
import uuid

# Настройка логирования
logging.basicConfig(level=10, filename="auri_bot_log.log", filemode="w",
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
    photo = Column(String)
    mentor_id = Column(Integer, ForeignKey('Mentors.id'))
    guild = Column(String)
    date_registration = Column(DateTime)
    status = Column(String)

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
    mentor_photo = Column(String)


# Определение класса Admin для БД
class Admin(Base):
    __tablename__ = 'Admins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_account_id = Column(String)  # равен Users.account_id
    admin_nickname = Column(String)
    admin_role = Column(String)
    admin_position = Column(String)
    admin_photo = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


class Registration(StatesGroup):
    nickname = State()
    hero_class = State()
    account_id = State()
    photo = State()
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
    # await bot.set_webhook(url="https://api.telegram.org/bot7091077757:AAHfCZj7j48smo9WWhSo6Oi-JnJR47gwIY0/setwebhook",
    #                       allowed_updates=["message", "callback_query"])


# Команда показа профиля пользователя
profile_callback = CallbackData("profile", "type", "id")  # Создаем CallbackData

edit_profile_callback = CallbackData('change', 'action', 'type', 'id')


# Показываем профиль пользователей
@dp.message_handler(lambda message: message.text == '\U0001F464Мой профиль')
async def show_all_profiles(message: types.Message):
    user_id = message.from_user.id

    # Получаем ВСЕ данные пользователя из таблицы Users по telegram_id
    users = session.query(User).filter_by(telegram_id=user_id).all()

    # Создаем inline-клавиатуру
    keyboard = InlineKeyboardMarkup(row_width=1)

    # Добавляем кнопки для профилей всех пользователей с данным telegram_id
    for user in users:
        # Создайте callback_data вне цикла
        callback_data = profile_callback.new(type="user", id=user.id)
        keyboard.add(InlineKeyboardButton(
            text=f"\U0001F476Участник: {user.nickname} ({user.hero_class}, {user.status})",
            callback_data=callback_data
        ))

    # получаем ВСЕ данные пользователя из таблицы Mentors по user.account_id
    for user in users:
        account_id = user.account_id
        mentors = session.query(Mentor).filter_by(mentor_account_id=account_id).all()
        for mentor in mentors:
            keyboard.add(InlineKeyboardButton(
                text=f"\U0001F468Наставник: {mentor.mentor_nickname}",
                callback_data=profile_callback.new(type="mentor", id=mentor.id)
            ))

    # получаем ВСЕ данные пользователя из таблицы Admins по user.account_id
    for user in users:
        account_id = user.account_id
        admins = session.query(Admin).filter_by(admin_account_id=account_id).all()
        for admin in admins:
            keyboard.add(InlineKeyboardButton(
                text=f"\U0001F474Офицер: {admin.admin_nickname} ({admin.admin_role}, {admin.admin_position})",
                callback_data=profile_callback.new(type="admin", id=admin.id)
            ))

    # Если нет ни одного профиля
    if not keyboard.inline_keyboard:  # Проверяем наличие кнопок
        await message.answer("Профиль не найден.")
        return

    await message.answer("Выберите профиль:", reply_markup=keyboard)


# Показываем выбранный профиль пользователя
# @dp.callback_query_handler(profile_callback.filter(type=['user']))
@dp.callback_query_handler(profile_callback.filter())
async def show_user_profile(call: CallbackQuery, callback_data: dict):
    profile_type = callback_data["type"]
    profile_id = callback_data["id"]
    if profile_type == 'user':
        # profile_data = session.query(User).filter_by(account_id=profile_id).first()
        profile_data = session.query(User).filter_by(id=profile_id).first()
        profile_photo_user = profile_data.photo
        if profile_data:
            profile_text = f"Профиль {profile_type}:\n"

            # Создаем словарь для замены mentor_id на mentor_nickname
            field_values = {}
            for field_name in ('telegram_id', 'username', 'first_name', 'nickname', 'hero_class', 'account_id',
                               'mentor_id', 'guild', 'date_registration', 'status', 'photo'):
                field_value = getattr(profile_data, field_name, None)
                field_values[field_name] = field_value
                if field_name == 'mentor_id' and field_value is not None:
                    # Запрос данных о менторе по ID
                    mentor_data = session.query(Mentor).filter_by(id=field_value).first()
                    if mentor_data:
                        field_values['mentor_id'] = mentor_data.mentor_nickname  # Заменяем ID на никнейм
                        field_values['mentor_account_id'] = mentor_data.mentor_account_id  # Получаем mentor_account_id
                        logging.info(f"полученные field_value если есть mentor_data: {field_value}")  # del

            # Формируем текст сообщения с заменой mentor_id
            # profile_text += f"Telegram ID:  {field_values.get('telegram_id', 'Не указан')}\n"
            profile_text += f"Имя пользователя:  {field_values.get('username', 'Не указан')}\n"
            profile_text += f"Имя:  {field_values.get('first_name', 'Не указан')}\n"
            profile_text += f"Никнейм:  {field_values.get('nickname', 'Не указан')}\n"
            profile_text += f"Класс героя:  {field_values.get('hero_class', 'Не указан')}\n"
            profile_text += f"ID аккаунта:  {field_values.get('account_id', 'Не указан')}\n"
            profile_text += f"Наставник:  {field_values.get('mentor_id', 'Не указан')}\n"

            # Получение связи с наставником
            mentor_account_id = field_values.get('mentor_account_id')
            if mentor_account_id:
                mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                if mentor_user_data:
                    mentor_username = mentor_user_data.username
                    profile_text += f"Связь с наставником:  @{mentor_username}\n"
                else:
                    profile_text += f"Связь с наставником:  Не найдена\n"
            else:
                profile_text += f"Связь с наставником:  Не указана\n"

            profile_text += f"Гильдия:  {field_values.get('guild', 'Не указан')}\n"

            # Вычисление времени с момента регистрации
            registration_date = field_values.get('date_registration')
            if registration_date:
                registration_date = datetime.strptime(registration_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
                time_delta = datetime.now() - registration_date
                time_delta_str = f"{time_delta.days} дней {time_delta.seconds // 3600} часов"
                profile_text += f"Дата регистрации:  {registration_date.strftime('%d-%m-%Y')}\n"
                profile_text += f"В системе:  {time_delta_str}\n"
            else:
                profile_text += f"Дата регистрации:  Не указана\n"

            profile_text += f"Статус:  {field_values.get('status', 'Не указан')}\n"
            # Добавляем кнопки для изменения профиля
            reply_markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(
                    text="Изменить Никнейм",
                    callback_data=edit_profile_callback.new(action='nickname', type='nickname', id=profile_id)
                ),
                InlineKeyboardButton(
                    text="Изменить Фото",
                    callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                ),
                InlineKeyboardButton(
                    text="Сменить класс",
                    callback_data=edit_profile_callback.new(action='change_hero_class', type=profile_type,
                                                            id=profile_id)
                ),
                InlineKeyboardButton(
                    text="Заявка на отпуск",
                    callback_data=edit_profile_callback.new(action='vacation', type=profile_type,
                                                            id=profile_id)
                )
            )

            if profile_photo_user:
                try:
                    with open(profile_photo_user, 'rb') as user_profile_photo:
                        await call.message.answer_photo(
                            photo=user_profile_photo,
                            caption=profile_text,
                            reply_markup=reply_markup
                        )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При поиске фотографии в Users.photo для {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()
            else:
                reply_markup = InlineKeyboardMarkup(row_width=1).add(
                    InlineKeyboardButton(
                        text="Изменить Никнейм",
                        callback_data=edit_profile_callback.new(action='nickname', type='nickname', id=profile_id)
                    ),
                    InlineKeyboardButton(
                        text="Добавить Фото",
                        callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                    ),
                    InlineKeyboardButton(
                        text="Сменить класс",
                        callback_data=edit_profile_callback.new(action='change_hero_class', type=profile_type,
                                                                id=profile_id)
                    ),
                    InlineKeyboardButton(
                        text="Заявка на отпуск",
                        callback_data=edit_profile_callback.new(action='vacation', type=profile_type,
                                                                id=profile_id)
                    )
                )
                try:
                    await call.message.answer(
                        text=profile_text,
                        reply_markup=reply_markup
                    )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При отправке профиля USER {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()

    # Получаем профиль Наставника
    elif profile_type == 'mentor':
        profile_data_mentors = session.query(Mentor).filter_by(id=profile_id).first()
        if profile_data_mentors:
            profile_text_mentor = f"Профиль {profile_type}:\n"

            # Получение данных о связи с ментором
            mentor_account_id = profile_data_mentors.mentor_account_id
            if mentor_account_id:
                mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                if mentor_user_data:
                    mentor_username = mentor_user_data.username
                    profile_text_mentor += f"Связь: @{mentor_username}\n"
                else:
                    profile_text_mentor += f"Связь: Не найдена\n"
            else:
                profile_text_mentor += f"Связь: Не указана\n"

            # Вывод остальных данных о менторе
            profile_text_mentor += f"Ник: {profile_data_mentors.mentor_nickname}\n"

            # Получение класса героя ментора
            if mentor_account_id:
                mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                if mentor_user_data:
                    profile_text_mentor += f"Класс: {mentor_user_data.hero_class}\n"
                else:
                    profile_text_mentor += f"Класс: Не найдена\n"
            else:
                profile_text_mentor += f"Класс: Не указан\n"

            profile_text_mentor += f"Знает: {profile_data_mentors.mentor_interest}\n"
            profile_text_mentor += f"Количество учеников: {profile_data_mentors.mentor_number_of_students}\n"
            profile_text_mentor += f"Время онлайн: {profile_data_mentors.mentor_time_online}\n"
            profile_text_mentor += f"Характеристика: {profile_data_mentors.mentor_characteristic}\n"
            # Добавляем кнопки для изменения профиля
            reply_markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(
                    text="Изменить Фото",
                    callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                )
            )
            # Поиск фотографии ментора (если есть)
            profile_photo_mentor = profile_data_mentors.mentor_photo  # Предполагается, что у Mentor есть поле "photo"
            if profile_photo_mentor:
                try:
                    with open(profile_photo_mentor, 'rb') as mentor_profile_photo:
                        await call.message.answer_photo(
                            photo=mentor_profile_photo,
                            caption=profile_text_mentor,
                            reply_markup=reply_markup
                        )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При поиске фотографии в Mentors.mentor_photo {profile_id} "
                                  f"- произошла ошибка - [{e}]")
                    await call.answer()
            else:
                reply_markup = InlineKeyboardMarkup(row_width=1).add(
                    InlineKeyboardButton(
                        text="Добавить Фото",
                        callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                    )
                )
                try:
                    await call.message.answer(
                        text=profile_text_mentor,
                        reply_markup=reply_markup
                    )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При отправке профиля MENTOR {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()
        else:
            await call.message.answer("Профиль Наставника не найден.")
            await call.answer()

    # Получаем профиль Наставника
    elif profile_type == 'admin':
        profile_data_admin = session.query(Admin).filter_by(id=profile_id).first()
        if profile_data_admin:
            profile_text_admin = f"Профиль {profile_type}:\n"
            profile_text_admin += f"Ник: {profile_data_admin.admin_nickname}\n"
            profile_text_admin += f"Роль: {profile_data_admin.admin_role}\n"
            profile_text_admin += f"Должность: {profile_data_admin.admin_position}\n"
            # Поиск фотографии Админа (если есть)
            profile_photo_admin = profile_data_admin.admin_photo
            # Добавляем кнопки для изменения профиля
            reply_markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(
                    text="Изменить Фото",
                    callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                )
            )

            if profile_photo_admin:
                try:
                    with open(profile_photo_admin, 'rb') as admin_profile_photo:
                        await call.message.answer_photo(
                            photo=admin_profile_photo,
                            caption=profile_text_admin,
                            reply_markup=reply_markup
                        )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При поиске фотографии в Admins.admin_photo {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()
            else:
                reply_markup = InlineKeyboardMarkup(row_width=1).add(
                    InlineKeyboardButton(
                        text="Добавить Фото",
                        callback_data=edit_profile_callback.new(action='photo', type=profile_type, id=profile_id)
                    )
                )
                try:
                    await call.message.answer(
                        text=profile_text_admin,
                        reply_markup=reply_markup
                    )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При отправке профиля ADMIN {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()
        else:
            await call.message.answer("Профиль Администратора не найден.")
            await call.answer()


# объявляем состояние для изменения профиля
class UserStates(StatesGroup):
    nickname_state = State()
    photo_state = State()
    change_hero_class = State()


# обработка callback изменения профиля
@dp.callback_query_handler(edit_profile_callback.filter())
async def handle_change(call: types.CallbackQuery, callback_data: dict):
    edit_type = callback_data["type"]
    profile_id = callback_data["id"]
    logging.info(f"Тип изменения профиля: {edit_type} - id_user [{profile_id}]")
    if callback_data['action'] == 'nickname':
        await call.message.answer("Введи новый ник"
                                  "\nДля отмены введите /cancel"
                                  "\n\nВаш Nickname изменится во всех профилях автоматически")
        await dp.current_state().set_state(UserStates.nickname_state)
        # Сохраняем profile_id в контексте
        await dp.current_state().update_data(profile_id=profile_id)
        await call.answer()

    elif callback_data['action'] == 'photo':
        await call.message.answer("Загрузите новую фотографию:"
                                  "\nДля отмены введите /cancel")
        await dp.current_state().set_state(UserStates.photo_state)
        await dp.current_state().update_data(profile_id=profile_id)
        await dp.current_state().update_data(edit_type=edit_type)
        await call.answer()

    elif callback_data['action'] == 'change_hero_class':
        # await call.message.answer("Для смены класса воспользуйтесь кнопками:"
        #                           "\nДля отмены введите /cancel")
        # await dp.current_state().set_state(UserStates.change_hero_class)
        # await dp.current_state().update_data(profile_id=profile_id)
        # await call.answer()
        await call.answer("В разработке")

    elif callback_data['action'] == 'vacation':
        await call.answer("В разработке")


# Обработка состояния для изменения nickname и запись в БД
@dp.message_handler(state=UserStates.nickname_state)
async def change_nickname(message: types.Message, state: FSMContext):
    new_nickname = message.text
    # Проверяем, что предыдущее сообщение было запросом на ввод nickname
    if new_nickname.startswith('/') and new_nickname != "/cancel":
        await message.reply("Неверно. Ник не должен начинаться с символа /")
        return  # Выход из обработчика, если ник неверный
    elif new_nickname != "/cancel":
        await state.finish()
        await message.reply("Смена никнейма отменена!")
    else:
        try:
            data = await state.get_data()
            profile_id = data.get('profile_id')
            user = session.query(User).filter_by(id=profile_id).first()

            if user:
                user.nickname = new_nickname
                session.commit()
                # Обновление Nickname в table Mentors и Admins
                mentor = session.query(Mentor).filter_by(mentor_account_id=user.account_id).first()
                if mentor:
                    mentor.mentor_nickname = new_nickname
                    session.commit()

                admin = session.query(Admin).filter_by(admin_account_id=user.account_id).first()
                if admin:
                    admin.admin_nickname = new_nickname
                    session.commit()

                await state.finish()
                await message.reply(f"Ваш новый ник: {new_nickname}"
                                    f"\nДля продолжения работы нажмите /start")
            else:
                await message.reply(f"В процессе смены никнейма произошла ошибка. Обратитесь к Администратору")
        except Exception as e:
            await message.reply(f"Невозможно сменить никнейм из-за внутренней ошибки [change_nickname]"
                                f"Обратитесь к Администратору")
            logging.error(f"Ошибка при изменении user_nickname[change_nickname]  -  [{e}]")


# Обработка состояния для смены фотографии пользователя и запись в БД
@dp.message_handler(content_types=['photo', 'text'], state=UserStates.photo_state)
async def change_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    type_user = data.get('edit_type')
    profile_id = data.get('profile_id')

    if message.photo:
        # Скачиваем фотографию, если сообщение не команда и не текст
        try:
            if type_user == 'user':
                photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
                file_id = photo.file_id
                file_path = await bot.get_file(file_id)
                file_name = file_path['file_path']
                await photo.download(destination_file=file_name)

                # Определяем путь для сохранения файла
                save_path = 'photos_profile/users'
                os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

                # Скачиваем файл в заданную директорию
                await photo.download(destination_file=os.path.join(save_path, file_name))

                # Генерируем уникальное имя для файла
                unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

                # Переименовываем файл
                os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
                # Удаляем загруженный файл из \photos
                os.remove(file_name)

                user = session.query(User).filter_by(id=profile_id).first()
                if user.photo:
                    try:
                        os.remove(user.photo)
                    except FileNotFoundError:
                        pass  # Файл уже удален, игнорируем ошибку

                new_photo = os.path.join(save_path, unique_filename)
                user.photo = new_photo
                session.commit()
                await state.finish()
                await message.reply("Фото профиля участника гильдии успешно изменено")

            elif type_user == 'mentor':
                photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
                file_id = photo.file_id
                file_path = await bot.get_file(file_id)
                file_name = file_path['file_path']
                await photo.download(destination_file=file_name)

                # Определяем путь для сохранения файла
                save_path = 'photos_profile/mentors'
                os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

                # Скачиваем файл в заданную директорию
                await photo.download(destination_file=os.path.join(save_path, file_name))

                # Генерируем уникальное имя для файла
                unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

                # Переименовываем файл
                os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
                # Удаляем загруженный файл из \photos
                os.remove(file_name)

                mentor = session.query(Mentor).filter_by(id=profile_id).first()
                if mentor.mentor_photo:
                    try:
                        os.remove(mentor.mentor_photo)
                    except FileNotFoundError:
                        pass  # Файл уже удален, игнорируем ошибку
                new_photo = os.path.join(save_path, unique_filename)
                mentor.mentor_photo = new_photo
                session.commit()
                await state.finish()
                await message.reply("Фото профиля наставника успешно изменено")

            elif type_user == 'admin':
                photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
                file_id = photo.file_id
                file_path = await bot.get_file(file_id)
                file_name = file_path['file_path']
                await photo.download(destination_file=file_name)

                # Определяем путь для сохранения файла
                save_path = 'photos_profile/admins'
                os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

                # Скачиваем файл в заданную директорию
                await photo.download(destination_file=os.path.join(save_path, file_name))

                # Генерируем уникальное имя для файла
                unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

                # Переименовываем файл
                os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
                # Удаляем загруженный файл из \photos
                os.remove(file_name)

                admin = session.query(Admin).filter_by(id=profile_id).first()
                if admin.admin_photo:
                    try:
                        os.remove(admin.admin_photo)
                    except FileNotFoundError:
                        pass  # Файл уже удален, игнорируем ошибку
                new_photo = os.path.join(save_path, unique_filename)
                admin.admin_photo = new_photo
                session.commit()
                await state.finish()
                await message.reply("Фото профиля администратора успешно изменено")

        except Exception as e:
            await message.reply(f"Невозможно добавить/обновить фото профиля [change_photo]"
                                f"Обратитесь к Администратору")
            logging.error(f"Ошибка при изменении photo_nickname[change_photo] для {type_user} c id:{profile_id} "
                          f" -  [{e}]")
    elif message.text.lower() != '/cancel':
        await message.reply("Пожалуйста загрузите только фото:"
                            "\n/cancel - для отмены добавления/изменения фото профиля")
        return
    else:
        await state.finish()  # Завершаем состояние
        await message.reply("Добавление/изменение фото профиля отменены.")
        return


# Обработка кнопки Регистрация
@dp.message_handler(lambda message: message.text == 'Регистрация')
async def registration_start(message: types.Message):
    buttons = [
        types.KeyboardButton('Регистрация участника', description='Регистрация пользователя'),  # /reg
        types.KeyboardButton('Регистрация Наставника', description='Регистрация как Наставник'),  # /reg_mentors
        types.KeyboardButton('Регистрация Админа', description='Регистрация Админа'),  # /reg_admins
        types.KeyboardButton('\U0001F50DПоиск наставника', description='Найти свободных Наставников'),
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


# команда поиска свободный Наставников
# @dp.message_handler(commands=['show_free_mentors'])
@dp.message_handler(lambda message: message.text.replace('\U0001F50D', '') == 'Поиск наставника')
async def show_free_mentors(message: types.Message):
    mentors_data = session.query(Mentor).filter(Mentor.mentor_number_of_students <= 2).all()
    if mentors_data:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for mentor in mentors_data:
            mentor_id = mentor.id
            mentor_nickname = mentor.mentor_nickname

            # Получение класса героя и знаний ментора
            mentor_account_id = mentor.mentor_account_id
            mentor_interest = mentor.mentor_interest
            mentor_number_of_students = mentor.mentor_number_of_students
            mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
            if mentor_user_data:
                hero_class = mentor_user_data.hero_class
            else:
                hero_class = "Не указан"

            button = types.InlineKeyboardButton(
                text=f"Наставник: {mentor_nickname} ({hero_class}) - {mentor_interest}"
                     f"\nУчеников: {mentor_number_of_students}",
                callback_data=f"profile:mentor:{mentor_id}"
            )
            keyboard.insert(button)

        await message.answer("Выберите свободного наставника:", reply_markup=keyboard)
    else:
        await message.answer("В данный момент нет свободных наставников.")


'''КОМАНДЫ ДЛЯ РЕГИСТРАЦИИ'''


# Команда регистрации Пользователей
# @dp.message_handler(commands=['reg'], state=None)
@dp.message_handler(lambda message: message.text == 'Регистрация пользователя')
async def registration_start(message: types.Message, state: FSMContext):
    # Автоматически получаем nickname и id из информации об аккаунте telegram user
    username = message.from_user.first_name

    with open('image/reg_user_2.jpg', 'rb') as reg_user_2_photo:
        await message.answer_photo(
            photo=reg_user_2_photo,
            caption=f'Привет! {username}. Давай зарегистрируем тебя.\n'
                    'Какой у тебя Ник в игре?'
                    '\n\nДля отмены или выхода из регистрации введи /cancel'
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
            data['status'] = '\U0001F7E2Active'

            # Запрос фотографии
            await message.reply("Загрузите свою фотографию:"
                                "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
            await Registration.photo.set()
    elif account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(content_types=['photo', 'text'], state=Registration.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.photo:
        # Скачиваем фотографию, если сообщение не команда и не текст
        photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
        file_id = photo.file_id
        file_path = await bot.get_file(file_id)
        file_name = file_path['file_path']
        await photo.download(destination_file=file_name)

        # Определяем путь для сохранения файла
        save_path = 'photos_profile/users'
        os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

        # Скачиваем файл в заданную директорию
        await photo.download(destination_file=os.path.join(save_path, file_name))

        # Генерируем уникальное имя для файла
        unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

        # Переименовываем файл
        os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
        # Удаляем загруженный файл из \photos
        os.remove(file_name)
        # Сохраняем путь к фотографии в данные состояния
        async with state.proxy() as data:
            data['photo'] = os.path.join(save_path, unique_filename)  # Сохраняем путь к файлу

        # Переходим к выбору наставника
        mentors = session.query(Mentor).all()
        mentor_nicknames = [mentor.mentor_nickname for mentor in mentors]

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for nickname in mentor_nicknames:
            keyboard.add(types.KeyboardButton(nickname))

        try:
            await message.reply("Выберите наставника:", reply_markup=keyboard)
        except MessageNotModified:
            pass  # Если сообщение не было изменено, игнорируем ошибку

        await Registration.user_mentor_id.set()

    elif message.text:
        # Проверяем на команды /cancel и /next
        if message.text.lower() == '/cancel':
            await state.finish()  # Завершаем состояние
            await message.reply("Регистрация отменена.")
            return
        elif message.text.lower() == '/next':
            await state.finish()  # Завершаем состояние
            mentors = session.query(Mentor).all()
            mentor_nicknames = [mentor.mentor_nickname for mentor in mentors]

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for nickname in mentor_nicknames:
                keyboard.add(types.KeyboardButton(nickname))

            await message.reply("Выберите наставника:", reply_markup=keyboard)
            await Registration.user_mentor_id.set()
            return

        # Проверяем, является ли сообщение текстовым
        elif message.text.lower() != '/next' or message.text.lower() != '/cancel':
            await message.reply("На этом этапе доступна только загрузка фотографии или команды:"
                                "\n/cancel - для отмены и выхода из регистрации"
                                "\n/next - для пропуска этапа, если сейчас нет фотографии для профиля")
            return
    else:
        # Если сообщение не текст и не фото, выводим ошибку
        await message.reply("Неверный тип сообщения. Пожалуйста, загрузите фотографию.")


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
                    photo=data['photo'],
                    guild=data['guild'],
                    mentor_id=data['user_mentor_id'],
                    date_registration=datetime.now(),
                    status=data['status']  # Может иметь 3 значения:
                    # active (активный участник ги);
                    # absense (отпуск)
                    # и offline (инактив)
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
                # session.close()  # Закрываем сеанс с БД после завершения регистрации
                # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
                #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
                change_students_member_text = f"Наставник {mentor_nickname} (ID: {mentor.id}) - " \
                                              f"Количество подопечных: {old_students_count} -> {new_students_count}"
                await bot.send_message(config.id_leader, change_students_member_text)

                # Отправка сообщения выбранному ментору
                mentor_account_id = mentor.mentor_account_id
                if mentor_account_id:
                    mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                    if mentor_user_data:
                        mentor_telegram_id = mentor_user_data.telegram_id
                        if mentor_telegram_id is not None and mentor_telegram_id != "":
                            try:
                                mentor_username = mentor_user_data.username
                                mentor_nickname = mentor_user_data.nickname
                                mentor_message = f"Участник {user.nickname} с гильдии {user.guild} " \
                                                 f"выбрал Вас в качестве своего наставника." \
                                                 f"\n\nДля связи с учеником используйте @{mentor_username}"
                                notification_guild = f"Участник {user.nickname} герой {user.hero_class} " \
                                                     f"с гильдии {user.guild} " \
                                                     f"выбрал качестве своего наставника{mentor_nickname}" \
                                                     f"\n\nДля связи с участником используйте @{user.username}"
                                await bot.send_message(mentor_telegram_id, mentor_message)
                                # await bot.send_message(config.officer_chat_id, notification_guild,
                                #                        message_thread_id=config.office_mentor_thread_id) НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
                            except Exception as e:
                                logging.error(f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")
                session.close()  # Закрытие сессии после отправки сообщения
            except Exception as e:
                logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
                session.close()  # Закрываем сеанс с БД после завершения регистрации

    elif mentor_nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


class RegistrationMentors(StatesGroup):
    mentor_nickname = State()
    mentor_account_id = State()
    mentor_photo = State()
    mentor_interest = State()
    mentor_time_online = State()
    mentor_characteristic = State()


# Команда регистрации Наставников
# @dp.message_handler(commands=['reg_mentors'], state=None)
@dp.message_handler(lambda message: message.text == 'Регистрация Наставника')
async def registration_mentors_start(message: types.Message):
    await message.reply("Введите свой никнейм:"
                        "\n\nДля отмены или выхода из регистрации введи /cancel")
    await RegistrationMentors.mentor_nickname.set()


@dp.message_handler(state=RegistrationMentors.mentor_nickname)
async def process_mentor_nickname(message: types.Message, state: FSMContext):
    mentor_nickname = message.text
    # Проверка на запрещённый символ "/"
    if mentor_nickname.startswith('/') and mentor_nickname != '/cancel':
        await message.reply("Неверно. Никнейм наставника не должен начинаться с символа /."
                            "\nВоспользуйся кнопками для выбора Наставника")
        return  # Выход из обработчика, если никнейм неверный

    if mentor_nickname != '/cancel':
        async with state.proxy() as data:
            data['mentor_nickname'] = message.text
        await message.reply("Теперь введите ID наставника в игре:")
        await RegistrationMentors.mentor_account_id.set()
    elif mentor_nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=RegistrationMentors.mentor_account_id)
async def process_mentor_account_id(message: types.Message, state: FSMContext):
    mentor_account_id = message.text

    # Проверка на запрещённый символ "/"
    if mentor_account_id.startswith('/') and mentor_account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный

    if not (
            mentor_account_id.isdigit() and
            len(mentor_account_id) == 11 and
            mentor_account_id[-3:] == '160' and
            int(mentor_account_id) > 0 or  # Проверка на наличие лишних нулей
            mentor_account_id != '/cancel'
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

    if mentor_account_id != '/cancel':
        async with state.proxy() as data:
            data['mentor_account_id'] = message.text

            # Запрос данных о менторе
            await message.reply("Загрузите фотографию профиля (опционально):"
                                "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
            await RegistrationMentors.mentor_photo.set()
    elif mentor_account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


# Обработчик загрузки фото для Наставника
@dp.message_handler(content_types=['photo', 'text'], state=RegistrationMentors.mentor_photo)
async def process_mentor_photo(message: types.Message, state: FSMContext):
    if message.photo:
        # Скачиваем фотографию, если сообщение не команда и не текст
        photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
        file_id = photo.file_id
        file_path = await bot.get_file(file_id)
        file_name = file_path['file_path']
        await photo.download(destination_file=file_name)

        # Определяем путь для сохранения файла
        save_path = 'photos_profile/mentors'
        os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

        # Скачиваем файл в заданную директорию
        await photo.download(destination_file=os.path.join(save_path, file_name))

        # Генерируем уникальное имя для файла
        unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

        # Переименовываем файл
        os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
        # Удаляем загруженный файл из \photos
        os.remove(file_name)
        # Сохраняем путь к фотографии в данные состояния
        async with state.proxy() as data:
            data['photo'] = os.path.join(save_path, unique_filename)  # Сохраняем путь к файлу

        await message.reply("Введите интересы ментора (через запятую):")
        await RegistrationMentors.mentor_interest.set()

    elif message.text:
        # Проверяем на команды /cancel и /next
        if message.text.lower() == '/cancel':
            await state.finish()  # Завершаем состояние
            await message.reply("Регистрация отменена.")
            return
        elif message.text.lower() == '/next':
            await message.reply("Введите интересы ментора (через запятую):")
            await RegistrationMentors.mentor_interest.set()
            return

        # Проверяем, является ли сообщение текстовым
        elif message.text.lower() != '/next' or message.text.lower() != '/cancel':
            await message.reply("На этом этапе доступна только загрузка фотографии или команды:"
                                "\n/cancel - для отмены и выхода из регистрации"
                                "\n/next - для пропуска этапа, если сейчас нет фотографии для профиля")
            return
    else:
        # Если сообщение не текст и не фото, выводим ошибку
        await message.reply("Неверный тип сообщения. Пожалуйста, загрузите фотографию.")


@dp.message_handler(state=RegistrationMentors.mentor_interest)
async def process_mentor_interest(message: types.Message, state: FSMContext):
    mentor_interest = message.text
    # Проверка на запрещённый символ "/"
    if mentor_interest.startswith('/') and mentor_interest != '/cancel':
        await message.reply("Неверно. Интересы ментора не должны начинаться с символа /."
                            "\nПожалуйста, введите интересы без символа /")
        return  # Выход из обработчика, если никнейм неверный

    if mentor_interest != '/cancel':
        async with state.proxy() as data:
            data['mentor_interest'] = mentor_interest
            await message.reply("Введите время онлайн ментора (пример: 18:00-22:00):")
            await RegistrationMentors.mentor_time_online.set()
    elif mentor_interest == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=RegistrationMentors.mentor_time_online)
async def process_mentor_time_online(message: types.Message, state: FSMContext):
    mentor_time_online = message.text
    # Проверка на запрещённый символ "/"
    if mentor_time_online.startswith('/') and mentor_time_online != '/cancel':
        await message.reply("Неверно. Время онлайн ментора не должно начинаться с символа /."
                            "\nПожалуйста, введите время онлайн без символа /")
        return  # Выход из обработчика, если никнейм неверный

    if mentor_time_online != '/cancel':
        async with state.proxy() as data:
            data['mentor_time_online'] = mentor_time_online
            await message.reply("Введите краткую характеристику ментора (максимум 100 символов):")
            await RegistrationMentors.mentor_characteristic.set()
    elif mentor_time_online == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=RegistrationMentors.mentor_characteristic)
async def process_mentor_characteristic(message: types.Message, state: FSMContext):
    mentor_characteristic = message.text
    # Проверка на запрещённый символ "/"
    if mentor_characteristic.startswith('/') and mentor_characteristic != '/cancel':
        await message.reply("Неверно. Характеристика ментора не должна начинаться с символа /."
                            "\nПожалуйста, введите характеристику без символа /")
        return  # Выход из обработчика, если никнейм неверный

    if mentor_characteristic != '/cancel':
        async with state.proxy() as data:
            data['mentor_characteristic'] = mentor_characteristic

            # Сохраняем данные в БД
            mentor = Mentor(
                mentor_account_id=data['mentor_account_id'],
                mentor_nickname=data['mentor_nickname'],
                mentor_photo=data['photo'],
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
    elif mentor_characteristic == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


class RegistrationAdmins(StatesGroup):
    admin_nickname = State()
    admin_account_id = State()
    admin_photo = State()
    admin_role = State()
    admin_position = State()


# Команда регистрации Офицеров гильдии
# @dp.message_handler(commands=['reg_admins'], state=None)
@dp.message_handler(lambda message: message.text == 'Регистрация Админа')
async def registration_admins_start(message: types.Message):
    await message.reply("Введите свой никнейм:"
                        "\n\nДля отмены или выхода из регистрации введи /cancel")
    await RegistrationAdmins.admin_nickname.set()


@dp.message_handler(state=RegistrationAdmins.admin_nickname)
async def process_admin_nickname(message: types.Message, state: FSMContext):
    admin_nickname = message.text
    # Проверка на запрещённый символ "/"
    if admin_nickname.startswith('/') and admin_nickname != '/cancel':
        await message.reply("Неверно. Никнейм не должен начинаться с символа /")
        return  # Выход из обработчика, если никнейм неверный
    if admin_nickname != '/cancel':
        async with state.proxy() as data:
            data['admin_nickname'] = message.text
        await message.reply("Введите ID администратора в игре:")
        await RegistrationAdmins.admin_account_id.set()
    elif admin_nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=RegistrationAdmins.admin_account_id)
async def process_admin_account_id(message: types.Message, state: FSMContext):
    admin_account_id = message.text

    # Проверка на запрещённый символ "/"
    if admin_account_id.startswith('/') and admin_account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный
    # Проверка длины и окончания ID
    if not (
            admin_account_id.isdigit() and
            len(admin_account_id) == 11 and
            admin_account_id[-3:] == '160' and
            int(admin_account_id) > 0 or  # Проверка на наличие лишних нулей
            admin_account_id != '/cancel'
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

    if admin_account_id != '/cancel':
        async with state.proxy() as data:
            data['admin_account_id'] = message.text
        await message.reply("Загрузите фотографию профиля (опционально):"
                            "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
        await RegistrationAdmins.admin_photo.set()
    elif admin_account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


# Обработчик загрузки фото для администратора
@dp.message_handler(content_types=['photo', 'text'], state=RegistrationAdmins.admin_photo)
async def process_admin_photo(message: types.Message, state: FSMContext):
    if message.photo:
        # Скачиваем фотографию, если сообщение не команда и не текст
        photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
        file_id = photo.file_id
        file_path = await bot.get_file(file_id)
        file_name = file_path['file_path']
        await photo.download(destination_file=file_name)

        # Определяем путь для сохранения файла
        save_path = 'photos_profile/admins'
        os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет

        # Скачиваем файл в заданную директорию
        await photo.download(destination_file=os.path.join(save_path, file_name))

        # Генерируем уникальное имя для файла
        unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]

        # Переименовываем файл
        os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
        # Удаляем загруженный файл из \photos
        os.remove(file_name)
        # Сохраняем путь к фотографии в данные состояния
        async with state.proxy() as data:
            data['admin_photo'] = os.path.join(save_path, unique_filename)  # Сохраняем путь к файлу

        await message.reply("Выберите роль администратора:",
                            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                                types.KeyboardButton("Управляющий"),
                                types.KeyboardButton("Заместитель"),
                                types.KeyboardButton("\U0001F451Глава")
                            ))
        await RegistrationAdmins.admin_role.set()

    elif message.text:
        # Проверяем на команды /cancel и /next
        if message.text.lower() == '/cancel':
            await state.finish()  # Завершаем состояние
            await message.reply("Регистрация отменена.")
            return
        elif message.text.lower() == '/next':
            await message.reply("Выберите роль администратора:",
                                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                                    types.KeyboardButton("Управляющий"),
                                    types.KeyboardButton("Заместитель"),
                                    types.KeyboardButton("\U0001F451Глава")
                                ))
            await RegistrationAdmins.admin_role.set()
            return

        # Проверяем, является ли сообщение текстовым
        elif message.text.lower() != '/next' or message.text.lower() != '/cancel':
            await message.reply("На этом этапе доступна только загрузка фотографии или команды:"
                                "\n/cancel - для отмены и выхода из регистрации"
                                "\n/next - для пропуска этапа, если сейчас нет фотографии для профиля")
            return
    else:
        # Если сообщение не текст и не фото, выводим ошибку
        await message.reply("Неверный тип сообщения. Пожалуйста, загрузите фотографию.")


@dp.message_handler(state=RegistrationAdmins.admin_role)
async def process_admin_role(message: types.Message, state: FSMContext):
    if message.text not in ['Управляющий', 'Заместитель', '\U0001F451Глава']:
        await message.reply("Выберите роль из предложенных кнопок!")
        return

    admin_role = message.text.replace('\U0001F451', '')

    if admin_role.startswith('/') and admin_role != '/cancel':
        await message.reply("Неверно. Роль не может начинаться с символа /."
                            "\nВоспользуйся кнопками для выбора роли")
        return  # Выход из обработчика, если класс неверный

    if admin_role != '/cancel':
        async with state.proxy() as data:
            data['admin_role'] = admin_role

            # Проверка количества admin_role
            existing_roles = session.query(Admin).filter_by(admin_role='Глава').all()  # Изменили фильтр на 'Глава'
            if len(existing_roles) >= 2:
                await message.reply(f"Достигнут предел количества Администраторов с ролью 'Глава'. "
                                    f"Введите другую роль или используйте команду /cancel для выхода из регистрации.")
                return

            # Переходим к вводу должности
            await message.reply("Введите должность администратора:")
            await RegistrationAdmins.admin_position.set()
    elif admin_role == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=RegistrationAdmins.admin_position)
async def process_admin_position(message: types.Message, state: FSMContext):
    admin_position = message.text

    if admin_position.startswith('/') and admin_position != '/cancel':
        await message.reply("Неверно. Должность не может начинаться с символа /."
                            "\nВведите должность без символа /")
        return  # Выход из обработчика, если должность неверна

    if admin_position != '/cancel':
        async with state.proxy() as data:
            data['admin_position'] = admin_position

            # Сохраняем данные в БД
            admin = Admin(
                admin_account_id=data['admin_account_id'],
                admin_nickname=data['admin_nickname'],
                admin_role=data['admin_role'],
                admin_position=data['admin_position'],
                admin_photo=data['admin_photo']
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
    elif admin_position == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


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
