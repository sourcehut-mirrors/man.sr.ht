import subprocess
from srht.database import db
from mansrht.types import Wiki, RootWiki
from mansrht.repo import GitsrhtBackend
import shutil
import re
import os

def validate_name(valid, owner, wiki_name):
    if not valid.ok:
        return None
    valid.expect(re.match(r'^[A-Za-z0-9._-]+$', wiki_name),
            "Name must match [A-Za-z0-9._-]+", field="name")
    valid.expect(wiki_name not in [".", ".."],
            "Name cannot be '.' or '..'", field="name")
    valid.expect(wiki_name not in [".git", ".hg"],
            "Name must not be '.git' or '.hg'", field="name")
    existing = (Wiki.query
            .filter(Wiki.owner_id == owner.id)
            .filter(Wiki.name.ilike(wiki_name.replace('_', '\\_')))
            .first())
    valid.expect(not existing, "This name is already in use.", field="name")
    return None

def is_root_wiki(wiki):
    if not wiki:
        return False
    root_wiki = RootWiki.query.one_or_none()
    if root_wiki:
        return root_wiki.id == wiki.id
    return False

def delete_wiki(wiki, owner, delete_from_backend=False):
    backend = GitsrhtBackend(owner)

    # The repo is always removed from the backend table. Deletion of the actual
    # repo is done separately if the user asks for that to be done.
    if delete_from_backend:
        try:
            backend.delete_repo(wiki.repo_name)
        except:
            pass # Presumably deleted by the user

    root_wiki = RootWiki.query.one_or_none()
    if root_wiki and root_wiki.id == wiki.id:
        db.session.delete(root_wiki)

    db.session.delete(wiki)
    db.session.commit()
