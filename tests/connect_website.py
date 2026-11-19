def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    })

    return session


def request_with_retry(session, method, url, **kwargs):

    for attempt in range(3):

        try:
            response = session.request(
                method,
                url,
                timeout=(15, 180),
                verify=VERIFY_SSL,
                **kwargs
            )

            response.raise_for_status()
            return response

        except requests.RequestException as error:

            print(
                f"  Tentative {attempt + 1}/3 échouée : {error}"
            )

            if attempt == 2:
                raise

            time.sleep(5)
