import requests
from flask import url_for
from srht.api import ensure_webhooks, get_authorization, get_results
from srht.config import cfg, get_origin
from srht.oauth import current_user
import abc
import os

origin = get_origin("man.sr.ht")
git_user = cfg("git.sr.ht::dispatch", "/usr/bin/gitsrht-keys", "git:git").split(":")[0]

def _request_get(url, user):
    r = requests.get(url, headers=get_authorization(user))
    if r.status_code == 404:
        # We treat "resource not found" as a non-error.
        return None
    elif r.status_code != 200:
        raise Exception(r.json())
    return r.json()

def _request_post(url, user, data=None):
    r = requests.post(url, json=data, headers=get_authorization(user))
    if r.status_code != 201:
        raise Exception(r.text)
    return r.json()

def _request_delete(url, user):
    r = requests.delete(url, headers=get_authorization(user))
    if r.status_code != 204:
        raise Exception(r.text)

class RepoBackend(abc.ABC):
    """
    Abstraction for wiki-related API calls to a scm backend.

    Implementations are expected to make requests to the appropriate backend
    in-order for man.sr.ht to access/modify wikis.
    """

    @property
    @abc.abstractmethod
    def origin(self): pass

    @property
    @abc.abstractmethod
    def origin_ext(self): pass

    @property
    @abc.abstractmethod
    def ssh_format(self): pass

    @abc.abstractmethod
    def get_repos(self): pass

    @abc.abstractmethod
    def get_repo(self, repo_name): pass

    @abc.abstractmethod
    def create_repo(self, repo_name): pass

    @abc.abstractmethod
    def delete_repo(self, repo_name): pass

    @abc.abstractmethod
    def get_repo_url(self, repo_name): pass

    @abc.abstractmethod
    def get_refs(self, repo_name): pass

    @abc.abstractmethod
    def get_ref_url(self, repo_name, ref): pass

    @abc.abstractmethod
    def get_latest_commit(self, repo_name, ref): pass

    @abc.abstractmethod
    def get_tree(self, repo_name, ref, path=None): pass

    @abc.abstractmethod
    def get_blob(self, repo_name, blob_id): pass

    @abc.abstractmethod
    def ensure_repo_postupdate(self, repo_name): pass

    @abc.abstractmethod
    def unensure_repo_postupdate(self, repo): pass

    @abc.abstractmethod
    def ensure_repo_update(self): pass

class GitsrhtBackend(RepoBackend):
    """
    git.sr.ht-based backend for man.sr.ht.
    """

    _origin = get_origin("git.sr.ht")
    _origin_ext = get_origin("git.sr.ht", external=True)

    def __init__(self, owner):
        super(GitsrhtBackend, self).__init__()
        self.owner = owner
        self.api_url = f"{self.origin}/api"
        self.api_user_url = f"{self.api_url}/{owner.canonical_name}"

    @property
    def origin(self):
        return self._origin

    @property
    def origin_ext(self):
        return self._origin_ext

    @property
    def ssh_format(self):
        return git_user + "@{origin}:{user}/{repo}"

    def get_repos(self):
        url = f"{self.api_user_url}/repos"
        yield from get_results(url, self.owner)

    def get_repo(self, repo_name):
        url = f"{self.api_user_url}/repos/{repo_name}"
        return _request_get(url, self.owner)

    def create_repo(self, repo_name):
        if current_user == self.owner:
            url = f"{self.origin}/api/repos"
            return _request_post(url, self.owner, data={"name": repo_name})

    def delete_repo(self, repo_name):
        if current_user == self.owner:
            url = f"{self.origin}/api/repos/{repo_name}"
            _request_delete(url, self.owner)

    def get_repo_url(self, repo_name):
        return os.path.join(self.origin_ext,
                self.owner.canonical_name, repo_name)

    def get_refs(self, repo_name):
        url = f"{self.api_user_url}/repos/{repo_name}/refs"
        for ref in get_results(url, self.owner):
            if not ref["name"].startswith("refs/heads/"):
                continue
            yield ref

    def get_ref_url(self, repo_name, ref):
        return os.path.join(self.origin_ext,
                self.owner.canonical_name, repo_name, ref)

    def get_latest_commit(self, repo_name, ref):
        url = f"{self.api_user_url}/repos/{repo_name}/log/{ref}"
        return _request_get(url, self.owner).get("results")[0]

    def get_tree(self, repo_name, ref, path=None):
        url = f"{self.api_user_url}/repos/{repo_name}/tree/{ref}"
        if path:
            url = os.path.join(url, path)
        return _request_get(url, self.owner)

    def get_blob(self, repo_name, blob_id):
        # TODO: Perhaps get_blob() should do all the tree-traversal for us?
        url = f"{self.api_user_url}/blob/{repo_name}/blob/{blob_id}"
        r = requests.get(
            url, headers=get_authorization(self.owner))

        plaintext = r.headers.get("content-type", "").startswith("text/plain")
        if r.status_code != 200 or not plaintext:
            return None
        return r.text

    def ensure_repo_postupdate(self, repo):
        url = origin + url_for("webhooks.notify.ref_update", repo_id=repo.id)
        ensure_webhooks(self.owner,
            f"{self.api_user_url}/repos/{repo.name}/webhooks", {
                url: ["repo:post-update"],
            })

    def unensure_repo_postupdate(self, repo):
        url = origin + url_for("webhooks.notify.ref_update", repo_id=repo.id)
        ensure_webhooks(self.owner,
            f"{self.api_user_url}/repos/{repo.name}/webhooks", { url: None })

    def ensure_repo_update(self):
        url = origin + url_for("webhooks.notify.repo_update")
        ensure_webhooks(self.owner,
            f"{self.api_url}/user/webhooks", {
                url: ["repo:update", "repo:delete"],
            })
