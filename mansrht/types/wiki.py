import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base
from enum import Enum

class WikiVisibility(Enum):
    public = 'public'
    private = 'private'
    unlisted = 'unlisted'

class Wiki(Base):
    __tablename__ = 'wiki'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    name = sa.Column(sa.Unicode(256), nullable=False)
    owner_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    owner = sa.orm.relationship('User', backref=sa.orm.backref('repos'))
    path = sa.Column(sa.Unicode(1024))
    visibility = sa.Column(
            sau.ChoiceType(WikiVisibility, impl=sa.String()),
            nullable=False,
            default=WikiVisibility.public)
