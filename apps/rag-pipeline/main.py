"""RAG pipeline entrypoint - watches a directory for file changes."""
import os
import time
import uuid
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path.cwd()
while env_path.name != "ai-local" and env_path.parent != env_path:
    env_path = env_path.parent
load_dotenv(env_path / ".env")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from text_processor import extract_text_from_file
from db_handler import process_file_for_rag


class RAGFileHandler(FileSystemEventHandler):
    def __init__(self, watch_dir: str, config: dict):
        self.watch_dir = Path(watch_dir)
        self.config = config

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self.process_file(event.src_path)

    def process_file(self, file_path: str):
        path = Path(file_path)
        if path.name.startswith("."):
            return

        print(f"Processing: {path}")
        try:
            content = path.read_bytes()
            mime_type = "text/plain"
            if path.suffix == ".pdf":
                mime_type = "application/pdf"
            elif path.suffix == ".csv":
                mime_type = "text/csv"
            elif path.suffix in (".png", ".jpg", ".jpeg", ".gif"):
                mime_type = f"image/{path.suffix.lstrip('.')}"

            text = extract_text_from_file(content, mime_type, path.name, self.config)
            file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())))
            process_file_for_rag(
                file_content=content,
                text=text,
                file_id=file_id,
                file_url=str(path),
                file_title=path.name,
                mime_type=mime_type,
                config=self.config,
            )
            print(f"  ✓ Indexed: {path.name}")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline File Watcher")
    parser.add_argument("--watch", default="../../shared", help="Directory to watch")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")
    args = parser.parse_args()

    watch_dir = Path(args.watch).resolve()
    watch_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "openai_api_key": os.getenv("LLM_API_KEY", ""),
        "embedding_model": os.getenv("EMBEDDING_MODEL_CHOICE", "text-embedding-3-small"),
    }

    handler = RAGFileHandler(str(watch_dir), config)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()

    print(f"RAG Pipeline watching: {watch_dir}")
    print("Drop files into this directory to index them.")

    # Process existing files
    for file_path in watch_dir.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            handler.process_file(str(file_path))

    try:
        while True:
            time.sleep(args.interval)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
