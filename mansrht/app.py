from mansrht.types import User, Visibility
from srht.config import cfg
from srht.database import DbSession
from srht.flask import SrhtFlask
from urllib.parse import urlparse

db = DbSession(cfg("man.sr.ht", "connection-string"))
db.init()

class ManApp(SrhtFlask):
    def __init__(self):
        super().__init__("man.sr.ht", __name__, user_class=User)

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

        @self.context_processor
        def inject():
            return {
                "Visibility": Visibility,
            }

app = ManApp()
