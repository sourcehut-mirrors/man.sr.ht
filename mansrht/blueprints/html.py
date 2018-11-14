from flask import Blueprint, render_template, abort, request, redirect
from flask_login import current_user
from srht.config import cfg
from srht.flask import loginrequired
from srht.markdown import markdown, extract_toc
from srht.validation import Validation
from mansrht.types import User, Wiki
from mansrht.wikis import create_wiki
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import pygit2
import os

html = Blueprint('html', __name__)
repo_path = cfg("man.sr.ht", "repo-path")

def content(repo, path, wiki=None, **kwargs):
    master = repo.branches.get("master")
    if not master:
        return render_template("new-wiki.html", wiki=wiki)
    commit = repo.get(master.target)
    tree = commit.tree
    _path = path
    path = os.path.split(path) if path else tuple()
    path = tuple(p for p in path if p != "")
    for entry in path:
        if isinstance(tree, pygit2.TreeEntry):
            tree = repo.get(tree.id)
        if not isinstance(tree, pygit2.Tree):
            abort(404)
        if not entry in tree:
            abort(404)
        tree = tree[entry]
    if tree.type != "blob":
        tree = repo.get(tree.id)
        if "index.md" in tree:
            # redirect directories to / so links work right
            tree = tree["index.md"]
            url = urlparse(request.url)
            if url.path and url.path[-1] != "/":
                url = list(url)
                url[2] += "/"
                return redirect(urlunparse(url))
        else:
            abort(404)
    blob = repo.get(tree.id)
    md = blob.data.decode()
    html = markdown(md, ["h1", "h2", "h3", "h4", "h5"], baselevel=3)
    title = path[-1].rstrip(".md") if path else "index"
    ctime = datetime.fromtimestamp(commit.commit_time)
    toc = extract_toc(html)
    return render_template("content.html",
            content=html, title=title, commit=commit, ctime=ctime, toc=toc,
            wiki=wiki, **kwargs)

@html.route("/")
@html.route("/<path:path>")
def root_content(path=None):
    try:
        repo = pygit2.Repository(os.path.join(repo_path, "root"))
    except:
        # Fallback page
        return render_template("index.html")
    return content(repo, path, is_root=True)

@html.route("/~<owner_name>/<wiki_name>")
@html.route("/~<owner_name>/<wiki_name>/")
@html.route("/~<owner_name>/<wiki_name>/<path:path>")
def user_content(owner_name, wiki_name, path=None):
    owner = User.query.filter(User.username == owner_name).first()
    if not owner:
        abort(404)
    wiki = (Wiki.query
            .filter(Wiki.owner_id == owner.id)
            .filter(Wiki.name.ilike(wiki_name))
        ).first()
    if not wiki:
        abort(404)
    repo = pygit2.Repository(os.path.join(wiki.path))
    return content(repo, path, wiki)

@html.route("/wiki/create")
@loginrequired
def create_GET():
    return render_template("create.html")

@html.route("/wiki/create", methods=["POST"])
@loginrequired
def create_POST():
    valid = Validation(request)
    wiki = create_wiki(valid, current_user)
    if not wiki:
        return render_template("create.html", **valid.kwargs)
    return redirect("/~{}/{}".format(current_user.username, wiki.name))
