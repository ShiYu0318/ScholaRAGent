"""Store 工廠：依設定選擇 SQLite+FAISS 或 Postgres+pgvector 後端。"""
from src import config
from src.store.base import Store

_store = None


def create_store(backend=None, **kwargs) -> Store:
    backend = backend or config.STORE_BACKEND
    if backend == "postgres":
        from src.store.postgres_pgvector import PostgresPgvectorStore
        return PostgresPgvectorStore(**kwargs)
    from src.store.sqlite_faiss import SqliteFaissStore
    return SqliteFaissStore(**kwargs)


def get_store() -> Store:
    """行程級單例；API 層透過此函式取得儲存後端。"""
    global _store
    if _store is None:
        _store = create_store()
    return _store


def set_store(store):
    """注入替身（測試）或替換後端；回傳先前的實例。"""
    global _store
    prev, _store = _store, store
    return prev
