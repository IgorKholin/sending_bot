import requests
from keys import InstanceWhatsup, ApiWhatsup

def check_greenapi_status():
    """Проверка статуса Green-API аккаунта"""
    try:
        idInstance = InstanceWhatsup
        apiTokenInstance = ApiWhatsup

        # Проверяем состояние аккаунта
        state_url = f"https://api.green-api.com/waInstance{idInstance}/getStateInstance/{apiTokenInstance}"
        state_response = requests.get(state_url)

        if state_response.status_code == 200:
            state_data = state_response.json()
            state = state_data.get('stateInstance')
            return state
        else:
            return f"Ошибка: {state_response.status_code}"

    except Exception as e:
        return f"Ошибка проверки: {e}"