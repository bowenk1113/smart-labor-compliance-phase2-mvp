from app.rag.context import create_query_context
from app.rag.retrieval import _search
from app.rag.store import KnowledgeDocument, RetrievalHit


def test_search_falls_back_to_local_faq_when_milvus_returns_no_hits(monkeypatch):
    context = create_query_context(
        query="居民医保断缴后还能报销吗？",
        scenario_id="social_security",
        session_id="test-session",
        history=[],
        user_role="employee",
        province="陕西省",
        city="西安市",
    )

    local_hit = RetrievalHit(
        document=KnowledgeDocument(
            content="问题：居民医保断缴后还能报销吗？\n答案：等待期内通常不能按居民医保待遇报销。",
            metadata={"id": "SS005", "title": "居民医保断缴后还能报销吗？"},
        ),
        score=0.91,
    )

    monkeypatch.setattr("app.rag.retrieval.vector_backend", lambda: "milvus")
    monkeypatch.setattr("app.rag.milvus_store.search_milvus", lambda *args, **kwargs: [])
    monkeypatch.setattr("app.rag.retrieval.search_local_faq", lambda *args, **kwargs: ([local_hit], 1.0))

    hits, elapsed_ms = _search(
        context,
        ["居民医保断缴后还能报销吗？"],
        source_type="faq",
        top_k=5,
    )

    assert elapsed_ms >= 0
    assert [hit.document.metadata["id"] for hit in hits] == ["SS005"]
