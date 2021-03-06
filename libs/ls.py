from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions


def _handle_unauthorized(func):
    '''
    Re-authenticates and retries if 401 is received.
    '''
    def wrapper(*args, **kwargs):
        resp = func(*args, **kwargs)
        if resp.status_code == 401:
            client_instance = args[0]
            client_instance.authenticate()
            resp = func(*args, **kwargs)
        return resp
    return wrapper


class LSClient():
    '''
    Very simple interface around the rest API's. The https methods are decorated
    so that an expired authorization token will re-authenticate and retry the
    request. 

    TODO: Add error handling around Connection Errors
    '''

    def __init__(self, uri, username, password):
        if uri.startswith('http'):
            self.url = uri
            self.cls = '~'
        else:
            self.url = 'https://teradici.compliance.flexnetoperations.com'
            self.cls = uri
		
        self.creds = {
            "password": password,
            "user": username,
        }
        self._session = Session()
        self._session.mount(self.url, HTTPAdapter(
            max_retries=Retry(total=3, status_forcelist=[500, 503, 502]))
        )
        self.authenticate()

    @_handle_unauthorized
    def _get(self, url, token, data=dict(), **kwargs):
        return self._session.get(url=url,
                            headers=dict(authorization="Bearer " + self.token),
                            params=data)

    def authenticate(self):
        resp = self._session.post(
            url=self.url + "/api/1.0/instances/" + self.cls + "/authorize", json=self.creds)

        if not resp.status_code == 200:
            msg = ("Authentication Error: Response code: {}. "
                "Please verify ls url or cls id, username and password and try again.".format(resp.status_code))
            raise Exception(msg)

        token = resp.json()["token"]
        self.token = token
        return token

    def get_used_features(self):
        resp = self._get(
            url=self.url + "/api/1.0/instances/" + self.cls + "/features", token=self.token)

        rd = {
            "standard": {
                "count": 0,
                "used": 0
            },
            "graphics": {
                "count": 0,
                "used": 0
            }
        }

        for item in resp.json():
            if (item["featureName"] == "Agent-Session"):
                rd["standard"]["count"] += item["featureCount"]
                rd["standard"]["used"] += item["used"]
            elif (item["featureName"] == "Agent-Graphics"):
                rd["graphics"]["count"] += item["featureCount"]
                rd["graphics"]["used"] += item["used"]

        return rd
