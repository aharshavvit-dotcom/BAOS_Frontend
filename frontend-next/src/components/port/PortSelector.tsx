/**
 * PortSelector — Port dropdown with training status indicator.
 * Shows berth count and model status badge.
 */
'use client';

import { useEffect } from 'react';
import { usePortStore } from '@/store/portStore';

export function PortSelector() {
  const {
    ports, selectedPortCode, portStatus,
    loading, error,
    fetchPorts, selectPort,
  } = usePortStore();

  useEffect(() => {
    fetchPorts();
  }, [fetchPorts]);

  const statusBadge = portStatus ? (
    portStatus.trained
      ? { icon: '🟢', text: 'Trained', color: '#10b981' }
      : { icon: '🟡', text: 'Not Trained', color: '#f59e0b' }
  ) : null;

  return (
    <div className="flex items-center gap-3">
      <div style={{ position: 'relative' }}>
        <select
          className="form-input"
          value={selectedPortCode}
          onChange={(e) => selectPort(e.target.value)}
          disabled={loading}
          style={{
            minWidth: 180, paddingRight: 36,
            fontWeight: 600, fontSize: 13,
            background: 'var(--color-dark-card)',
            border: '1px solid var(--color-border)',
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
          <span className="animate-spin" style={{
            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
            fontSize: 14,
          }}>
            ⚙️
          </span>
        )}
      </div>

      {statusBadge && (
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          fontSize: 11, fontWeight: 600,
          color: statusBadge.color,
          padding: '3px 10px', borderRadius: 12,
          background: `${statusBadge.color}15`,
        }}>
          {statusBadge.icon} {statusBadge.text}
        </span>
      )}

      {portStatus && (
        <span style={{
          fontSize: 10, color: 'var(--color-text-muted)',
          display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>
          📋 {portStatus.data_quality?.source || 'Unknown'} data
          · {portStatus.berth_count} berths
        </span>
      )}

      {error && (
        <span style={{ fontSize: 11, color: '#ef4444' }}>
          ⚠️ {error}
        </span>
      )}
    </div>
  );
}
