import os
import shutil
import pytest
import json
from factory_agent.rag.ingestion import IngestionEngine
from factory_agent.rag.schemas import DocumentEntry

TEST_DB_PATH = "factory_agent/rag/test_vector_db"
TEST_BM25_PATH = "factory_agent/rag/test_bm25_index.pkl"


def _write_test_register(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    doc_path = sources / "loto.md"
    doc_path.write_text(
        "# LOTO SOP\n\n## Lockout\n\nThe LOTO procedure requires locking out all energy sources before maintenance.\n",
        encoding="utf-8",
    )
    register_path = tmp_path / "source_register.json"
    register_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "doc_id": "SOP-LOTO-001",
                        "title": "LOTO SOP",
                        "file_path": str(doc_path),
                        "source_type": "markdown",
                        "organization": "eMAS Safety",
                        "domain": "safety",
                        "subdomain": "loto",
                        "authority_level": "mandatory_procedure",
                        "use_for": ["loto"],
                        "do_not_use_for": ["live factory status lookup"],
                        "related_entities": ["machine"],
                        "risk_level": "high",
                        "license": "internal",
                        "version": "1.0",
                        "retrieved_date": "2026-05-10",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return register_path

@pytest.fixture
def engine(tmp_path):
    # Cleanup before test
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH, ignore_errors=True)
    if os.path.exists(TEST_BM25_PATH):
        try:
            os.remove(TEST_BM25_PATH)
        except:
            pass
        
    engine = IngestionEngine(db_path=TEST_DB_PATH, bm25_path=TEST_BM25_PATH)
    engine.test_register = str(_write_test_register(tmp_path))
    yield engine
    
    # Cleanup after test
    # Attempt cleanup but don't fail if files are locked
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH, ignore_errors=True)
    if os.path.exists(TEST_BM25_PATH):
        try:
            os.remove(TEST_BM25_PATH)
        except:
            pass

def test_full_ingestion(engine):
    # Requirement I1: Ingest from register
    engine.run_full_ingestion(engine.test_register)
    
    # Requirement I2: Vector DB chunk count
    count = engine.collection.count()
    assert count > 0
    print(f"Total chunks ingested: {count}")
    
    # Requirement I3: BM25 index file exists
    assert os.path.exists(TEST_BM25_PATH)
    
    # Requirement I4 & I9: Metadata and Section Prefixing
    results = engine.collection.get(limit=5)
    for i in range(len(results['ids'])):
        meta = results['metadatas'][i]
        text = results['documents'][i]
        
        # I4: Required metadata fields
        assert "doc_id" in meta
        assert "section_title" in meta
        assert "section_path" in meta
        assert "authority_level" in meta
        assert "risk_level" in meta
        
        # I5: List types
        assert isinstance(json.loads(meta["use_for"]), list)
        assert isinstance(json.loads(meta["do_not_use_for"]), list)
        
        # I9: Section prefixing
        assert text.startswith("[Section:")

def test_reingestion_logic(engine):
    # First ingestion
    engine.run_full_ingestion(engine.test_register)
    initial_count = engine.collection.count()
    
    # Requirement I6: Re-ingest unchanged doc (should skip)
    engine.run_full_ingestion(engine.test_register)
    assert engine.collection.count() == initial_count
    
    # Requirement I7: Re-ingest with changed version
    with open(engine.test_register, 'r') as f:
        data = json.load(f)
        data['documents'][0]['version'] = "2.0"
        
    temp_register = os.path.join(os.path.dirname(engine.test_register), "temp_register.json")
    with open(temp_register, 'w') as f:
        json.dump(data, f)
        
    engine.run_full_ingestion(temp_register)
    # Count should still be same as it replaces
    assert engine.collection.count() == initial_count
    
    # Verify version updated in metadata
    res = engine.collection.get(where={"doc_id": "SOP-LOTO-001"}, limit=1)
    assert res['metadatas'][0]['version'] == "2.0"
    
    os.remove(temp_register)

def test_failed_ingestion_logging(engine):
    # Requirement I8: Missing file doesn't crash and logs error
    bad_doc = DocumentEntry(
        doc_id="MISSING-001",
        title="Missing Doc",
        file_path="non_existent.md",
        source_type="test",
        organization="test",
        domain="test",
        subdomain="test",
        authority_level="test",
        use_for=[],
        do_not_use_for=[],
        related_entities=[],
        risk_level="low",
        license="test",
        version="1.0",
        retrieved_date="2026-05-10"
    )
    
    if os.path.exists("failed_ingestion.log"):
        os.remove("failed_ingestion.log")
        
    success = engine.ingest_document(bad_doc)
    assert success is False
    assert os.path.exists("failed_ingestion.log")
