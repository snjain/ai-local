"""Execute read-only SQL queries via Supabase PostgREST."""
from supabase import Client


async def execute_sql_query(supabase: Client, query: str) -> str:
    """Execute a read-only SQL query via Supabase RPC.

    Args:
        supabase: Supabase client (connected via Kong).
        query: SQL SELECT or WITH statement.

    Returns:
        Query results formatted as text.
    """
    stripped = query.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        return "Error: Only SELECT and WITH queries are allowed."

    try:
        result = supabase.rpc("execute_sql", {"query": query}).execute()

        if result.data:
            rows = result.data
            if not rows:
                return "(no rows returned)"

            # Format as table-like text
            headers = list(rows[0].keys())
            lines = []
            lines.append(" | ".join(headers))
            lines.append("-" * len(lines[0]))
            for row in rows[:100]:
                lines.append(" | ".join(str(v) for v in row.values()))
            if len(rows) > 100:
                lines.append(f"... ({len(rows) - 100} more rows)")
            return "\n".join(lines)
        return "(no rows returned)"
    except Exception as e:
        error_str = str(e)
        if "execute_sql" in error_str and ("Could not find" in error_str or "not found" in error_str.lower()):
            return (
                "Error: The execute_sql RPC function is not available.\n"
                "Run this in Supabase SQL Editor:\n"
                "CREATE OR REPLACE FUNCTION execute_sql(query TEXT)\n"
                "RETURNS TABLE(result JSON) AS $$\n"
                "DECLARE rec RECORD;\n"
                "BEGIN\n"
                "  FOR rec IN EXECUTE query LOOP\n"
                "    result := to_json(rec);\n"
                "    RETURN NEXT;\n"
                "  END LOOP;\n"
                "END;\n"
                "$$ LANGUAGE plpgsql;"
            )
        return f"Database error: {e}"
