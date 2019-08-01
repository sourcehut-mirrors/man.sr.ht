import sqlalchemy as sa
from srht.database import Base

class BackingRepo(Base):
    __tablename__ = 'backing_repo'
    id = sa.Column(sa.Integer, primary_key=True)
    resource_id = sa.Column(sa.Integer)
    new = sa.Column(sa.Boolean, nullable=False)
    name = sa.Column(sa.Unicode(256), nullable=False)
    ref = sa.Column(sa.Unicode(1024), nullable=False)
    commit_sha = sa.Column(sa.Unicode(256))
    commit_author = sa.Column(sa.Unicode(256))
    commit_email = sa.Column(sa.Unicode(256))
    commit_time = sa.Column(sa.Unicode(256))
    commit_message = sa.Column(sa.Unicode(1024))
    tree_sha = sa.Column(sa.Unicode(256))
