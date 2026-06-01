import pytest
from pathlib import Path
from app.services.document_extraction_service import extract_document_text

@pytest.fixture
def setup_test_files(monkeypatch):
    tests_dir = Path(__file__).parent
    monkeypatch.setattr("app.services.document_extraction_service.settings.UPLOAD_DIR", str(tests_dir))
    return tests_dir

def test_extract_pdf_insights(setup_test_files):
    pdf_filename = "Comparative Analysis of Ensemble ResNet50 Modalities in Hematological and Dermatological Oncology.pdf" 
    
    if not (setup_test_files / pdf_filename).exists():
        pytest.skip(f"File {pdf_filename} not found.")

    result = extract_document_text(pdf_filename)
    
    print(f"\n--- PDF STATS: {result['metadata'].get('page_count')} pages, {result['metadata'].get('char_count')} chars ---")
    print(f"PREVIEW: {result['text'][:500]}...\n")
    
    assert result["extraction_method"] == "pypdf_text"
    assert len(result["text"]) > 100

def test_extract_docx_insights(setup_test_files):
    docx_filename = "AeroPharm_Clinical_Data_RAG_Test.docx"
    
    if not (setup_test_files / docx_filename).exists():
        pytest.skip(f"File {docx_filename} not found.")

    result = extract_document_text(docx_filename)
    
    print(f"\n--- DOCX STATS: {result['metadata'].get('paragraph_count')} paragraphs, {result['metadata'].get('table_count')} tables ---")
    print(f"PREVIEW: {result['text'][:500]}...\n")
    
    assert result["extraction_method"] == "python_docx_text"
    assert len(result["text"]) > 0

def test_extract_txt_insights(setup_test_files):
    txt_filename = "test_compliance_violation.txt"
    
    if not (setup_test_files / txt_filename).exists():
        pytest.skip(f"File {txt_filename} not found.")

    result = extract_document_text(txt_filename)
    
    print(f"\n--- TXT STATS: {result['metadata'].get('char_count')} chars ---")
    print(f"PREVIEW: {result['text'][:500]}...\n")
    
    # FIX: Changed "plain_text" to "utf8_text"
    assert result["extraction_method"] == "utf8_text"
    assert len(result["text"]) > 0

def test_extract_json_insights(setup_test_files):
    json_filename = "test_nested_metadata.json"
    
    if not (setup_test_files / json_filename).exists():
        pytest.skip(f"File {json_filename} not found.")

    result = extract_document_text(json_filename)
    
    print(f"\n--- JSON STATS: {result['metadata'].get('key_count')} keys, max depth {result['metadata'].get('max_depth')} ---")
    
    assert result["extraction_method"] == "json_text"

def test_extract_csv_insights(setup_test_files):
    csv_filename = "test_messy_table.csv"
    
    if not (setup_test_files / csv_filename).exists():
        pytest.skip(f"File {csv_filename} not found.")

    result = extract_document_text(csv_filename)
    
    print(f"\n--- CSV STATS: {result['metadata'].get('row_count')} rows, {result['metadata'].get('column_count')} columns ---")
    
    assert result["extraction_method"] == "csv_text"