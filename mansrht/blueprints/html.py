from io import BytesIO
from bs4 import BeautifulSoup
from flask import (
    Blueprint, url_for, render_template, abort, request, redirect, send_file,
)
from srht.flask import session, date_handler
from srht.markdown import SRHT_MARKDOWN_VERSION, markdown, extract_toc
from srht.oauth import UserType, current_user
from srht.cache import set_cache, get_cache
from srht.validation import Validation
from mansrht.access import UserAccess, check_access
from mansrht.repo import GitsrhtBackend
from mansrht.types import User, Wiki, RootWiki
from mansrht.wikis import is_root_wiki
from prometheus_client import Counter
from datetime import timedelta
from markupsafe import Markup
from urllib.parse import urlparse, urlunparse
import json
import os
import yaml

html = Blueprint('html', __name__)

metrics = type("metrics", tuple(), {
    c.describe()[0].name: c
    for c in [
        Counter("mansrht_tree_cache_access", "Number of tree cache accesses"),
        Counter("mansrht_tree_cache_miss", "Number of tree cache misses"),
        Counter("mansrht_blob_cache_access", "Number of blob cache accesses"),
        Counter("mansrht_blob_cache_miss", "Number of blob cache misses"),
        Counter("mansrht_markdown_cache_access", "Number of markdown cache accesses"),
        Counter("mansrht_markdown_cache_miss", "Number of markdown cache misses"),
    ]
})

def content(wiki, path, is_root=False, **kwargs):
    backend = GitsrhtBackend(wiki.owner)

    ssh_host = urlparse(backend.origin_ext).hostname
    clone_urls = {
            "https": f"{backend.origin}/{wiki.owner}/{wiki.repo.name}",
            "ssh": f"{backend.ssh_user}@{ssh_host}:{wiki.owner}/{wiki.repo.name}",
    }

    web_url = f"{backend.origin}/{wiki.owner.canonical_name}/{wiki.repo.name}"
    if not wiki.repo.commit_sha:
        return render_template("new-wiki.html", wiki=wiki,
                clone_urls=clone_urls, repo=wiki.repo, web_url=web_url)

    if not path:
        path = ""

    n = 0
    item = backend.get_tree_entry(wiki.repo.name, wiki.repo.ref, path=path)
    if item and item["object"]["type"] == "TREE" and not path.endswith("/"):
        if path and path != "/":
            return redirect(request.path + "/")

    while item and item["object"]["type"] == "TREE" and n < 5:
        item = backend.get_tree_entry(wiki.repo.name, wiki.repo.ref,
            path=os.path.join(path, "index.md"))
        if not item and is_root:
            item = backend.get_tree_entry(wiki.repo.name, wiki.repo.ref,
                path=os.path.join(path, "index.html"))
        n += 1
    if not item or item["object"]["type"] != "BLOB":
        abort(404)

    head, tail = os.path.split(path) if path else (None, None)
    path = tuple(p for p in (head, tail) if p)

    blob_id = item["object"]["id"]
    blob_name = item["name"]
    cachekey = f"{wiki.repo.name}:{blob_id}"
    html_cachekey = f"man.sr.ht:content:{cachekey}:v{SRHT_MARKDOWN_VERSION}:v4"
    frontmatter_cachekey = f"man.sr.ht:frontmatter:{cachekey}"
    html = get_cache(html_cachekey)
    metrics.mansrht_markdown_cache_access.inc()
    if not html:
        metrics.mansrht_markdown_cache_miss.inc()
        if not "text" in item["object"]:
            # TODO: Return raw blobs?
            abort(404)
        md = item["object"]["text"]

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
        if is_root:
            if blob_name.endswith(".html"):
                html = Markup(md)
            elif blob_name.endswith(".md"):
                html = markdown(md, baselevel=3, sanitize_output=False)
            else:
                abort(404)
        elif blob_name.endswith(".md"):
            html = markdown(md, baselevel=3)
        else:
            abort(404)
        if current_user:
            html = html.replace("{{{srht_username}}}", current_user.username)
        else:
            html = html.replace("{{{srht_username}}}", "USERNAME")
        set_cache(html_cachekey, timedelta(days=7), html)
        set_cache(frontmatter_cachekey,
                timedelta(days=7), json.dumps(frontmatter, default=date_handler))
    else:
        html = Markup(html.decode())
        frontmatter = get_cache(frontmatter_cachekey)
        frontmatter = json.loads(frontmatter.decode())
    title = path[-1].rstrip(".md") if path else "index"
    toc = extract_toc(html)
    if "title" in frontmatter:
        title = frontmatter["title"]
    soup = BeautifulSoup(html, "html.parser")
    firstpara = ""
    if frontmatter.get("toc", True) and len(toc) != 0:
        if soup.contents[0].name == "p":
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
    return content(wiki, path, is_root=True)

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
    return content(wiki, path)
