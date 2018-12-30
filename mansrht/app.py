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

class ManOAuthService(AbstractOAuthService):
    def __init__(self):
        super().__init__(client_id, client_secret, user_class=User)

class ManApp(SrhtFlask):
    def __init__(self):
        super().__init__("man.sr.ht", __name__, oauth_service=ManOAuthService())

        from mansrht.blueprints.html import html
        self.register_blueprint(html)

        self.url_map.strict_slashes = False

        @self.context_processor
        def inject():
            git_user = cfg("man.sr.ht", "git-user")
            origin = urlparse(cfg("man.sr.ht", "origin"))
            return {
                "repo_uri": lambda user=None, wiki=None: (
                    "{}@{}:{}".format(
                        git_user.split(":")[0],
                        origin.netloc,
                        "~{}/{}".format(
                            user, wiki) if user and wiki else "root")
                ),
            }

app = ManApp()
