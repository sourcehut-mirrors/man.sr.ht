from flask import Blueprint, request
from srht.database import db
from srht.flask import csrf_bypass
from mansrht.types import User, Wiki, BackingRepo
import json

webhooks_notify = Blueprint("webhooks.notify", __name__)

@csrf_bypass
@webhooks_notify.route("/webhook/notify/<reponame>/refs", methods=["POST"])
def ref_update(reponame):
    payload = json.loads(request.data.decode("utf-8"))
    event = request.headers.get("X-Webhook-Event")
    if event != "repo:post-update":
        return f"Unexpected event {event}"

    owner = User.query.filter(
            User.username.like(payload["pusher"]["name"])).one_or_none()
    wiki = (Wiki.query.join(Wiki.repo)
            .filter(Wiki.owner_id == owner.id)
            .filter(BackingRepo.name == reponame)).one_or_none()
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
