"""Small PostgreSQL/pgvector store used by the document RAG service."""
import hashlib
import json
import re
import unicodedata
import uuid

from django.db import connection, transaction

TABLE = "ai_document_embedding"
DIMENSIONS = 3072  # text-embedding-3-large (unchanged from the existing configuration)

_VI_ACCENT_SRC = "áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
_VI_ACCENT_DST = "aaaaaaaaaaaaaaaaadeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy"


def _fold_vietnamese(text):
    normalized = unicodedata.normalize("NFKD", str(text or "")).casefold()
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_marks.replace("đ", "d")).strip()


def _vector_literal(values):
    if len(values) != DIMENSIONS:
        raise ValueError(f"Expected {DIMENSIONS}-dimension embedding; received {len(values)}")
    return "[" + ",".join(format(float(value), ".9g") for value in values) + "]"


def _decode_metadata(value):
    return json.loads(value) if isinstance(value, str) else value


def _compile_where_dict(where):
    """Compile metadata filter dict (supporting exact match and $and/$or/$in operators) to SQL."""
    if not where:
        return "TRUE", []
    parts, params = [], []
    for key, value in where.items():
        if key == "$and" and isinstance(value, list):
            sub_parts = []
            for item in value:
                sql, sub_params = _compile_where_dict(item)
                if sql and sql != "TRUE":
                    sub_parts.append(f"({sql})")
                    params.extend(sub_params)
            if sub_parts:
                parts.append(" AND ".join(sub_parts))
        elif key == "$or" and isinstance(value, list):
            sub_parts = []
            for item in value:
                sql, sub_params = _compile_where_dict(item)
                if sql and sql != "TRUE":
                    sub_parts.append(f"({sql})")
                    params.extend(sub_params)
            if sub_parts:
                parts.append("(" + " OR ".join(sub_parts) + ")")
        elif isinstance(value, dict) and "$in" in value:
            candidates = [str(v) for v in (value.get("$in") or []) if v is not None]
            if not candidates:
                parts.append("FALSE")
            else:
                parts.append("metadata ->> %s = ANY(%s)")
                params.extend((key, candidates))
        elif isinstance(value, dict) and "$exists" in value:
            if value["$exists"]:
                parts.append("metadata ? %s")
            else:
                parts.append("NOT (metadata ? %s)")
            params.append(key)
        else:
            parts.append("metadata @> %s::jsonb")
            params.append(json.dumps({key: value}, ensure_ascii=False))
    return " AND ".join(parts) or "TRUE", params


def _where_clause(where):
    if not where:
        return "", []
    sql, params = _compile_where_dict(where)
    if not sql or sql == "TRUE":
        return "", []
    return " AND " + sql, params


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

    def list_filenames(self, allowed_keys=None):
        """Return distinct file_name values scoped to permitted knowledge sources."""
        if allowed_keys is None:
            sql = f"SELECT DISTINCT metadata ->> 'file_name' FROM {TABLE} WHERE metadata ? 'file_name'"
            params = []
        elif allowed_keys:
            sql = (
                f"SELECT DISTINCT metadata ->> 'file_name' FROM {TABLE} "
                f"WHERE metadata ? 'file_name' "
                f"AND (metadata @> %s::jsonb OR metadata ->> 'sql_doc_key' = ANY(%s))"
            )
            params = ['{"source_class":"ai_knowledge_base"}', list(allowed_keys)]
        else:
            sql = (
                f"SELECT DISTINCT metadata ->> 'file_name' FROM {TABLE} "
                f"WHERE metadata ? 'file_name' AND metadata @> %s::jsonb"
            )
            params = ['{"source_class":"ai_knowledge_base"}']
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return sorted({row[0] for row in cursor.fetchall() if row[0]})

    def get(self, where=None, include=None, ids=None):
        clause, params = _where_clause(where)
        if ids:
            clause += " AND "
            clause += "id::text = ANY(%s)"
            params.append([str(item) for item in ids])
        want_documents = include is None or "documents" in include
        select_cols = "id, content_text, metadata" if want_documents else "id, NULL::text AS content_text, metadata"
        query = f"SELECT {select_cols} FROM {TABLE} WHERE TRUE{clause}"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return {
            "ids": [str(row[0]) for row in rows],
            "documents": [row[1] for row in rows] if want_documents else [],
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
    from llama_index.core.schema import MetadataMode

    texts = []
    for document in documents:
        if hasattr(document, "get_content"):
            embed_text = document.get_content(metadata_mode=MetadataMode.EMBED)
        else:
            embed_text = document.text
        base_text = embed_text or document.text
        contextual_prefix = (getattr(document, "metadata", None) or {}).get("contextual_prefix")
        if contextual_prefix and contextual_prefix not in base_text:
            texts.append(f"{contextual_prefix}\n{base_text}")
        else:
            texts.append(base_text)
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


def keyword_search(keywords, limit=12, filters=None):
    """Search chunks by normalized ASCII/Vietnamese keywords across content and file names."""
    clean_terms = []
    seen = set()
    for term in (keywords or []):
        folded = _fold_vietnamese(term)
        if not folded or folded in seen:
            continue
        seen.add(folded)
        clean_terms.append(folded)
        if len(clean_terms) >= 12:
            break
    if not clean_terms:
        return []

    filter_sql, filter_params = _compile_filters(filters) if filters else ("TRUE", [])
    searchable_expr = (
        "translate(lower(coalesce(content_text, '') || ' ' "
        "|| coalesce(metadata ->> 'parent_context', '') || ' ' "
        "|| coalesce(metadata ->> 'contextual_prefix', '') || ' ' "
        "|| coalesce(metadata ->> 'doc_code', '') || ' ' "
        "|| coalesce(metadata ->> 'file_name', '') || ' ' "
        "|| coalesce(metadata ->> 'attachment_name', '')), %s, %s)"
    )
    filename_expr = (
        "translate(lower(coalesce(metadata ->> 'file_name', '') || ' ' "
        "|| coalesce(metadata ->> 'doc_code', '') || ' ' "
        "|| coalesce(metadata ->> 'attachment_name', '')), %s, %s)"
    )

    score_cases = []
    match_predicates = []
    score_params = []
    where_term_params = []
    for term in clean_terms:
        score_cases.append(f"CASE WHEN strpos({searchable_expr}, %s) > 0 THEN 1.0 ELSE 0.0 END")
        score_params.extend((_VI_ACCENT_SRC, _VI_ACCENT_DST, term))
        score_cases.append(f"CASE WHEN strpos({filename_expr}, %s) > 0 THEN 1.5 ELSE 0.0 END")
        score_params.extend((_VI_ACCENT_SRC, _VI_ACCENT_DST, term))
        match_predicates.append(f"strpos({searchable_expr}, %s) > 0")
        where_term_params.extend((_VI_ACCENT_SRC, _VI_ACCENT_DST, term))

    score_expr = " + ".join(score_cases)
    any_match_sql = " OR ".join(match_predicates)
    where_clause = f"({filter_sql}) AND ({any_match_sql})" if filters else any_match_sql
    sql = (
        f"SELECT content_text, metadata, ({score_expr}) AS kw_score "
        f"FROM {TABLE} WHERE {where_clause} "
        f"ORDER BY kw_score DESC, updated_at DESC LIMIT %s"
    )
    params = [*score_params, *filter_params, *where_term_params, max(1, int(limit))]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    from llama_index.core.schema import NodeWithScore, TextNode

    max_possible = max(len(clean_terms) * 2.5, 1.0)
    return [
        NodeWithScore(
            node=TextNode(text=text, metadata=_decode_metadata(metadata)),
            score=min(0.85, 0.18 + 0.67 * (float(kw_score) / max_possible)),
        )
        for text, metadata, kw_score in rows
        if float(kw_score or 0) > 0
    ]
