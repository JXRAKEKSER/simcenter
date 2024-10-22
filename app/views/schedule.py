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
    global test3
    connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD, database=DATABASE_NAME)
    cursor = connection.cursor()


    i = 0
    timez = c.strftime("%H:%M")
    cursor.execute("SELECT * from stud_access WHERE time_end>(%s) order by time_begin", timez)
    tmp = cursor.fetchall()

    print(len(tmp))
    #test4 = data.Stud_access.query.filter(data.Stud_access.time_begin > timez).order_by(data.Stud_access.time_begin).all()


def access():
    a = datetime.now()
    d = timedelta(hours=3)
    c = a + d
    d1 = c.strftime("%d.%m.%Y")
    global test3
    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    domain = "SYSTEM"
    nameuser = "parsec"
    password = "parsec"
    session = (client.service.OpenSession(domain, nameuser, password))
    sessionID = session.Value.SessionID
    lastname = "Student"
    pers1 = (client.service.FindPeople(sessionID, lastname))
    timez = c.strftime("%H:%M")
    connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD, database=DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT * from stud_access WHERE time_end>(%s) AND time_begin<=(%s) AND date=(%s) order by time_begin", (timez, timez, d1) )
    test4 = cursor.fetchall()
    connection.close()

    #test4 = data.Stud_access.query.filter(data.Stud_access.time_begin > timez).order_by(data.Stud_access.time_begin).all()
    if test3 != test4:

        test5 = get_unique_numbers(test3, test4) #добавляемые пользователи

        test6 = get_numbers(test3, test4) #удаляемые пользователи

        test3 = test4
        g = 0
        while g < len(test5):
            client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
            domain = "SYSTEM"
            nameuser = "parsec"
            password = "parsec"
            session = (client.service.OpenSession(domain, nameuser, password))
            sessionID = session.Value.SessionID
            lastname = "Student"
            firstname = test5[g][1]

            buf = (client.service.FindPeople(sessionID, lastname, firstname))

            PERSON_ID = buf[0].ID

            code1 = (client.service.GetPersonIdentifiers(sessionID, PERSON_ID))
            CODE = code1[0].CODE
            session = (client.service.OpenPersonEditingSession(sessionID, PERSON_ID))
            personEditSessionID = (session.Value)

            endpoint = f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl"
            IS_PRIMARY = 1
            NAME = "Этажи"  # name территории

            ter = (client.service.GetAccessGroups(sessionID))  # список всех территорий
            matches = [el for el in ter if el.NAME == NAME]  # поиск территории по имени
            ACCGROUP_ID = matches[0].ID

            login_template = """
                            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                            <soap:Body>
                            <AddPersonIdentifier xmlns="http://parsec.ru/Parsec3IntergationService">
                            <personEditSessionID>{personEditSessionID}</personEditSessionID>
                            <identifier xsi:type="Identifier">
                            <CODE>{CODE}</CODE>
                            <PERSON_ID>{PERSON_ID}</PERSON_ID>
                            <IS_PRIMARY>{IS_PRIMARY}</IS_PRIMARY>
                            <ACCGROUP_ID>{ACCGROUP_ID}</ACCGROUP_ID>
                            </identifier>
                            </AddPersonIdentifier>
                            </soap:Body>
                            </soap:Envelope>
                            """

            body = login_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID,
                                         IS_PRIMARY=IS_PRIMARY, ACCGROUP_ID=ACCGROUP_ID)
            body = body.encode('utf-8')

            session = requests.session()
            session.headers = {"Content-Type": "text/xml; charset=utf8"}
            session.headers.update({"Content-Length": str(len(body))})
            response = session.post(url=endpoint, data=body, verify=False)
            #print(response.content.decode("utf-8"))
            #print(response.status_code)
            #print(test5)
            print(timez)
            g += 1






        i = 0
        while i < len(test6):

                    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")

                    domain = "SYSTEM"
                    nameuser = "parsec"
                    password = "parsec"
                    session = (client.service.OpenSession(domain, nameuser, password))
                    sessionID = session.Value.SessionID
                    lastname = "Student"
                    firstname = test6[i][1]

                    buf = (client.service.FindPeople(sessionID, lastname, firstname))
                    PERSON_ID = buf[0].ID
                    code1 = (client.service.GetPersonIdentifiers(sessionID, PERSON_ID))

                    CODE = code1[0].CODE

                    session = (client.service.OpenPersonEditingSession(sessionID, PERSON_ID))
                    personEditSessionID = (session.Value)

                    endpoint = f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl"
                    IS_PRIMARY = 1
                    NAME = test6[i][2]  # name территории

                    ter = (client.service.GetAccessGroups(sessionID))  # список всех территорий
                    matches = [el for el in ter if el.NAME == NAME]  # поиск территории по имени
                    ACCGROUP_ID = matches[0].ID

                    login_template = """
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                    <soap:Body>
                    <AddPersonIdentifier xmlns="http://parsec.ru/Parsec3IntergationService">
                    <personEditSessionID>{personEditSessionID}</personEditSessionID>
                    <identifier xsi:type="Identifier">
                    <CODE>{CODE}</CODE>
                    <PERSON_ID>{PERSON_ID}</PERSON_ID>
                    <IS_PRIMARY>{IS_PRIMARY}</IS_PRIMARY>
                    <ACCGROUP_ID>{ACCGROUP_ID}</ACCGROUP_ID>
                    </identifier>
                    </AddPersonIdentifier>
                    </soap:Body>
                    </soap:Envelope>
                    """

                    body = login_template.format(personEditSessionID=personEditSessionID, CODE=CODE, PERSON_ID=PERSON_ID,
                                                 IS_PRIMARY=IS_PRIMARY, ACCGROUP_ID=ACCGROUP_ID)
                    body = body.encode('utf-8')

                    session = requests.session()
                    session.headers = {"Content-Type": "text/xml; charset=utf8"}
                    session.headers.update({"Content-Length": str(len(body))})
                    response = session.post(url=endpoint, data=body, verify=False)
                    #print(response.content.decode("utf-8"))
                    #print(response.status_code)
                    #print(CODE + "B")
                    print(timez)
                    i+=1



def schedule1():

    schedule.every(5).seconds.do(access)
