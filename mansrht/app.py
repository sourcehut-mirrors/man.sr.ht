from flask import render_template, request
from flask_login import LoginManager, current_user
from jinja2 import Markup
from datetime import datetime
import locale
import urllib

from srht.config import cfg, cfgi, load_config
load_config("man")
from srht.database import DbSession
db = DbSession(cfg("sr.ht", "connection-string"))
from mansrht.types import User
db.init()

from srht.flask import SrhtFlask
app = SrhtFlask("man", __name__)
app.url_map.strict_slashes = False
app.secret_key = cfg("server", "secret-key")
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(username):
    return User.query.filter(User.username == username).first()

login_manager.anonymous_user = lambda: None

try:
    locale.setlocale(locale.LC_ALL, 'en_US')
except:
    pass

def oauth_url(return_to):
    return "{}/oauth/authorize?client_id={}&scopes=profile,keys&state={}".format(
        meta_sr_ht, meta_client_id, urllib.parse.quote_plus(return_to))

from mansrht.blueprints.auth import auth
from mansrht.blueprints.html import html

app.register_blueprint(auth)
app.register_blueprint(html)

meta_sr_ht = cfg("network", "meta")
meta_client_id = cfg("meta.sr.ht", "oauth-client-id")
git_user = cfg("man.sr.ht", "git-user")
domain = cfg("server", "domain")

@app.context_processor
def inject():
    return {
        "oauth_url": oauth_url(request.full_path),
        "current_user": (
            User.query.filter(User.id == current_user.id).first()
        ) if current_user else None,
        "repo_uri": lambda user=None, wiki=None: (
            "{}@{}:{}".format(
                git_user.split(":")[0],
                domain,
                "~{}/{}".format(user, wiki) if user and wiki else "root"
            )
        ),
        "now": datetime.now
    }
