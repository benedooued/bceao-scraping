import time
import warnings
import requests
from config import VERIFY_SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def create_session() -> requests.Session:
    """Creates and configures a requests Session with a default User-Agent.

    Returns:
        requests.Session: Configured session instance.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    })
    return session


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs
) -> requests.Response:
    """Executes an HTTP request with automatic retry logic (up to 3 attempts).

    Args:
        session (requests.Session): Active HTTP session.
        method (str): HTTP method ('GET', 'POST', etc.).
        url (str): Target URL for the request.
        **kwargs: Additional parameters passed to `requests.Session.request`.

    Raises:
        requests.RequestException: If all 3 request attempts fail.

    Returns:
        requests.Response: Successful HTTP response object.
    """
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
            print(f"  Tentative {attempt + 1}/3 échouée : {error}")
            if attempt == 2:
                raise
            time.sleep(5)
