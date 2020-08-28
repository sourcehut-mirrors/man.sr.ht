from mansrht.types import User
from srht.config import cfg
from srht.database import DbSession
from srht.flask import SrhtFlask
from srht.oauth import AbstractOAuthService
from urllib.parse import urlparse

db = DbSession(cfg("man.sr.ht", "connection-string"))
db.init()

client_id = cfg("man.sr.ht", "oauth-client-id")
client_secret = cfg("man.sr.ht", "oauth-client-secret")
gitsrht_cid = cfg("git.sr.ht", "oauth-client-id")

class ManOAuthService(AbstractOAuthService):
    def __init__(self):
        super().__init__(
                client_id, client_secret,
                required_scopes=[
                    "profile",
                    f"{gitsrht_cid}/data",
                    f"{gitsrht_cid}/info:write",
                ],
                user_class=User)

class ManApp(SrhtFlask):
    def __init__(self):
        super().__init__("man.sr.ht", __name__, oauth_service=ManOAuthService())

        from mansrht.blueprints.html import html
        from mansrht.blueprints.create import create
        from mansrht.blueprints.manage import manage
        from mansrht.blueprints.notify import webhooks_notify
        from mansrht.blueprints.public import public

        self.register_blueprint(html)
        self.register_blueprint(create)
        self.register_blueprint(manage)
        self.register_blueprint(webhooks_notify)
        self.register_blueprint(public)

        self.url_map.strict_slashes = False

app = ManApp()
