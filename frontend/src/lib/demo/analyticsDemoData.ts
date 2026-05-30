export const TERMINALS = [
  { name: 'Jawahar Terminal', code: '262', berths: ['JD1', 'JD2', 'JD3', 'JD4', 'JD5', 'JD6'] },
  { name: 'CITPL Terminal', code: '6272', berths: ['SCB1', 'SCB2', 'SCB3'] },
  { name: 'CCTL Terminal', code: '6273', berths: ['CTB1', 'CTB2', 'CTB3', 'CTB4'] },
  { name: 'Oil Terminal', code: '81', berths: ['BD1', 'BD2', 'BD3'] },
  { name: 'Ambedkar Terminal', code: '999', berths: ['1 South', '2 West', '3 West', '4 West', 'C', '1 West', '2 South'] },
];

export const BERTH_STATUS = [
  { berth: 'Berth JD1', terminal: 'Jawahar', status: 'occupied', vessel: 'MV Ocean Crown', vesselType: 'Bulk Dry', since: '6h ago', eta_depart: '18h', progress: 65 },
  { berth: 'Berth JD2', terminal: 'Jawahar', status: 'occupied', vessel: 'SS Pacific Trader', vesselType: 'General Cargo', since: '12h ago', eta_depart: '8h', progress: 85 },
  { berth: 'Berth JD3', terminal: 'Jawahar', status: 'free', vessel: '', vesselType: '', since: '2h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth JD4', terminal: 'Jawahar', status: 'occupied', vessel: 'MT Horizon Star', vesselType: 'Chemical', since: '4h ago', eta_depart: '24h', progress: 30 },
  { berth: 'Berth JD5', terminal: 'Jawahar', status: 'free', vessel: '', vesselType: '', since: '5h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth JD6', terminal: 'Jawahar', status: 'maintenance', vessel: '', vesselType: '', since: '1d ago', eta_depart: '', progress: 0 },
  { berth: 'Berth SCB1', terminal: 'CITPL', status: 'occupied', vessel: 'MV Ever Glory', vesselType: 'Container', since: '8h ago', eta_depart: '14h', progress: 55 },
  { berth: 'Berth SCB2', terminal: 'CITPL', status: 'occupied', vessel: 'MV Nordic Express', vesselType: 'Container', since: '2h ago', eta_depart: '28h', progress: 12 },
  { berth: 'Berth SCB3', terminal: 'CITPL', status: 'free', vessel: '', vesselType: '', since: '4h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth CTB1', terminal: 'CCTL', status: 'occupied', vessel: 'MV Maersk Tanaka', vesselType: 'Container', since: '10h ago', eta_depart: '6h', progress: 90 },
  { berth: 'Berth CTB2', terminal: 'CCTL', status: 'occupied', vessel: 'MV CMA Zenith', vesselType: 'Container', since: '6h ago', eta_depart: '18h', progress: 50 },
  { berth: 'Berth CTB3', terminal: 'CCTL', status: 'free', vessel: '', vesselType: '', since: '8h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth CTB4', terminal: 'CCTL', status: 'free', vessel: '', vesselType: '', since: '3h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth BD1', terminal: 'Oil', status: 'occupied', vessel: 'MT Jade Voyager', vesselType: 'Oil', since: '16h ago', eta_depart: '10h', progress: 75 },
  { berth: 'Berth BD2', terminal: 'Oil', status: 'occupied', vessel: 'MT Chem Pioneer', vesselType: 'Chemical', since: '20h ago', eta_depart: '4h', progress: 92 },
  { berth: 'Berth BD3', terminal: 'Oil', status: 'free', vessel: '', vesselType: '', since: '1h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth 1 South', terminal: 'Ambedkar', status: 'occupied', vessel: 'MV Coastal Star', vesselType: 'General Cargo', since: '24h ago', eta_depart: '12h', progress: 70 },
  { berth: 'Berth 2 West', terminal: 'Ambedkar', status: 'free', vessel: '', vesselType: '', since: '6h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth 3 West', terminal: 'Ambedkar', status: 'occupied', vessel: 'MV Ro-Ro King', vesselType: 'Ro-Ro Cargo', since: '3h ago', eta_depart: '20h', progress: 22 },
  { berth: 'Berth 4 West', terminal: 'Ambedkar', status: 'free', vessel: '', vesselType: '', since: '12h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth C', terminal: 'Ambedkar', status: 'occupied', vessel: 'MV Atlas Dry', vesselType: 'Bulk Dry', since: '8h ago', eta_depart: '16h', progress: 45 },
  { berth: 'Berth 1 West', terminal: 'Ambedkar', status: 'free', vessel: '', vesselType: '', since: '2h ago', eta_depart: '', progress: 0 },
  { berth: 'Berth 2 South', terminal: 'Ambedkar', status: 'free', vessel: '', vesselType: '', since: '10h ago', eta_depart: '', progress: 0 },
];

export const WEEKLY_THROUGHPUT = [
  { day: 'Mon', vessels: 8, cargo_kt: 120, avgWait: 3.2 },
  { day: 'Tue', vessels: 10, cargo_kt: 145, avgWait: 4.1 },
  { day: 'Wed', vessels: 7, cargo_kt: 105, avgWait: 2.8 },
  { day: 'Thu', vessels: 12, cargo_kt: 180, avgWait: 5.2 },
  { day: 'Fri', vessels: 9, cargo_kt: 135, avgWait: 3.9 },
  { day: 'Sat', vessels: 6, cargo_kt: 85, avgWait: 2.1 },
  { day: 'Sun', vessels: 5, cargo_kt: 72, avgWait: 1.8 },
];

export const MONTHLY_UTILIZATION = [
  { month: 'Oct', utilization: 68 },
  { month: 'Nov', utilization: 72 },
  { month: 'Dec', utilization: 78 },
  { month: 'Jan', utilization: 75 },
  { month: 'Feb', utilization: 81 },
  { month: 'Mar', utilization: 76 },
  { month: 'Apr', utilization: 73 },
];

export const ANALYTICS_COLORS = ['#10b981', '#0ea5e9', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#6366f1'];
