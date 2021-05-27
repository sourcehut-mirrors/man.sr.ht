from flask import Blueprint, request
from srht.crypto import verify_request_signature
from srht.database import db
from srht.flask import csrf_bypass
from mansrht.types import User, Wiki, BackingRepo
from mansrht.wikis import delete_wiki
import json

webhooks_notify = Blueprint("webhooks_notify", __name__)

@csrf_bypass
@webhooks_notify.route("/webhook/notify/<repo_id>/refs", methods=["POST"])
def ref_update(repo_id):
    event = request.headers.get("X-Webhook-Event")
    payload = verify_request_signature(request)
    payload = json.loads(payload.decode("utf-8"))
    if event != "repo:post-update":
        return f"Unexpected event {event}"
    wiki = (Wiki.query.join(Wiki.repo)
            .filter(BackingRepo.id == repo_id)).one_or_none()
    if not wiki:
        return "I don't recognize this wiki"
    repo = wiki.repo
    for ref in payload["refs"]:
        if ref["name"] == f"refs/heads/{repo.ref}":
            commit = ref.get("new")
            if commit:
                repo.commit_sha = commit["id"]
                repo.commit_author = commit["author"]["name"]
                repo.commit_email = commit["author"]["email"]
                repo.commit_time = commit["timestamp"]
                repo.commit_message = commit["message"]
                repo.tree_sha = commit["tree"]
            else:
                # Nullify all the fields so that the wiki defaults back to the
                # "new-wiki" page.
                repo.commit_sha = None
                repo.commit_author = None
                repo.commit_email = None
                repo.commit_time = None
                repo.commit_message = None
                repo.tree_sha = None
            db.session.commit()
            break
    else:
        return "No wikis updated"
    return "Updated wiki SHA, thanks!"

@csrf_bypass
@webhooks_notify.route("/webhook/notify/repos/update", methods=["POST"])
def repo_update():
    event = request.headers.get("X-Webhook-Event")
    payload = json.loads(request.data.decode("utf-8"))
    if event not in ["repo:update", "repo:delete"]:
        return f"Unexpected event {event}"
    repo = BackingRepo.query.filter(
            BackingRepo.resource_id == payload["id"]).one_or_none()
    if not repo:
        return "Unknown repo"
    if event == "repo:update":
        if repo and payload["name"] != repo.name:
            repo.name = payload["name"]
            db.session.commit()
            return "Updated repo name"
    elif event == "repo:delete":
        wiki = Wiki.query.filter(Wiki.repo_id == repo.id).one_or_none()
        wiki_name = wiki.name
        delete_wiki(wiki, wiki.owner, delete_from_backend=False)
        return f"Deleted wiki {wiki_name}"
    return "No repos updated"
