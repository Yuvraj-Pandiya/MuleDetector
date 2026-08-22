"""
backend/tests/test_universal_schema_ingestion.py
=================================================
Comprehensive Unit & Integration Test Suite for Universal CSV Ingestion & Schema Normalizer.

Test Cases Covered:
  1. Canonical CSV auto-detection & mapping (100% confidence).
  2. PaySim CSV auto-detection & step timestamp mode tracking.
  3. Bank-Style Custom CSV with alternate headers ('From_Acct', 'To_Acct', 'Txn_Value', 'Txn_Date').
  4. Header normalization (capitalization, spaces, hyphens, underscores).
  5. Semantic Disambiguation (column 'value' with text vs numeric amounts).
  6. Strict Invalid Amount Detection (No silent 0.0 coercion).
  7. Labeled vs Unlabeled Dataset capability flags (can_train vs can_predict).
  8. Preview API (/upload-dataset/preview) & Confirm API (/upload-dataset/confirm).
  9. Download Canonical Template API (/upload-dataset/template).
"""

import io
import pathlib
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.schema import (
    profile_csv,
    map_columns,
    validate_normalized_dataframe,
    normalize_dataset,
    CANONICAL_FIELDS,
)

client = TestClient(app)
_DATA_DIR = pathlib.Path(__file__).parent.parent / "app" / "data"


@pytest.fixture
def tmp_csv_factory(tmp_path):
    """Fixture to create temporary CSV files for testing."""
    def _create(filename: str, csv_text: str):
        filepath = tmp_path / filename
        filepath.write_text(csv_text.strip(), encoding="utf-8")
        return filepath
    return _create


def test_canonical_csv_profiling_and_mapping(tmp_csv_factory):
    csv_text = """transaction_id,sender_account_id,receiver_account_id,amount,timestamp,transaction_type,is_mule_pattern
TXN_001,ACC-101,ACC-201,15000.50,2026-08-23T10:00:00Z,TRANSFER,1
TXN_002,ACC-102,ACC-202,28000.00,2026-08-23T10:15:00Z,TRANSFER,0
"""
    file_path = tmp_csv_factory("canonical.csv", csv_text)
    prof = profile_csv(file_path)
    map_res = map_columns(prof["column_profiles"])

    assert map_res.status == "auto_ready"
    assert len(map_res.missing_required) == 0
    assert map_res.can_predict is True
    assert map_res.can_train is True
    assert map_res.mapped_dict["sender_account_id"] == "sender_account_id"
    assert map_res.mapped_dict["amount"] == "amount"


def test_paysim_csv_profiling_and_mapping(tmp_csv_factory):
    csv_text = """step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud
1,TRANSFER,9839.64,C1231006815,9839.64,0.0,M1979787155,0.0,0.0,1
2,CASH_OUT,21182.00,C1305486145,21182.00,0.0,C2053011500,0.0,0.0,0
"""
    file_path = tmp_csv_factory("paysim.csv", csv_text)
    prof = profile_csv(file_path)
    map_res = map_columns(prof["column_profiles"])

    assert len(map_res.missing_required) == 0
    assert map_res.mapped_dict["nameOrig"] == "sender_account_id"
    assert map_res.mapped_dict["nameDest"] == "receiver_account_id"
    assert map_res.mapped_dict["amount"] == "amount"
    assert map_res.mapped_dict["step"] == "timestamp"
    assert map_res.mapped_dict["isFraud"] == "is_mule_pattern"


def test_bank_custom_csv_mapping(tmp_csv_factory):
    csv_text = """Txn Ref,From Acct ID,To Account No,Txn Value,Created Date Time,Mode
REF-9901,DEBIT-1001,CREDIT-2002,45000.00,2026-08-23 12:00:00,NEFT
REF-9902,DEBIT-1002,CREDIT-2003,12000.00,2026-08-23 12:05:00,UPI
"""
    file_path = tmp_csv_factory("bank_custom.csv", csv_text)
    prof = profile_csv(file_path)
    map_res = map_columns(prof["column_profiles"])

    assert len(map_res.missing_required) == 0
    assert map_res.mapped_dict["From Acct ID"] == "sender_account_id"
    assert map_res.mapped_dict["To Account No"] == "receiver_account_id"
    assert map_res.mapped_dict["Txn Value"] == "amount"
    assert map_res.mapped_dict["Created Date Time"] == "timestamp"
    assert map_res.mapped_dict["Txn Ref"] == "transaction_id"


def test_value_pattern_semantic_disambiguation(tmp_csv_factory):
    # Column 'value' with numeric amounts vs column 'value' with channel text strings
    numeric_value_csv = """sender_id,receiver_id,value,timestamp
S1,R1,5000.00,2026-08-23T10:00:00
"""
    text_value_csv = """sender_id,receiver_id,amount,value,timestamp
S1,R1,5000.00,UPI_PAYMENT,2026-08-23T10:00:00
"""
    num_path = tmp_csv_factory("num_val.csv", numeric_value_csv)
    text_path = tmp_csv_factory("text_val.csv", text_value_csv)

    prof_num = profile_csv(num_path)
    map_num = map_columns(prof_num["column_profiles"])
    assert map_num.mapped_dict["value"] == "amount"

    prof_text = profile_csv(text_path)
    map_text = map_columns(prof_text["column_profiles"])
    assert map_text.mapped_dict["value"] == "transaction_type"
    assert map_text.mapped_dict["amount"] == "amount"


def test_strict_invalid_amount_detection(tmp_csv_factory):
    csv_text = """transaction_id,sender_account_id,receiver_account_id,amount,timestamp
TXN_1,A1,B1,1000.00,2026-08-23T10:00:00
TXN_2,A2,B2,INVALID_ABC,2026-08-23T10:00:00
TXN_3,A3,B3,-50.00,2026-08-23T10:00:00
"""
    file_path = tmp_csv_factory("invalid_amounts.csv", csv_text)
    df = pd.read_csv(file_path)
    val_res = validate_normalized_dataframe(df)

    assert val_res["invalid_amount_count"] == 2
    assert 1 in val_res["invalid_amount_row_indices"]
    assert 2 in val_res["invalid_amount_row_indices"]


def test_unlabeled_prediction_dataset(tmp_csv_factory):
    csv_text = """transaction_id,sender_account_id,receiver_account_id,amount,timestamp
TXN_1,A1,B1,1000.00,2026-08-23T10:00:00
"""
    file_path = tmp_csv_factory("unlabeled.csv", csv_text)
    prof = profile_csv(file_path)
    map_res = map_columns(prof["column_profiles"])

    assert map_res.can_predict is True
    assert map_res.can_train is False


def test_api_download_template():
    response = client.get("/upload-dataset/template")
    assert response.status_code == 200
    assert "transaction_id,sender_account_id,receiver_account_id,amount,timestamp" in response.text


def test_api_preview_and_confirm_flow(tmp_csv_factory):
    csv_text = """Txn_ID,From_Acct,To_Acct,Txn_Value,Txn_Date,Mode
TXN_99,SND_99,RCV_99,75000.00,2026-08-23T14:00:00Z,TRANSFER
"""
    csv_file = tmp_csv_factory("api_flow.csv", csv_text)

    # 1. Preview
    with open(csv_file, "rb") as f:
        preview_res = client.post("/upload-dataset/preview", files={"file": ("api_flow.csv", f, "text/csv")})
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    assert "upload_id" in pdata
    assert pdata["can_predict"] is True

    upload_id = pdata["upload_id"]
    mapping = pdata["mapped_dict"]

    # 2. Confirm
    confirm_res = client.post("/upload-dataset/confirm", json={"upload_id": upload_id, "mapping": mapping})
    assert confirm_res.status_code == 200
    cdata = confirm_res.json()
    assert cdata["status"] == "success"
    assert cdata["row_count"] == 1
