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
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import BotBlocked, ChatNotFound
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey, DateTime
from sqlalchemy.exc import IntegrityError, OperationalError
import config
from datetime import datetime
from aiogram.utils.exceptions import MessageNotModified
import os
import uuid
import re

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
    from_guild = Column(String)
    where_guild = Column(String)


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


# Определение класса BM_DPS для БД
class BM_DPS(Base):
    __tablename__ = 'BM_DPS'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.id'))  # равен Users.id
    bm = Column(String)
    dps = Column(String)
    date_update = Column(DateTime)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


class Registration(StatesGroup):
    user_mentor_id = State()
    nickname = State()
    hero_class = State()
    hero_class2 = State()
    account_id = State()
    photo = State()


class AdminEditProfile(StatesGroup):
    search_account = State()
    reason = State()
    change_guild = State()
    select_reason = State()


'''СТАРТОВЫЕ КОМАНДЫ И ФУНКЦИИ'''

# CallbackData для обработки показа профиля пользователя
profile_callback = CallbackData("profile", "type", "id")  # Создаем CallbackData
# CallbackData для обработки редактирования профиля пользователя
edit_profile_callback = CallbackData('change', 'action', 'type', 'id')
# CallbackData для профиля пользователя через Наставника
my_students_profile_callback = CallbackData('change', 'action', 'id')
# CallbackData для обработки функций администратора
admin_edit_profile_callback = CallbackData('change', 'action', 'type', 'id')

transfer_reasons_callback = CallbackData('transfer_reasons', 'action', 'reason')


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    username = message.from_user.first_name
    # user_role = get_user_role(message.from_user.id)

    buttons = [
        types.KeyboardButton('\U0001F464Мой профиль'),
        types.KeyboardButton('Регистрация'),
        types.KeyboardButton('\U0001F198Помощь'),
        types.KeyboardButton('Администрирование')
    ]
    # Заготовка под ролевую модель #РОЛЕВАЯ
    # buttons = [
    #     types.KeyboardButton('\U0001F464Мой профиль'),
    #     types.KeyboardButton('Регистрация'),
    #     types.KeyboardButton('\U0001F198Помощь')
    # ]

    # if user_role == 'admin':
    #     buttons.append(types.KeyboardButton('Администрирование'))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(*buttons)

    with open('image/start_message.jpg', 'rb') as start_mess_photo:
        await message.answer_photo(
            photo=start_mess_photo,
            caption="Здрям, " + f"<b>{username}</b>" + ' - я милый бот клана <b>AURI!!</b>\n' + config.start_message,
            reply_markup=markup,
            parse_mode='HTML'
        )
    # await bot.set_webhook(url="https://api.telegram.org/bot7091077757:AAHfCZj7j48smo9WWhSo6Oi-JnJR47gwIY0/setwebhook",
    #                       allowed_updates=["message", "callback_query"])


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

    with open('image/my_profile_photo.jpg', 'rb') as my_profile_photo:
        await message.answer_photo(
            photo=my_profile_photo,
            caption=config.my_profile_message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


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
            profile_text += f"telegram:  @{field_values.get('username', 'Не указан')}\n"
            profile_text += f"Имя:  {field_values.get('first_name', 'Не указан')}\n"
            profile_text += f"Никнейм:  {field_values.get('nickname', 'Не указан')}\n"
            profile_text += f"Класс героя:  {field_values.get('hero_class', 'Не указан')}\n"
            bm_dps_data = session.query(BM_DPS).filter_by(user_id=profile_id).first()
            if bm_dps_data is not None:
                profile_text += f"БМ/ДПС: {bm_dps_data.bm or 'Не указан'} / {bm_dps_data.dps or 'Не указан'}\n"
            profile_text += f"ID аккаунта:  <code>{field_values.get('account_id', 'Не указан')}</code>\n"
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
                registration_date = datetime.strptime(registration_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                      '%Y-%m-%d %H:%M:%S')
                time_delta = datetime.now() - registration_date

                days = time_delta.days
                hours = time_delta.seconds // 3600
                minutes = (time_delta.seconds % 3600) // 60
                seconds = time_delta.seconds % 60

                profile_text += f"Дата регистрации:  {registration_date.strftime('%d-%m-%Y')}\n"
                profile_text += f"В системе:  {days} дней {hours} часов {minutes} минут {seconds} секунд\n"
            else:
                profile_text += f"Дата регистрации:  Не указана\n"

            profile_text += f"Статус:  {field_values.get('status', 'Не указан')}\n"
            # Добавляем кнопки для изменения профиля
            reply_markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(
                    text="Изменить Никнейм",
                    callback_data=edit_profile_callback.new(action='nickname', type=profile_type, id=profile_id)
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
                    text="Обновить БМ/ДПС",
                    callback_data=edit_profile_callback.new(action='change_bm_dps', type=profile_type,
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
                            reply_markup=reply_markup,
                            parse_mode='html'
                        )
                    await call.answer()
                except Exception as e:
                    logging.error(f"При поиске фотографии в Users.photo для {profile_id} - произошла ошибка - [{e}]")
                    await call.answer()
            else:
                reply_markup = InlineKeyboardMarkup(row_width=1).add(
                    InlineKeyboardButton(
                        text="Изменить Никнейм",
                        callback_data=edit_profile_callback.new(action='nickname', type=profile_type, id=profile_id)
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
                        text="Обновить БМ/ДПС",
                        callback_data=edit_profile_callback.new(action='change_bm_dps', type=profile_type,
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
                        reply_markup=reply_markup,
                        parse_mode='html'
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
                ),
                InlineKeyboardButton(
                    text="Мои ученики",
                    callback_data=edit_profile_callback.new(action='show_students', type=profile_type, id=profile_id)
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
                    ),
                    InlineKeyboardButton(
                        text="Мои ученики",
                        callback_data=edit_profile_callback.new(action='show_students', type=profile_type,
                                                                id=profile_id)
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
    change_bm_dps_state = State()


# обработка callback изменения профиля
@dp.callback_query_handler(edit_profile_callback.filter())
async def handle_change(call: types.CallbackQuery, callback_data: dict):
    logging.info(f"Полученный callback_data в handle_change: {callback_data}")
    profile_type = callback_data["type"]
    profile_id = callback_data["id"]
    logging.info(f"Тип {profile_type} - изменения профиля: {callback_data['action']} - id_user [{profile_id}]")
    # команды для профиля пользователя
    if profile_type == 'user':
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
            await dp.current_state().update_data(edit_type=profile_type)
            await call.answer()

        elif callback_data['action'] == 'change_hero_class':
            # await call.message.answer("Для смены класса воспользуйтесь кнопками:"
            #                           "\nДля отмены введите /cancel")
            # await dp.current_state().set_state(UserStates.change_hero_class)
            # await dp.current_state().update_data(profile_id=profile_id)
            # await call.answer()
            await call.answer("В разработке")

        elif callback_data['action'] == 'change_bm_dps':
            await call.message.answer("Введите свой БМ:"
                                      "\nДля отмены изменений введите /cancel")
            await dp.current_state().set_state(UserStates.change_bm_dps_state)
            await dp.current_state().update_data(profile_id=profile_id)
            await call.answer()
            # await call.answer("В разработке")

        elif callback_data['action'] == 'vacation':
            await call.answer("В разработке")

    elif profile_type == 'mentor':
        if callback_data['action'] == 'show_students':
            students_data = session.query(User).filter_by(mentor_id=profile_id).all()
            keyboard = InlineKeyboardMarkup(row_width=1)
            if students_data:
                for student in students_data:
                    if student:
                        callback_data = my_students_profile_callback.new(action="show_my_student", id=student.id)
                        keyboard.add(InlineKeyboardButton(
                            text=f"\U0001F476Ученик: {student.nickname} ({student.hero_class}, {student.status}) - "
                                 f"{student.guild}",
                            callback_data=callback_data
                        ))
                await call.message.answer(text='Ваши ученики:', reply_markup=keyboard)
                await call.answer()
            else:
                await call.message.answer(text='У вас еще нет участников.')


# Обработка профиля ученика (show_my_student)
@dp.callback_query_handler(my_students_profile_callback.filter(action="show_my_student"))
async def show_my_student_profile(call: CallbackQuery, callback_data: dict):
    student_id = callback_data["id"]
    # Получаем данные ученика
    student_data = session.query(User).filter_by(id=student_id).first()
    profile_photo_student = student_data.photo

    if student_data:
        profile_text = f"Профиль:\n"

        # Создаем словарь для замены mentor_id на mentor_nickname
        field_values = {}
        for field_name in ('telegram_id', 'username', 'first_name', 'nickname', 'hero_class', 'account_id',
                           'guild', 'date_registration', 'status', 'photo'):
            field_value = getattr(student_data, field_name, None)
            field_values[field_name] = field_value
        profile_text += f"telegram:  @{field_values.get('username', 'Не указан')}\n"
        profile_text += f"Имя:  {field_values.get('first_name', 'Не указан')}\n"
        profile_text += f"Никнейм:  {field_values.get('nickname', 'Не указан')}\n"
        profile_text += f"Класс героя:  {field_values.get('hero_class', 'Не указан')}\n"
        bm_dps_data = session.query(BM_DPS).filter_by(user_id=student_id).first()
        if bm_dps_data is not None:
            profile_text += f"БМ/ДПС: {bm_dps_data.bm or 'Не указан'} / {bm_dps_data.dps or 'Не указан'}\n"
        profile_text += f"ID аккаунта:  <code>{field_values.get('account_id', 'Не указан')}</code>\n"
        profile_text += f"Гильдия:  {field_values.get('guild', 'Не указан')}\n"
        # Вычисление времени с момента регистрации
        registration_date = field_values.get('date_registration')
        if registration_date:
            registration_date = datetime.strptime(registration_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                  '%Y-%m-%d %H:%M:%S')
            time_delta = datetime.now() - registration_date

            days = time_delta.days
            hours = time_delta.seconds // 3600
            minutes = (time_delta.seconds % 3600) // 60
            seconds = time_delta.seconds % 60

            profile_text += f"Дата регистрации:  {registration_date.strftime('%d-%m-%Y')}\n"
            profile_text += f"В системе:  {days} дней {hours} часов {minutes} минут {seconds} секунд\n"
        else:
            profile_text += f"Дата регистрации:  Не указана\n"

        profile_text += f"Статус:  {field_values.get('status', 'Не указан')}\n"
        # Добавляем кнопку "Назад"
        reply_markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(
                text="Назад",
                callback_data=profile_callback.new(type="mentor", id=student_data.mentor_id)
                # Возвращаемся к профилю ментора
            )
        )

        if profile_photo_student:
            try:
                with open(profile_photo_student, 'rb') as student_profile_photo:
                    await call.message.answer_photo(
                        photo=student_profile_photo,
                        caption=profile_text,
                        reply_markup=reply_markup,
                        parse_mode='html'
                    )
                await call.answer()
            except Exception as e:
                logging.error(f"При поиске фотографии в Users.photo для {student_id} - произошла ошибка - [{e}]")
                await call.answer()
        else:
            try:
                await call.message.answer(
                    text=profile_text,
                    reply_markup=reply_markup,
                    parse_mode='html'
                )
                await call.answer()
            except Exception as e:
                logging.error(f"При отправке профиля STUDENT {student_id} - произошла ошибка - [{e}]")
                await call.answer()

    else:
        await call.message.answer("Профиль ученика не найден.")
        await call.answer()


# Обработка состояния для изменения nickname и запись в БД
@dp.message_handler(state=UserStates.nickname_state)
async def change_nickname(message: types.Message, state: FSMContext):
    new_nickname = message.text
    # Проверяем, что предыдущее сообщение было запросом на ввод nickname
    if new_nickname.startswith('/') and new_nickname != "/cancel":
        await message.reply("Неверно. Ник не должен начинаться с символа /")
        return  # Выход из обработчика, если ник неверный
    elif new_nickname == "/cancel":
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


# Обработка состояния для обновления БМ и ДПС и запись в БД
@dp.message_handler(state=UserStates.change_bm_dps_state)
async def process_bm_dps(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        profile_id = data['profile_id']

        if message.text == '/cancel':
            await message.answer("Изменение БМ и ДПС отменено.")
            await state.finish()
            return

        if '/' in message.text:
            await message.answer(
                "Ввод БМ и ДПС не должен содержать символ '/'. Пожалуйста, введите данные заново.")
            return

        if not validate_input(message.text):
            await message.answer(
                "Введёный БМ/ДПС не соответствует формату: "
                "\nВведите число от 3 до 5 знаков с буквой K, M, B, T или AA в конце")
            return

        if 'bm' in data:  # Если БМ уже введен
            dps = message.text

            user_data = session.query(User).filter_by(id=profile_id).first()
            notification_update_dps = f"Участник {user_data.nickname} герой {user_data.hero_class} " \
                                      f"с гильдии {user_data.guild} " \
                                      f"обновил данные своего БМ и ДПС"
            date_update = datetime.now()

            existing_bm_dps = session.query(BM_DPS).filter_by(user_id=profile_id).first()

            if existing_bm_dps:
                # Обновление данных
                existing_bm_dps.bm = data['bm']
                existing_bm_dps.dps = dps
                existing_bm_dps.date_update = date_update
            else:
                # Создание новой записи
                bm_dps_data = BM_DPS(user_id=profile_id, bm=data['bm'], dps=dps, date_update=date_update)
                session.add(bm_dps_data)

            try:
                session.commit()
                logging.info(f"{notification_update_dps}")
                await message.answer("БМ и ДПС успешно обновлены.")
                await state.finish()  # Завершение состояния после записи данных
                session.close()
            except IntegrityError as e:
                await message.reply(
                    "Произошла ошибка при обновлении данных. Пожалуйста, проверьте правильность "
                    "введенных данных и попробуйте снова.")
                logging.error(
                    f"Ошибка IntegrityError при изменении bm_dps_data[change_bm_dps] для {user_data.nickname} "
                    f"c id:{profile_id}"
                    f"\n Ошибка {e}")
            except OperationalError as e:
                await message.reply("Произошла ошибка соединения с базой данных. Пожалуйста, попробуйте позже.")
                logging.error(
                    f"Ошибка OperationalError при изменении bm_dps_data[change_bm_dps] для {user_data.nickname} "
                    f"c id:{profile_id}"
                    f"\n Ошибка {e}")
            except Exception as e:
                await message.reply("Невозможно обновить БМ и ДПС. Обратитесь к Администратору.")
                logging.error(f"Ошибка при изменении bm_dps_data[change_bm_dps] для {user_data.nickname} "
                              f"c id:{profile_id}"
                              f"\n Ошибка {e}")

            # await bot.send_message(config.officer_chat_id, notification_guild,
            # message_thread_id=config.office_mentor_thread_id) НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
        else:  # Если БМ еще не введен
            bm = message.text
            if '/' in bm:
                await message.answer("Ввод БМ не должен содержать символ '/'. Пожалуйста, введите данные заново.")
                return
            await message.answer("Введите свой ДПС:")
            await dp.current_state().update_data(bm=bm)


# Обработка кнопки Регистрация
@dp.message_handler(lambda message: message.text == 'Регистрация')
async def registration_start(message: types.Message):
    # user_role = get_user_role(message.from_user.id)
    first_name = message.from_user.first_name
    buttons = [
        types.KeyboardButton('Регистрация участника', description='Регистрация пользователя'),  # /reg
        types.KeyboardButton('Регистрация Наставника', description='Регистрация как Наставник'),  # /reg_mentors
        types.KeyboardButton('Регистрация Админа', description='Регистрация Админа'),  # /reg_admins
        types.KeyboardButton('\U0001F519Назад', description='Вернуться к предыдущему меню')
    ]
    # Заготовка под ролевую модель #РОЛЕВАЯ
    # buttons = [
    #     types.KeyboardButton('Регистрация участника', description='Регистрация пользователя'),
    #     types.KeyboardButton('\U0001F519Назад', description='Вернуться к предыдущему меню')
    # ]
    # if user_role == 'admin':
    #     buttons.insert(1, types.KeyboardButton('Регистрация Наставника', description='Регистрация как Наставник'))
    #     buttons.insert(2, types.KeyboardButton('Регистрация Админа', description='Регистрация Админа'))

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder='Выберите тип регистрации:'
    )

    markup.add(*buttons)
    with open('image/reg_user_1.jpg', 'rb') as reg_user_1_photo:
        await message.answer_photo(
            photo=reg_user_1_photo,
            caption=f'Я очень рад, что именно ты — <b>{first_name}</b>, будешь играть с нами!' +
                    config.start_register_message,
            reply_markup=markup,
            parse_mode='HTML'
        )


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


# команда поиска Наставников - удалить
# @dp.message_handler(commands=['show_free_mentors'])
# @dp.message_handler(lambda message: message.text.replace('\U0001F50D', '') == 'Поиск наставника')
# async def show_free_mentors(message: types.Message):
#     mentors_data = session.query(Mentor).filter().all()
#     if mentors_data:
#         keyboard = types.InlineKeyboardMarkup(row_width=1)
#         for mentor in mentors_data:
#             mentor_id = mentor.id
#             mentor_nickname = mentor.mentor_nickname
#
#             # Получение класса героя и знаний ментора
#             mentor_account_id = mentor.mentor_account_id
#             mentor_interest = mentor.mentor_interest
#             mentor_number_of_students = mentor.mentor_number_of_students
#             mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
#             if mentor_user_data:
#                 hero_class = mentor_user_data.hero_class
#             else:
#                 hero_class = "Не указан"
#
#             button = types.InlineKeyboardButton(
#                 text=f"Наставник: {mentor_nickname} ({hero_class}) - {mentor_interest}"
#                      f"\nУчеников: {mentor_number_of_students}",
#                 callback_data=f"profile:mentor:{mentor_id}"
#             )
#             keyboard.insert(button)
#
#         await message.answer("Выберите свободного наставника:", reply_markup=keyboard)
#     else:
#         await message.answer("В данный момент нет свободных наставников.")


# Обработка кнопки Администрирование
@dp.message_handler(lambda message: message.text == 'Администрирование')
async def command_administration(message: types.Message):
    buttons = [
        types.KeyboardButton('Действия над участниками')
    ]

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )
    markup.add(*buttons)
    await message.answer('Что хотите сделать?', reply_markup=markup)


# Обработка кнопки Администрирование
@dp.message_handler(lambda message: message.text == 'Действия над участниками')
async def command_edit_members(message: types.Message, state: FSMContext):
    with open('image/reg_user_3.jpg', 'rb') as transfer_id_account_photo:
        await message.answer_photo(
            photo=transfer_id_account_photo,
            caption='Напиши ID аккаунта участника?'
        )
    await state.set_state(AdminEditProfile.search_account.state)


# обработка поиска участника для администратора
@dp.message_handler(state=AdminEditProfile.search_account)
async def search_account(message: types.Message, state: FSMContext):
    account_id = message.text

    if not (
            account_id.isdigit() and
            len(account_id) == 11 and
            account_id[-3:] == '160' and
            int(account_id) > 0
    ):
        await message.reply(
            "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
        return  # Выход из обработчика, если ID неверный

    user = session.query(User).filter_by(account_id=account_id).first()
    user_photo = user.photo
    if user:
        # Создаем словарь для замены mentor_id на mentor_nickname
        field_values = {}
        for field_name in ('telegram_id', 'username', 'first_name', 'nickname', 'hero_class', 'account_id',
                           'mentor_id', 'guild', 'date_registration', 'status', 'photo'):
            field_value = getattr(user, field_name, None)
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
        profile_text = f"Имя пользователя:  {field_values.get('username', 'Не указан')}\n"
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
            registration_date = datetime.strptime(registration_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
            time_delta = datetime.now() - registration_date

            days = time_delta.days
            hours = time_delta.seconds // 3600
            minutes = (time_delta.seconds % 3600) // 60
            seconds = time_delta.seconds % 60

            profile_text += f"Дата регистрации:  {registration_date.strftime('%d:%m:%Y')}\n"
            profile_text += f"В системе:  {days} дней {hours} часов {minutes} минут {seconds} секунд\n"
        else:
            profile_text += f"Дата регистрации:  Не указана\n"

        profile_text += f"Статус:  {field_values.get('status', 'Не указан')}\n"
        # Команды действия над аккаунтом пользователя для администратора (Добавляем сперва здесь команды)
        buttons = [
            InlineKeyboardButton(text="Перевести в другую гильдию",
                                 callback_data=admin_edit_profile_callback.new(action='change', type='guild',
                                                                               id=account_id)),
            InlineKeyboardButton(text="Сменить Наставника",
                                 callback_data=admin_edit_profile_callback.new(action='change', type='mentor',
                                                                               id=account_id)),
            InlineKeyboardButton(text="Назад", callback_data="back")
        ]
        reply_markup = InlineKeyboardMarkup(row_width=1).add(*buttons)

        user_photo_path = user.photo  # Получение пути к фото из базы
        if user_photo_path:
            with open(user_photo_path, 'rb') as user_profile_photo:
                await message.answer_photo(photo=user_profile_photo, caption=profile_text, reply_markup=reply_markup)
        else:
            await message.answer(profile_text, reply_markup=reply_markup)
        session.close()
        await state.set_state(AdminEditProfile.reason.state)
    else:
        session.close()
        await message.reply("Пользователь не найден")
        return


# Обработчик для кнопки "Перевести в другую гильдию"
@dp.callback_query_handler(admin_edit_profile_callback.filter(action='change', type='guild'),
                           state=AdminEditProfile.reason)
async def handle_change_guild(call: CallbackQuery, state: FSMContext):
    await call.message.delete()  # Удаляем сообщение с кнопками

    account_id = call.data.split(':')[3]
    user = session.query(User).filter_by(account_id=account_id).first()

    # Проверяем текущую гильдию
    current_guild = user.guild
    new_guild = "AURI" if current_guild == "AcademAURI" else "AcademAURI"

    # Создаем клавиатуру с причинами
    keyboard = InlineKeyboardMarkup(row_width=1)
    for key, reason in config.transfer_reasons.items():
        keyboard.insert(InlineKeyboardButton(
            text=str(key),
            callback_data=transfer_reasons_callback.new(action='select', reason=key)
        ))

    # Отправляем сообщение с клавиатурой
    await call.message.answer(
        f"Выберите причину перевода пользователя {user.username} из {current_guild} в {new_guild}:",
        reply_markup=keyboard)

    # Сохраняем account_id и новую гильдию в состоянии
    async with state.proxy() as data:
        data['account_id'] = account_id
        data['new_guild'] = new_guild

    session.close()

    await state.set_state(AdminEditProfile.select_reason.state)


# Обработчик для ввода причины перевода
@dp.callback_query_handler(transfer_reasons_callback.filter(action='select'),
                           state=AdminEditProfile.select_reason)
async def process_select_reason(call: CallbackQuery, state: FSMContext):
    await call.message.delete()  # Удаляем сообщение с кнопками

    reason_key = call.data.split(':')[2]
    reason = config.transfer_reasons.get(int(reason_key))

    async with state.proxy() as data:
        account_id = data['account_id']
        new_guild = data['new_guild']

    # Обновление данных в базе данных
    user = session.query(User).filter_by(account_id=account_id).first()
    current_guild = user.guild  # Сохраняем текущую гильдию
    user.guild = new_guild
    user.transfer_reason = reason  # Устанавливаем причину перевода
    session.commit()

    admin_tg = call.from_user.id  # Получаем ID администратора
    admin_id = get_admin_id(admin_tg)  # Получаем ID администратора из базы данных
    admin = session.query(Admin).filter_by(id=admin_id).first()

    if admin_id is not None:
        try:
            transfer_date = datetime.now()
            # Добавление записи в таблицу Transfers
            new_transfer = Transfers(
                user_id=user.id,
                admin_id=admin_id,
                transfer_date=transfer_date,
                reason=reason,  # Записываем причину перевода
                from_guild=current_guild,  # Добавляем текущую гильдию
                where_guild=new_guild  # Добавляем новую гильдию
            )
            session.add(new_transfer)
            session.commit()

            await call.message.answer(f"Пользователь {user.username} успешно переведен в {new_guild} администратором "
                                      f"{admin.admin_nickname} по причине: {reason}",
                                      reply_markup=await get_start_menu())
            # await call.bot.send_message(config.officer_chat_id, f"Пользователь {user.username} успешно переведен в
            # {new_guild} администратором " f"{admin.admin_nickname} по причине: {reason}",
            # message_thread_id=config.office_mentor_thread_id) НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ #РОЛЕВАЯ
            await state.finish()
        except Exception as e:
            logging.error(f"Ошибка при записи данных в Transfers - {e}")
            await call.message.answer(f"Произошла ошибка при переводе пользователя. Попробуйте позже.")
    else:
        await call.message.answer("Вы не являетесь администратором.")
        session.close()
        await state.finish()


# Обработчик кнопки сменить наставника
@dp.callback_query_handler(admin_edit_profile_callback.filter(action='change', type='mentor'),
                           state=AdminEditProfile.reason)
async def handle_change_mentor(call: CallbackQuery, state: FSMContext):
    await call.answer("В разработке")


# Обработчик для кнопки "Назад"
@dp.callback_query_handler(lambda call: call.data == "back", state=AdminEditProfile.reason)
async def handle_back_from_reason(call: CallbackQuery, state: FSMContext):
    await call.message.delete()  # Удаляем сообщение с кнопками
    await call.message.answer(
        "Выберите действие:", reply_markup=await get_start_menu())  # Возвращаемся на главное меню
    await state.finish()  # Завершаем состояние


'''КОМАНДЫ ДЛЯ РЕГИСТРАЦИИ'''
# Определение CallbackData для этапов регистрации
mentor_select_callback = CallbackData("mentor_select", "action", "mentor_id")


@dp.message_handler(lambda message: message.text == 'Регистрация участника')
async def process_user_mentor_id(message: Message, state: FSMContext):
    username = message.from_user.first_name

    # Сохранение данных в state
    async with state.proxy() as data:
        data['telegram_id'] = message.from_user.id
        data['username'] = message.from_user.username
        data['first_name'] = message.from_user.first_name
    # Показать inline кнопки с наставниками
    mentors = session.query(Mentor).all()
    # logging.info(f"Менторы {mentors} найдены в базе данных")
    mentor_buttons = []
    for mentor in mentors:
        mentor_class = session.query(User).filter_by(account_id=mentor.mentor_account_id).first()
        if mentor_class is not None:
            # logging.info(f"Ментор инфо {mentor_class}")
            mentor_hero_class = mentor_class.hero_class
            mentor_buttons.append(
                InlineKeyboardButton(
                    f"{mentor.mentor_nickname} ({mentor_hero_class}) - учеников:{mentor.mentor_number_of_students}",
                    callback_data=mentor_select_callback.new(action="select",
                                                             mentor_id=mentor.id))
            )
    keyboard = InlineKeyboardMarkup(row_width=1).add(*mentor_buttons)
    keyboard.add(
        InlineKeyboardButton("🔴Отмена", callback_data=mentor_select_callback.new(action="cancel", mentor_id=0)))
    await message.reply(config.register_message_stage_1, reply_markup=keyboard, parse_mode='HTML')


@dp.callback_query_handler(mentor_select_callback.filter(action=["select", "cancel"]))
async def process_mentor_selection(call: CallbackQuery, state: FSMContext, callback_data: dict):
    action = callback_data['action']
    # обрабатываем кнопку Отмена
    if action == "cancel":
        await call.message.delete()
        await call.message.answer("Вы отменили регистрацию и возвращены в главное меню",
                                  reply_markup=await get_start_menu())
        await call.answer()
        await state.finish()
        # Добавьте здесь необходимую логику для выхода с этапа
        # Например, вывод сообщения пользователю, переход на другой этап и т.д.
        return

    mentor_id = int(callback_data['mentor_id'])
    # Получаем профиль Наставника
    if action == "select":
        mentor = session.query(Mentor).filter_by(id=mentor_id).first()
        if mentor:
            profile_text_mentor = ""
            # Получение данных о связи с ментором
            mentor_account_id = mentor.mentor_account_id

            # Получение информации о профиле Героя Наставника
            if mentor_account_id:
                mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                profile_text_mentor_hero = "<b>О персонаже:</b>\n"
                if mentor_user_data:
                    profile_text_mentor_hero += f"Класс: {mentor_user_data.hero_class}\n"
                    profile_text_mentor_hero += f"Ник: <code>{mentor_user_data.nickname}</code>\n"
                    profile_text_mentor_hero += f"ID в игре: <code>{mentor_user_data.account_id}</code>\n"
                    profile_text_mentor_hero += '<blockquote>Можешь прямо сейчас скопировать ID, просто нажав на него,' \
                                                ' и просмотреть наставника в игре: "<b>Друзья</b>" —> ' \
                                                '"<b>Добавить</b>".</blockquote>'
                    profile_text_mentor = profile_text_mentor_hero
                    profile_text_mentor += "\n\n<b>О наставнике:</b>\n"
                    profile_text_mentor += f"Имя: {mentor_user_data.first_name}\n"
                else:
                    profile_text_mentor_hero += "Персонаж не найден\n"
            else:
                profile_text_mentor += "Персонаж не найден\n"

            if mentor_account_id:
                mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                if mentor_user_data:
                    mentor_username = mentor_user_data.username
                    profile_text_mentor += f"Профиль tg: @{mentor_username}\n"
                else:
                    profile_text_mentor += f"Профиль tg: Не найдена\n"
            else:
                profile_text_mentor += f"Профиль tg: Не указана\n"
            # (Логика для получения и отображения профиля наставника с помощью существующей функции 'profile_type')
            profile_text_mentor += f"Время онлайн: {mentor.mentor_time_online}\n"
            profile_text_mentor += f"Сильные стороны: {mentor.mentor_interest}\n"
            profile_text_mentor += f"Количество учеников: {mentor.mentor_number_of_students}\n"
            profile_text_mentor += f"Немного о наставнике: {mentor.mentor_characteristic}\n"
            # кнопки "Подтвердить" и "Сменить" в разметку ответа
            reply_markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("Подтвердить",
                                     callback_data=mentor_select_callback.new(action="confirm", mentor_id=mentor_id)),
                InlineKeyboardButton("Сменить",
                                     callback_data=mentor_select_callback.new(action="change", mentor_id=mentor_id)),
            )
            # logging.info(f"DATA process_mentor_selection:  {state.proxy()}")
            await call.message.edit_text(text=profile_text_mentor, reply_markup=reply_markup, parse_mode='HTML')
            await call.answer()
        else:
            await call.answer("Профиль Наставника не найден.")


@dp.callback_query_handler(mentor_select_callback.filter(action=["confirm"]))
async def process_mentor_confirm(call: CallbackQuery, state: FSMContext, callback_data: dict):
    action = callback_data['action']
    mentor_id = int(callback_data['mentor_id'])

    # СОХРАНЯЕМ mentor_id В state ПЕРЕД ПЕРЕХОДОМ В ДРУГОЕ СОСТОЯНИЕ
    async with state.proxy() as data:
        data['mentor_id'] = mentor_id
    # logging.info(f"DATA process_mentor_confirm:  {data}")
    # logging.info(f"ID MENTOR:  {data['mentor_id']}")
    await state.set_state(Registration.nickname.state)  # Переход в Registration.nickname.state
    await call.answer()

    # ЗАПУСКАЕМ registration_start
    await registration_start(call.message, state)


@dp.message_handler(state=Registration.nickname)
async def registration_start(message: Message, state: FSMContext):
    # Сохранение данных в state
    async with state.proxy() as data:
        username = data['first_name']
        await message.answer_photo(
            photo=open('image/reg_user_2.jpg', 'rb'),
            caption=config.register_message_stage_2,
            parse_mode='HTML'
        )
        # message = message.text
        # logging.info(f"message:  {message}")

    # logging.info(f"DATA1:  {data}")
    await state.set_state(Registration.hero_class)


@dp.message_handler(state=Registration.hero_class)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text

    # Проверка на запрещённый символ "/"
    if nickname.startswith('/') and nickname != '/cancel':
        await message.reply(config.register_message_stage_2_error, parse_mode='HTML')
        return  # Выход из обработчика, если ник неверный

    if nickname != '/cancel':
        # Сохранение ника и переход к выбору класса
        async with state.proxy() as data:
            data['nickname'] = nickname

        await message.reply(config.register_message_stage_3,
                            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                                types.KeyboardButton("\U0001FA93Берсерк"),
                                types.KeyboardButton("\u2695Друид"),
                                types.KeyboardButton("\U0001F3F9Лучница")
                            ),
                            parse_mode='HTML')
        await state.set_state(Registration.hero_class2.state)
        # logging.info(f"DATA process_nickname:  {data}")
    elif nickname == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


@dp.message_handler(state=Registration.hero_class2)
async def process_hero_class(message: types.Message, state: FSMContext):
    if message.text not in ['\U0001FA93Берсерк', '\u2695Друид', '\U0001F3F9Лучница'] and message.text != '/cancel':
        await message.reply("Выберите класс из предложенных кнопок!")
        return

    hero_class = message.text.replace('\U0001FA93', '').replace('\u2695', '').replace('\U0001F3F9', '')

    # Проверка на запрещённый символ "/"
    if hero_class.startswith('/') and hero_class != '/cancel':
        await message.reply(config.register_message_stage_3_error, parse_mode='HTML')
        return  # Выход из обработчика, если класс неверный

    if hero_class != '/cancel':
        # Сохраняем данные в БД
        async with state.proxy() as data:
            data['hero_class'] = hero_class
        with open('image/reg_user_3.jpg', 'rb') as reg_user_3_photo:
            await message.answer_photo(
                photo=reg_user_3_photo,
                caption=config.register_message_stage_4,
                parse_mode='HTML'
            )
        await Registration.account_id.set()
        # logging.info(f"DATA process_hero_class:  {data}")
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

    # Проверка на команду /cancel
    if account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")
        return

    # Проверка на запрещённый символ "/"
    if account_id.startswith('/') and account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный

    # Проверка на корректный ID
    if not (
            account_id.isdigit() and
            len(account_id) == 11 and  # Проверка длины не более 11 символов
            account_id.endswith('160') and
            int(account_id) > 0
    ):
        await message.reply(config.register_message_stage_4_error, parse_mode='HTML')
        return  # Выход из обработчика, если ID неверный

    # Проверка на уникальность account_id
    existing_user = session.query(User).filter_by(account_id=message.text).first()
    if existing_user:
        await message.reply(f"Пользователь с таким ID в игре уже зарегистрирован!\n"
                            f"Его имя: {existing_user.first_name}\n"
                            f"Его tg: @{existing_user.username}\n"
                            f"Ник: {existing_user.nickname}\n"
                            f"Класс: {existing_user.hero_class}"
                            f"\n\n Регистрация завершена. Для помощи обратись к @VovaM")
        await state.finish()
        return

    # Сохранение данных в state
    async with state.proxy() as data:
        data['account_id'] = account_id
        data['guild'] = 'AcademAURI'  # Автоматически задаем гильдию
        data['status'] = '\U0001F7E2Active'
        # logging.info(f"DATA process_account_id:  {data}")
    # Запрос фотографии
    await message.reply(config.register_message_stage_5, parse_mode='HTML')
    await Registration.photo.set()


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
            # Сохраняем путь к файлу
            data['photo'] = os.path.join(save_path, unique_filename)
            # logging.info(f"DATA process_photo:  {data}")
            # Получаем old_students_count из таблицы Mentors
            id_mentor = data['mentor_id']
            selected_mentor = session.query(Mentor).filter_by(id=id_mentor).first()
            old_students_count = selected_mentor.mentor_number_of_students
            mentor_nickname = selected_mentor.mentor_nickname
            # Получаем ТГ наставника для сообщения
            mentor_data = session.query(User).filter_by(account_id=selected_mentor.mentor_account_id).first()
            if mentor_data:
                tg_mentor = mentor_data.username
            # logging.info(f"У {mentor_nickname} было - {old_students_count}")  # for Debug -> delete after

            try:
                # Получаем количество подопечных до обновления
                # old_students_count = session.query(User).filter_by(mentor_id=mentor.id).count()

                # сохраняем данные в БД
                user = User(
                    telegram_id=data['telegram_id'],  # id пользователя tg
                    username=data['username'],  # тег пользователя tg
                    first_name=data['first_name'],  # Имя аккаунта tg
                    nickname=data['nickname'],
                    hero_class=data['hero_class'],
                    account_id=data['account_id'],  # id аккаунта в игре
                    photo=data['photo'],
                    guild=data['guild'],
                    mentor_id=data['mentor_id'],
                    date_registration=datetime.now(),
                    status=data['status']  # Может иметь 3 значения:
                    # active (активный участник ги);
                    # absense (отпуск)
                    # и offline (инактив)
                )
                session.add(user)
                session.commit()

                # logging.info(
                #     f"Пользователь {message.from_user.first_name} (username:{message.from_user.username}, "
                #     f"ID: {message.from_user.id}) успешно завершил регистрацию."
                # )
                text_message = config.register_message_stage_final + "\n\n" + f"{data['first_name']}, я уже приступил " \
                                                                              'к своим обязанностям и ' \
                                                                              f'сообщил твоему наставнику: ' \
                                                                              f'<b>{mentor_nickname}</b>, что ему нужно ' \
                                                                              f'с тобой связаться. ' \
                                                                              f'\n\nОбычно наставники отвечают достаточно '\
                                                                              f'быстро, но не мгновенно. Просто подожди ' \
                                                                              f'пока он тебе напишет или напиши ему:' \
                                                                              f'@{tg_mentor}, если ты сомневаешься, ' \
                                                                              f'что {mentor_nickname} получил сообщение.'
                with open('image/end_registration_user.jpg', 'rb') as reg_user_end_photo:
                    await message.answer_photo(
                        photo=reg_user_end_photo,
                        caption=text_message,
                        parse_mode='HTML'
                    )
                await state.finish()
                from script_db import update_students  # Вызов скрипта для функции обновления данных в таблице Mentors
                await update_students()  # Обновление данных таблице Mentors

                # Получаем количество подопечных после обновления
                new_students_count = session.query(Mentor).filter_by(id=selected_mentor.id).first() \
                    .mentor_number_of_students
                # logging.info("Функция update_students - успешно выполнена")
                # logging.info(f"У {mentor_nickname} стало - {new_students_count}")  # for Debug -> delete after
                # session.close()  # Закрываем сеанс с БД после завершения регистрации
                # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
                #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
                change_students_member_text = f"Наставник {mentor_nickname} (ID: {id_mentor}) - " \
                                              f"Количество подопечных: {old_students_count} -> {new_students_count}"
                await bot.send_message(config.id_leader, change_students_member_text)

                # Отправка сообщения выбранному ментору
                mentor_account_id = selected_mentor.mentor_account_id
                if mentor_account_id:
                    mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
                    if mentor_user_data:
                        mentor_telegram_id = mentor_user_data.telegram_id
                        if mentor_telegram_id is not None and mentor_telegram_id != "":
                            try:
                                mentor_username = mentor_user_data.username
                                mentor_nickname = mentor_user_data.nickname
                                # mentor_message = f"Участник {user.nickname} с гильдии {user.guild} " \
                                #                  f"выбрал Вас в качестве своего наставника." \
                                #                  f"\n\nДля связи с учеником используйте @{user.username}"
                                profile_user_text = "<b>Профиль участника:</b>"
                                profile_user_text += f"\nИмя: {data['first_name']}"
                                profile_user_text += f"\ntelegram: @{data['username']}"
                                profile_user_text += f"\n\nНикнейм: <code>{data['nickname']}</code>"
                                profile_user_text += f"\nКласс героя: <b>{data['hero_class']}</b>"
                                profile_user_text += f"\nID аккаунта: <code>{data['account_id']}</code>"
                                profile_user_text += f"\n\nГильдия: <b>{data['guild']}</b>"
                                profile_user_text += "\n<blockquote>Не забудь перевести ученика в основной клан, " \
                                                     "как он будет готов. Сделать это можно вбив его ID и выбрать " \
                                                     "нужную команду в карточке участника</blockquote>"
                                mentor_message = config.mentor_notification_message + "\n\n" + profile_user_text
                                profile_photo_user = data['photo']
                                if profile_photo_user:
                                    try:
                                        with open(profile_photo_user, 'rb') as user_profile_photo:
                                            await bot.send_photo(
                                                mentor_telegram_id,
                                                photo=user_profile_photo,
                                                caption=mentor_message,
                                                parse_mode='HTML'
                                            )
                                    except Exception as e:
                                        logging.error(
                                            f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")

                                notification_guild = "<b>Ура! У нас пополнение🥰</b>" \
                                                     f"\n\nТеперь <b>{data['first_name']}</b> с нами!" \
                                                     f"\ntelegram: @{data['username']}" \
                                                     "\nПоприветствуйте нового члена нашей дружной команды лично " \
                                                     "и поделитесь премудростями игры и клана. Расскажите что " \
                                                     "лучше сделать, чтобы быстрее попасть в <b>AURI!</b>" \
                                                     "\n\n<b>О Бессмертном:</b>" \
                                                     f"\nНикнейм: <code>{data['nickname']}</code>" \
                                                     f"\nКласс героя: <b>{data['hero_class']}</b>" \
                                                     f"\nID аккаунта: <code>{data['account_id']}</code>" \
                                                     f"\n\nНаставник: {mentor_nickname}"
                                profile_photo_user = data['photo']
                                if profile_photo_user:
                                    try: # НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
                                        with open(profile_photo_user, 'rb') as user_profile_photo:
                                            await bot.send_photo(
                                                config.officer_chat_id,
                                                photo=user_profile_photo,
                                                caption=notification_guild,
                                                parse_mode='HTML',
                                                message_thread_id=config.office_mentor_thread_id
                                            )
                                    except Exception as e:
                                        logging.error(
                                            f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")

                            except Exception as e:
                                logging.error(
                                    f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")

                # Возврат на главное меню
                await bot.send_message(message.from_user.id, "Регистрация завершена! Спасибо! Вы возвращены "
                                                             "в главное меню", reply_markup=await get_start_menu())
                session.close()  # Закрытие сессии после отправки сообщений

            except Exception as e:
                logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
                await bot.send_message(message.from_user.id, "При сохранении данных произошла ошибка, обратитесь "
                                                             "к Администратору", reply_markup=await get_start_menu())
                session.close()  # Закрываем сеанс с БД после завершения регистрации

    elif message.text:
        # Проверяем на команды /cancel и /next
        if message.text.lower() == '/cancel':
            await state.finish()  # Завершаем состояние
            await message.reply("Регистрация отменена.")
            return
        elif message.text.lower() == '/next':
            try:
                async with state.proxy() as data:
                    # logging.info(f"DATA process_photo:  {data}")
                    # Получаем old_students_count из таблицы Mentors
                    id_mentor = data['mentor_id']
                    selected_mentor = session.query(Mentor).filter_by(id=id_mentor).first()
                    old_students_count = selected_mentor.mentor_number_of_students
                    mentor_nickname = selected_mentor.mentor_nickname
                    mentor_data = session.query(User).filter_by(account_id=selected_mentor.mentor_account_id).first()
                    if mentor_data:
                        tg_mentor = mentor_data.username
                    # Получаем количество подопечных до обновления
                    # old_students_count = session.query(User).filter_by(mentor_id=mentor.id).count()

                    # сохраняем данные в БД
                    user = User(
                        telegram_id=data['telegram_id'],  # id пользователя tg
                        username=data['username'],  # тег пользователя tg
                        first_name=data['first_name'],  # Имя аккаунта tg
                        nickname=data['nickname'],
                        hero_class=data['hero_class'],
                        account_id=data['account_id'],  # id аккаунта в игре
                        guild=data['guild'],
                        mentor_id=data['mentor_id'],
                        date_registration=datetime.now(),
                        status=data['status']  # Может иметь 3 значения:
                        # active (активный участник ги);
                        # absense (отпуск)
                        # и offline (инактив)
                    )
                    session.add(user)
                    session.commit()

                    # logging.info(
                    #     f"Пользователь {message.from_user.first_name} (username:{message.from_user.username}, "
                    #     f"ID: {message.from_user.id}) успешно завершил регистрацию."
                    # )
                    text_message = config.register_message_stage_final + "\n\n" + f"{data['first_name']}, я уже приступил " \
                                                                                  'к своим обязанностям и ' \
                                                                                  f'сообщил твоему наставнику: ' \
                                                                                  f'<b>{mentor_nickname}</b>, что ему нужно ' \
                                                                                  f'с тобой связаться. ' \
                                                                                  f'\n\nОбычно наставники отвечают достаточно ' \
                                                                                  f'быстро, но не мгновенно. Просто подожди ' \
                                                                                  f'пока он тебе напишет или напиши ему:' \
                                                                                  f'@{tg_mentor}, если ты сомневаешься, ' \
                                                                                  f'что {mentor_nickname} получил сообщение.'
                    with open('image/end_registration_user.jpg', 'rb') as reg_user_end_photo:
                        await message.answer_photo(
                            photo=reg_user_end_photo,
                            caption=text_message,
                            parse_mode='HTML'
                        )
                    await state.finish()
                    from script_db import \
                        update_students  # Вызов скрипта для функции обновления данных в таблице Mentors
                    await update_students()  # Обновление данных таблице Mentors

                    # Получаем количество подопечных после обновления
                    new_students_count = session.query(Mentor).filter_by(id=selected_mentor.id).first() \
                        .mentor_number_of_students
                    logging.info("Функция update_students - успешно выполнена")
                    # logging.info(f"У {mentor_nickname} стало - {new_students_count}")  # for Debug -> delete after
                    # session.close()  # Закрываем сеанс с БД после завершения регистрации
                    # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
                    #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
                    change_students_member_text = f"Наставник {mentor_nickname} (ID: {id_mentor}) - " \
                                                  f"Количество подопечных: {old_students_count} -> {new_students_count}"
                    await bot.send_message(config.id_leader, change_students_member_text)

                    # Отправка сообщения выбранному ментору
                    mentor_account_id = selected_mentor.mentor_account_id
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
                                                     f"\n\nДля связи с учеником используйте @{user.username}"
                                    profile_user_text = "<b>Профиль участника:</b>"
                                    profile_user_text += f"\nИмя: {data['first_name']}"
                                    profile_user_text += f"\ntelegram: @{data['username']}"
                                    profile_user_text += f"\n\nНикнейм: <code>{data['nickname']}</code>"
                                    profile_user_text += f"\nКласс героя: <b>{data['hero_class']}</b>"
                                    profile_user_text += f"\nID аккаунта: <code>{data['account_id']}</code>"
                                    profile_user_text += f"\n\nГильдия: <b>{data['guild']}</b>"
                                    profile_user_text += "\n<blockquote>Не забудь перевести ученика в основной клан, " \
                                                         "как он будет готов. Сделать это можно вбив его ID и выбрать " \
                                                         "нужную команду в карточке участника</blockquote>"
                                    mentor_message = config.mentor_notification_message + "\n\n" + profile_user_text
                                    try:
                                        await bot.send_message(
                                            mentor_telegram_id,
                                            text=mentor_message,
                                            parse_mode='HTML'
                                        )
                                    except Exception as e:
                                        logging.error(
                                            f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")
                                    notification_guild = "<b>Ура! У нас пополнение🥰</b>" \
                                                         f"\n\nТеперь <b>{data['first_name']}</b> с нами!" \
                                                         f"\ntelegram: @{data['username']}" \
                                                         "\nПоприветствуйте нового члена нашей дружной команды лично " \
                                                         "и поделитесь премудростями игры и клана. Расскажите что " \
                                                         "лучше сделать, чтобы быстрее попасть в <b>AURI!</b>" \
                                                         "\n\n<b>О Бессмертном:</b>" \
                                                         f"\nНикнейм: <code>{data['nickname']}</code>" \
                                                         f"\nКласс героя: <b>{data['hero_class']}</b>" \
                                                         f"\nID аккаунта:: <code>{data['account_id']}</code>" \
                                                         f"\n\nНаставник: {mentor_nickname}"
                                    try: # НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
                                        await bot.send_message(
                                            chat_id=config.officer_chat_id,
                                            text=notification_guild,
                                            message_thread_id=config.office_mentor_thread_id,
                                            parse_mode='HTML'
                                        )
                                    except Exception as e:
                                        logging.error(
                                            f"При отправке сообщения Офицерам - произошла ошибка - [{e}]")

                                except Exception as e:
                                    logging.error(
                                        f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")
                await bot.send_message(message.from_user.id, "Регистрация завершена! Спасибо! Вы возвращены "
                                                             "в главное меню", reply_markup=await get_start_menu())
                session.close()  # Закрытие сессии после отправки сообщений
                await state.finish()  # Завершаем состояние
            except Exception as e:
                logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
                await bot.send_message(message.from_user.id, "При сохранении данных произошла ошибка, обратитесь "
                                                             "к Администратору", reply_markup=await get_start_menu())
                session.close()  # Закрываем сеанс с БД после завершения регистрации
                await state.finish()  # Завершаем состояние

        # Проверяем, является ли сообщение текстовым
        elif message.text.lower() != '/next' or message.text.lower() != '/cancel':
            await message.reply("На этом этапе доступна только загрузка фотографии или команды:"
                                "\n/cancel - для отмены и выхода из регистрации"
                                "\n/next - для пропуска этапа, если сейчас нет фотографии для профиля")
            return

    else:
        # Если сообщение не текст и не фото, выводим ошибку
        await message.reply("Неверный тип сообщения. Пожалуйста, загрузите фотографию.")


# Команда регистрации Пользователей
# @dp.message_handler(commands=['reg'], state=None)
# @dp.message_handler(lambda message: message.text == 'Регистрация участника')
# async def registration_start(message: types.Message, state: FSMContext):
#     # Автоматически получаем nickname и id из информации об аккаунте telegram user
#     username = message.from_user.first_name
#
#     async with state.proxy() as data:
#         data['telegram_id'] = message.from_user.id
#         data['username'] = message.from_user.username
#         data['first_name'] = message.from_user.first_name
#     with open('image/reg_user_2.jpg', 'rb') as reg_user_2_photo:
#         await message.answer_photo(
#             photo=reg_user_2_photo,
#             caption=f'Привет! {username}. Давай зарегистрируем тебя.\n'
#                     'Какой у тебя Ник в игре?'
#                     '\n\nДля отмены или выхода из регистрации введи /cancel'
#         )
#     logging.info(f"DATA1:  {data}") # delete
#     await state.set_state(Registration.nickname.state)
#
#
# @dp.message_handler(state=Registration.nickname)
# async def process_nickname(message: types.Message, state: FSMContext):
#     nickname = message.text
#
#     # Проверка на запрещённый символ "/"
#     if nickname.startswith('/') and nickname != '/cancel':
#         await message.reply("Неверно. Ник не должен начинаться с символа /")
#         return  # Выход из обработчика, если ник неверный
#
#     if nickname != '/cancel':
#         # Сохранение ника и переход к выбору класса
#         async with state.proxy() as data:
#             data['nickname'] = nickname
#
#         await message.reply("Прекрасно! Теперь выбери класс, в котором ты играешь:",
#                             reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
#                                 types.KeyboardButton("\U0001FA93Берсерк"),
#                                 types.KeyboardButton("\u2695Друид"),
#                                 types.KeyboardButton("\U0001F3F9Лучница")
#                             ))
#         await Registration.hero_class.set()
#         logging.info(f"DATA2:  {data}")
#     elif nickname == '/cancel':
#         await state.finish()
#         await message.reply("Регистрация отменена!")
#
#     # Устанавливаем таймаут для ответа 5 минут
#     # await asyncio.sleep(300)
#     # await message.reply("Извини, но ты слишком долго не отвечал. Регистрация отменена.")
#     # await state.finish()
#
#
# @dp.message_handler(state=Registration.hero_class)
# async def process_hero_class(message: types.Message, state: FSMContext):
#     if message.text not in ['\U0001FA93Берсерк', '\u2695Друид', '\U0001F3F9Лучница'] and message.text != '/cancel':
#         await message.reply("Выберите класс из предложенных кнопок!")
#         return
#
#     hero_class = message.text.replace('\U0001FA93', '').replace('\u2695', '').replace('\U0001F3F9', '')
#
#     # Проверка на запрещённый символ "/"
#     if hero_class.startswith('/') and hero_class != '/cancel':
#         await message.reply("Неверно. Класс не должен начинаться с символа /")
#         return  # Выход из обработчика, если класс неверный
#
#     if hero_class != '/cancel':
#         # Сохраняем данные в БД
#         async with state.proxy() as data:
#             data['hero_class'] = hero_class
#         with open('image/reg_user_3.jpg', 'rb') as reg_user_3_photo:
#             await message.answer_photo(
#                 photo=reg_user_3_photo,
#                 caption='Отлично! Теперь напиши свой ID в игре:'
#             )
#         await Registration.account_id.set()
#         logging.info(f"DATA3:  {data}")
#     elif hero_class == '/cancel':
#         await state.finish()
#         await message.reply("Регистрация отменена!")
#
#     # Устанавливаем таймаут для ответа 5 минут
#     # await asyncio.sleep(300)
#     # await message.reply("Извини, но ты слишком долго не отвечал. Регистрация отменена.")
#     # await state.finish()
#
#
# @dp.message_handler(state=Registration.account_id)
# async def process_account_id(message: types.Message, state: FSMContext):
#     account_id = message.text
#
#     # Проверка на команду /cancel
#     if account_id == '/cancel':
#         await state.finish()
#         await message.reply("Регистрация отменена!")
#         return
#
#     # Проверка на запрещённый символ "/"
#     if account_id.startswith('/') and account_id != '/cancel':
#         await message.reply("Неверно. ID не должен начинаться с символа /")
#         return  # Выход из обработчика, если ID неверный
#
#     # Проверка на корректный ID
#     if not (
#             account_id.isdigit() and
#             len(account_id) == 11 and  # Проверка длины не более 11 символов
#             account_id.endswith('160') and
#             int(account_id) > 0
#     ):
#         await message.reply(
#             "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
#         return  # Выход из обработчика, если ID неверный
#
#     # Проверка на уникальность account_id
#     existing_user = session.query(User).filter_by(account_id=message.text).first()
#     if existing_user:
#         await message.reply(f"Пользователь с таким ID в игре уже зарегистрирован!\n"
#                             f"Его имя: {existing_user.first_name}\n"
#                             f"Его tg: @{existing_user.username}\n"
#                             f"Ник: {existing_user.nickname}\n"
#                             f"Класс: {existing_user.hero_class}"
#                             f"\n\n Регистрация завершена. Для помощи обратитесь к Администратору!")
#         await state.finish()
#         return
#
#     # Сохранение данных в state
#     async with state.proxy() as data:
#         data['account_id'] = account_id
#         data['guild'] = 'AcademAURI'  # Автоматически задаем гильдию
#         data['status'] = '\U0001F7E2Active'
#         logging.info(f"DATA4:  {data}")
#     # Запрос фотографии
#     await message.reply("Загрузите свою фотографию:"
#                         "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
#     await Registration.photo.set()
#
#
# @dp.message_handler(content_types=['photo', 'text'], state=Registration.photo)
# async def process_photo(message: types.Message, state: FSMContext):
#     if message.photo:
#         # Скачиваем фотографию, если сообщение не команда и не текст
#         photo = message.photo[-1]  # Берем последнюю фотографию (самую большую)
#         file_id = photo.file_id
#         file_path = await bot.get_file(file_id)
#         file_name = file_path['file_path']
#         await photo.download(destination_file=file_name)
#
#         # Определяем путь для сохранения файла
#         save_path = 'photos_profile/users'
#         os.makedirs(save_path, exist_ok=True)  # Создаем директорию, если ее нет
#
#         # Скачиваем файл в заданную директорию
#         await photo.download(destination_file=os.path.join(save_path, file_name))
#
#         # Генерируем уникальное имя для файла
#         unique_filename = str(uuid.uuid4()) + os.path.splitext(file_name)[1]
#
#         # Переименовываем файл
#         os.rename(os.path.join(save_path, file_name), os.path.join(save_path, unique_filename))
#         # Удаляем загруженный файл из \photos
#         os.remove(file_name)
#         # Сохраняем путь к фотографии в данные состояния
#         async with state.proxy() as data:
#             # Сохраняем путь к файлу
#             data['photo'] = os.path.join(save_path, unique_filename)
#             logging.info(f"DATA process_photo:  {data}")
#         # Переходим к выбору наставника
#         await state.set_state(Registration.user_mentor_id.state)
#         await process_user_mentor_id(message, state)
#
#
#
#     elif message.text:
#         # Проверяем на команды /cancel и /next
#         if message.text.lower() == '/cancel':
#             await state.finish()  # Завершаем состояние
#             await message.reply("Регистрация отменена.")
#             return
#         elif message.text.lower() == '/next':
#             await state.finish()  # Завершаем состояние
#             await process_user_mentor_id(message, state)
#             return
#
#         # Проверяем, является ли сообщение текстовым
#         elif message.text.lower() != '/next' or message.text.lower() != '/cancel':
#             await message.reply("На этом этапе доступна только загрузка фотографии или команды:"
#                                 "\n/cancel - для отмены и выхода из регистрации"
#                                 "\n/next - для пропуска этапа, если сейчас нет фотографии для профиля")
#             return
#     else:
#         # Если сообщение не текст и не фото, выводим ошибку
#         await message.reply("Неверный тип сообщения. Пожалуйста, загрузите фотографию.")
#
#
#
# @dp.message_handler(state=Registration.user_mentor_id)
# async def process_user_mentor_id(message: types.Message, state: FSMContext):
#     current_state = await state.get_state()  # Проверка состояния
#     logging.info(f"КАКОЙ СТАТУС {current_state}")
#     async with state.proxy() as data:
#         logging.info(f"DATA user_mentor_id:  {data}")
#     # Показать inline кнопки с наставниками
#     mentors = session.query(Mentor).all()
#     mentor_buttons = [
#         InlineKeyboardButton(mentor.mentor_nickname, callback_data=mentor_select_callback.new(action="select",
#                                                                                               mentor_id=mentor.id))
#         for mentor in mentors
#     ]
#     keyboard = InlineKeyboardMarkup(row_width=1).add(*mentor_buttons)
#
#     await message.reply("Выберите наставника:", reply_markup=keyboard)
#     # await state.finish()
#     print(mentor_select_callback)
#
#
# @dp.callback_query_handler(mentor_select_callback.filter(action=["select"]))
# async def process_mentor_selection(call: CallbackQuery, state: FSMContext, callback_data: dict):
#     action = callback_data['action']
#     mentor_id = int(callback_data['mentor_id'])
#     # Получаем профиль Наставника
#     mentor = session.query(Mentor).filter_by(id=mentor_id).first()
#     if mentor:
#         # ... (Логика для получения и отображения профиля наставника с помощью существующей функции 'profile_type')
#         profile_text_mentor = f"Профиль Наставника:\n"
#         # Получение данных о связи с ментором
#         mentor_account_id = mentor.mentor_account_id
#         if mentor_account_id:
#             mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
#             if mentor_user_data:
#                 mentor_username = mentor_user_data.username
#                 profile_text_mentor += f"Связь: @{mentor_username}\n"
#             else:
#                 profile_text_mentor += f"Связь: Не найдена\n"
#         else:
#             profile_text_mentor += f"Связь: Не указана\n"
#
#         # Вывод остальных данных о менторе
#         profile_text_mentor += f"Ник: {mentor.mentor_nickname}\n"
#
#         # Получение класса героя ментора
#         if mentor_account_id:
#             mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
#             if mentor_user_data:
#                 profile_text_mentor += f"Класс: {mentor_user_data.hero_class}\n"
#             else:
#                 profile_text_mentor += f"Класс: Не найдена\n"
#         else:
#             profile_text_mentor += f"Класс: Не указан\n"
#
#         profile_text_mentor += f"Знает: {mentor.mentor_interest}\n"
#         profile_text_mentor += f"Количество учеников: {mentor.mentor_number_of_students}\n"
#         profile_text_mentor += f"Время онлайн: {mentor.mentor_time_online}\n"
#         profile_text_mentor += f"Характеристика: {mentor.mentor_characteristic}\n"
#         # ... (Добавить кнопки "Подтвердить" и "Сменить" в разметку ответа)
#         reply_markup = InlineKeyboardMarkup(row_width=1).add(
#             InlineKeyboardButton("Подтвердить",
#                                  callback_data=mentor_select_callback.new(action="confirm", mentor_id=mentor_id)),
#             InlineKeyboardButton("Сменить",
#                                  callback_data=mentor_select_callback.new(action="change", mentor_id=mentor_id)),
#         )
#         logging.info(f"DATA process_mentor_selection:  {state.proxy()}")
#         await call.message.edit_text(text=profile_text_mentor, reply_markup=reply_markup)
#         await call.answer()
#     else:
#         await call.answer("Профиль Наставника не найден.")
#
#
# @dp.callback_query_handler(mentor_select_callback.filter(action=["confirm"]))
# async def process_mentor_confirm(call: CallbackQuery, state: FSMContext, callback_data: dict):
#     action = callback_data['action']
#     mentor_id = int(callback_data['mentor_id'])
#     # await state.update_data(mentor_id=mentor_id)
#     current_state = await state.get_state()
#     # Проверка состояния
#     logging.info(f"current_state:  {current_state}")
#     await state.finish()
#
#     async with state.proxy() as data:
#         logging.info(f"DATA END:  {data}")

# data['mentor_id'] = mentor_id
# mentor = session.query(Mentor).filter_by(id=mentor_id).first()
# # Получаем old_students_count из таблицы Mentors
# old_students_count = session.query(Mentor).filter_by(id=mentor_id).first().mentor_number_of_students
# selected_mentor = mentor
# # logging.info(f"У {mentor_nickname} было - {old_students_count}")  # for Debug -> delete after
# try:
#     # Получаем количество подопечных до обновления
#     # old_students_count = session.query(User).filter_by(mentor_id=mentor.id).count()
#
#     # сохраняем данные в БД
#     user = User(
#         telegram_id=data['telegram_id'],  # id пользователя tg
#         username=data['username'],  # тег пользователя tg
#         first_name=data['first_name'],  # Имя аккаунта tg
#         nickname=data['nickname'],
#         hero_class=data['hero_class'],
#         account_id=data['account_id'],  # id аккаунта в игре
#         photo=data['photo'],
#         guild=data['guild'],
#         mentor_id=data['user_mentor_id'],
#         date_registration=datetime.now(),
#         status=data['status']  # Может иметь 3 значения:
#         # active (активный участник ги);
#         # absense (отпуск)
#         # и offline (инактив)
#     )
#     session.add(user)
#     session.commit()
#
#     logging.info(
#         f"Пользователь {call.from_user.first_name} (username:{call.from_user.username}, "
#         f"ID: {call.from_user.id}) успешно завершил регистрацию."
#     )
#
#     await call.message.edit_text("Регистрация завершена! Спасибо за информацию!")
#     await state.finish()
#     from script_db import \
#         update_students  # Вызов скрипта для функции обновления данных в таблице Mentors
#     try:
#         await update_students()
#         logging.info("Функция update_students - успешно выполнена")# Обновление данных таблице Mentors
#     except Exception as e:
#         logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
#     # Получаем количество подопечных после обновления
#     new_students_count = session.query(Mentor).filter_by(id=selected_mentor.id).first() \
#         .mentor_number_of_students
#
#     # logging.info(f"У {mentor_nickname} стало - {new_students_count}")  # for Debug -> delete after
#     # session.close()  # Закрываем сеанс с БД после завершения регистрации
#     # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
#     #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
#     change_students_member_text = f"Наставник {mentor.mentor_nickname} (ID: {mentor.id}) - " \
#                                   f"Количество подопечных: {old_students_count} -> {new_students_count}"
#     await bot.send_message(config.id_leader, change_students_member_text)
#
#     # Отправка сообщения выбранному ментору
#     mentor_account_id = mentor.mentor_account_id
#     if mentor_account_id:
#         mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
#         if mentor_user_data:
#             mentor_telegram_id = mentor_user_data.telegram_id
#             if mentor_telegram_id is not None and mentor_telegram_id != "":
#                 try:
#                     mentor_username = mentor_user_data.username
#                     mentor_nickname = mentor_user_data.nickname
#                     mentor_message = f"Участник {user.nickname} с гильдии {user.guild} " \
#                                      f"выбрал Вас в качестве своего наставника." \
#                                      f"\n\nДля связи с учеником используйте @{user.username}"
#                     notification_guild = f"Участник {user.nickname} герой {user.hero_class} " \
#                                          f"с гильдии {user.guild}" \
#                                          f"выбрал качестве своего наставника{mentor_nickname}" \
#                                          f"\n\nДля связи с участником используйте @{user.username}"
#                     await bot.send_message(mentor_telegram_id, mentor_message)
#                     # await bot.send_message(config.officer_chat_id, notification_guild,
#                     #                        message_thread_id=config.office_mentor_thread_id) НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
#                 except Exception as e:
#                     logging.error(f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")
#     session.close()  # Закрытие сессии после отправки сообщения
# except Exception as e:
#     logging.error(f"При выполнении записи в БД - произошла ошибка - [{e}]")
#     session.close()  # Закрываем сеанс с БД после завершения регистрации


@dp.callback_query_handler(mentor_select_callback.filter(action=["change"]))
async def process_change_mentor(call: CallbackQuery, state: FSMContext, callback_data: dict):
    action = callback_data['action']
    if action == "change":
        # Отправить сообщение с кнопками наставников
        mentors = session.query(Mentor).filter().all()
        # logging.info(f"Менторы {mentors} найдены в базе данных")
        mentor_buttons = []
        for mentor in mentors:
            mentor_class = session.query(User).filter_by(account_id=mentor.mentor_account_id).first()
            if mentor_class is not None:
                # logging.info(f"Ментор инфо {mentor_class}")
                mentor_hero_class = mentor_class.hero_class
                mentor_buttons.append(
                    InlineKeyboardButton(
                        f"{mentor.mentor_nickname} ({mentor_hero_class})-учеников:{mentor.mentor_number_of_students}",
                        callback_data=mentor_select_callback.new(action="select",
                                                                 mentor_id=mentor.id))
                )
            else:
                logging.error(f"Ментор with account_id={mentor.mentor_account_id} не найден в базе данных Users")
        keyboard = InlineKeyboardMarkup(row_width=1).add(*mentor_buttons)
        keyboard.add(
            InlineKeyboardButton("🔴Отмена", callback_data=mentor_select_callback.new(action="cancel", mentor_id=0)))

        await call.message.edit_text(config.register_message_stage_1, reply_markup=keyboard, parse_mode='HTML')

    # @dp.message_handler(state=Registration.user_mentor_id)


# async def process_user_mentor_id(message: types.Message, state: FSMContext):
#     mentor_nickname = message.text
#
#     # Проверка на запрещённый символ "/"
#     if mentor_nickname.startswith('/') and mentor_nickname != '/cancel':
#         await message.reply("Неверно. Никнейм наставника не должен начинаться с символа /. "
#                             "Воспользуйся кнопками для выбора Наставника")
#         return  # Выход из обработчика, если никнейм неверный
#
#     mentor = session.query(Mentor).filter_by(mentor_nickname=message.text).first()
#     if not mentor and mentor_nickname != '/cancel':
#         await message.reply(f"Наставник с таким никнеймом не найден.\n"
#                             f"Выберите наставника из списка.")
#         return
#
#     if mentor_nickname != '/cancel':
#         async with state.proxy() as data:
#             data['user_mentor_id'] = mentor.id
#
#             # Получаем old_students_count из таблицы Mentors
#             old_students_count = session.query(Mentor).filter_by(id=mentor.id).first().mentor_number_of_students
#             selected_mentor = mentor
#             # logging.info(f"У {mentor_nickname} было - {old_students_count}")  # for Debug -> delete after
#
#             try:
#                 # Получаем количество подопечных до обновления
#                 # old_students_count = session.query(User).filter_by(mentor_id=mentor.id).count()
#
#                 # сохраняем данные в БД
#                 user = User(
#                     telegram_id=message.from_user.id,  # id пользователя tg
#                     username=message.from_user.username,  # тег пользователя tg
#                     first_name=message.from_user.first_name,  # Имя аккаунта tg
#                     nickname=data['nickname'],
#                     hero_class=data['hero_class'],
#                     account_id=data['account_id'],  # id аккаунта в игре
#                     photo=data['photo'],
#                     guild=data['guild'],
#                     mentor_id=data['user_mentor_id'],
#                     date_registration=datetime.now(),
#                     status=data['status']  # Может иметь 3 значения:
#                     # active (активный участник ги);
#                     # absense (отпуск)
#                     # и offline (инактив)
#                 )
#                 session.add(user)
#                 session.commit()
#
#                 logging.info(
#                     f"Пользователь {message.from_user.first_name} (username:{message.from_user.username}, "
#                     f"ID: {message.from_user.id}) успешно завершил регистрацию."
#                 )
#
#                 await message.reply("Регистрация завершена! Спасибо за информацию!")
#                 await state.finish()
#                 from script_db import update_students  # Вызов скрипта для функции обновления данных в таблице Mentors
#                 await update_students()  # Обновление данных таблице Mentors
#
#                 # Получаем количество подопечных после обновления
#                 new_students_count = session.query(Mentor).filter_by(id=selected_mentor.id).first() \
#                     .mentor_number_of_students
#                 logging.info("Функция update_students - успешно выполнена")
#                 # logging.info(f"У {mentor_nickname} стало - {new_students_count}")  # for Debug -> delete after
#                 # session.close()  # Закрываем сеанс с БД после завершения регистрации
#                 # logging.info(f"Наставник {mentor_nickname} (ID: {mentor.id}) - "
#                 #              f"Количество подопечных: {old_students_count} -> {new_students_count}")
#                 change_students_member_text = f"Наставник {mentor_nickname} (ID: {mentor.id}) - " \
#                                               f"Количество подопечных: {old_students_count} -> {new_students_count}"
#                 await bot.send_message(config.id_leader, change_students_member_text)
#
#                 # Отправка сообщения выбранному ментору
#                 mentor_account_id = mentor.mentor_account_id
#                 if mentor_account_id:
#                     mentor_user_data = session.query(User).filter_by(account_id=mentor_account_id).first()
#                     if mentor_user_data:
#                         mentor_telegram_id = mentor_user_data.telegram_id
#                         if mentor_telegram_id is not None and mentor_telegram_id != "":
#                             try:
#                                 mentor_username = mentor_user_data.username
#                                 mentor_nickname = mentor_user_data.nickname
#                                 mentor_message = f"Участник {user.nickname} с гильдии {user.guild} " \
#                                                  f"выбрал Вас в качестве своего наставника." \
#                                                  f"\n\nДля связи с учеником используйте @{user.username}"
#                                 notification_guild = f"Участник {user.nickname} герой {user.hero_class} " \
#                                                      f"с гильдии {user.guild}" \
#                                                      f"выбрал качестве своего наставника{mentor_nickname}" \
#                                                      f"\n\nДля связи с участником используйте @{user.username}"
#                                 await bot.send_message(mentor_telegram_id, mentor_message)
#                                 # await bot.send_message(config.officer_chat_id, notification_guild,
#                                 #                        message_thread_id=config.office_mentor_thread_id) НАСТРОИТЬ ПЕРЕД ЗАПУСКОМ
#                             except Exception as e:
#                                 logging.error(f"При отправке сообщения Наставнику - произошла ошибка - [{e}]")
#                 session.close()  # Закрытие сессии после отправки сообщения
#             except Exception as e:
#                 logging.error(f"При выполнении функции update_students - произошла ошибка - [{e}]")
#                 session.close()  # Закрываем сеанс с БД после завершения регистрации
#
#     elif mentor_nickname == '/cancel':
#         await state.finish()
#         await message.reply("Регистрация отменена!")


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

    # Проверка на команду /cancel
    if mentor_account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")
        return

    # Проверка на запрещённый символ "/"
    if mentor_account_id.startswith('/') and mentor_account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный

    if not (
            mentor_account_id.isdigit() and
            len(mentor_account_id) == 11 and
            mentor_account_id[-3:] == '160' and
            int(mentor_account_id) > 0
    ):
        await message.reply(
            "Неверно. ID должен содержать только цифры, быть не более 11 символов и заканчиваться на '160'.")
        return  # Выход из обработчика, если ID неверный

    # Проверка на уникальность account_id
    existing_mentor = session.query(Mentor).filter_by(mentor_account_id=message.text).first()
    if existing_mentor:
        await message.reply(f"Наставник с таким ID в игре уже зарегистрирован!\n"
                            f"Его Никнейм в игре {existing_mentor.mentor_nickname}"
                            f"Введите другой ID или используйте команду /cancel для выхода из регистрации.")
        return

    async with state.proxy() as data:
        data['mentor_account_id'] = message.text

        # Запрос данных о менторе
        await message.reply("Загрузите фотографию профиля (опционально):"
                            "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
        await RegistrationMentors.mentor_photo.set()


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
    if mentor_characteristic == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")
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
            await bot.send_message(message.from_user.id, "Регистрация завершена! Спасибо! Вы возвращены "
                                                         "в главное меню", reply_markup=await get_start_menu())
            await state.finish()


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

    # Проверка на команду /cancel
    if admin_account_id == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")
        return

    # Проверка на запрещённый символ "/"
    if admin_account_id.startswith('/') and admin_account_id != '/cancel':
        await message.reply("Неверно. ID не должен начинаться с символа /")
        return  # Выход из обработчика, если ID неверный
    # Проверка длины и окончания ID
    if not (
            admin_account_id.isdigit() and
            len(admin_account_id) == 11 and
            admin_account_id[-3:] == '160' and
            int(admin_account_id) > 0
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
    await message.reply("Загрузите фотографию профиля (опционально):"
                        "\nИспользуйте /next - для пропуска, если сейчас нет фотографии профиля")
    await RegistrationAdmins.admin_photo.set()


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

            await bot.send_message(message.from_user.id, "Регистрация завершена! Спасибо! Вы возвращены "
                                                         "в главное меню", reply_markup=await get_start_menu())
            await state.finish()
    elif admin_position == '/cancel':
        await state.finish()
        await message.reply("Регистрация отменена!")


'''КОМАНДЫ ДЛЯ СИС-АДМИНИСТРАТОРА'''


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


'''фУНКЦИИ ДЛЯ РАБОТЫ БОТА'''


# Определяем, роль пользователя
def get_user_role(user_id):
    users = session.query(User).filter_by(telegram_id=user_id).all()
    if users:
        # Проверка роли для каждого аккаунта пользователя
        for user in users:
            is_mentor = session.query(Mentor).filter_by(mentor_account_id=user.account_id).first()
            is_admin = session.query(Admin).filter_by(admin_account_id=user.account_id).first()

            if is_admin:
                return 'admin'
            elif is_mentor:
                return 'mentor'

        # Если ни один аккаунт не является ни админом, ни ментором, возвращаем 'user'
        return 'user'
    else:
        return None  # Пользователь не найден


# Возврат на главное меню
async def get_start_menu():
    # user_role = get_user_role(message.from_user.id)
    # Создайте кнопки для меню
    buttons = [
        KeyboardButton('\U0001F464Мой профиль'),
        KeyboardButton('Регистрация'),
        KeyboardButton('\U0001F198Помощь'),
        KeyboardButton('Администрирование')
    ]
    # Заготовка под ролевую модель #РОЛЕВАЯ
    # buttons = [
    #     types.KeyboardButton('\U0001F464Мой профиль'),
    #     types.KeyboardButton('Регистрация'),
    #     types.KeyboardButton('\U0001F198Помощь')
    # ]

    # if user_role == 'admin':
    #     buttons.append(types.KeyboardButton('Администрирование'))

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(*buttons)
    return markup


# функция получения ID Администратора через его telegram_id
def get_admin_id(telegram_id):
    users = session.query(User).filter_by(telegram_id=telegram_id).all()
    logging.info(f"Функция get_admin_id - users: {users}")
    if users:
        for user in users:
            admin = session.query(Admin).filter_by(admin_account_id=user.account_id).first()
            logging.info(f"Функция get_admin_id - admin: {admin}")
            logging.info(f"Функция get_admin_id - id админа: {admin.id}")
            return admin.id
    else:
        logging.info(f"Функция get_admin_id - id админа: NULL")
        return None


# функция проверки DPS и BM
def validate_input(input_string):
    """
  Проверяет, соответствует ли строка заданному формату:
  число от 3 до 5 знаков с буквой K, M, B, T или AA в конце.
  """
    pattern = r'^[1-9]\d{2,4}[KMBTA]{1}$'
    match = re.match(pattern, input_string)
    if match:
        return True
    else:
        return False


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
