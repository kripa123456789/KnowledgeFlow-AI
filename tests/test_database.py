from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database.models import Chunk, Document
from backend.main import app


def test_document_and_chunks_inserted(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        document = Document(filename="sample.txt", file_type="txt", pages=1, characters=10, chunk_count=2)
        session.add(document)
        session.flush()
        session.add_all(
            [
                Chunk(document_id=document.id, chunk_id=1, text="one", character_count=3, start_offset=0, end_offset=3),
                Chunk(document_id=document.id, chunk_id=2, text="two", character_count=3, start_offset=3, end_offset=6),
            ]
        )
        session.commit()

        stored_document = session.query(Document).filter(Document.filename == "sample.txt").one()
        stored_chunks = session.query(Chunk).filter(Chunk.document_id == stored_document.id).all()

    assert stored_document.filename == "sample.txt"
    assert len(stored_chunks) == 2
    assert stored_document.chunk_count == 2
