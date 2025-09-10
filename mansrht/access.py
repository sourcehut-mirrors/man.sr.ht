from flask import abort, request
from datetime import datetime
from enum import IntFlag
from mansrht.types import User, Wiki, Visibility
from srht.database import db
from srht.graphql import exec_gql
from srht.oauth import current_user
from srht.validation import Validation

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

def get_repo_access(wiki, owner, user=None):
    if not user:
        user = current_user
    valid = Validation(request)
    repo = wiki.repo
    resp = exec_gql("git.sr.ht", """
    query RepoAccess($repo: String!, $username: String!) {
        user(username: $username) {
            repository(name: $repo) {
                access
            }
        }
    }
    """, valid=valid, user=user,
        username=owner.username, repo=repo.name)
    if not valid.ok:
        return UserAccess.none
    try:
        access = resp["user"]["repository"]["access"]
        if access == "RW":
            return UserAccess.read | UserAccess.write
        else:
            return UserAccess.read
    except:
        return UserAccess.none

def get_access(wiki, owner, user=None):
    if not user:
        user = current_user
    if not wiki:
        return UserAccess.none
    if not user:
        if wiki.visibility == Visibility.PUBLIC or \
                wiki.visibility == Visibility.UNLISTED:
            return UserAccess.read
        return UserAccess.none
    if wiki.owner_id == user.id:
        return UserAccess.read | UserAccess.write | UserAccess.manage
    if wiki.visibility == Visibility.PRIVATE:
        return get_repo_access(wiki, owner, user)
    return UserAccess.read

def has_access(wiki, owner, access, user=None):
    return access in get_access(wiki, owner, user)

def check_access(owner_name, wiki_name, access):
    owner, wiki = get_wiki(owner_name, wiki_name)
    if not owner or not wiki:
        abort(404)
    a = get_access(wiki, owner)
    if not access in a:
        abort(404)
    return owner, wiki
