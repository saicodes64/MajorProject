// Single axios client for the FastAPI backend. All data access goes through here;
// React never touches the database directly.
import axios from 'axios';
import type {
  Health,
  Machine,
  Statistics,
  SummaryItem,
  Tag,
  TrendResponse,
} from './types';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const http = axios.create({ baseURL, timeout: 30000 });

export async function getHealth(): Promise<Health> {
  const { data } = await http.get<Health>('/api/health');
  return data;
}

export async function getMachines(): Promise<Machine[]> {
  const { data } = await http.get<Machine[]>('/api/machines');
  return data;
}

export async function getTags(machineId?: number): Promise<Tag[]> {
  const { data } = await http.get<Tag[]>('/api/tags', {
    params: machineId != null ? { machine_id: machineId } : undefined,
  });
  return data;
}

export async function getSummary(machineId: number): Promise<SummaryItem[]> {
  const { data } = await http.get<SummaryItem[]>('/api/readings/summary', {
    params: { machine_id: machineId },
  });
  return data;
}

export async function getTrend(params: {
  machineId: number;
  tagId: number;
  startTime: string; // ISO
  endTime: string; // ISO
  interval?: string;
}): Promise<TrendResponse> {
  const { data } = await http.get<TrendResponse>('/api/readings/trend', {
    params: {
      machine_id: params.machineId,
      tag_id: params.tagId,
      start_time: params.startTime,
      end_time: params.endTime,
      interval: params.interval,
    },
  });
  return data;
}

export async function getStatistics(params: {
  machineId: number;
  tagId: number;
  startTime?: string;
  endTime?: string;
}): Promise<Statistics> {
  const { data } = await http.get<Statistics>('/api/readings/statistics', {
    params: {
      machine_id: params.machineId,
      tag_id: params.tagId,
      start_time: params.startTime,
      end_time: params.endTime,
    },
  });
  return data;
}

// Normalise any thrown error into a readable message for the UI.
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.response) {
      const detail = (err.response.data as { detail?: unknown })?.detail;
      if (typeof detail === 'string') return detail;
      return `Request failed (${err.response.status})`;
    }
    if (err.request) return 'Cannot reach the API server.';
  }
  return err instanceof Error ? err.message : 'Unknown error';
}
