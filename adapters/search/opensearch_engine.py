from __future__ import annotations

try:
    from opensearchpy import OpenSearch
except Exception:  # pragma: no cover
    OpenSearch = None  # type: ignore


class OpenSearchEngine:
    def __init__(self, hosts: list[str] | None = None):
        if hosts is None:
            hosts = ["http://localhost:9200"]
        assert OpenSearch is not None, "opensearch-py not installed"
        self.client = OpenSearch(hosts=hosts)

    def index(self, index: str, doc_id: str, document: dict):
        return self.client.index(index=index, id=doc_id, body=document)
