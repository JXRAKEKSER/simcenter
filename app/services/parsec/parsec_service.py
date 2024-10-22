from host_data import SOAP_HOST
from datetime import datetime
from zeep import Client
import time


def get_code(person_id):
    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    domain = "SYSTEM"
    nameuser = "parsec"
    password = "parsec"
    session = (client.service.OpenSession(domain, nameuser, password))
    sessionID = session.Value.SessionID
    lastname = "Student"
    firstname = person_id
    buf = (client.service.FindPeople(sessionID, lastname, firstname))
    PERSON_ID = buf[0].ID
    code1 = (client.service.GetPersonIdentifiers(sessionID, PERSON_ID))
    CODE = code1[0].CODE
    return int(CODE, 16) # demical code value


domain = "SYSTEM"
username = "parsec"
password = "parsec"

def open_session(domain, username, password):
    client = Client(wsdl=f"http://172.29.3.2:10101/IntegrationService/IntegrationService.asmx?wsdl")
    session = (client.service.OpenSession(domain, username, password))
    sessionID = session.Value.SessionID
    lastname = "Student"
    firstname = 60
    buf = (client.service.FindPeople(sessionID, lastname, firstname))
    global person_id
    person_id = buf[0].ID
    print(person_id)
    return sessionID


door_events = []

def get_events():
    session_id = open_session(domain, username, password)

    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")

    # Определение начала и конца текущего дня
    dt_from = datetime.combine(datetime.today(), datetime.min.time())  # Начало текущих суток
    dt_to = datetime.combine(datetime.today(), datetime.max.time())  # Конец текущих суток

    studs = (client.service.FindPeople(session_id, "Student"))
    for stud in studs:
        for tr in [590144, 590145]:
            # Параметры для запроса событий
            query_params = {
                'Users': [stud['ID']],  # Фильтр по пользователю
                'StartDate': dt_from.strftime('%Y-%m-%dT%H:%M:%S'),  # Дата начала в формате UTC
                'EndDate': dt_to.strftime('%Y-%m-%dT%H:%M:%S'),      # Дата окончания в формате UTC
                'TransactionTypes': [tr],  # Нормальный и фактический вход
            }

            # Вызов функции OpenEventHistorySession с фильтрами по дате и типам событий
            params = {
                'sessionID': session_id,
                'parameters': query_params  # Передаем фильтр
            }

            events = client.service.OpenEventHistorySession(**params)
            event_history_session_id = events['Value']

            get_event_history_details(session_id, event_history_session_id, dt_from, dt_to)



def get_event_history_details(session_id, event_history_session_id, dt_from=None, dt_to=None):
    client = Client(wsdl=f"http://{SOAP_HOST}/IntegrationService/IntegrationService.asmx?wsdl")
    global door_events

    # Поля для запроса (из документации)
    fields = [
        '2C5EE108-28E3-4DCC-8C95-7F3222D8E67F',  # Дата/время события
        '57CA38E4-ED6F-4D12-ADCB-2FAA16F950D7',  # Тип события (код в 10-ной системе)
        '633904B5-971B-4751-96A0-92DC03D5F616',  # Источник события (наименование территории или оператора)
        '7C6D82A0-C8C8-495B-9728-357807193D23',  # id user
        '9F7A30E6-C9ED-4E62-83E3-59032A0F8D27 '  # id event
    ]

    # Получаем количество событий
    event_count = client.service.GetEventHistoryResultCount(sessionID=session_id,
                                                            eventHistorySessionID=event_history_session_id)

    if int(event_count) > 0:
        # print(f"Найдено событий: {event_count}")

        events = []

        # Получаем события по каждому полю последовательно
        for field in fields:
            params = {
                'sessionID': session_id,
                'eventHistorySessionID': event_history_session_id,
                'fields': [field],  # Запрашиваем только одно поле за раз
                'offset': 0,
                'count': 10000  # Измените лимит на нужное количество
            }

            # Получаем события
            event_results = client.service.GetEventHistoryResult(**params)
            lil_events = []
            for ev in event_results:
                event_data = ev['Values']  # Массив значений
                lil_events.append(event_data)  # Добавляем событие в список
            events.append(lil_events)

        result = {}
        for idx, type_array in enumerate(events):
            for idy, type_value in enumerate(type_array):
                key = 'наименование поля'
                if idx == 0:
                    key = 'Дата/время события'
                if idx == 1:
                    key = 'Тип события (код в 10-ной системе)'
                if idx == 2:
                    key = 'Источник события (наименование территории или оператора)'
                if idx == 3:
                    key = 'Идентификатор субъекта (PERS_ID - Guid)'
                if idx == 4:
                    key = 'Идентификатор события (Guid)'
                if idy not in result:
                    result[idy] = {}
                result[idy][key] = type_value

        for k in result:
            event_code = result[k]['Тип события (код в 10-ной системе)']['anyType'][0]
            datew = result[k]['Дата/время события']['anyType'][0]
            st_id = result[k]['Идентификатор субъекта (PERS_ID - Guid)']['anyType'][0]
            door = result[k]['Источник события (наименование территории или оператора)']['anyType'][0]
            ev_id = result[k]['Идентификатор события (Guid)']['anyType'][0]

            if event_code == '590144':
                print(f"Студент {st_id} вошел в дверь ({door}) по ключу {datew}")
            if event_code == '590145':
                print(f"Студент {st_id} вышел {datew}")
            if ev_id not in door_events:
                door_events.append(ev_id)
