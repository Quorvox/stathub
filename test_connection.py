import requests
import json

STEAM_API_KEY = "Steam_key"
STEAM_ID = "Steam_id в ссылке"  

print("Проверяем подключение к Steam API...")
try:
    url = f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?key={STEAM_API_KEY}&steamid={STEAM_ID}&count=10"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        print("[OK] API работает.")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:2000])
    else:
        print(f"[FAIL] Код ответа: {response.status_code}")
        print(response.text)
except requests.exceptions.RequestException as e:
    print(f"❌ ОШИБКА СОЕДИНЕНИЯ: {e}")
