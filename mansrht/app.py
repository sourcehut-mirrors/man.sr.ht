from srht.flask import SrhtFlask
from srht.config import cfg
from srht.database import DbSession

db = DbSession(cfg("man.sr.ht", "connection-string"))

from mansrht.types import User

db.init()

from datetime import datetime

class ManApp(SrhtFlask):
    def __init__(self):
        super().__init__("man.sr.ht", __name__)

        from mansrht.blueprints.html import html
        self.register_blueprint(html)

        self.url_map.strict_slashes = False

        meta_client_id = cfg("man.sr.ht", "oauth-client-id")
        meta_client_secret = cfg("man.sr.ht", "oauth-client-secret")
        self.configure_meta_auth(meta_client_id, meta_client_secret,
                base_scopes=["profile", "keys"])

        @self.login_manager.user_loader
        def user_loader(username):
            # TODO: Switch to a session token
            return User.query.filter(User.username == username).one_or_none()

        @self.context_processor
        def inject():
            git_user = cfg("man.sr.ht", "git-user")
            return {
                "repo_uri": lambda user=None, wiki=None: (
                    "{}@{}:{}".format(
                        git_user.split(":")[0],
                        cfg("man.sr.ht", "origin"),
                        "~{}/{}".format(user, wiki) if user and wiki else "root")
                ),
                "now": datetime.now
            }

    def lookup_or_register(self, exchange, profile, scopes):
        user = User.query.filter(User.username == profile["username"]).first()
        if not user:
            user = User()
            db.session.add(user)
        user.username = profile.get("username")
        user.admin = profile.get("admin")
        user.email = profile.get("email")
        user.oauth_token = exchange["token"]
        user.oauth_token_expires = exchange["expires"]
        user.oauth_token_scopes = scopes
        db.session.commit()
        return user

app = ManApp()
