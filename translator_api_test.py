import sys
import csv
import json
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"
REPORT_FILE = Path("report.csv")

test_cases = [
    {
        "id": "TC-01",
        "name": "Получение списка языков",
        "method": "GET",
        "url": f"{BASE_URL}/languages",
        "expected_status": 200,
        "type": "languages"
    },
    {
        "id": "TC-02",
        "name": "Перевод hello en->ru",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "hello", "source": "en", "target": "ru", "format": "text"},
        "expected_status": 200,
        "type": "translate"
    },
    {
        "id": "TC-03",
        "name": "Перевод Доброе утро ru->en",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "Доброе утро", "source": "ru", "target": "en", "format": "text"},
        "expected_status": 200,
        "type": "translate"
    },
    {
        "id": "TC-04",
        "name": "Автоопределение языка en->ru",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "hello", "source": "auto", "target": "ru", "format": "text"},
        "expected_status": 200,
        "type": "auto_translate"
    },
    {
        "id": "TC-05",
        "name": "Пустая строка",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "", "source": "en", "target": "ru", "format": "text"},
        "expected_status": 400,
        "type": "negative"
    },
    {
        "id": "TC-06",
        "name": "Неверный source",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "hello", "source": "xx", "target": "ru", "format": "text"},
        "expected_status": 400,
        "type": "negative"
    },
    {
        "id": "TC-07",
        "name": "Неверный target",
        "method": "POST",
        "url": f"{BASE_URL}/translate",
        "payload": {"q": "hello", "source": "en", "target": "zz", "format": "text"},
        "expected_status": 400,
        "type": "negative"
    },
]

def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {"raw_text": response.text}

def validate_case(case, response, data):
    if response.status_code != case["expected_status"]:
        return False, f"Ожидался HTTP {case['expected_status']}, получен HTTP {response.status_code}"

    case_type = case["type"]

    if case_type == "languages":
        if not isinstance(data, list):
            return False, "Ответ /languages не является списком"

        codes = {item.get("code") for item in data if isinstance(item, dict)}

        for code in ("en", "ru"):
            if code not in codes:
                return False, f"В списке языков нет кода {code}"

        return True, "Список языков корректен"

    if case_type == "translate":
        translated = data.get("translatedText") if isinstance(data, dict) else None

        if not isinstance(translated, str) or not translated.strip():
            return False, "translatedText пустой или отсутствует"

        return True, "Перевод получен"

    if case_type == "auto_translate":
        translated = data.get("translatedText") if isinstance(data, dict) else None
        if not isinstance(translated, str) or not translated.strip():
            return False, "translatedText пустой или отсутствует"

        detected = data.get("detectedLanguage") if isinstance(data, dict) else None
        if not isinstance(detected, dict):
            return False, "Нет detectedLanguage"

        lang = detected.get("language")
        if lang != "en":
            return False, f"Ожидался detectedLanguage.language='en', получено: {lang}"

        if translated.strip().lower() == "hello":
            return False, "Перевод не произошёл"

        return True, "Автоопределение языка работает"

    if case_type == "negative":
        if response.status_code >= 400:
            return True, "Ошибка корректно обработана"

        return False, "Ожидалась ошибка, но запрос завершился успешно"

    return True, "OK"

def run_test(case):
    try:
        if case["method"] == "GET":
            response = requests.get(case["url"], timeout=10)
        else:
            response = requests.post(case["url"], json=case["payload"], timeout=10)

        data = safe_json(response)
        passed, comment = validate_case(case, response, data)

        return {
            "id": case["id"],
            "name": case["name"],
            "status": "PASSED" if passed else "FAILED",
            "http_status": response.status_code,
            "expected_status": case["expected_status"],
            "response": json.dumps(data, ensure_ascii=False),
            "comment": comment,
        }

    except Exception as e:
        return {
            "id": case["id"],
            "name": case["name"],
            "status": "FAILED",
            "http_status": "",
            "expected_status": case["expected_status"],
            "response": str(e),
            "comment": "Ошибка выполнения запроса",
        }

results = [run_test(case) for case in test_cases]

with open(REPORT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["id", "name", "status", "http_status", "expected_status", "response", "comment"],
        delimiter=";"
    )
    writer.writeheader()
    writer.writerows(results)

passed = sum(1 for r in results if r["status"] == "PASSED")
failed = sum(1 for r in results if r["status"] == "FAILED")

print("Результаты тестов:")
for r in results:
    print(f'{r["id"]}: {r["status"]} | {r["name"]}')

print()
print(f"Всего: {len(results)}")
print(f"Пройдено: {passed}")
print(f"Провалено: {failed}")
print(f"Отчет сохранен в: {REPORT_FILE.resolve()}")