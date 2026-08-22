import time
import subprocess
import requests
import json
import os
import pathlib
import sys

BASE_URL = "http://localhost:8000"

def wait_for_server():
    for _ in range(20):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except:
            time.sleep(0.5)
    return False

def start_server():
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"])
    if not wait_for_server():
        proc.kill()
        raise Exception("Server failed to start")
    return proc

def run_tests():
    # 4. FULL END-TO-END RUN
    print("--- 4. FULL END-TO-END RUN ---")
    r = requests.get(f"{BASE_URL}/health")
    print("GET /health:", r.status_code)
    assert r.status_code == 200

    # 5. ERROR HANDLING SANITY: missing column
    print("--- 5. ERROR HANDLING SANITY ---")
    with open("bad.csv", "w") as f:
        f.write("transaction_id,timestamp,sender_account_id,receiver_account_id,transaction_type\n")
        f.write("T1,2024-01-01 12:00:00,A,B,TRANSFER\n")
    with open("bad.csv", "rb") as f:
        r = requests.post(f"{BASE_URL}/upload-dataset", files={"file": ("bad.csv", f, "text/csv")})
    print("POST /upload-dataset (bad CSV):", r.status_code, r.text)
    assert r.status_code == 400
    assert "amount" in r.text.lower() # missing column name in response

    # Upload real data
    print("\n--- Uploading real data ---")
    with open("app/data/mule_injected.csv", "rb") as f:
        r = requests.post(f"{BASE_URL}/upload-dataset", files={"file": ("mule_injected.csv", f, "text/csv")})
    print("POST /upload-dataset (real):", r.status_code, r.text)
    assert r.status_code == 200

    # Features check
    print("\n--- GET /features ---")
    r = requests.get(f"{BASE_URL}/features")
    assert r.status_code == 200
    data = r.json()
    schema_diff = data["schema_diff"]
    print("schema_diff:", schema_diff)
    assert schema_diff["ok"] == True
    
    # NaN check
    null_found = any(v is None for r in data['records'] for v in r.values())
    print("null_found:", null_found)
    assert not null_found

    # Train model
    print("\n--- POST /train ---")
    r = requests.post(f"{BASE_URL}/train")
    assert r.status_code == 200
    metrics = r.json()["metrics"]
    print("ROC-AUC:", metrics.get("roc_auc"))
    assert os.path.exists("app/data/model.pkl")
    assert os.path.exists("app/data/metrics.json")

    # Risk scores
    print("\n--- GET /risk-scores ---")
    r = requests.get(f"{BASE_URL}/risk-scores")
    assert r.status_code == 200
    risk_data = r.json()
    accounts = risk_data["accounts"]
    
    # Check sorting
    scores = [a["risk_score"] for a in accounts]
    assert scores == sorted(scores, reverse=True), "Not sorted descending"

    # Known mules
    # Let's get injected mules from the CSV
    import pandas as pd
    df = pd.read_csv("app/data/mule_injected.csv")
    injected_mules = set(df[df["is_mule_pattern"] == 1]["sender_account_id"].unique())
    print("Total injected mules (senders):", len(injected_mules))
    
    high_med_mules = [a["account_id"] for a in accounts if a["account_id"] in injected_mules and a["risk_tier"] in ["High", "Medium"]]
    print("Injected mules caught in High/Medium:", len(high_med_mules))
    assert len(high_med_mules) >= 3

    # Error handling: nonexistent account
    print("\n--- GET /explain/NON_EXISTENT ---")
    r = requests.get(f"{BASE_URL}/explain/NON_EXISTENT")
    print("Status:", r.status_code)
    print("Response:", r.text)
    assert 400 <= r.status_code < 500

    # Explain high risk account
    high_risk_acct = accounts[0]["account_id"]
    print(f"\n--- GET /explain/{high_risk_acct} ---")
    r = requests.get(f"{BASE_URL}/explain/{high_risk_acct}")
    assert r.status_code == 200
    explain_data = r.json()
    print("Reason:", explain_data.get("reason"))
    assert len(explain_data.get("reason", "")) > 0

    # Alerts
    print("\n--- GET /alerts ---")
    r = requests.get(f"{BASE_URL}/alerts")
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    print("Total alerts:", len(alerts))
    
    if len(alerts) > 0:
        alert_id = alerts[0]["alert_id"]
        old_status = alerts[0]["status"]
        new_status = "investigating" if old_status == "open" else "open"
        print(f"PATCH /alerts/{alert_id} to {new_status}")
        r = requests.patch(f"{BASE_URL}/alerts/{alert_id}", json={"status": new_status})
        assert r.status_code == 200
        
        return alert_id, new_status
    return None, None

def verify_persistence_and_dashboard(alert_id, expected_status):
    print("\n--- Verify Persistence ---")
    if alert_id:
        r = requests.get(f"{BASE_URL}/alerts")
        alerts = r.json()["alerts"]
        alert = next(a for a in alerts if a["alert_id"] == alert_id)
        print(f"Alert {alert_id} status:", alert["status"])
        assert alert["status"] == expected_status
    
    print("\n--- GET /dashboard-summary ---")
    r = requests.get(f"{BASE_URL}/dashboard-summary")
    assert r.status_code == 200
    dash = r.json()
    print("Dashboard summary:", json.dumps(dash, indent=2))
    print("\nALL E2E TESTS PASSED.")

if __name__ == "__main__":
    proc = start_server()
    try:
        alert_id, expected_status = run_tests()
    except Exception as e:
        proc.kill()
        raise e
    
    proc.kill()
    proc.wait()
    time.sleep(1)
    
    proc = start_server()
    try:
        verify_persistence_and_dashboard(alert_id, expected_status)
    finally:
        proc.kill()
