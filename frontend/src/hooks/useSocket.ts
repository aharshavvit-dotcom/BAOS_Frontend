/**
 * useSocket — React hook for Socket.IO real-time updates.
 * Connects on mount, disconnects on unmount.
 * Listens for KPI updates, assignment updates, and notifications.
 */
'use client';

import { useEffect, useRef } from 'react';
import { getSocket, connectSocket, disconnectSocket } from '@/lib/socket';
import { useDashboardStore } from '@/store/dashboardStore';
import { useUIStore } from '@/store/uiStore';
import type { KPIData, DashboardRecommendation } from '@/types';

export function useSocket() {
  const connected = useRef(false);
  const updateKPIs = useDashboardStore(s => s.updateKPIs);
  const addRecommendation = useDashboardStore(s => s.addRecommendation);
  const showToast = useUIStore(s => s.showToast);

  useEffect(() => {
    if (connected.current) return;
    connected.current = true;

    const socket = getSocket();

    socket.on('connect', () => {
      // FIX (Phase 7.9): console.log → dev-only debug
      if (process.env.NODE_ENV === 'development') console.debug('[WS] Connected to BAOS AI server');
    });

    socket.on('disconnect', (reason) => {
      // FIX (Phase 7.9): console.log → dev-only debug
      if (process.env.NODE_ENV === 'development') console.debug('[WS] Disconnected:', reason);
    });

    // Real-time KPI updates
    socket.on('kpi_update', (data: KPIData) => {
      updateKPIs(data);
    });

    // New assignment/recommendation
    socket.on('new_assignment', (data: DashboardRecommendation) => {
      addRecommendation(data);
      showToast(`New assignment: ${data.vessel_name} → ${data.berth_name}`, 'info');
    });

    // Generic notification
    socket.on('notification', (data: { message: string; type?: 'success' | 'error' | 'info' | 'warning' }) => {
      showToast(data.message, data.type || 'info');
    });

    socket.on('connect_error', (err) => {
      console.warn('[WS] Connection failed:', err.message);
    });

    connectSocket();

    return () => {
      disconnectSocket();
      connected.current = false;
    };
  }, [updateKPIs, addRecommendation, showToast]);
}
