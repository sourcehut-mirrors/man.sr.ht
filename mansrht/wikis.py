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

def is_root_wiki(wiki):
    if not wiki:
        return False
    root_wiki = RootWiki.query.one_or_none()
    if root_wiki:
        return root_wiki.id == wiki.id
    return False

def create_repo(is_new, name, resource_id, ref, owner, commit=None):
    repo = BackingRepo()
    repo.new = is_new
    repo.name = name
    repo.resource_id = resource_id
    repo.ref = ref
    if commit:
        repo.commit_sha = commit["id"]
        repo.commit_author = commit["author"]["name"]
        repo.commit_email = commit["author"]["email"]
        # Directly store the datetime string.
        repo.commit_time = commit["timestamp"]
        repo.commit_message = commit["message"]
        repo.tree_sha = commit["tree"]

    db.session.add(repo)
    db.session.flush()

    backend = GitsrhtBackend(owner)
    backend.ensure_repo_postupdate(repo)

    db.session.flush()
    db.session.commit()
    return repo

def create_wiki(valid, owner, wiki_name, repo, visibility, is_root=False):
    wiki = Wiki()
    wiki.name = wiki_name
    wiki.owner_id = owner.id
    wiki.repo_id = repo.id
    wiki.visibility = visibility
    db.session.add(wiki)
    db.session.flush()

    if is_root:
        root_wiki = RootWiki(id=wiki.id)
        db.session.add(root_wiki)
        db.session.flush()

    db.session.commit()
    return wiki

def delete_wiki(wiki, owner, delete_from_backend=False):
    backend = GitsrhtBackend(owner)
    repo = wiki.repo

    # The repo is always removed from the backend table. Deletion of the actual
    # repo is done separately if the user asks for that to be done.
    if delete_from_backend:
        backend.delete_repo(repo.name)

    root_wiki = RootWiki.query.all()
    if root_wiki and root_wiki[0].id == wiki.id:
        db.session.delete(root_wiki[0])
        db.session.flush()

    db.session.delete(wiki)
    db.session.flush()
    db.session.delete(repo)
    db.session.flush()
    db.session.commit()
