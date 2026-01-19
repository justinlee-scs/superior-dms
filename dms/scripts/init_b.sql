CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    doc_class TEXT NOT NULL DEFAULT 'unknown',
    content BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_class ON documents(doc_class);
