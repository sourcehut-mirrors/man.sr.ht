from io import BytesIO
from bs4 import BeautifulSoup
from flask import (
    Blueprint, url_for, render_template, abort, request, redirect, send_file,
)
from srht.flask import session
from srht.markdown import SRHT_MARKDOWN_VERSION, markdown, extract_toc
from srht.oauth import UserType, current_user
from srht.cache import set_cache, get_cache
from srht.validation import Validation
from scmsrht.urls import get_clone_urls
from mansrht.access import UserAccess, check_access
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
    tree = get_cache(cachekey)
    if not tree:
        tree = backend.get_tree(wiki.repo.name, sha, path=path)
        if not tree:
            return None
        set_cache(cachekey, timedelta(days=7), json.dumps(tree))
    else:
        tree = json.loads(tree)
    return tree

def get_blob(backend, wiki, sha, path=None):
    cachekey = f"man.sr.ht:blob:{wiki.repo.name}:{sha}"
    ctype_cachekey = f"{cachekey}:content_type"
    blob = get_cache(cachekey)
    ctype = get_cache(ctype_cachekey)

    if not blob or not ctype:
        blob, ctype = backend.get_blob(
            wiki.repo.name,
            sha,
            path=path,
            return_ctype=True,
        )
        if not blob:
            return None, None
        set_cache(cachekey, timedelta(days=7), blob)
        set_cache(ctype_cachekey, timedelta(days=7), ctype)
    else:
        if isinstance(ctype, bytes):
            ctype = ctype.decode("utf-8")

    return blob, ctype

def content(wiki, path, is_root=False, **kwargs):
    def find_entry(tree, name):
        for entry in tree["entries"]:
            if entry["name"] == name:
                return entry
        return None

    link_prefix = kwargs.get('link_prefix')
    backend = GitsrhtBackend(wiki.owner)
    clone_urls = get_clone_urls(
            backend.origin, wiki.owner, wiki.repo, backend.ssh_format)
    web_url=f"{backend.origin}/{wiki.owner.canonical_name}/{wiki.repo.name}"
    if not wiki.repo.commit_sha:
        return render_template("new-wiki.html", wiki=wiki,
                clone_url=clone_urls[1], repo=wiki.repo, web_url=web_url)

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
            return render_template("new-wiki.html", wiki=wiki,
                    clone_url=clone_urls[1], repo=wiki.repo, web_url=web_url)

    blob_id = tree["id"]
    blob_name = tree["name"]
    cachekey = f"{wiki.repo.name}:{blob_id}"
    html_cachekey = f"man.sr.ht:content:{cachekey}:v{SRHT_MARKDOWN_VERSION}:v1"
    frontmatter_cachekey = f"man.sr.ht:frontmatter:{cachekey}"
    html = get_cache(html_cachekey)
    if not html:
        md, ctype = get_blob(backend, wiki, blob_id, path=blob_name)
        if md is None:
            abort(404)

        if not ctype.startswith("text/plain"):
            # Non-text file (img, etc.). Return the raw data
            return send_file(BytesIO(md), mimetype=ctype)

        if isinstance(md, bytes):
            md = md.decode()

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
            html = markdown(
                md,
                baselevel=3,
                link_prefix=link_prefix,
            )
        else:
            html = Markup(md)
        if current_user:
            html = html.replace("{{{srht_username}}}", current_user.username)
        else:
            html = html.replace("{{{srht_username}}}", "USERNAME")
        set_cache(html_cachekey, timedelta(days=7), html)
        set_cache(frontmatter_cachekey,
                timedelta(days=7), json.dumps(frontmatter))
    else:
        html = Markup(html.decode())
        frontmatter = get_cache(frontmatter_cachekey)
        frontmatter = json.loads(frontmatter.decode())
    title = path[-1].rstrip(".md") if path else "index"
    toc = extract_toc(html)
    if "title" in frontmatter:
        title = frontmatter["title"]
    soup = BeautifulSoup(html, "html.parser")
    firstpara = soup.find("p")
    if firstpara:
        firstpara = firstpara.extract()
    return render_template("content.html",
            content=Markup(soup), firstpara=Markup(firstpara),
            title=title, repo=wiki.repo, toc=toc, wiki=wiki, is_root=is_root,
            path=path, frontmatter=frontmatter, clone_urls=clone_urls,
            web_url=web_url, **kwargs)

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
    link_prefix = url_for("html.root_content", path=path)
    return content(wiki, path, is_root=True, link_prefix=link_prefix)

# The tilde (~) in the route is necessary in order to differentiate between the
# root wiki and user wikis.
@html.route("/~<owner_name>/<wiki_name>")
@html.route("/~<owner_name>/<wiki_name>/")
@html.route("/~<owner_name>/<wiki_name>/<path:path>")
def user_content(owner_name, wiki_name, path=None):
    owner, wiki = check_access(f"~{owner_name}", wiki_name, UserAccess.read)
    if not owner or not wiki:
        abort(404)
    # Redirect to root if it _is_ the root.
    if is_root_wiki(wiki):
        return redirect("/")
    link_prefix = url_for(
        "html.user_content",
        owner_name=owner_name,
        wiki_name=wiki_name,
    )
    return content(wiki, path, link_prefix=link_prefix)
