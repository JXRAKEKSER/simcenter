from flask import Flask, request, Response

app = Flask(__name__)


@app.route('/IntegrationService/IntegrationService.asmx', methods=['GET', 'POST'])
def integration_service():
    # Обрабатываем входящий запрос
    incoming_request = request.data
    print(f"Received request: {incoming_request.decode('utf-8')}")

    # Создаем положительный ответ
    response_xml = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                        <soap:Body>
                            <YourResponse xmlns="http://tempuri.org/">
                                <YourResult>Success</YourResult>
                            </YourResponse>
                        </soap:Body>
                      </soap:Envelope>"""

    # Отправляем ответ клиенту
    return Response(response_xml, mimetype='text/xml')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10101)
