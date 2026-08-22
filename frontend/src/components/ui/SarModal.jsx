import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, FileText, Download, Save, CheckCircle, Loader } from 'lucide-react';
import { getApiSarForAccount, postApiSaveSar } from '../../api/client';
import './SarModal.css';

export default function SarModal({ accountId, onClose, onSaveSuccess }) {
  const [sarData, setSarData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [narrative, setNarrative] = useState('');

  useEffect(() => {
    async function loadSar() {
      try {
        setLoading(true);
        const data = await getApiSarForAccount(accountId);
        setSarData(data);
        setNarrative(data.narrative || '');
      } catch (err) {
        console.error("Failed to load or generate SAR draft", err);
        setMessage({ type: 'error', text: 'Failed to load report data.' });
      } finally {
        setLoading(false);
      }
    }
    if (accountId) {
      loadSar();
    }
  }, [accountId]);

  const handleSave = async (status) => {
    try {
      setSaving(true);
      setMessage(null);
      
      const payload = {
        ...sarData,
        status: status,
        narrative: narrative,
      };

      const updated = await postApiSaveSar(payload);
      setSarData(updated);
      setMessage({
        type: 'success',
        text: status === 'SUBMITTED' 
          ? 'SAR submitted to regulatory database and account flagged!' 
          : 'SAR draft saved successfully.'
      });
      if (onSaveSuccess) {
        onSaveSuccess(updated);
      }
    } catch (err) {
      console.error("Failed to save SAR", err);
      setMessage({ type: 'error', text: 'Failed to save SAR report.' });
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!sarData) return;
    
    let jsPDF;
    try {
      const module = await import('jspdf');
      jsPDF = module.jsPDF || module.default;
    } catch (e) {
      console.warn('jspdf package not installed, downloading text SAR report fallback:', e);
      const textReport = `FINANCIAL CRIMES ENFORCEMENT NETWORK (FinCEN)\nAUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR)\n\nSAR ID: ${sarData.sar_id}\nAccount ID: ${sarData.account_id}\nRisk Tier: ${sarData.risk_tier}\nRisk Score: ${sarData.risk_score}/100\nFiling Date: ${sarData.filing_date}\n\nREGULATORY NARRATIVE:\n${narrative}\n`;
      const blob = new Blob([textReport], { type: 'text/plain;charset=utf-8' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `SAR_${sarData.account_id}_${sarData.sar_id}.txt`;
      link.click();
      return;
    }

    const doc = new jsPDF();
    
    // Header banner
    doc.setFillColor(15, 23, 42); // slate-900
    doc.rect(0, 0, 210, 40, 'F');
    
    doc.setFont('Helvetica', 'bold');
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.text('FINANCIAL CRIMES ENFORCEMENT NETWORK (FinCEN)', 14, 18);
    doc.setFontSize(12);
    doc.text('AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR) - MULESCOPE', 14, 28);
    
    // Body Text
    doc.setTextColor(30, 41, 59); // slate-800
    doc.setFontSize(10);
    doc.setFont('Helvetica', 'normal');
    
    let y = 50;
    
    // Report meta table
    doc.setFont('Helvetica', 'bold');
    doc.text('REPORT INFORMATION', 14, y);
    doc.setFont('Helvetica', 'normal');
    y += 8;
    
    const metaInfo = [
      ['SAR Reference ID', sarData.sar_id],
      ['Filing Status', sarData.status],
      ['Filing Date', sarData.filing_date],
      ['Lead Investigator', sarData.investigator || 'Analyst #402'],
      ['Reporting Institution', 'MuleScope Digital Banking Intelligence Unit']
    ];
    
    metaInfo.forEach(([label, val]) => {
      doc.setFont('Helvetica', 'bold');
      doc.text(`${label}:`, 14, y);
      doc.setFont('Helvetica', 'normal');
      doc.text(String(val), 65, y);
      y += 6;
    });
    
    y += 6;
    doc.setDrawColor(226, 232, 240); // border-slate-200
    doc.line(14, y, 196, y);
    y += 10;
    
    // Section 1: Subject
    doc.setFont('Helvetica', 'bold');
    doc.text('SECTION 1: SUBJECT DETAILS', 14, y);
    doc.setFont('Helvetica', 'normal');
    y += 8;
    
    const subjectInfo = [
      ['Account Identifier', sarData.account_id],
      ['ML Risk Tier Classification', `${sarData.risk_tier} RISK`],
      ['Supervised Risk Score', `${sarData.risk_score} / 100`],
      ['Unsupervised Anomaly Metric', String(sarData.anomaly_score)],
      ['Primary Indicators Flashed', (sarData.top_features || []).join(', ')]
    ];
    
    subjectInfo.forEach(([label, val]) => {
      doc.setFont('Helvetica', 'bold');
      doc.text(`${label}:`, 14, y);
      doc.setFont('Helvetica', 'normal');
      doc.text(String(val), 65, y);
      y += 6;
    });
    
    y += 6;
    doc.line(14, y, 196, y);
    y += 10;
    
    // Section 2: Narrative
    doc.setFont('Helvetica', 'bold');
    doc.text('SECTION 2: SUSPICIOUS ACTIVITY NARRATIVE SUMMARY', 14, y);
    doc.setFont('Helvetica', 'normal');
    y += 8;
    
    const splitNarrative = doc.splitTextToSize(narrative, 182);
    doc.text(splitNarrative, 14, y);
    
    // Footer
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(148, 163, 184); // slate-400
      doc.text(`Page ${i} of ${pageCount}`, 14, 285);
      doc.text('CONFIDENTIAL - FOR REGULATORY DISCLOSURE ONLY', 120, 285);
    }
    
    doc.save(`${sarData.sar_id}_fincen_draft.pdf`);
  };

  if (!accountId) return null;

  return createPortal(
    <div className="sar-modal-overlay">
      <div className="sar-modal-container">
        <div className="sar-modal-header">
          <div className="title-area">
            <FileText className="header-icon" />
            <div>
              <h3>Regulatory SAR Draft</h3>
              <span className="subtitle">Account ID: {accountId}</span>
            </div>
          </div>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="sar-modal-body">
          {loading ? (
            <div className="sar-loading">
              <Loader className="spinner" />
              <span>Fetching model insights and auto-generating draft...</span>
            </div>
          ) : !sarData ? (
            <div className="sar-loading">
              <span>Unable to load SAR draft data for account {accountId}.</span>
            </div>
          ) : (
            <>
              {message && (
                <div className={`sar-message ${message.type}`}>
                  <span>{message.text}</span>
                </div>
              )}

              <div className="sar-meta-grid">
                <div className="meta-card">
                  <span className="meta-label">SAR ID</span>
                  <span className="meta-val">{sarData.sar_id}</span>
                </div>
                <div className="meta-card">
                  <span className="meta-label">Status</span>
                  <span className={`meta-val status-badge ${sarData.status}`}>
                    {sarData.status}
                  </span>
                </div>
                <div className="meta-card">
                  <span className="meta-label">Risk Score</span>
                  <span className={`meta-val risk-score ${sarData.risk_tier}`}>
                    {sarData.risk_score} / 100
                  </span>
                </div>
                <div className="meta-card">
                  <span className="meta-label">Anomaly Score</span>
                  <span className="meta-val">{sarData.anomaly_score}</span>
                </div>
              </div>

              <div className="sar-form-group">
                <label className="sar-field-label">Regulatory Narrative & Evidence Summary</label>
                <span className="field-help">
                  Please review and customize the auto-generated explanation below before filing with FinCEN or archiving.
                </span>
                <textarea
                  className="sar-narrative-textarea"
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  placeholder="Explain the pattern of suspicious behavior in detail..."
                  rows={12}
                />
              </div>

              <div className="sar-evidence-chips">
                <span className="chip-title">Flagged Signal Vectors:</span>
                <div className="chips-container">
                  {(sarData.top_features || []).map((feat, i) => (
                    <span key={i} className="evidence-chip">
                      {feat}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="sar-modal-footer">
          <button 
            className="btn-secondary" 
            onClick={onClose} 
            disabled={saving}
          >
            Cancel
          </button>
          
          {sarData && (
            <>
              <button 
                className="btn-info" 
                onClick={handleDownloadPdf}
                disabled={loading}
              >
                <Download size={16} />
                Download PDF
              </button>
              
              <button 
                className="btn-primary" 
                onClick={() => handleSave('DRAFT')}
                disabled={saving || loading}
              >
                <Save size={16} />
                Save Draft
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
