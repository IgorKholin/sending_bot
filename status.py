import requests

def check_greenapi_status():
    """Проверка статуса Green-API аккаунта"""
    try:
        idInstance = "1103397900"
        apiTokenInstance = "546ae028174846fc977b87bc99bfcc2834bbe0c022ef4e2794"

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