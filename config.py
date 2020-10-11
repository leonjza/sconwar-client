class Config(object):
    gameid: str
    playerid: str
    api_host: str

    def __init__(self):
        self.gameid = ""
        self.playerid = ""
        self.api_host = "http://localhost:8080/api"


config = Config()
