from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row

from app.core.config import get_settings


settings = get_settings()


def get_postgres_checkpointer() -> PostgresSaver:
    connection = Connection.connect(
        settings.LANGGRAPH_CHECKPOINT_DATABASE_URL,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )

    return PostgresSaver(connection)