import json

import requests


class ApiClient(object):
    base: str

    def __init__(self, base):
        self.base = base

    def build_uri(self, endpoint: str):
        return f'{self.base}{endpoint if endpoint.startswith("/") else ("/" + endpoint)}'

    @staticmethod
    def to_dict(r: requests.Response):
        return json.loads(r.text)

    def get(self, uri: str):
        r = requests.get(self.build_uri(uri))
        return self.to_dict(r)

    def post(self, uri: str, data: dict):
        r = requests.post(self.build_uri(uri), json=data)
        return self.to_dict(r)

    def call(self, endpoint: str):
        pass
