from flask import Blueprint, render_template, abort, request, redirect
from srht.flask import loginrequired
from srht.validation import Validation
from mansrht.access import UserAccess, check_access
from mansrht.wikis import delete_wiki

manage = Blueprint('manage', __name__)

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
    delete_wiki(wiki, owner, delete_repo == "on")
    return redirect("/")
