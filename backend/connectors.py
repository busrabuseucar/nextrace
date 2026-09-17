"""Jira ve GitLab verisini NexTrace izlenebilirlik grafiğine dönüştürür.

Bağlayıcılar yalnızca okuma işlemi yapar. Kimlik bilgileri çağrı anında ortam
değişkenlerinden alınır; proje veritabanına veya API yanıtlarına yazılmaz.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from engine import Edge, Node, TraceGraph


DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_PAGES = 10
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
JIRA_FIELDS = ["summary", "issuetype", "assignee", "priority", "issuelinks", "status"]
JIRA_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{1,19}-\d+\b")


class ConnectorError(RuntimeError):
    """Dış kaynak bağlantısı güvenli veya geçerli biçimde tamamlanamadı."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class JsonResponse:
    payload: Any
    headers: dict[str, str]


class HttpJsonClient:
    """Kısıtlı, JSON odaklı ve SSRF korumalı HTTP istemcisi."""

    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, str],
        *,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        opener: Any | None = None,
        resolver: Callable[..., list] | None = None,
        allow_private: bool | None = None,
        allow_insecure: bool | None = None,
    ):
        self.base_url = self._normalize_base_url(base_url)
        self.default_headers = dict(default_headers)
        self.timeout = max(1, min(int(timeout), 60))
        self.opener = opener or build_opener(_NoRedirectHandler())
        self.resolver = resolver or socket.getaddrinfo
        self.allow_private = (
            os.environ.get("NEXTRACE_ALLOW_PRIVATE_CONNECTORS") == "1"
            if allow_private is None
            else allow_private
        )
        self.allow_insecure = (
            os.environ.get("NEXTRACE_ALLOW_INSECURE_CONNECTORS") == "1"
            if allow_insecure is None
            else allow_insecure
        )

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = str(base_url).strip().rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ConnectorError("Bağlayıcı adresi http veya https biçiminde olmalıdır.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ConnectorError("Bağlayıcı adresinde kullanıcı, parola, sorgu veya parça bulunamaz.")
        if parsed.path not in {"", "/"}:
            raise ConnectorError("Bağlayıcı temel adresi bir yol içermemelidir.")
        return normalized

    def _validate_destination(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "https" and not self.allow_insecure:
            raise ConnectorError("Bağlayıcılar için HTTPS zorunludur.")
        if self.allow_private:
            return
        try:
            default_port = 443 if parsed.scheme == "https" else 80
            records = self.resolver(
                parsed.hostname, parsed.port or default_port, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise ConnectorError("Bağlayıcı sunucu adresi çözümlenemedi.") from exc
        if not records:
            raise ConnectorError("Bağlayıcı sunucu adresi çözümlenemedi.")
        for record in records:
            address = ipaddress.ip_address(record[4][0])
            if not address.is_global:
                raise ConnectorError(
                    "Özel veya yerel ağ adresleri varsayılan olarak bağlayıcılara kapalıdır."
                )

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> JsonResponse:
        if not path.startswith("/") or path.startswith("//"):
            raise ConnectorError("Geçersiz bağlayıcı API yolu.")
        self._validate_destination()
        query = urlencode(params or {}, doseq=True)
        url = f"{self.base_url}{path}{'?' + query if query else ''}"
        headers = {"Accept": "application/json", **self.default_headers}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                final = urlsplit(response.geturl())
                expected = urlsplit(self.base_url)
                if (final.scheme, final.hostname, final.port) != (
                    expected.scheme,
                    expected.hostname,
                    expected.port,
                ):
                    raise ConnectorError("Bağlayıcı isteği farklı bir sunucuya yönlendirildi.")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ConnectorError("Bağlayıcı yanıtı izin verilen boyutu aşıyor.")
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except HTTPError as exc:
            raise ConnectorError(f"Bağlayıcı API isteği HTTP {exc.code} ile reddedildi.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ConnectorError("Bağlayıcı API sunucusuna ulaşılamadı.") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError("Bağlayıcı geçerli bir JSON yanıtı vermedi.") from exc
        return JsonResponse(payload=payload, headers=response_headers)


def _bounded_env_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


class JiraConnector:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        *,
        client: HttpJsonClient | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ):
        if not email.strip() or not api_token:
            raise ConnectorError("Jira e-posta adresi ve API anahtarı zorunludur.")
        credentials = base64.b64encode(f"{email}:{api_token}".encode("utf-8")).decode("ascii")
        self.client = client or HttpJsonClient(
            base_url,
            {"Authorization": f"Basic {credentials}"},
            timeout=_bounded_env_integer(
                "NEXTRACE_CONNECTOR_TIMEOUT", DEFAULT_TIMEOUT_SECONDS, 1, 60
            ),
        )
        self.max_pages = max(1, min(int(max_pages), 100))

    @classmethod
    def from_env(cls) -> "JiraConnector":
        values = {
            "base_url": os.environ.get("NEXTRACE_JIRA_BASE_URL", ""),
            "email": os.environ.get("NEXTRACE_JIRA_EMAIL", ""),
            "api_token": os.environ.get("NEXTRACE_JIRA_API_TOKEN", ""),
        }
        if not all(values.values()):
            raise ConnectorError("Jira bağlayıcısı ortam değişkenleriyle yapılandırılmamış.")
        return cls(
            **values,
            max_pages=_bounded_env_integer(
                "NEXTRACE_CONNECTOR_MAX_PAGES", DEFAULT_MAX_PAGES, 1, 100
            ),
        )

    def list_issues(self, project_key: str) -> list[dict]:
        issues: list[dict] = []
        next_page_token: str | None = None
        for _ in range(self.max_pages):
            request_body: dict[str, Any] = {
                "jql": f'project = "{project_key}" ORDER BY updated ASC',
                "fields": JIRA_FIELDS,
                "maxResults": 100,
            }
            if next_page_token:
                request_body["nextPageToken"] = next_page_token
            response = self.client.request_json(
                "/rest/api/3/search/jql", method="POST", body=request_body
            )
            if not isinstance(response.payload, dict) or not isinstance(
                response.payload.get("issues"), list
            ):
                raise ConnectorError("Jira arama yanıtının biçimi beklenenden farklı.")
            issues.extend(item for item in response.payload["issues"] if isinstance(item, dict))
            if response.payload.get("isLast") is True:
                return issues
            next_page_token = response.payload.get("nextPageToken")
            if not isinstance(next_page_token, str) or not next_page_token:
                return issues
        raise ConnectorError("Jira veri sınırı aşıldı; sorguyu daraltın veya sayfa sınırını artırın.")


class GitLabConnector:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        *,
        client: HttpJsonClient | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ):
        if not api_token:
            raise ConnectorError("GitLab erişim anahtarı zorunludur.")
        self.client = client or HttpJsonClient(
            base_url,
            {"PRIVATE-TOKEN": api_token},
            timeout=_bounded_env_integer(
                "NEXTRACE_CONNECTOR_TIMEOUT", DEFAULT_TIMEOUT_SECONDS, 1, 60
            ),
        )
        self.max_pages = max(1, min(int(max_pages), 100))

    @classmethod
    def from_env(cls) -> "GitLabConnector":
        base_url = os.environ.get("NEXTRACE_GITLAB_BASE_URL", "")
        api_token = os.environ.get("NEXTRACE_GITLAB_TOKEN", "")
        if not base_url or not api_token:
            raise ConnectorError("GitLab bağlayıcısı ortam değişkenleriyle yapılandırılmamış.")
        return cls(
            base_url,
            api_token,
            max_pages=_bounded_env_integer(
                "NEXTRACE_CONNECTOR_MAX_PAGES", DEFAULT_MAX_PAGES, 1, 100
            ),
        )

    def list_commits(self, project: str) -> list[dict]:
        commits: list[dict] = []
        page = 1
        for _ in range(self.max_pages):
            response = self.client.request_json(
                f"/api/v4/projects/{quote(project, safe='')}/repository/commits",
                params={"page": page, "per_page": 100},
            )
            if not isinstance(response.payload, list):
                raise ConnectorError("GitLab commit yanıtının biçimi beklenenden farklı.")
            commits.extend(item for item in response.payload if isinstance(item, dict))
            next_page = response.headers.get("x-next-page", "").strip()
            if next_page:
                try:
                    page = int(next_page)
                except ValueError as exc:
                    raise ConnectorError("GitLab sayfalama başlığı geçersiz.") from exc
                continue
            if len(response.payload) < 100:
                return commits
            page += 1
        raise ConnectorError("GitLab veri sınırı aşıldı; sayfa sınırını artırın.")


def connector_status() -> dict[str, dict[str, Any]]:
    """Kimlik bilgilerini açığa çıkarmadan bağlayıcı yapılandırmasını özetler."""

    def public_origin(value: str) -> str | None:
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "geçersiz adres"
        try:
            port = f":{parsed.port}" if parsed.port else ""
        except ValueError:
            return "geçersiz adres"
        return f"{parsed.scheme}://{parsed.hostname}{port}"

    jira_values = [
        os.environ.get("NEXTRACE_JIRA_BASE_URL", ""),
        os.environ.get("NEXTRACE_JIRA_EMAIL", ""),
        os.environ.get("NEXTRACE_JIRA_API_TOKEN", ""),
    ]
    gitlab_values = [
        os.environ.get("NEXTRACE_GITLAB_BASE_URL", ""),
        os.environ.get("NEXTRACE_GITLAB_TOKEN", ""),
    ]
    return {
        "jira": {
            "configured": all(jira_values),
            "base_url": public_origin(jira_values[0]),
            "mode": "salt okunur issue araması",
        },
        "gitlab": {
            "configured": all(gitlab_values),
            "base_url": public_origin(gitlab_values[0]),
            "mode": "salt okunur commit listesi",
        },
    }


def _clean(value: Any, maximum: int = 240, fallback: str = "—") -> str:
    text = " ".join(str(value or "").split())
    return text[:maximum] or fallback


def _jira_type(issue_type: str) -> str:
    normalized = issue_type.casefold()
    if any(term in normalized for term in ("requirement", "gereksinim", "story", "epic")):
        return "Gereksinim"
    if any(term in normalized for term in ("bug", "hata", "defect")):
        return "Hata"
    if "test" in normalized:
        return "Test"
    return "İş Öğesi"


def _criticality(priority: str) -> int:
    normalized = priority.casefold()
    if any(term in normalized for term in ("highest", "blocker", "critical", "kritik")):
        return 10
    if any(term in normalized for term in ("high", "yüksek", "major")):
        return 7
    if any(term in normalized for term in ("medium", "orta", "normal")):
        return 4
    if any(term in normalized for term in ("low", "düşük", "minor")):
        return 1
    return 0


def build_trace_graph(
    jira_issues: list[dict] | None = None,
    gitlab_commits: list[dict] | None = None,
    gitlab_project: str = "",
) -> tuple[TraceGraph, dict[str, int]]:
    """Kaynak kayıtlarını ortak düğüm ve ilişki modeline dönüştürür."""

    jira_issues = jira_issues or []
    gitlab_commits = gitlab_commits or []
    nodes: list[Node] = []
    edges: list[Edge] = []
    issue_keys: set[str] = set()

    for issue in jira_issues:
        key = _clean(issue.get("key"), 64, "")
        if not key or key in issue_keys:
            continue
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        issue_type = fields.get("issuetype") if isinstance(fields.get("issuetype"), dict) else {}
        assignee = fields.get("assignee") if isinstance(fields.get("assignee"), dict) else {}
        priority = fields.get("priority") if isinstance(fields.get("priority"), dict) else {}
        nodes.append(
            Node(
                id=key,
                label=_clean(fields.get("summary"), 240, key),
                type=_jira_type(_clean(issue_type.get("name"), 80, "İş Öğesi")),
                owner=_clean(assignee.get("displayName"), 120, "Atanmamış"),
                criticality=_criticality(_clean(priority.get("name"), 80, "")),
            )
        )
        issue_keys.add(key)

    edge_keys: set[tuple[str, str, str]] = set()
    for issue in jira_issues:
        source = _clean(issue.get("key"), 64, "")
        if source not in issue_keys:
            continue
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        links = fields.get("issuelinks") if isinstance(fields.get("issuelinks"), list) else []
        for link in links:
            if not isinstance(link, dict):
                continue
            link_type = link.get("type") if isinstance(link.get("type"), dict) else {}
            outward = link.get("outwardIssue")
            inward = link.get("inwardIssue")
            if isinstance(outward, dict):
                target = _clean(outward.get("key"), 64, "")
                relation = _clean(link_type.get("outward"), 100, "ilişkilidir")
                pair = (source, target, relation)
            elif isinstance(inward, dict):
                origin = _clean(inward.get("key"), 64, "")
                relation = _clean(link_type.get("outward"), 100, "ilişkilidir")
                pair = (origin, source, relation)
            else:
                continue
            if pair[0] in issue_keys and pair[1] in issue_keys and pair not in edge_keys:
                edge_keys.add(pair)
                edges.append(
                    Edge(
                        source=pair[0],
                        target=pair[1],
                        relation=pair[2],
                        reason=f"Jira issue bağlantısı: {pair[2]}.",
                    )
                )

    repository_id = ""
    if gitlab_commits:
        digest = hashlib.sha256(gitlab_project.encode("utf-8")).hexdigest()[:10].upper()
        repository_id = f"GL-REPO-{digest}"
        nodes.append(
            Node(
                id=repository_id,
                label=f"GitLab: {_clean(gitlab_project, 180, 'depo')}",
                type="Kod Deposu",
                owner="Yazılım Ekibi",
                criticality=3,
            )
        )

    seen_commit_ids: set[str] = set()
    for commit in gitlab_commits:
        sha = _clean(commit.get("id"), 64, "")
        if not sha:
            continue
        commit_id = f"GL-COMMIT-{sha[:12].upper()}"
        if commit_id in seen_commit_ids:
            continue
        seen_commit_ids.add(commit_id)
        message = _clean(commit.get("message") or commit.get("title"), 600, "")
        title = _clean(commit.get("title") or message.splitlines()[0], 240, sha[:12])
        nodes.append(
            Node(
                id=commit_id,
                label=title,
                type="Commit",
                owner=_clean(commit.get("author_name"), 120, "Bilinmeyen geliştirici"),
                criticality=2,
            )
        )
        if repository_id:
            edges.append(
                Edge(
                    source=repository_id,
                    target=commit_id,
                    relation="içerir",
                    reason="Commit, GitLab depo geçmişinden salt okunur olarak alındı.",
                )
            )
        for jira_key in sorted(set(JIRA_KEY_PATTERN.findall(message.upper()))):
            if jira_key in issue_keys:
                edges.append(
                    Edge(
                        source=jira_key,
                        target=commit_id,
                        relation="uygulanır",
                        reason=f"Commit mesajı {jira_key} Jira anahtarını içeriyor.",
                    )
                )

    if not nodes:
        raise ConnectorError("Kaynak sistemlerde grafiğe dönüştürülebilecek kayıt bulunamadı.")
    graph = TraceGraph(nodes, edges)
    return graph, {
        "jira_issue_count": len(issue_keys),
        "gitlab_commit_count": len(seen_commit_ids),
        "node_count": len(graph.nodes),
        "edge_count": sum(len(items) for items in graph.adjacency.values()),
    }
