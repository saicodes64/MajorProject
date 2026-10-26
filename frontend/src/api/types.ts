// TypeScript types mirroring the FastAPI response schemas.
// Keep in sync with backend/app/schemas/*.

export interface Health {
  status: string;
  database: string;
  timescaledb: boolean;
  reading_count: number | null;
  latest_data_timestamp: string | null;
  server_time: string;
}

export interface Machine {
  id: number;
  machine_code: string;
  name: string;
  machine_type: string | null;
  location: string | null;
  description: string | null;
  created_at: string | null;
  tag_count: number | null;
  latest_data_timestamp: string | null;
}

export interface Tag {
  id: number;
  machine_id: number;
  tag_name: string;
  display_name: string | null;
  data_type: string | null; // "analog" | "digital"
  unit: string | null;
  description: string | null;
  created_at: string | null;
}

export interface SummaryItem {
  tag_id: number;
  tag_name: string;
  display_name: string | null;
  data_type: string | null;
  unit: string | null;
  current: number | null;
  current_timestamp: string | null;
  minimum: number | null;
  maximum: number | null;
  average: number | null;
  stddev: number | null;
  count: number;
  status: string;
}

export interface TrendPoint {
  timestamp: string;
  value: number | null;
  min: number | null;
  max: number | null;
}

export interface TrendResponse {
  machine_id: number;
  tag_id: number;
  tag_name: string;
  display_name: string | null;
  unit: string | null;
  start_time: string;
  end_time: string;
  aggregated: boolean;
  interval: string | null;
  point_count: number;
  points: TrendPoint[];
}

export interface Statistics {
  machine_id: number;
  tag_id: number;
  tag_name: string;
  display_name: string | null;
  unit: string | null;
  start_time: string | null;
  end_time: string | null;
  current: number | null;
  current_timestamp: string | null;
  minimum: number | null;
  maximum: number | null;
  average: number | null;
  stddev: number | null;
  count: number;
  status: string;
}
