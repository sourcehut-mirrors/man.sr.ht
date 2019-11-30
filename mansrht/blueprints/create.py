from flask import Blueprint, render_template, abort, request, redirect
from srht.database import db
from srht.flask import session
from srht.oauth import current_user, loginrequired
from srht.validation import Validation
from mansrht.repo import GitsrhtBackend
from mansrht.types import Wiki, WikiVisibility
from mansrht.wikis import validate_name, create_repo, create_wiki
from collections import namedtuple
import os

ListItem = namedtuple("ListItem", ["name", "url"])
create = Blueprint('create', __name__)

def select_repo(backend, wiki_name, **kwargs):
    repos = [
        ListItem(repo["name"], backend.get_repo_url(repo["name"]))
        for repo in backend.get_repos()
    ]

    existing = [
        wiki.repo.name
        for wiki in Wiki.query.filter(Wiki.owner_id == current_user.id).all()
        if wiki.repo
    ]

    # TODO: Add cancel button.
    return render_template(
            "select.html", typename="repo", typename_pretty="repo",
            default=wiki_name, items=sorted(repos, key=lambda x: x.name),
            existing=existing, **kwargs)

def select_ref(backend, wiki_name, repo_name, new_repo):
    refs = []
    if not new_repo:
        try:
            refs = [ref for ref in backend.get_refs(repo_name)]
        except:
            abort(500)
    if refs:
        refs = [ListItem(
            os.path.split(ref["name"])[1],
            backend.get_ref_url(repo_name, ref["name"])) for ref in refs]

    # TODO: Add cancel button.
    return render_template(
            "select.html", typename="ref", typename_pretty="ref",
            default="wiki", items=sorted(refs, key=lambda x: x.name))

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
            default="public",
            cls=WikiVisibility)
    session["wiki_name"] = wiki_name
    session["wiki_visibility"] = visibility.name
    return redirect("/wiki/create/repo")

@create.route("/wiki/create/repo")
@loginrequired
def select_repo_GET():
    wiki_name = session.get("wiki_name")
    if not wiki_name:
        return redirect("/wiki/create")
    backend = GitsrhtBackend(current_user)
    return select_repo(backend, wiki_name)

@create.route("/wiki/create/repo", methods=["POST"])
@create.route("/wiki/create/repo/new", methods=["POST"])
@loginrequired
def select_repo_POST():
    valid = Validation(request)
    repo_name = valid.require("repo", friendly_name="Repo")
    if not valid.ok:
        backend = GitsrhtBackend(current_user)
        return select_repo(backend, session.get("wiki_name"), **valid.kwargs)

    # The repo name is checked at the end of the form.
    session["wiki_repo"] = (repo_name, request.path.endswith("new"))
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
    repo_name, new_repo = wiki_repo
    return select_ref(backend, wiki_name, repo_name, new_repo)

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
    visibility = WikiVisibility(session.get("wiki_visibility", "public"))
    repo_name, new_repo = wiki_repo
    backend = GitsrhtBackend(current_user)

    valid = Validation(request)
    ref_name = valid.require("ref", friendly_name="Ref")
    if not valid.ok:
        return select_ref(backend, wiki_name, repo_name,
                new_repo, **valid.kwargs)

    repo_dict = backend.get_repo(repo_name)
    if new_repo:
        # Check if a repo with the same name already exists.
        # If it does, we treat it as an error.
        valid.expect(
                repo_dict is None,
                "Repository already exists.",
                field="repo")
        if not valid.ok:
            return select_repo(backend, wiki_name, **valid.kwargs)
        repo_dict = backend.create_repo(repo_name)

    # Try to find the latest commit if we're using an existing repo + ref.
    new_ref = request.path.endswith("new")
    commit = None
    if not new_repo and not new_ref:
        commit = backend.get_latest_commit(repo_name, ref_name)

    backend.ensure_repo_update()

    repo = create_repo(
            new_repo, repo_dict["name"], repo_dict["id"], ref_name,
            current_user, commit=commit)
    create_wiki(
            valid, current_user, wiki_name,
            repo, visibility, is_root=is_root)

    del session["wiki_name"]
    del session["wiki_repo"]
    session.pop("wiki_visibility", None)
    session.pop("configure_root", None)

    return redirect("/{}/{}".format(current_user.canonical_name, wiki_name))
