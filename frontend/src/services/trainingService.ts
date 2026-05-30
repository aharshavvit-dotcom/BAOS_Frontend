import { getPortStatus, type PortStatus } from './ports';

export function getTrainingStatus(portCode: string): Promise<PortStatus> {
  return getPortStatus(portCode);
}
