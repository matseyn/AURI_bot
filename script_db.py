from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from aiogram import Bot
import config
import logging


engine = create_engine('sqlite:///Auri.db', echo=True)
Base = declarative_base()
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

bot = Bot(token=config.BOT_TOKEN)


# Функция для обновления количества подопечных в таблице Mentors у каждого наставника после завершения /reg
async def update_students():
    session.execute(text('''
        CREATE TEMP TABLE MentorStudentCount AS
        SELECT
            mentor_id,
            COUNT(*) AS mentor_number_of_students
        FROM
            Users
        GROUP BY
            mentor_id;
    '''))
    session.execute(text('''
        UPDATE Mentors
        SET
            mentor_number_of_students = (
                SELECT
                    mentor_number_of_students
                FROM
                    MentorStudentCount
                WHERE
                    Mentors.id = MentorStudentCount.mentor_id
            );
    '''))
    session.execute(text('DROP TABLE MentorStudentCount;'))
    session.commit()
