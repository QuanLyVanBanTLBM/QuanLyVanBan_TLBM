"""Store AI document chunks and embeddings in PostgreSQL using pgvector."""
from django.db import migrations


FORWARD_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE ai_document_embedding (
    id UUID PRIMARY KEY,
    source_key VARCHAR(500) UNIQUE NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id BIGINT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(3072) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ai_document_embedding_metadata_idx ON ai_document_embedding USING GIN (metadata);
CREATE INDEX ai_document_embedding_hnsw_idx ON ai_document_embedding
    USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qlvb_readonly') THEN
        GRANT SELECT ON ai_document_embedding TO qlvb_readonly;
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [("documents", "0014_ai_user_scoped_attachments")]
    operations = [migrations.RunSQL(FORWARD_SQL, reverse_sql="DROP TABLE ai_document_embedding;")]
