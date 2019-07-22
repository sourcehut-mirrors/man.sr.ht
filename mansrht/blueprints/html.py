from bs4 import BeautifulSoup
from flask import Blueprint, render_template, abort, request, redirect
from flask_login import current_user
from srht.flask import session
from srht.markdown import markdown, extract_toc
from srht.oauth import UserType
from srht.validation import Validation
from scmsrht.urls import get_clone_urls
from mansrht.access import UserAccess, check_access
from mansrht.redis import redis
from mansrht.repo import GitsrhtBackend
from mansrht.types import User, Wiki, RootWiki
from mansrht.wikis import is_root_wiki
from datetime import timedelta
from jinja2 import Markup
from urllib.parse import urlparse, urlunparse
import json
import os
import yaml

html = Blueprint('html', __name__)

def get_tree(backend, wiki, sha, path=None):
    # Cached tree includes the relative path from the root.
    path = path or ""
    cachekey = f"man.sr.ht:tree:{wiki.repo.name}:{sha}:{path}"
    tree = redis.get(cachekey)
    if not tree:
        tree = backend.get_tree(wiki.repo.name, sha, path=path)
        if not tree:
            return None
        redis.setex(cachekey, timedelta(days=7), json.dumps(tree))
    else:
        tree = json.loads(tree)
    return tree

def get_blob(backend, wiki, sha):
    cachekey = f"man.sr.ht:blob:{wiki.repo.name}:{sha}"
    blob = redis.get(cachekey)
    if not blob:
        blob = backend.get_blob(wiki.repo.name, sha)
        if not blob:
            return None
        redis.setex(cachekey, timedelta(days=7), blob)
    return blob

def content(wiki, path, is_root=False, **kwargs):
    def find_entry(tree, name):
        for entry in tree["entries"]:
            if entry["name"] == name:
                return entry
        return None

    backend = GitsrhtBackend(wiki.owner)
    clone_urls = get_clone_urls(
            backend.origin, wiki.owner, wiki.repo, backend.ssh_format)
    if not wiki.repo.commit_sha:
        return render_template(
                "new-wiki.html", clone_url=clone_urls[1], repo=wiki.repo)

    head, tail = os.path.split(path) if path else (None, None)
    path = tuple(p for p in (head, tail) if p)
    tree = get_tree(backend, wiki, wiki.repo.tree_sha, path=head)
    if tree and tail:
        tree = find_entry(tree, tail)
    if not tree:
        abort(404)
    if tree.get("type") != "blob":
        tree = get_tree(backend, wiki, tree["id"])
        if not tree:
            abort(404)
        # Redirect directories to / so links work right.
        if find_entry(tree, "index.md") is not None:
            tree = find_entry(tree, "index.md")
            url = urlparse(request.url)
            if url.path and url.path[-1] != "/":
                url = list(url)
                url[2] += "/"
                return redirect(urlunparse(url))
        elif is_root and find_entry(tree, "index.html") is not None:
            tree = find_entry(tree, "index.html")
            url = urlparse(request.url)
            if url.path and url.path[-1] != "/":
                url = list(url)
                url[2] += "/"
                return redirect(urlunparse(url))
        else:
            abort(404)

    blob_id = tree["id"]
    cachekey = f"{wiki.repo.name}:{blob_id}"
    html_cachekey = f"man.sr.ht:content:{cachekey}"
    frontmatter_cachekey = f"man.sr.ht:frontmatter:{cachekey}"
    html = redis.get(html_cachekey)
    if not html:
        md = get_blob(backend, wiki, blob_id)
        if md is None:
            abort(404)

        frontmatter = dict()
        if md.startswith("---\n"):
            try:
                end = md.index("---\n\n", 1)
            except ValueError:
                end = -1 # this is dumb, Guido
            if end != -1:
                frontmatter = md[4:end]
                md = md[end+5:]
        if frontmatter:
            try:
                frontmatter = yaml.safe_load(frontmatter)
                if not isinstance(frontmatter, dict):
                    raise Exception()
            except:
                md = "<!-- Error parsing YAML frontmatter -->\n\n" + md
                frontmatter = dict()
        if tree["name"].endswith(".md"):
            html = markdown(md, ["h1", "h2", "h3", "h4", "h5"], baselevel=3)
        else:
            html = Markup(md)
        if current_user:
            html = html.replace("{{{srht_username}}}", current_user.username)
        else:
            html = html.replace("{{{srht_username}}}", "USERNAME")
        redis.setex(html_cachekey, timedelta(days=7), html)
        redis.setex(frontmatter_cachekey,
                timedelta(days=7), json.dumps(frontmatter))
    else:
        html = Markup(html.decode())
        frontmatter = redis.get(frontmatter_cachekey)
        frontmatter = json.loads(frontmatter.decode())
    title = path[-1].rstrip(".md") if path else "index"
    toc = extract_toc(html)
    if "title" in frontmatter:
        title = frontmatter["title"]
    return render_template("content.html",
            content=html, title=title, repo=wiki.repo, toc=toc,
            wiki=wiki, is_root=is_root, path=path, frontmatter=frontmatter,
            clone_urls=clone_urls, **kwargs)

@html.route("/")
@html.route("/<path:path>")
def root_content(path=None):
    root_wiki = RootWiki.query.all()
    if not root_wiki:
        if current_user and current_user.user_type == UserType.admin:
            session["configure_root"] = True
            return redirect("/wiki/create")
        # Fallback page
        return render_template("index.html")
    root_wiki = root_wiki[0]
    wiki = Wiki.query.filter(Wiki.id == root_wiki.id).first()
    if not wiki:
        abort(404)
    return content(wiki, path, is_root=True)

@html.route("/<owner_name>/<wiki_name>")
@html.route("/<owner_name>/<wiki_name>/")
@html.route("/<owner_name>/<wiki_name>/<path:path>")
def user_content(owner_name, wiki_name, path=None):
    owner, wiki = check_access(owner_name, wiki_name, UserAccess.read)
    if not owner or not wiki:
        abort(404)
    # Redirect to root if it _is_ the root.
    if is_root_wiki(wiki):
        return redirect("/")
    return content(wiki, path)
