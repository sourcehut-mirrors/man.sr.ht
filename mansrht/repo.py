from flask import url_for
from srht.api import ensure_webhooks
from srht.config import cfg, get_origin
from srht.graphql import exec_gql
from srht.oauth import current_user
import os

origin = get_origin("man.sr.ht")
git_user = cfg("git.sr.ht::dispatch", "/usr/bin/gitsrht-keys", "git:git").split(":")[0]

class GitsrhtBackend():
    """
    git.sr.ht-based backend for man.sr.ht.
    """

    _origin = get_origin("git.sr.ht")
    _origin_ext = get_origin("git.sr.ht", external=True)

    def __init__(self, owner):
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

    def get_repos(self, cursor=None):
        r = exec_gql("git.sr.ht", """
        query GetRepos($cursor: Cursor) {
            me {
                repositories(cursor: $cursor) {
                    cursor
                    results {
                        id
                        name
                    }
                }
            }
        }
        """, cursor=cursor)
        repos = r["me"]["repositories"]
        return repos["results"], repos["cursor"]

    def get_repo(self, repo_name):
        r = exec_gql("git.sr.ht", """
        query GetRepo($name: String!) {
            me {
                repository(name: $name) {
                    id
                    name
                }
            }
        }
        """, name=repo_name)
        return r["me"]["repository"]

    def create_repo(self, repo_name, repo_visibility):
        # TODO: Convert man.sr.ht visibility type to uppercase
        r = exec_gql("git.sr.ht", """
        mutation CreateRepo($name: String!, $visibility: Visibility!) {
            createRepository(name: $name, visibility: $visibility) {
                id
                name
            }
        }
        """, name=repo_name, visibility=repo_visibility.upper())
        return r["createRepository"]

    def delete_repo(self, repo_name):
        repo = get_repo(self, repo_name)

        exec_gql("git.sr.ht", """
        mutation DeleteRepo($id: Int!) {
            deleteRepository(id: $id) { id }
        }
        """, id=repo["id"])

    def get_repo_url(self, repo_name):
        return os.path.join(self.origin_ext,
                self.owner.canonical_name, repo_name)

    def get_refs(self, repo_name, cursor=None):
        r = exec_gql("git.sr.ht", """
        query GetRefs($name: String!, $cursor: Cursor) {
            me {
                repository(name: $name) {
                    references(cursor: $cursor) {
                        cursor
                        results {
                            name
                        }
                    }
                }
            }
        }
        """, name=repo_name, cursor=cursor)
        refs = r["me"]["repository"]["references"]
        return [
                r for r in refs["results"] if r["name"].startswith("refs/heads/")
        ], refs["cursor"]

    def get_ref_url(self, repo_name, ref):
        return os.path.join(self.origin_ext,
                self.owner.canonical_name, repo_name, ref)

    def get_latest_commit(self, repo_name, ref):
        r = exec_gql("git.sr.ht", """
        query GetLatestCommit($name: String!, $ref: String!) {
            me {
                repository(name: $name) {
                    log(from: $ref) {
                        results {
                            id
                            author {
                                name
                                email
                                time
                            }
                            message
                            tree {
                                id
                            }
                        }
                    }
                }
            }
        }
        """, name=repo_name, ref=ref)
        log = r["me"]["repository"]["log"]["results"]
        if len(log) == 0:
            return None
        return log[0]

    def get_tree_entry(self, repo_name, ref, path=None):
        if not path:
            return { "object": { "type": "TREE" } } # root

        r = exec_gql("git.sr.ht", """
        query GetTree($name: String!, $ref: String!, $path: String!) {
            me {
                repository(name: $name) {
                    path(revspec: $ref, path: $path) {
                        name
                        object {
                            id
                            type

                            ... on TextBlob {
                                text
                            }
                        }
                    }
                }
            }
        }
        """, name=repo_name, ref=ref, path=path)
        return r["me"]["repository"]["path"]

    # TODO: Drop webhooks
    def ensure_repo_postupdate(self, repo):
        url = origin + url_for("webhooks_notify.ref_update", repo_id=repo.id)
        ensure_webhooks(self.owner,
            f"{self.api_user_url}/repos/{repo.name}/webhooks", {
                url: ["repo:post-update"],
            })

    def unensure_repo_postupdate(self, repo):
        url = origin + url_for("webhooks_notify.ref_update", repo_id=repo.id)
        ensure_webhooks(self.owner,
            f"{self.api_user_url}/repos/{repo.name}/webhooks", { url: None })

    def ensure_repo_update(self):
        url = origin + url_for("webhooks_notify.repo_update")
        ensure_webhooks(self.owner,
            f"{self.api_url}/user/webhooks", {
                url: ["repo:update", "repo:delete"],
            })
