from bs4 import BeautifulSoup
from flask import Blueprint, render_template, abort, request, redirect
from flask_login import current_user
from srht.config import cfg
from srht.flask import loginrequired
from srht.markdown import markdown, extract_toc
from srht.validation import Validation
from mansrht.types import User, Wiki
from mansrht.wikis import create_wiki
from datetime import datetime
from jinja2 import Markup
from urllib.parse import urlparse, urlunparse
import pygit2
import os

html = Blueprint('html', __name__)
repo_path = cfg("man.sr.ht", "repo-path")

def content(repo, path, wiki=None, is_root=False, **kwargs):
    master = repo.branches.get("master")
    if not master:
        if wiki:
            return render_template("new-wiki.html", wiki=wiki)
        # Root wiki with no content.
        return render_template("index.html")
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
        elif "index.html" in tree and is_root:
            tree = tree["index.html"]
            url = urlparse(request.url)
            if url.path and url.path[-1] != "/":
                url = list(url)
                url[2] += "/"
                return redirect(urlunparse(url))
        else:
            abort(404)
    blob = repo.get(tree.id)
    if blob.is_binary:
        abort(404)
    md = blob.data.decode()
    if tree.name.endswith(".md"):
        html = markdown(md, ["h1", "h2", "h3", "h4", "h5"], baselevel=3)
    else:
        html = Markup(md)
    title = path[-1].rstrip(".md") if path else "index"
    ctime = datetime.fromtimestamp(commit.commit_time)
    toc = extract_toc(html)
    soup = BeautifulSoup(str(html), "html5lib")
    h3 = soup.find("h2")
    if h3:
        title = h2.text
    return render_template("content.html",
            content=html, title=title, commit=commit, ctime=ctime, toc=toc,
            wiki=wiki, is_root=is_root, **kwargs)

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
