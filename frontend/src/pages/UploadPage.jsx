import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle, AlertTriangle,
  ArrowRight, Database, RefreshCw, Download, Sliders, ShieldCheck,
  Zap, Info, FileSpreadsheet, Check, Sparkles
} from 'lucide-react';
import { previewDataset, confirmDatasetMapping, uploadDataset } from '../api/client';
import './UploadPage.css';

const CANONICAL_OPTIONS = [
  { value: 'transaction_id', label: 'Transaction ID (transaction_id)', required: false },
  { value: 'sender_account_id', label: 'Sender Account ID (sender_account_id)', required: true },
  { value: 'receiver_account_id', label: 'Receiver Account ID (receiver_account_id)', required: true },
  { value: 'amount', label: 'Transaction Amount (amount)', required: true },
  { value: 'timestamp', label: 'Timestamp (timestamp)', required: true },
  { value: 'transaction_type', label: 'Transaction Type (transaction_type)', required: false },
  { value: 'is_mule_pattern', label: 'Fraud / Mule Label (is_mule_pattern)', required: false },
  { value: 'old_balance_sender', label: 'Sender Old Balance (old_balance_sender)', required: false },
  { value: 'new_balance_sender', label: 'Sender New Balance (new_balance_sender)', required: false },
  { value: 'old_balance_receiver', label: 'Receiver Old Balance (old_balance_receiver)', required: false },
  { value: 'new_balance_receiver', label: 'Receiver New Balance (new_balance_receiver)', required: false },
  { value: 'unmapped', label: '— Ignore / Unmapped Column —', required: false },
];

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // Schema Mapping State
  const [previewData, setPreviewData] = useState(null);
  const [userMapping, setUserMapping] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f?.name.endsWith('.csv')) {
      resetState(f);
    } else {
      setError('Please upload a valid CSV file.');
    }
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f?.name.endsWith('.csv')) {
      resetState(f);
    } else {
      setError('Please upload a valid CSV file.');
    }
  };

  const resetState = (selectedFile) => {
    setFile(selectedFile);
    setPreviewData(null);
    setUserMapping({});
    setResult(null);
    setError(null);
  };

  const [uploadProgress, setUploadProgress] = useState(0);

  // Step 1: Preview CSV & Extract Multi-Stage Schema Mapping
  const handlePreviewUpload = async () => {
    if (!file) return;
    setLoading(true);
    setUploadProgress(0);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const previewRes = await previewDataset(formData, (percent) => setUploadProgress(percent));
      setPreviewData(previewRes);

      // Initialize mapping dictionary with mapped_dict and mapped column targets
      const initialMap = { ...(previewRes.mapped_dict || {}) };
      (previewRes.columns || []).forEach((col) => {
        if (col.target) {
          initialMap[col.source] = col.target;
        }
      });
      setUserMapping(initialMap);
    } catch (err) {
      console.error('Schema preview error:', err);
      if (err.response?.status === 404) {
        // Fallback for servers without /preview endpoint
        try {
          const formData = new FormData();
          formData.append('file', file);
          const directRes = await uploadDataset(formData);
          setResult(directRes);
          return;
        } catch (fallbackErr) {
          const msg = fallbackErr.response?.data?.detail || fallbackErr.message || 'Direct upload failed.';
          setError(`Upload Error: ${msg}`);
          return;
        }
      }
      const isTimeout = err.code === 'ECONNABORTED' || err.message?.includes('timeout');
      if (isTimeout) {
        setError(`Upload Timeout (${(file.size / (1024 * 1024)).toFixed(1)} MB): Processing large CSVs requires extended time. The 10-minute timeout has been applied. Please click 'Analyze & Map Schema' to retry.`);
      } else {
        const msg = err.response?.data?.detail || err.message || 'Failed to profile CSV schema.';
        setError(`Upload Error: ${msg}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const MANDATORY_CANONICAL = [
    { id: 'sender_account_id', label: 'Sender Account ID (sender_account_id)' },
    { id: 'receiver_account_id', label: 'Receiver Account ID (receiver_account_id)' },
    { id: 'amount', label: 'Transaction Amount (amount)' },
    { id: 'timestamp', label: 'Timestamp (timestamp)' },
  ];

  const getMissingMandatoryFields = () => {
    const currentTargets = Object.values(userMapping);
    return MANDATORY_CANONICAL.filter((item) => !currentTargets.includes(item.id));
  };

  // Step 2: Confirm User Schema Mapping
  const handleConfirmMapping = async () => {
    if (!previewData || !previewData.upload_id) return;

    const missing = getMissingMandatoryFields();
    if (missing.length > 0) {
      setError(`Action Required: Please assign CSV columns for mandatory field(s): ${missing.map((m) => m.label).join(', ')}.`);
      return;
    }

    setConfirming(true);
    setError(null);

    try {
      const payload = {
        upload_id: previewData.upload_id,
        mapping: userMapping,
      };
      const confirmRes = await confirmDatasetMapping(payload);
      setResult(confirmRes);
    } catch (err) {
      const serverDetail = err.response?.data?.detail;
      setError(serverDetail ? `Schema Error: ${serverDetail}` : (err.message || 'Failed to confirm schema mapping.'));
    } finally {
      setConfirming(false);
    }
  };

  const handleMappingChange = (sourceCol, targetVal) => {
    setUserMapping((prev) => {
      const updated = { ...prev };
      if (targetVal === 'unmapped') {
        delete updated[sourceCol];
      } else {
        updated[sourceCol] = targetVal;
      }
      return updated;
    });
  };

  const handleDownloadTemplate = () => {
    window.open('/upload-dataset/template', '_blank');
  };

  return (
    <div className="upload-page animate-fade-in">
      <div className="page-head flex-between">
        <div>
          <h2>Universal CSV Ingestion & Schema Normalizer</h2>
          <p>Multi-stage AI column profiler automatically normalizes multi-bank CSV formats to Canonical AML Schema.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={handleDownloadTemplate}>
          <Download size={14} /> Download Canonical Template (.csv)
        </button>
      </div>

      <div className="upload-grid">
        {/* Left — Main Upload Workflow */}
        <div className="upload-col">
          {/* File Dropzone */}
          {!previewData && !result && (
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
                <h3>{file ? file.name : 'Drag & drop bank CSV here'}</h3>
                <p>Supports PaySim, Core Bank CSVs, custom column names up to 250MB</p>
                {!file && <span className="browse-btn">Browse Files</span>}
              </label>
            </div>
          )}

          {error && (
            <div className="error-banner margin-top-xs">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* File Selected — Trigger Preview */}
          {file && !previewData && !result && (
            <div className="file-preview margin-top-xs">
              <div className="file-info">
                <FileText size={22} className="file-icon" />
                <div>
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">{(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for AI Profiling</div>
                </div>
              </div>
              <button className="btn-primary" onClick={handlePreviewUpload} disabled={loading}>
                {loading ? (
                  <><RefreshCw size={16} className="animate-spin" /> {uploadProgress > 0 && uploadProgress < 100 ? `Uploading (${uploadProgress}%)...` : 'Profiling Schema...'}</>
                ) : (
                  <>Analyze & Map Schema <ArrowRight size={16} /></>
                )}
              </button>
            </div>
          )}

          {/* Step 2: Interactive Schema Mapping Preview Table */}
          {previewData && !result && (
            <div className="schema-preview-card margin-top-xs animate-fade-in">
              <div className="card-head flex-between">
                <div>
                  <h3 className="flex-align gap-xs">
                    <Sliders size={18} className="text-teal" /> Universal Schema Mapping Review
                  </h3>
                  <p className="text-xs text-stone">
                    Review and confirm automatic column mappings before converting to Canonical AML Schema. Unmapped extra columns are safely ignored.
                  </p>
                </div>

                <div className="status-badge-caps">
                  {previewData.can_train && <span className="cap-tag green"><Sparkles size={11} /> Labeled (Trainable)</span>}
                  {previewData.can_predict && <span className="cap-tag teal"><ShieldCheck size={11} /> Prediction Ready</span>}
                  {!previewData.can_predict && <span className="cap-tag amber"><AlertTriangle size={11} /> Missing Core Fields</span>}
                </div>
              </div>

              {/* Dataset Not Applicable Warning */}
              {previewData.status === 'dataset_not_applicable' && (
                <div className="missing-mandatory-banner margin-top-xs">
                  <AlertTriangle size={18} />
                  <div>
                    <strong>Dataset Not Applicable / Action Required:</strong> {previewData.user_message || 'This CSV is missing mandatory transaction fields. Please select appropriate columns for Sender Account, Receiver Account, Amount, and Timestamp below.'}
                  </div>
                </div>
              )}

              {/* Columns Mapping List */}
              <div className="mapping-table-wrapper margin-top-xs">
                <table className="mapping-table">
                  <thead>
                    <tr>
                      <th>Source CSV Column</th>
                      <th>Inferred Data Type</th>
                      <th>Sample Data Values</th>
                      <th>Confidence</th>
                      <th>Canonical AML Target Field</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(previewData.columns || []).map((col, idx) => {
                      const currentTarget = userMapping[col.source] || 'unmapped';
                      const confPct = Math.round((col.confidence || 0) * 100);
                      const isHigh = confPct >= 90;
                      const isMed = confPct >= 70 && confPct < 90;

                      return (
                        <tr key={idx} className={col.status === 'review' ? 'highlight-review' : ''}>
                          <td className="font-mono font-bold text-ink">
                            {col.source}
                          </td>
                          <td>
                            <span className="type-pill">{col.inferred_type}</span>
                          </td>
                          <td className="sample-val-cell">
                            {(col.sample_values || []).slice(0, 3).join(', ')}
                          </td>
                          <td>
                            <span className={`conf-badge ${isHigh ? 'high' : isMed ? 'med' : 'low'}`}>
                              {confPct}% {col.matched_stage || 'Match'}
                            </span>
                          </td>
                          <td>
                            <select
                              value={currentTarget}
                              onChange={(e) => handleMappingChange(col.source, e.target.value)}
                              className="mapping-select"
                            >
                              {CANONICAL_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Missing Mandatory Fields Alert Prompt */}
              {getMissingMandatoryFields().length > 0 && (
                <div className="missing-mandatory-banner margin-top-xs">
                  <AlertCircle size={16} />
                  <span>
                    <strong>Mapping Required:</strong> Assign CSV columns for mandatory fields:{' '}
                    {getMissingMandatoryFields().map((m) => m.label).join(', ')}.
                  </span>
                </div>
              )}

              {error && (
                <div className="error-banner margin-top-xs">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              {/* Confirm Actions */}
              <div className="preview-actions flex-between margin-top-md">
                <button className="btn-secondary" onClick={() => setPreviewData(null)}>
                  Cancel / Re-upload
                </button>

                <button
                  className="btn-primary"
                  onClick={handleConfirmMapping}
                  disabled={confirming || getMissingMandatoryFields().length > 0}
                >
                  {confirming ? (
                    <><RefreshCw size={16} className="animate-spin" /> Normalizing & Indexing…</>
                  ) : (
                    <>Confirm Mapping & Run AML Pipeline <Check size={16} /></>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Ingestion & Quality Report Result */}
          {result && (
            <div className="result-card margin-top-xs animate-fade-in">
              <div className="result-head">
                <CheckCircle2 size={24} className="success-check" />
                <div>
                  <h3>Dataset Normalized & Active</h3>
                  <p>External CSV converted to Canonical AML Schema and indexed for ML models.</p>
                </div>
              </div>

              <div className="metrics-strip">
                <div className="metric-box">
                  <span className="metric-label">Total Transactions</span>
                  <span className="metric-val">{result.row_count?.toLocaleString()}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Unique Senders</span>
                  <span className="metric-val">{result.quality_report?.unique_senders || '—'}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Unique Receivers</span>
                  <span className="metric-val">{result.quality_report?.unique_receivers || '—'}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Status</span>
                  <span className="metric-val status-ok">Ready</span>
                </div>
              </div>

              {/* Data Quality Highlights */}
              <div className="quality-audit-box margin-top-xs">
                <h4>Data Quality Audit & Integrity Report</h4>
                <div className="audit-grid">
                  <div className="audit-item">
                    <span>Invalid Amounts (Flagged):</span>
                    <strong>{result.quality_report?.invalid_amount_count || 0} rows</strong>
                  </div>
                  <div className="audit-item">
                    <span>Duplicate Transactions:</span>
                    <strong>{result.quality_report?.duplicate_count || 0}</strong>
                  </div>
                  <div className="audit-item">
                    <span>Timestamp Source:</span>
                    <strong>{result.quality_report?.timestamp_source || 'provided'}</strong>
                  </div>
                  <div className="audit-item">
                    <span>Fraud Label Present:</span>
                    <strong>{result.quality_report?.fraud_label_distribution?.has_label ? 'Yes (Labeled)' : 'No (Unlabeled Prediction)'}</strong>
                  </div>
                </div>
              </div>

              <div className="result-actions margin-top-md">
                <button className="btn-primary" onClick={() => navigate('/dashboard')}>
                  Command Center <ArrowRight size={14} />
                </button>
                <button className="btn-secondary" onClick={() => navigate('/accounts')}>
                  Risk Directory
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right — Schema Requirements Guide */}
        <div className="upload-guide-col">
          <div className="guide-card">
            <h3>Canonical Schema Fields</h3>
            <p className="text-xs text-stone">MuleDetector accepts any external CSV column name and normalizes it to these fields:</p>

            <ul className="canonical-fields-list">
              <li>
                <span className="field-name required">transaction_id *</span>
                <span className="field-desc">Unique transfer ID</span>
              </li>
              <li>
                <span className="field-name required">sender_account_id *</span>
                <span className="field-desc">Sender / Originator account</span>
              </li>
              <li>
                <span className="field-name required">receiver_account_id *</span>
                <span className="field-desc">Receiver / Beneficiary account</span>
              </li>
              <li>
                <span className="field-name required">amount *</span>
                <span className="field-desc">Monetary transaction value</span>
              </li>
              <li>
                <span className="field-name required">timestamp *</span>
                <span className="field-desc">ISO datetime or PaySim step</span>
              </li>
              <li>
                <span className="field-name optional">transaction_type</span>
                <span className="field-desc">TRANSFER, CASH_OUT, PAYMENT</span>
              </li>
              <li>
                <span className="field-name optional">is_mule_pattern</span>
                <span className="field-desc">Ground truth label (0/1)</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
