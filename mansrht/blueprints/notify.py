from flask import Blueprint, request
from srht.database import db
from srht.flask import csrf_bypass
from mansrht.types import User, Wiki, BackingRepo
from mansrht.wikis import delete_wiki
import json

webhooks_notify = Blueprint("webhooks.notify", __name__)

def check_event(request, expected):
    payload = json.loads(request.data.decode("utf-8"))
    event = request.headers.get("X-Webhook-Event")
    if event != expected:
        return payload, None
    return payload, event

@csrf_bypass
@webhooks_notify.route("/webhook/notify/<repo_id>/refs", methods=["POST"])
def ref_update(repo_id):
    payload, event = check_event(request, "repo:post-update")
    if not event:
        return f"Unexpected event {event}"
    owner = User.query.filter(
            User.username.like(payload["pusher"]["name"])).one_or_none()
    wiki = (Wiki.query.join(Wiki.repo)
            .filter(Wiki.owner_id == owner.id)
            .filter(BackingRepo.id == repo_id)).one_or_none()
    repo = wiki.repo
    for ref in payload["refs"]:
        if ref["name"] == f"refs/heads/{repo.ref}":
            commit = ref.get("new")
            if not commit:
                break
            repo.commit_sha = commit["id"]
            repo.commit_author = commit["author"]["name"]
            repo.commit_email = commit["author"]["email"]
            repo.commit_time = commit["timestamp"]
            repo.commit_message = commit["message"]
            repo.tree_sha = commit["tree"]
            db.session.commit()
            break
    else:
        return "No wikis updated"
    return "Updated wiki SHA, thanks!"

@csrf_bypass
@webhooks_notify.route("/webhook/notify/repos/update", methods=["POST"])
def repo_update():
    payload, event = check_event(request, "repo:update")
    if not event:
        return f"Unexpected event {event}"
    repo = BackingRepo.query.filter(
            BackingRepo.resource_id == payload["id"]).one_or_none()
    if repo and payload["name"] != repo.name:
        repo.name = payload["name"]
        db.session.commit()
        return "Updated repo name"
    return "No repos updated"

@csrf_bypass
@webhooks_notify.route("/webhook/notify/repos/delete", methods=["POST"])
def repo_delete():
    payload, event = check_event(request, "repo:delete")
    if not event:
        return f"Unexpected event {event}"
    repo = BackingRepo.query.filter(
            BackingRepo.resource_id == payload["id"]).one_or_none()
    if not repo:
        return "No wikis updated"
    wiki = Wiki.query.filter(Wiki.repo_id == repo.id).one_or_none()
    delete_wiki(wiki, wiki.owner, delete_from_backend=False)
    return f"Deleted wiki {wiki.name}"
