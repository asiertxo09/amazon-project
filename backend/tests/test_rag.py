from backend.rag import get_store


def test_store_builds_passages_from_both_sources():
    store = get_store()
    docs = {p["doc"] for p in store._passages}
    assert "Service_description.pptx" in docs
    assert "PL_Industry_Challenge.xlsx" in docs


def test_search_retrieves_weight_limit_passage_for_dimension_query():
    store = get_store()
    results = store.search("maximum weight and dimensions allowed", k=3)
    assert any("15 Kg" in r["text"] or "80x80x60" in r["text"] for r in results)


def test_search_retrieves_guardrail_passage_for_margin_query():
    store = get_store()
    results = store.search("minimum contribution margin guardrail", k=3)
    assert any("contribution margin" in r["text"] for r in results)
