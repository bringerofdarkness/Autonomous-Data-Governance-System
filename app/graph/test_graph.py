from pathlib import Path
from pprint import pprint

from app.core.config import get_settings
from app.graph.workflow import build_adgs_graph


settings = get_settings()


def create_test_file() -> str:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    test_filename = "phase3_test_policy_with_pii.txt"
    test_file_path = upload_dir / test_filename

    test_file_path.write_text(
        """
        ADGS Internal Policy Document

        This policy explains how employees should handle internal data.
        Contact person: John Doe
        Email: john.doe@example.com
        Phone: +1-202-555-0198
        Employee ID: EMP-12345

        All admin accounts must use multi-factor authentication.
        This document is created only for LangGraph Phase 3 testing.
        """,
        encoding="utf-8",
    )

    return test_filename


def main() -> None:
    stored_filename = create_test_file()

    graph = build_adgs_graph()

    initial_state = {
        "document_id": "test-document-002",
        "original_filename": "phase3_test_policy_with_pii.txt",
        "stored_filename": stored_filename,
        "current_step": "STARTED",
    }

    result = graph.invoke(initial_state)

    pprint(result)


if __name__ == "__main__":
    main()