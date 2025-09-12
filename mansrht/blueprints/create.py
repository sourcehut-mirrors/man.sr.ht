from flask import Blueprint, render_template, abort, request, redirect
from srht.database import db
from srht.flask import session
from srht.oauth import current_user, loginrequired
from srht.validation import Validation
from mansrht.repo import GitsrhtBackend
from mansrht.types import Wiki, Visibility
from mansrht.wikis import validate_name
from collections import namedtuple
import os

ListItem = namedtuple("ListItem", ["name", "url"])
create = Blueprint('create', __name__)

def select_repo(backend, wiki_name, wiki_visibility, **kwargs):
    repos, cursor = backend.get_repos()

    repos = [
        ListItem(repo["name"], backend.get_repo_url(repo["name"]))
        for repo in repos
    ]

    existing = [
        wiki.repo_name
        for wiki in Wiki.query.filter(Wiki.owner_id == current_user.id).all()
    ]

    # TODO: Add cancel button.
    return render_template(
            "select.html", typename="repo", typename_pretty="repo",
            default=wiki_name, default_visibility=wiki_visibility,
            items=sorted(repos, key=lambda x: x.name),
            existing=existing, **kwargs)

def select_ref(backend, wiki_name, repo_name, repo_visibility, new_repo, **kwargs):
    refs = []
    if not new_repo:
        refs, cursor = backend.get_refs(repo_name)
    if refs:
        refs = [ListItem(
            os.path.split(ref["name"])[1],
            backend.get_ref_url(repo_name, ref["name"])) for ref in refs]

    # TODO: Add cancel button.
    return render_template(
            "select.html", typename="ref", typename_pretty="ref",
            default="wiki", items=sorted(refs, key=lambda x: x.name), **kwargs)

@create.route("/wiki/create")
@loginrequired
def create_GET():
    is_root = session.get("configure_root", False)
    return render_template("create.html", is_root=is_root)

@create.route("/wiki/create", methods=["POST"])
@loginrequired
def create_POST():
    valid = Validation(request)
    wiki_name = valid.require("name", friendly_name="Name")
    if not valid.ok:
        return render_template("create.html", **valid.kwargs)
    validate_name(valid, current_user, wiki_name)
    if not valid.ok:
        return render_template("create.html", **valid.kwargs)
    visibility = valid.optional("visibility",
            default="PUBLIC",
            cls=Visibility)
    session["wiki_name"] = wiki_name
    session["wiki_visibility"] = visibility.value
    return redirect("/wiki/create/repo")

@create.route("/wiki/create/repo")
@loginrequired
def select_repo_GET():
    wiki_name = session.get("wiki_name")
    wiki_visibility = Visibility(session.get("wiki_visibility", "PRIVATE"))
    if not wiki_name:
        return redirect("/wiki/create")
    backend = GitsrhtBackend(current_user)
    return select_repo(backend, wiki_name, wiki_visibility)

@create.route("/wiki/create/repo", methods=["POST"])
@create.route("/wiki/create/repo/new", methods=["POST"])
@loginrequired
def select_repo_POST():
    valid = Validation(request)
    repo_name = valid.require("repo", friendly_name="Repo")
    # will not be set (and does not matter) if existing repo selected
    repo_visibility = valid.optional("visibility", default="PUBLIC")
    if not valid.ok:
        backend = GitsrhtBackend(current_user)
        wiki_name = session.get("wiki_name")
        visibility = Visibility(session.get("wiki_visibility", "PRIVATE"))
        return select_repo(backend, wiki_name, visibility, **valid.kwargs)

    # The repo name is checked at the end of the form.
    session["wiki_repo"] = (repo_name, repo_visibility, request.path.endswith("new"))
    return redirect("/wiki/create/ref")

@create.route("/wiki/create/ref")
@loginrequired
def select_ref_GET():
    wiki_name = session.get("wiki_name")
    wiki_repo = session.get("wiki_repo")
    if not wiki_name or not wiki_repo:
        session.pop("wiki_name", None)
        session.pop("wiki_repo", None)
        return redirect("/wiki/create")

    backend = GitsrhtBackend(current_user)
    repo_name, repo_visibility, new_repo = wiki_repo
    return select_ref(backend, wiki_name, repo_name, repo_visibility, new_repo)

@create.route("/wiki/create/ref", methods=["POST"])
@create.route("/wiki/create/ref/new", methods=["POST"])
@loginrequired
def select_ref_POST():
    wiki_name = session.get("wiki_name")
    wiki_repo = session.get("wiki_repo")
    if not wiki_name or not wiki_repo:
        session.pop("wiki_name", None)
        session.pop("wiki_repo", None)
        return redirect("/wiki/create")

    is_root = session.get("configure_root", False)
    visibility = Visibility(session.get("wiki_visibility", "PRIVATE"))
    repo_name, repo_visibility, new_repo = wiki_repo
    backend = GitsrhtBackend(current_user)

    valid = Validation(request)
    ref_name = valid.require("ref", friendly_name="Ref")
    if not valid.ok:
        return select_ref(backend, wiki_name, repo_name,
                repo_visibility, new_repo, **valid.kwargs)

    backend_repo = backend.get_repo(repo_name)
    if new_repo:
        # Check if a repo with the same name already exists.
        # If it does, we treat it as an error.
        valid.expect(
                backend_repo is None,
                "Repository already exists.",
                field="repo")
        if not valid.ok:
            return select_repo(backend, wiki_name, visibility.value, **valid.kwargs)
        backend_repo = backend.create_repo(repo_name, repo_visibility)

    wiki = Wiki()
    wiki.name = wiki_name
    wiki.owner_id = current_user.id
    wiki.visibility = visibility
    wiki.repo_name = backend_repo["name"]
    wiki.repo_ref = ref_name
    db.session.add(wiki)

    if is_root:
        root_wiki = RootWiki(id=wiki.id)
        db.session.add(root_wiki)

    db.session.commit()

    del session["wiki_name"]
    del session["wiki_repo"]
    session.pop("wiki_visibility", None)
    session.pop("configure_root", None)

    return redirect("/{}/{}".format(current_user.canonical_name, wiki_name))
