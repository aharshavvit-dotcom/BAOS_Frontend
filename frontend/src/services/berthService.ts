import { getPortConfig, type BerthConfig } from './ports';

export async function getBerths(portCode: string): Promise<BerthConfig[]> {
  const config = await getPortConfig(portCode);
  return config.berths;
}
