-- Document rows table for tabular data
DROP TABLE IF EXISTS document_rows CASCADE;

CREATE TABLE document_rows (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    dataset_id UUID REFERENCES document_metadata(id) ON DELETE CASCADE,
    row_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for faster JSONB queries
CREATE INDEX idx_document_rows_dataset ON document_rows(dataset_id);
CREATE INDEX idx_document_rows_data ON document_rows USING GIN (row_data);
