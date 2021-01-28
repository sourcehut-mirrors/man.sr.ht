from flask import Blueprint, render_template, abort, request, redirect, url_for
from srht.database import db
from srht.oauth import loginrequired
from srht.validation import Validation
from mansrht.access import UserAccess, check_access
from mansrht.repo import GitsrhtBackend
from mansrht.types import WikiVisibility
from mansrht.wikis import delete_wiki, is_root_wiki

manage = Blueprint('manage', __name__)

@manage.route("/manage/<owner_name>/<wiki_name>/info")
@loginrequired
def info(owner_name, wiki_name):
    owner, wiki = check_access(owner_name, wiki_name, UserAccess.manage)
    is_root = is_root_wiki(wiki)
    backend = GitsrhtBackend(owner)
    return render_template(
            "info.html", owner=owner, wiki=wiki, backend=backend,
            is_root=is_root)

@manage.route("/manage/<owner_name>/<wiki_name>/info", methods=["POST"])
@loginrequired
def info_POST(owner_name, wiki_name):
    owner, wiki = check_access(owner_name, wiki_name, UserAccess.manage)
    valid = Validation(request)
    visibility = valid.optional("visibility",
            cls=WikiVisibility,
            default=wiki.visibility)
    wiki.visibility = visibility
    db.session.commit()
    return redirect(url_for(
        "manage.info", owner_name=owner_name, wiki_name=wiki_name))

@manage.route("/manage/<owner_name>/<wiki_name>/delete")
@loginrequired
def delete(owner_name, wiki_name):
    # check_access() guarantees owner and wiki are valid.
    owner, wiki = check_access(owner_name, wiki_name, UserAccess.manage)
    return render_template(
            "delete.html", owner=owner, wiki=wiki,
            # Fill default value for "delete repo" option based-on if the
            # wiki was created with a new repo in the first place.
            delete_repo=wiki.repo.new)

@manage.route("/manage/<owner_name>/<wiki_name>/delete", methods=["POST"])
@loginrequired
def delete_POST(owner_name, wiki_name):
    valid = Validation(request)
    delete_repo = valid.optional("delete_repo")

    # check_access() guarantees owner and wiki are valid.
    owner, wiki = check_access(owner_name, wiki_name, UserAccess.manage)
    backend = GitsrhtBackend(owner)
    try:
        backend.unensure_repo_postupdate(wiki.repo)
    except:
        pass # Deleted, presumably
    delete_wiki(wiki, owner, delete_repo == "on")
    return redirect("/")
