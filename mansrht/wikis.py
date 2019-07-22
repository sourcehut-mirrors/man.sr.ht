import subprocess
from srht.database import db
from mansrht.types import Wiki, RootWiki, BackingRepo
from mansrht.repo import GitsrhtBackend
import shutil
import re
import os

def validate_name(valid, owner, wiki_name):
    if not valid.ok:
        return None
    valid.expect(re.match(r'^[a-z._-][a-z0-9._-]*$', wiki_name),
            "Name must match [a-z._-][a-z0-9._-]*", field="name")
    existing = (Wiki.query
            .filter(Wiki.owner_id == owner.id)
            .filter(Wiki.name.like(wiki_name))
            .first())
    valid.expect(not existing, "This name is already in use.", field="name")
    return None

def create_repo(is_new, name, ref, webhook_id, commit=None):
    repo = BackingRepo()
    repo.new = is_new
    repo.name = name
    repo.ref = ref
    if commit:
        repo.commit_sha = commit["id"]
        repo.commit_author = commit["author"]["name"]
        repo.commit_email = commit["author"]["email"]
        # Directly store the datetime string.
        repo.commit_time = commit["timestamp"]
        repo.commit_message = commit["message"]
        repo.tree_sha = commit["tree"]
    repo.webhook_id = webhook_id

    db.session.add(repo)
    db.session.flush()
    db.session.commit()
    return repo


def create_wiki(valid, owner, wiki_name, repo, is_root=False):
    wiki = Wiki()
    wiki.name = wiki_name
    wiki.owner_id = owner.id
    wiki.repo_id = repo.id
    db.session.add(wiki)
    db.session.flush()

    if is_root:
        root_wiki = RootWiki(id=wiki.id)
        db.session.add(root_wiki)
        db.session.flush()

    db.session.commit()
    return wiki

def delete_wiki(wiki, owner, delete_from_backend=False):
    # The repo is always removed from the backend table. Deletion of the actual
    # repo is done separately if the user asks for that to be done.
    repo = wiki.repo
    backend = GitsrhtBackend(owner)
    backend.unsubscribe_repo_update(repo)

    if delete_from_backend:
        backend.delete_repo(repo.name)

    root_wiki = RootWiki.query.all()
    if root_wiki:
        root_wiki = Wiki.query.filter(Wiki.id == root_wiki[0].id).first()
        if root_wiki and wiki == root_wiki:
            db.session.delete(root_wiki)
            db.session.flush()

    db.session.delete(wiki)
    db.session.flush()
    db.session.delete(repo)
    db.session.flush()
    db.session.commit()
