from host_data import SOAP_HOST

from zeep import Client

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