/**
 * Port dropdown with model/data readiness status.
 */
'use client';

import { useEffect } from 'react';
import { usePortStore } from '@/store/portStore';
import type { TrainingStatus } from '@/lib/api/ports';

const STATUS_META: Record<TrainingStatus, { text: string; color: string }> = {
  data_missing: { text: 'Data Missing', color: '#ef4444' },
  insufficient_data: { text: 'Data Missing', color: '#ef4444' },
  data_loaded_training_pending: { text: 'Data Loaded - Training Pending', color: '#f59e0b' },
  training_in_progress: { text: 'Training In Progress', color: '#3b82f6' },
  trained: { text: 'Trained', color: '#10b981' },
  training_failed: { text: 'Training Failed', color: '#ef4444' },
};

export function PortSelector() {
  const {
    ports, selectedPortCode, portStatus,
    loading, error,
    fetchPorts, selectPort,
  } = usePortStore();

  useEffect(() => {
    fetchPorts();
  }, [fetchPorts]);

  const statusBadge = portStatus ? STATUS_META[portStatus.training_status] : null;

  return (
    <div className="flex items-center gap-3">
      <div style={{ position: 'relative' }}>
        <select
          className="form-input"
          value={selectedPortCode}
          onChange={(e) => selectPort(e.target.value)}
          disabled={loading}
          style={{
            minWidth: 180,
            paddingRight: 36,
            fontWeight: 600,
            fontSize: 13,
            background: 'var(--color-dark-card)',
            border: '1px solid var(--color-dark-border)',
          }}
        >
          {ports.map((p) => (
            <option key={p.port_code} value={p.port_code}>
              {p.port_name} ({p.port_code})
            </option>
          ))}
          {ports.length === 0 && (
            <option value={selectedPortCode}>
              Loading... ({selectedPortCode})
            </option>
          )}
        </select>
        {loading && (
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              right: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: 11,
              color: 'var(--color-text-muted)',
            }}
          >
            ...
          </span>
        )}
      </div>

      {statusBadge && portStatus && (
        <span
          title={portStatus.training_message}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            fontWeight: 600,
            color: statusBadge.color,
            padding: '3px 10px',
            borderRadius: 12,
            background: `${statusBadge.color}15`,
            whiteSpace: 'nowrap',
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 999,
              background: statusBadge.color,
              display: 'inline-block',
            }}
          />
          {statusBadge.text}
        </span>
      )}

      {portStatus && (
        <span
          style={{
            fontSize: 10,
            color: 'var(--color-text-muted)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            whiteSpace: 'nowrap',
          }}
        >
          {portStatus.data_quality?.source || 'Unknown'} data
          {' · '}
          {portStatus.berth_count} berths
        </span>
      )}

      {error && (
        <span style={{ fontSize: 11, color: '#ef4444' }}>
          {error}
        </span>
      )}
    </div>
  );
}
