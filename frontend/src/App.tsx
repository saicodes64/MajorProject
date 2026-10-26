import { useCallback, useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import LinearProgress from '@mui/material/LinearProgress';
import dayjs, { Dayjs } from 'dayjs';

import Header from './components/Header';
import KpiCards from './components/KpiCards';
import Controls, { type RangePreset } from './components/Controls';
import TrendChart from './components/TrendChart';
import TagTable from './components/TagTable';

import {
  errorMessage,
  getHealth,
  getMachines,
  getStatistics,
  getSummary,
  getTags,
  getTrend,
} from './api/client';
import type {
  Health,
  Machine,
  Statistics,
  SummaryItem,
  Tag,
  TrendResponse,
} from './api/types';

function overallStatus(summary: SummaryItem[]): string {
  if (summary.some((s) => s.status === 'Critical')) return 'Critical';
  if (summary.some((s) => s.status === 'Warning')) return 'Warning';
  if (summary.length && summary.every((s) => s.status === 'Monitoring')) return 'Monitoring';
  if (summary.some((s) => s.status === 'Normal')) return 'Normal';
  return 'Unknown';
}

// Ranges are anchored to the latest AVAILABLE data timestamp (dataset is 2020).
function computeRange(
  preset: RangePreset,
  anchorISO: string | null,
  customStart: Dayjs | null,
  customEnd: Dayjs | null,
): { start: string; end: string } | null {
  if (preset === 'custom') {
    if (customStart && customEnd && customStart.isBefore(customEnd)) {
      return { start: customStart.toISOString(), end: customEnd.toISOString() };
    }
    return null;
  }
  if (!anchorISO) return null;
  const end = dayjs(anchorISO);
  const hours = preset === '1h' ? 1 : preset === '6h' ? 6 : 24;
  return { start: end.subtract(hours, 'hour').toISOString(), end: end.toISOString() };
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<number | ''>('');
  const [tags, setTags] = useState<Tag[]>([]);
  const [selectedTagId, setSelectedTagId] = useState<number | ''>('');
  const [summary, setSummary] = useState<SummaryItem[]>([]);

  const [preset, setPreset] = useState<RangePreset>('24h');
  const [customStart, setCustomStart] = useState<Dayjs | null>(null);
  const [customEnd, setCustomEnd] = useState<Dayjs | null>(null);

  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);

  const [initLoading, setInitLoading] = useState(true);
  const [initError, setInitError] = useState<string | null>(null);

  const selectedMachine = useMemo(
    () => machines.find((m) => m.id === selectedMachineId) ?? null,
    [machines, selectedMachineId],
  );
  const selectedTag = useMemo(
    () => tags.find((t) => t.id === selectedTagId) ?? null,
    [tags, selectedTagId],
  );
  const anchor =
    health?.latest_data_timestamp ?? selectedMachine?.latest_data_timestamp ?? null;

  // --- Initial load: health + machines ---
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setInitLoading(true);
      setInitError(null);
      try {
        const [h, ms] = await Promise.all([getHealth(), getMachines()]);
        if (cancelled) return;
        setHealth(h);
        setMachines(ms);
        if (ms.length > 0) setSelectedMachineId(ms[0].id);
      } catch (e) {
        if (!cancelled) setInitError(errorMessage(e));
      } finally {
        if (!cancelled) setInitLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Periodic health poll (connection status) ---
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        setHealth(await getHealth());
      } catch {
        setHealth((h) => (h ? { ...h, status: 'error', database: 'unavailable' } : h));
      }
    }, 30000);
    return () => clearInterval(id);
  }, []);

  // --- Load tags + summary when machine changes ---
  const loadMachineData = useCallback(async (machineId: number) => {
    const [ts, sum] = await Promise.all([getTags(machineId), getSummary(machineId)]);
    setTags(ts);
    setSummary(sum);
    setSelectedTagId((prev) => {
      if (prev && ts.some((t) => t.id === prev)) return prev;
      const oil = ts.find((t) => t.tag_name === 'Oil_temperature');
      const analog = ts.find((t) => t.data_type === 'analog');
      return (oil ?? analog ?? ts[0])?.id ?? '';
    });
  }, []);

  useEffect(() => {
    if (selectedMachineId === '') return;
    loadMachineData(selectedMachineId).catch((e) => setInitError(errorMessage(e)));
  }, [selectedMachineId, loadMachineData]);

  // --- Load trend + statistics when machine/tag/range changes ---
  const loadTrend = useCallback(async () => {
    if (selectedMachineId === '' || selectedTagId === '') return;
    const range = computeRange(preset, anchor, customStart, customEnd);
    if (!range) {
      setTrendError('Please choose a valid start and end time (start must be before end).');
      setTrend(null);
      setStats(null);
      return;
    }
    setTrendLoading(true);
    setTrendError(null);
    try {
      const [tr, st] = await Promise.all([
        getTrend({
          machineId: selectedMachineId,
          tagId: selectedTagId,
          startTime: range.start,
          endTime: range.end,
        }),
        getStatistics({
          machineId: selectedMachineId,
          tagId: selectedTagId,
          startTime: range.start,
          endTime: range.end,
        }),
      ]);
      setTrend(tr);
      setStats(st);
    } catch (e) {
      setTrendError(errorMessage(e));
      setTrend(null);
      setStats(null);
    } finally {
      setTrendLoading(false);
    }
  }, [selectedMachineId, selectedTagId, preset, anchor, customStart, customEnd]);

  useEffect(() => {
    loadTrend();
  }, [loadTrend]);

  const handlePresetChange = (p: RangePreset) => {
    if (p === 'custom' && (!customStart || !customEnd) && anchor) {
      setCustomEnd(dayjs(anchor));
      setCustomStart(dayjs(anchor).subtract(24, 'hour'));
    }
    setPreset(p);
  };

  const refreshAll = () => {
    getHealth().then(setHealth).catch(() => {});
    if (selectedMachineId !== '') loadMachineData(selectedMachineId).catch(() => {});
    loadTrend();
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header health={health} machine={selectedMachine} />
      {initLoading && <LinearProgress />}

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Stack spacing={2}>
          {initError && <Alert severity="error">Failed to load: {initError}</Alert>}

          <KpiCards summary={summary} overallStatus={overallStatus(summary)} />

          <Controls
            machines={machines}
            selectedMachineId={selectedMachineId}
            onMachineChange={setSelectedMachineId}
            tags={tags}
            selectedTagId={selectedTagId}
            onTagChange={setSelectedTagId}
            preset={preset}
            onPresetChange={handlePresetChange}
            customStart={customStart}
            customEnd={customEnd}
            onCustomStart={setCustomStart}
            onCustomEnd={setCustomEnd}
            dataMin={null}
            dataMax={anchor}
            onRefresh={refreshAll}
          />

          <TrendChart
            trend={trend}
            stats={stats}
            loading={trendLoading}
            error={trendError}
            isDigital={selectedTag?.data_type === 'digital'}
          />

          <TagTable
            summary={summary}
            selectedTagId={selectedTagId}
            onSelectTag={setSelectedTagId}
          />
        </Stack>
      </Container>
    </Box>
  );
}
