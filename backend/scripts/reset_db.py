import os
import sys


def main() -> None:
    # Ensure we can import app.py from backend package root
    backend_root = os.path.dirname(os.path.dirname(__file__))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    # Delete existing SQLite file if present
    db_path = os.path.join(backend_root, "interview_prep.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Deleted existing DB: {db_path}")
        except OSError as exc:
            print(f"Failed to delete {db_path}: {exc}")
            sys.exit(1)

    # Import and run init_db from app.py (development path only)
    try:
        from app import init_db  # type: ignore
    except Exception as exc:
        print(f"Failed to import init_db from app.py: {exc}")
        sys.exit(1)

    try:
        init_db()
        print("Database schema recreated successfully.")
    except Exception as exc:
        print(f"Failed to initialize database: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()


