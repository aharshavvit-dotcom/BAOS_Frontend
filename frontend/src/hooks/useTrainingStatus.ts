import { usePortStatus } from './usePortStatus';

export function useTrainingStatus(portCode: string) {
  return usePortStatus(portCode);
}
