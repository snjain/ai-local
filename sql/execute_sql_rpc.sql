-- RPC function for executing read-only SQL queries
-- This allows the agent to query document data safely

CREATE OR REPLACE FUNCTION execute_custom_sql(sql_query TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    write_ops TEXT[] := ARRAY['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE'];
    upper_query TEXT;
    op TEXT;
BEGIN
    -- Convert to uppercase for checking
    upper_query := UPPER(sql_query);

    -- Check for write operations
    FOREACH op IN ARRAY write_ops
    LOOP
        IF upper_query LIKE '%' || op || '%' THEN
            RETURN jsonb_build_object('error', 'Write operations are not allowed: ' || op);
        END IF;
    END LOOP;

    -- Execute the query and return results as JSON
    EXECUTE 'SELECT jsonb_agg(row_to_json(t)) FROM (' || sql_query || ') t' INTO result;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$;
