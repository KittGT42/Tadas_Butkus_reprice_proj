import requests

# data for login
username = "td.butkus"
password = "ObigM$pI24SnrdPI333"

# URL for login
login_url = "https://pmpapi.pigugroup.eu/v3/login"


# function for getting token
def get_token():
    response = requests.post(login_url, json={
        "username": username,
        "password": password
    })

    if response.status_code == 200:
        token = response.json().get("token")  # Передбачається, що відповідь має поле 'token'
        print("Token received:", token)
        return token
    else:
        print("Error:", response.status_code, response.text)
        return None


# geting token
token = get_token()

print(token)
