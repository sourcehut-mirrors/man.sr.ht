import subprocess
from srht.database import db
from srht.config import cfg
from mansrht.types import Wiki
import shutil
import re
import os

repos_path = cfg("man.sr.ht", "repo-path")

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

def create_wiki(valid, owner):
    wiki_name = valid.require("name", friendly_name="Name")
    if not valid.ok:
        return None

    wiki = Wiki()
    wiki.name = wiki_name
    wiki.owner_id = owner.id
    wiki.path = os.path.join(repos_path, "~" + owner.username, wiki.name)
    db.session.add(wiki)
    db.session.flush()

    subprocess.run(["mkdir", "-p", wiki.path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "init", "--bare"], cwd=wiki.path,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "srht.repo-id", str(wiki.id)],
        cwd=wiki.path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    db.session.commit()
    return wiki
