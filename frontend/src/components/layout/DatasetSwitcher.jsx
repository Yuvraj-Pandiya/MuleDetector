import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, ChevronDown, Check, UploadCloud, Trash2, Sparkles, Layers } from 'lucide-react';
import { useDataset } from '../../context/DatasetContext';
import './DatasetSwitcher.css';

export default function DatasetSwitcher() {
  const { datasets, activeDataset, activeDatasetId, switchDataset, removeDataset, isLoading } = useDataset();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (id) => {
    if (id !== activeDatasetId) {
      switchDataset(id);
    }
    setIsOpen(false);
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this custom dataset?')) {
      removeDataset(id);
    }
  };

  const formatCount = (num) => {
    if (!num) return '0';
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return num.toLocaleString();
  };

  return (
    <div className="dataset-switcher-container" ref={dropdownRef}>
      <button
        type="button"
        className={`dataset-switcher-trigger ${isOpen ? 'active' : ''} ${isLoading ? 'loading' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Switch AML Dataset"
        id="dataset-switcher-btn"
      >
        <div className="trigger-icon-wrap">
          {activeDataset.is_builtin ? (
            <Sparkles size={14} className="icon-sparkle text-cyan" />
          ) : (
            <Database size={14} className="icon-db text-primary" />
          )}
        </div>
        <div className="trigger-text-wrap">
          <span className="trigger-label">Dataset</span>
          <span className="trigger-name">
            {activeDataset.name ? (activeDataset.name.length > 22 ? `${activeDataset.name.slice(0, 20)}…` : activeDataset.name) : 'PaySim Benchmark'}
          </span>
        </div>
        <ChevronDown size={13} className={`trigger-chevron ${isOpen ? 'rotated' : ''}`} />
      </button>

      {isOpen && (
        <div className="dataset-dropdown-menu animate-fade-in">
          <div className="dropdown-header">
            <div className="header-title">
              <Layers size={13} />
              <span>Available Datasets ({datasets.length})</span>
            </div>
            <span className="header-hint">Synced to all views</span>
          </div>

          <div className="dropdown-list custom-scrollbar">
            {datasets.map((ds) => {
              const isSelected = ds.id === activeDatasetId;
              return (
                <div
                  key={ds.id}
                  className={`dataset-option-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleSelect(ds.id)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="option-left">
                    <div className={`option-radio ${isSelected ? 'checked' : ''}`}>
                      {isSelected && <Check size={12} />}
                    </div>
                    <div className="option-info">
                      <div className="option-name-row">
                        <span className="option-name">{ds.name}</span>
                        {ds.is_builtin && <span className="badge-builtin">Default Benchmark</span>}
                      </div>
                      <div className="option-meta">
                        <span>{formatCount(ds.account_count || ds.row_count)} accounts</span>
                        <span className="meta-sep">•</span>
                        <span>{formatCount(ds.row_count)} txns</span>
                      </div>
                    </div>
                  </div>

                  {!ds.is_builtin && (
                    <button
                      type="button"
                      className="btn-delete-dataset"
                      title="Delete dataset"
                      onClick={(e) => handleDelete(e, ds.id)}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <div className="dropdown-footer">
            <button
              type="button"
              className="btn-upload-new-dataset"
              onClick={() => {
                setIsOpen(false);
                navigate('/upload');
              }}
            >
              <UploadCloud size={14} />
              <span>Upload New CSV Dataset</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
