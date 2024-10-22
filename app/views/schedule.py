import schedule
import random
import time
from zeep import Client, AsyncClient
import requests
from flask import url_for, flash, request, render_template, redirect, Blueprint
import os
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
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


def createperson(studs):
    # Открываем сессию SOAP
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

        # Получение группы доступа
        NAME = "Этажи"  # Указываем необходимую территорию (группу доступа)
        ter = client.service.GetAccessGroups(sessionID)
        matches = [el for el in ter if el.NAME == NAME]
        if matches:
            ACCGROUP_ID = matches[0].ID

            # SOAP-запрос для добавления идентификатора и группы доступа студенту
            identifier_template = """
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

            body = identifier_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID,
                                              ACCGROUP_ID=ACCGROUP_ID)
            body = body.encode('utf-8')

            # Отправляем запрос на сервер для назначения группы доступа
            response = session.post(url=endpoint, data=body, verify=False)

            # Печать результата запроса
            print(f"Создан студент с логином: {FIRST_NAME}, группа доступа: {NAME}")
        else:
            print(f"Группа доступа '{NAME}' не найдена")


def delete_students():
    # Открываем сессию SOAP
    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    session = client.service.OpenSession(domain, nameuser, password)
    sessionID = session.Value.SessionID

    # Получаем всех студентов
    studs = client.service.FindPeople(sessionID, "Student")
    if studs:
        # Удаляем каждого студента
        for stud in studs:
            client.service.DeletePerson(sessionID, stud['ID'])
            print(f"Удален студент с ID: {stud['ID']}")


def schedule_tasks():
    # Запланировать удаление студентов каждый день в 23:55
    schedule.every().day.at("23:55").do(delete_students)
