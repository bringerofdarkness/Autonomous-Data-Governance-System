from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()

    with PostgresSaver.from_conn_string(
        settings.LANGGRAPH_CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        checkpointer.setup()

    print("LangGraph PostgreSQL checkpoint tables are ready.")


if __name__ == "__main__":
    main()