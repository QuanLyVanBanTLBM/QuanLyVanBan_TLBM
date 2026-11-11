"""Small PostgreSQL/pgvector store used by the document RAG service."""
import hashlib
import json
import uuid

from django.db import connection, transaction

TABLE = "ai_document_embedding"
DIMENSIONS = 3072  # text-embedding-3-large (unchanged from the existing configuration)


def _vector_literal(values):
    if len(values) != DIMENSIONS:
        raise ValueError(f"Expected {DIMENSIONS}-dimension embedding; received {len(values)}")
    return "[" + ",".join(format(float(value), ".9g") for value in values) + "]"


def _decode_metadata(value):
    return json.loads(value) if isinstance(value, str) else value


def _where_clause(where):
    if not where:
        return "", []
    parts, params = [], []
    for key, value in where.items():
        parts.append("metadata @> %s::jsonb")
        params.append(json.dumps({key: value}, ensure_ascii=False))
    return " AND " + " AND ".join(parts), params


class PgVectorCollection:
    """Compatibility surface for the handful of collection operations RAG uses."""

    def count(self, where=None):
        clause, params = _where_clause(where)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT count(*) FROM {TABLE} WHERE TRUE{clause}", params)
            return cursor.fetchone()[0]

    def indexed_filenames(self):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT DISTINCT metadata ->> 'file_name' FROM {TABLE}
                    WHERE metadata @> %s::jsonb AND metadata ? 'file_name'""",
                ['{"source_class":"ai_knowledge_base"}'],
            )
            return {row[0] for row in cursor.fetchall() if row[0]}

    def get(self, where=None, include=None, ids=None):
        clause, params = _where_clause(where)
        if ids:
            clause += " AND "
            clause += "id::text = ANY(%s)"
            params.append([str(item) for item in ids])
        query = f"SELECT id, content_text, metadata FROM {TABLE} WHERE TRUE{clause}"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return {
            "ids": [str(row[0]) for row in rows],
            "documents": [row[1] for row in rows],
            "metadatas": [_decode_metadata(row[2]) for row in rows],
        }

    def delete(self, where=None, ids=None):
        clause, params = _where_clause(where)
        if ids:
            clause += " AND "
            clause += "id::text = ANY(%s)"
            params.append([str(item) for item in ids])
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {TABLE} WHERE TRUE{clause}", params)

    def update(self, ids, metadatas):
        with connection.cursor() as cursor:
            for row_id, metadata in zip(ids, metadatas):
                cursor.execute(
                    f"UPDATE {TABLE} SET metadata = %s::jsonb, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    [json.dumps(metadata, ensure_ascii=False), str(row_id)],
                )


def insert_documents(documents, embed_model):
    texts = [document.text for document in documents]
    vectors = embed_model.get_text_embedding_batch(texts, show_progress=True)
    rows = []
    for document, vector in zip(documents, vectors):
        metadata = dict(document.metadata)
        namespace = metadata.get("sql_doc_key") or metadata.get("file_name") or "document"
        chunk_key = metadata.get("chunk_id") or uuid.uuid4().hex
        source_key = f"{namespace}:{chunk_key}:{uuid.uuid4().hex}"
        sql_key = metadata.get("sql_doc_key")
        if sql_key and ":" in sql_key:
            source_type, source_id = sql_key.split(":", 1)
            try:
                source_id = int(source_id)
            except ValueError:
                source_id = 0
        else:
            source_type, source_id = "ai_knowledge_base", 0
        rows.append((
            str(uuid.uuid4()), source_key, source_type, source_id,
            hashlib.sha256(document.text.encode("utf-8")).hexdigest(), document.text,
            _vector_literal(vector), json.dumps(metadata, ensure_ascii=False),
        ))
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.executemany(
            f"""INSERT INTO {TABLE}
                (id, source_key, source_type, source_id, content_hash, content_text, embedding, metadata)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)""",
            rows,
        )
    return [row[0] for row in rows]


def _compile_filters(filters):
    conditions, params = [], []
    for item in filters.filters:
        if hasattr(item, "filters"):
            sql, nested_params = _compile_filters(item)
            conditions.append(f"({sql})")
            params.extend(nested_params)
            continue
        operator = getattr(item.operator, "value", item.operator)
        if str(operator).lower() == "in":
            conditions.append("metadata ->> %s = ANY(%s)")
            params.extend((item.key, list(item.value)))
        else:
            conditions.append("metadata @> %s::jsonb")
            params.append(json.dumps({item.key: item.value}, ensure_ascii=False))
    joiner = " OR " if str(getattr(filters, "condition", "and")).lower().endswith("or") else " AND "
    return joiner.join(conditions) or "TRUE", params


def similarity_search(query, embed_model, limit=6, filters=None):
    vector = _vector_literal(embed_model.get_query_embedding(query))
    filter_sql, filter_params = _compile_filters(filters) if filters else ("TRUE", [])
    clause = f" WHERE {filter_sql}" if filters else ""
    sql = f"""SELECT content_text, metadata,
        1 - (embedding::halfvec({DIMENSIONS}) <=> %s::halfvec({DIMENSIONS})) AS score
        FROM {TABLE}{clause}
        ORDER BY embedding::halfvec({DIMENSIONS}) <=> %s::halfvec({DIMENSIONS}) LIMIT %s"""
    params = [vector, *filter_params, vector, limit]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    from llama_index.core.schema import NodeWithScore, TextNode
    return [
        NodeWithScore(node=TextNode(text=text, metadata=_decode_metadata(metadata)), score=float(score))
        for text, metadata, score in rows
    ]
