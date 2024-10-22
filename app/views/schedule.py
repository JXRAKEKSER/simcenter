import schedule
import random
import time
from zeep import Client, AsyncClient
import requests
from flask import url_for, flash, request, render_template, redirect, Blueprint
import os
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
from datetime import datetime, time, timedelta
import csv
from flask import url_for, flash, render_template, redirect, session, jsonify, Blueprint, Flask, Response
import app.database as data
from app.middleware import db
from app.utils import ids, remove_string_noise
from app.helpers import (reject_operator, reject_no_offices, is_operator, is_office_operator,
                         is_common_task_operator, reject_setting, get_or_reject, decode_links)
from app.constants import TICKET_WAITING
import app
import pymysql

from host_data import SOAP_HOST, DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME

db.app = app
client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
domain = "SYSTEM"
nameuser = "parsec"
password = "parsec"


sched = Blueprint('sched', __name__)
test3 = ()

def get_unique_numbers(number1, number2):
    unique = []
    for number in number1:
        unique.append(number)
    for number in number2:
        if number in unique:
            unique.remove(number)
        else:
            continue
            #unique.append(number)
    return unique
def get_numbers(number1, number2):
    unique = []
    for number in number2:
        unique.append(number)
    for number in number1:
            if number in unique:
                unique.remove(number)
            else:
                continue
                #unique.append(number)
    return unique

def createperson(studs):
    session = client.service.OpenSession(domain, nameuser, password)
    sessionID = session.Value.SessionID
    lastname = "Student"

    for student in studs:  # Проходим по каждому студенту в списке
        A = 1000
        B = 9999
        CODE = str(random.randint(A, B)) + str(student.id)  # Генерация кода с использованием ID студента
        ID = "00000000-0000-0000-0000-000000000000"  # ID для нового студента
        LAST_NAME = "Student"
        FIRST_NAME = student.person_id  # Используем поле person_id как FIRST_NAME
        MIDDLE_NAME = ""
        TAB_NUM = ""
        ORG_ID = '766eb2b5-d5ef-4a12-a7ad-a55b073a0337'  # Организация
        endpoint = f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl"

        # SOAP-запрос для создания студента
        login_template = """
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <CreatePerson xmlns="http://parsec.ru/Parsec3IntergationService">
              <sessionID>{sessionID}</sessionID>
              <person>
                <ID>{ID}</ID>
                <LAST_NAME>{LAST_NAME}</LAST_NAME>
                <FIRST_NAME>{FIRST_NAME}</FIRST_NAME>
                <MIDDLE_NAME>{MIDDLE_NAME}</MIDDLE_NAME>
                <TAB_NUM>{TAB_NUM}</TAB_NUM>
                <ORG_ID>{ORG_ID}</ORG_ID>
              </person>
            </CreatePerson>
          </soap:Body>
        </soap:Envelope>
        """

        # Формируем тело SOAP-запроса
        body = login_template.format(sessionID=sessionID, ID=ID, LAST_NAME=LAST_NAME, FIRST_NAME=FIRST_NAME,
                                     MIDDLE_NAME=MIDDLE_NAME, TAB_NUM=TAB_NUM, ORG_ID=ORG_ID)
        body = body.encode('utf-8')

        # Отправляем запрос на сервер
        session = requests.session()
        session.headers = {"Content-Type": "text/xml; charset=utf8"}
        session.headers.update({"Content-Length": str(len(body))})
        response = session.post(url=endpoint, data=body, verify=False)

        # Получаем созданного человека
        buf = client.service.FindPeople(sessionID, lastname, FIRST_NAME)
        PERSON_ID = buf[0].ID

        # Открываем сессию редактирования для добавления идентификатора
        session = client.service.OpenPersonEditingSession(sessionID, PERSON_ID)
        personEditSessionID = session.Value

        # SOAP-запрос для добавления идентификатора студенту
        identifier_template = """
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Body>
        <AddPersonIdentifier xmlns="http://parsec.ru/Parsec3IntergationService">
        <personEditSessionID>{personEditSessionID}</personEditSessionID>
        <identifier xsi:type="Identifier">
        <CODE>{CODE}</CODE>
        <PERSON_ID>{PERSON_ID}</PERSON_ID>
        <IS_PRIMARY>1</IS_PRIMARY>
        </identifier>
        </AddPersonIdentifier>
        </soap:Body>
        </soap:Envelope>
        """

        # Формируем тело SOAP-запроса для добавления идентификатора
        body = identifier_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID)
        body = body.encode('utf-8')

        # Отправляем запрос на сервер
        response = session.post(url=endpoint, data=body, verify=False)

        # Печать результата запроса
        print("**********************")
        print(response.content.decode("utf-8"))
        print("**********************")
        print(response.status_code)
        print("**********************")
        print(f"Created person with login: {FIRST_NAME}")


def access1():
    a = datetime.now()
    d = timedelta(hours=3)
    c = a + d
    timez = c.strftime("%H:%M")

    connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD,
                                 database=DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM stud_access WHERE time_end > %s ORDER BY time_begin", (timez,))
    tmp = cursor.fetchall()
    connection.close()

    # Вывод количества записей
    print(f"Количество записей: {len(tmp)}")


def access():
    a = datetime.now()
    d = timedelta(hours=3)
    c = a + d
    d1 = c.strftime("%d.%m.%Y")
    global test3

    # Открытие сессии для SOAP клиента
    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    session = client.service.OpenSession(domain, nameuser, password)
    sessionID = session.Value.SessionID

    timez = c.strftime("%H:%M")

    # Подключение к базе данных и выборка пользователей
    connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD,
                                 database=DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * from stud_access WHERE time_end > %s AND time_begin <= %s AND date = %s ORDER BY time_begin",
        (timez, timez, d1))
    test4 = cursor.fetchall()
    connection.close()

    # Если произошли изменения в пользователях
    if test3 != test4:
        test5 = get_unique_numbers(test3, test4)  # Новые пользователи
        test6 = get_numbers(test3, test4)  # Удаляемые пользователи
        test3 = test4

        # Обработка добавляемых пользователей
        for student in test5:
            firstname = student[1]  # Используем вторую колонку как имя
            buf = client.service.FindPeople(sessionID, "Student", firstname)
            if buf and len(buf) > 0:
                PERSON_ID = buf[0].ID
                code1 = client.service.GetPersonIdentifiers(sessionID, PERSON_ID)
                CODE = code1[0].CODE
                personEditSessionID = client.service.OpenPersonEditingSession(sessionID, PERSON_ID).Value

                # Получение ID территории по имени
                NAME = "Этажи"
                ter = client.service.GetAccessGroups(sessionID)
                matches = [el for el in ter if el.NAME == NAME]
                if matches:
                    ACCGROUP_ID = matches[0].ID

                # Формируем и отправляем SOAP запрос для добавления идентификатора
                login_template = """
                <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                <AddPersonIdentifier xmlns="http://parsec.ru/Parsec3IntergationService">
                <personEditSessionID>{personEditSessionID}</personEditSessionID>
                <identifier xsi:type="Identifier">
                <CODE>{CODE}</CODE>
                <PERSON_ID>{PERSON_ID}</PERSON_ID>
                <IS_PRIMARY>1</IS_PRIMARY>
                <ACCGROUP_ID>{ACCGROUP_ID}</ACCGROUP_ID>
                </identifier>
                </AddPersonIdentifier>
                </soap:Body>
                </soap:Envelope>
                """
                body = login_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID,
                                             ACCGROUP_ID=ACCGROUP_ID)
                body = body.encode('utf-8')

                session = requests.session()
                session.headers = {"Content-Type": "text/xml; charset=utf8"}
                session.headers.update({"Content-Length": str(len(body))})
                response = session.post(url=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl",
                                        data=body, verify=False)

                print(f"Добавлен идентификатор для {firstname} на {NAME} в {timez}")

        # Обработка удаляемых пользователей
        for student in test6:
            firstname = student[1]
            NAME = student[2]

            buf = client.service.FindPeople(sessionID, "Student", firstname)
            if buf and len(buf) > 0:
                PERSON_ID = buf[0].ID
                code1 = client.service.GetPersonIdentifiers(sessionID, PERSON_ID)
                CODE = code1[0].CODE
                personEditSessionID = client.service.OpenPersonEditingSession(sessionID, PERSON_ID).Value

                ter = client.service.GetAccessGroups(sessionID)
                matches = [el for el in ter if el.NAME == NAME]
                if matches:
                    ACCGROUP_ID = matches[0].ID

                # Формируем и отправляем SOAP запрос для удаления идентификатора
                login_template = """
                <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                <AddPersonIdentifier xmlns="http://parsec.ru/Parsec3IntergationService">
                <personEditSessionID>{personEditSessionID}</personEditSessionID>
                <identifier xsi:type="Identifier">
                <CODE>{CODE}</CODE>
                <PERSON_ID>{PERSON_ID}</PERSON_ID>
                <IS_PRIMARY>1</IS_PRIMARY>
                <ACCGROUP_ID>{ACCGROUP_ID}</ACCGROUP_ID>
                </identifier>
                </AddPersonIdentifier>
                </soap:Body>
                </soap:Envelope>
                """
                body = login_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID,
                                             ACCGROUP_ID=ACCGROUP_ID)
                body = body.encode('utf-8')

                session = requests.session()
                session.headers = {"Content-Type": "text/xml; charset=utf8"}
                session.headers.update({"Content-Length": str(len(body))})
                response = session.post(url=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl",
                                        data=body, verify=False)

                print(f"Удален идентификатор для {firstname} с {NAME} в {timez}")


def schedule1():
    schedule.every(5).seconds.do(access)


