from flask import Blueprint, render_template, abort
from srht.config import cfg
from srht.markdown import markdown, extract_toc
from datetime import datetime
import pygit2 as git
import os

html = Blueprint('html', __name__)
repo_path = cfg("man.sr.ht", "repo-path")

def content(repo, path):
    master = repo.branches.get("master")
    if not master:
        # TODO: show reason maybe
        abort(404)
    commit = repo.get(master.target)
    tree = commit.tree
    path = os.path.split(path) if path else tuple()
    for entry in path:
        if tree.type != "tree":
            abort(404)
        if not entry in tree:
            abort(404)
        tree = tree["path"]
    if tree.type != "blob":
        if "index.md" in tree:
            tree = tree["index.md"]
        else:
            abort(404)
    blob = repo.get(tree.id)
    md = blob.data.decode()
    html = markdown(md, ["h1", "h2", "h3", "h4", "h5"], baselevel=3)
    title = os.path.splitext(path[-1])[0] if path else "index"
    ctime = datetime.fromtimestamp(commit.commit_time)
    toc = extract_toc(html)
    return render_template("content.html",
            content=html, title=title, commit=commit, ctime=ctime, toc=toc)

@html.route("/")
@html.route("/<path:path>")
def root_content(path=None):
    try:
        repo = git.Repository(os.path.join(repo_path, "root"))
    except:
        # Fallback page
        return render_template("index.html")
    return content(repo, path)
