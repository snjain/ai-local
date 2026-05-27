"""Execute Python code in a sandboxed subprocess."""
import asyncio
import tempfile
import os


async def execute_python_code(code: str) -> str:
    """Execute Python code and return stdout/stderr.

    Args:
        code: Python code string to execute.

    Returns:
        Output string (stdout + stderr combined).
    """
    # Write code to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        result = ""
        if out:
            result += f"--- stdout ---\n{out}\n"
        if err:
            result += f"--- stderr ---\n{err}\n"
        if not result:
            result = "(no output)"
        return result.strip()
    except asyncio.TimeoutError:
        return "Error: Code execution timed out after 30s"
    except Exception as e:
        return f"Error executing code: {e}"
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
