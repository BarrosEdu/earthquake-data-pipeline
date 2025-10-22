import os, time, requests, random

URL = os.getenv("TARGET_URL", "https://earthquake-data-pipeline.streamlit.app")

def ping(url: str) -> int:
    # query param para evitar cache
    full = f"{url}?_={int(time.time())}{random.randint(1000,9999)}"
    r = requests.get(
        full,
        headers={"User-Agent": "keepalive-heroku/1.0"},
        timeout=10,
    )
    print(f"{time.ctime()} - {r.status_code} - {url}")
    return r.status_code

if __name__ == "__main__":
    delay = 3
    for attempt in range(3):
        try:
            code = ping(URL)
            if 200 <= code < 500:  
                break
        except Exception as e:
            print(f"Error {attempt+1}: {e}")
        time.sleep(delay)
        delay *= 2
