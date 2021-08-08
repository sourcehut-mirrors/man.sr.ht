from flask import abort
from datetime import datetime
from enum import IntFlag
from mansrht.types import User, Wiki, WikiVisibility
from srht.database import db
from srht.oauth import current_user

class UserAccess(IntFlag):
    none = 0
    read = 1
    write = 2
    manage = 4

def get_wiki(owner_name, wiki_name):
    if owner_name[0] == "~":
        user = User.query.filter(User.username == owner_name[1:]).first()
        if user:
            wiki = Wiki.query.filter(Wiki.owner_id == user.id)\
                .filter(Wiki.name.ilike(wiki_name.replace('_', '\\_'))).first()
        else:
            wiki = None
        return user, wiki
    else:
        # TODO: organizations
        return None, None

def get_access(wiki, user=None):
    if not user:
        user = current_user
    if not wiki:
        return UserAccess.none
    if not user:
        if wiki.visibility == WikiVisibility.public or \
                wiki.visibility == WikiVisibility.unlisted:
            return UserAccess.read
        return UserAccess.none
    if wiki.owner_id == user.id:
        return UserAccess.read | UserAccess.write | UserAccess.manage
    if wiki.visibility == WikiVisibility.private:
        return UserAccess.none
    return UserAccess.read

def has_access(wiki, access, user=None):
    return access in get_access(wiki, user)

def check_access(owner_name, wiki_name, access):
    owner, wiki = get_wiki(owner_name, wiki_name)
    if not owner or not wiki:
        abort(404)
    a = get_access(wiki)
    if not access in a:
        abort(403)
    return owner, wiki
