import sqlalchemy as sa
from srht.database import Base
from srht.oauth import ExternalUserMixin

class User(Base, ExternalUserMixin):
    repo_update_webhook = sa.Column(sa.Integer)
    repo_delete_webhook = sa.Column(sa.Integer)

from mansrht.types.repo import BackingRepo
from mansrht.types.wiki import Wiki, RootWiki, WikiVisibility
