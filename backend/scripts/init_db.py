"""Initialize PostgreSQL tables for save/timeline persistence."""

from app.infrastructure.save.db import init_database


def main() -> None:
    init_database(create_tables=True)
    print("PostgreSQL tables initialized.")


if __name__ == "__main__":
    main()
