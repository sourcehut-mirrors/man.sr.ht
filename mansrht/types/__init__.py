from srht.database import Base
from srht.oauth import ExternalUserMixin

class User(Base, ExternalUserMixin):
    def __init__(*args, **kwargs):
        ExternalUserMixin.__init__(*args, **kwargs)

from mansrht.types.wiki import Wiki, WikiVisibility
