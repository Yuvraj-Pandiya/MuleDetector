import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle,
  ArrowRight, Database, RefreshCw,
} from 'lucide-react';
import { uploadDataset } from '../api/client';
import './UploadPage.css';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f?.name.endsWith('.csv')) { setFile(f); setError(null); }
    else setError('Please upload a valid CSV file.');
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f?.name.endsWith('.csv')) { setFile(f); setError(null); }
    else setError('Please upload a valid CSV file.');
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await uploadDataset(formData);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page animate-fade-in">
      <div className="page-head">
        <h2>Ingest Transaction Dataset</h2>
        <p>Upload CSV transaction logs for automated mule network extraction & risk scoring.</p>
      </div>

      <div className="upload-grid">
        {/* Left — Upload Zone */}
        <div className="upload-col">
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input type="file" accept=".csv" id="file-upload" onChange={handleFileSelect} className="file-hidden" />
            <label htmlFor="file-upload" className="dropzone-inner">
              <div className="upload-icon-circle">
                <UploadCloud size={28} />
              </div>
              <h3>{file ? file.name : 'Drag & drop CSV here'}</h3>
              <p>Supports .csv up to 250MB</p>
              {!file && <span className="browse-btn">Browse Files</span>}
            </label>
          </div>

          {error && (
            <div className="error-banner">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {file && !result && (
            <div className="file-preview">
              <div className="file-info">
                <FileText size={22} className="file-icon" />
                <div>
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">{(file.size / (1024 * 1024)).toFixed(2)} MB • Ready</div>
                </div>
              </div>
              <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
                {loading ? (
                  <><RefreshCw size={16} className="animate-spin" /> Processing…</>
                ) : (
                  <>Run Pipeline <ArrowRight size={16} /></>
                )}
              </button>
            </div>
          )}

          {result && (
            <div className="result-card">
              <div className="result-head">
                <CheckCircle2 size={24} className="success-check" />
                <div>
                  <h3>Ingestion Complete</h3>
                  <p>Transaction graph features indexed successfully.</p>
                </div>
              </div>

              <div className="metrics-strip">
                <div className="metric-box">
                  <span className="metric-label">Transactions</span>
                  <span className="metric-val">{result.rows.toLocaleString()}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Features</span>
                  <span className="metric-val">{result.columns.length}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Status</span>
                  <span className="metric-val status-ok">Scored</span>
                </div>
              </div>

              <div className="col-preview">
                <h4>Validated Columns</h4>
                <div className="col-tags">
                  {result.columns.map((col, i) => (
                    <span key={i} className="col-tag"><Database size={11} /> {col}</span>
                  ))}
                </div>
              </div>

              <div className="result-actions">
                <button className="btn-primary" onClick={() => navigate('/dashboard')}>
                  Dashboard <ArrowRight size={14} />
                </button>
                <button className="btn-secondary" onClick={() => navigate('/accounts')}>
                  Risk Table
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right — Schema Guide */}
        <div className="schema-col">
          <div className="schema-card">
            <h3>Expected CSV Schema</h3>
            <p className="schema-desc">Required columns for optimal feature engineering:</p>
            {[
              { name: 'account_id', desc: 'Unique account identifier', type: 'String' },
              { name: 'txn_amount', desc: 'Monetary transaction value', type: 'Float' },
              { name: 'txn_timestamp', desc: 'ISO 8601 UTC timestamp', type: 'Datetime' },
              { name: 'sender_id', desc: 'Source account reference', type: 'String' },
              { name: 'receiver_id', desc: 'Destination account reference', type: 'String' },
            ].map((col, i) => (
              <div key={i} className="schema-item">
                <div className="schema-name">{col.name}</div>
                <div className="schema-desc-sm">{col.desc}</div>
                <span className="schema-type">{col.type}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
