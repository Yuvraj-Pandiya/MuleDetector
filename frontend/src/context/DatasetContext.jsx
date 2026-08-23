import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getDatasets, activateDataset, deleteDataset, renameDataset } from '../api/client';

const DatasetContext = createContext(null);

export function DatasetProvider({ children }) {
  const [datasets, setDatasets] = useState([
    {
      id: 'paysim_benchmark',
      name: 'PaySim Benchmark (15,420 accounts)',
      type: 'benchmark',
      row_count: 185040,
      account_count: 15420,
      is_builtin: true,
      is_active: true,
    },
  ]);
  const [activeDatasetId, setActiveDatasetId] = useState(() => {
    return localStorage.getItem('active_dataset_id') || 'paysim_benchmark';
  });
  const [isLoading, setIsLoading] = useState(false);

  const fetchDatasets = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await getDatasets();
      if (res && res.datasets && res.datasets.length > 0) {
        setDatasets(res.datasets);
        const storedActive = localStorage.getItem('active_dataset_id');
        const active = storedActive || res.active_dataset_id || 'paysim_benchmark';
        setActiveDatasetId(active);
      }
    } catch (err) {
      console.warn('Could not fetch dataset registry:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const switchDataset = async (datasetId) => {
    try {
      setIsLoading(true);
      await activateDataset(datasetId);
      setActiveDatasetId(datasetId);
      localStorage.setItem('active_dataset_id', datasetId);
      setDatasets((prev) =>
        prev.map((d) => ({
          ...d,
          is_active: d.id === datasetId,
        }))
      );
      // Trigger a custom event so pages can re-fetch immediately without full browser reload
      window.dispatchEvent(new CustomEvent('dataset-changed', { detail: { datasetId } }));
    } catch (err) {
      console.error('Failed to switch dataset:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const removeDataset = async (datasetId) => {
    try {
      setIsLoading(true);
      await deleteDataset(datasetId);
      if (activeDatasetId === datasetId) {
        await switchDataset('paysim_benchmark');
      }
      await fetchDatasets();
    } catch (err) {
      console.error('Failed to delete dataset:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const activeDataset =
    datasets.find((d) => d.id === activeDatasetId) ||
    datasets[0] || {
      id: 'paysim_benchmark',
      name: 'PaySim Benchmark (15,420 accounts)',
      type: 'benchmark',
      row_count: 185040,
      account_count: 15420,
      is_builtin: true,
      is_active: true,
    };

  return (
    <DatasetContext.Provider
      value={{
        datasets,
        activeDataset,
        activeDatasetId,
        isLoading,
        switchDataset,
        removeDataset,
        refreshDatasets: fetchDatasets,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset() {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error('useDataset must be used within a DatasetProvider');
  return ctx;
}
