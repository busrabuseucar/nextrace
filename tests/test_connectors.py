import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from connectors import (  # noqa: E402
    ConnectorError,
    GitLabConnector,
    HttpJsonClient,
    JiraConnector,
    JsonResponse,
    build_trace_graph,
    connector_status,
)


class FakeJsonClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request_json(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self.responses.pop(0)


class ConnectorTests(unittest.TestCase):
    def test_jira_uses_enhanced_search_and_next_page_token(self):
        client = FakeJsonClient(
            [
                JsonResponse(
                    {"issues": [{"key": "AQ-1"}], "nextPageToken": "next-1"}, {}
                ),
                JsonResponse({"issues": [{"key": "AQ-2"}], "isLast": True}, {}),
            ]
        )
        connector = JiraConnector(
            "https://example.atlassian.net", "user@example.com", "secret", client=client
        )

        issues = connector.list_issues("AQ")

        self.assertEqual([item["key"] for item in issues], ["AQ-1", "AQ-2"])
        self.assertEqual(client.calls[0][0], "/rest/api/3/search/jql")
        self.assertEqual(client.calls[0][1]["method"], "POST")
        self.assertNotIn("nextPageToken", client.calls[0][1]["body"])
        self.assertEqual(client.calls[1][1]["body"]["nextPageToken"], "next-1")

    def test_gitlab_encodes_project_path_and_follows_pagination_header(self):
        first_page = [
            {"id": f"{index:040x}", "title": f"Commit {index}"}
            for index in range(100)
        ]
        client = FakeJsonClient(
            [
                JsonResponse(first_page, {"x-next-page": "2"}),
                JsonResponse([{"id": "f" * 40, "title": "Son commit"}], {}),
            ]
        )
        connector = GitLabConnector(
            "https://gitlab.example.com", "secret", client=client, max_pages=3
        )

        commits = connector.list_commits("uçuş/yazılım")

        self.assertEqual(len(commits), 101)
        self.assertIn("u%C3%A7u%C5%9F%2Fyaz%C4%B1l%C4%B1m", client.calls[0][0])
        self.assertEqual(client.calls[1][1]["params"]["page"], 2)

    def test_source_records_become_explainable_trace_graph(self):
        issues = [
            {
                "key": "AQ-1",
                "fields": {
                    "summary": "Gecikme gereksinimi",
                    "issuetype": {"name": "Requirement"},
                    "assignee": {"displayName": "Sistem Ekibi"},
                    "priority": {"name": "Highest"},
                    "issuelinks": [
                        {
                            "type": {"outward": "blocks"},
                            "outwardIssue": {"key": "AQ-2"},
                        }
                    ],
                },
            },
            {
                "key": "AQ-2",
                "fields": {
                    "summary": "Doğrulama görevi",
                    "issuetype": {"name": "Test"},
                    "assignee": None,
                    "priority": {"name": "Medium"},
                    "issuelinks": [],
                },
            },
        ]
        commits = [
            {
                "id": "a" * 40,
                "title": "AQ-1 eşiğini uygula",
                "message": "AQ-1 eşiğini uygula",
                "author_name": "Yazılım Ekibi",
            },
            {
                "id": "b" * 40,
                "title": "Bakım",
                "message": "Bağımsız bakım",
                "author_name": "Yazılım Ekibi",
            },
        ]

        graph, counts = build_trace_graph(issues, commits, "aquila/flight")
        result = graph.analyze("AQ-1")

        self.assertEqual(counts["node_count"], 5)
        self.assertEqual(counts["edge_count"], 4)
        self.assertEqual(counts["jira_issue_count"], 2)
        self.assertEqual(counts["gitlab_commit_count"], 2)
        impacted = {item["id"] for item in result["items"]}
        self.assertIn("AQ-2", impacted)
        self.assertIn("GL-COMMIT-AAAAAAAAAAAA", impacted)
        commit_item = next(
            item for item in result["items"] if item["id"].startswith("GL-COMMIT-")
        )
        self.assertIn("Commit mesajı AQ-1", commit_item["reason"])

    def test_status_never_exposes_credentials(self):
        environment = {
            "NEXTRACE_JIRA_BASE_URL": "https://example.atlassian.net",
            "NEXTRACE_JIRA_EMAIL": "person@example.com",
            "NEXTRACE_JIRA_API_TOKEN": "jira-super-secret",
            "NEXTRACE_GITLAB_BASE_URL": "https://gitlab.example.com",
            "NEXTRACE_GITLAB_TOKEN": "gitlab-super-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            serialized = json.dumps(connector_status())
        self.assertNotIn("jira-super-secret", serialized)
        self.assertNotIn("gitlab-super-secret", serialized)
        self.assertNotIn("person@example.com", serialized)
        self.assertIn("example.atlassian.net", serialized)

    def test_http_client_blocks_private_network_by_default(self):
        resolver = lambda *args, **kwargs: [  # noqa: E731
            (2, 1, 6, "", ("127.0.0.1", 443))
        ]
        client = HttpJsonClient(
            "https://jira.internal.example",
            {},
            resolver=resolver,
        )
        with self.assertRaisesRegex(ConnectorError, "Özel veya yerel"):
            client.request_json("/api")

    def test_http_client_requires_https_by_default(self):
        client = HttpJsonClient(
            "http://example.com",
            {},
            resolver=lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 80))],
        )
        with self.assertRaisesRegex(ConnectorError, "HTTPS"):
            client.request_json("/api")


if __name__ == "__main__":
    unittest.main()
