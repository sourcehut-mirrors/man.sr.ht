from flask import Blueprint, request
from srht.crypto import verify_request_signature
from srht.database import db
from srht.flask import csrf_bypass
from mansrht.types import User, Wiki
from mansrht.wikis import delete_wiki
import json

webhooks_notify = Blueprint("webhooks_notify", __name__)

@csrf_bypass
@webhooks_notify.route("/webhook/notify/<repo_id>/refs", methods=["POST"])
def ref_update(repo_id):
    pass # TODO: Remove me in a near-future commit

@csrf_bypass
@webhooks_notify.route("/webhook/notify/repos/update", methods=["POST"])
def repo_update():
    pass # TODO: Remove me in a near-future commit
