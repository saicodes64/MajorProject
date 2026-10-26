import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import dayjs from 'dayjs';
import type { Statistics, TrendResponse } from '../api/types';
import { fmtNumber } from '../format';

interface Props {
  trend: TrendResponse | null;
  stats: Statistics | null;
  loading: boolean;
  error: string | null;
  isDigital: boolean;
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ minWidth: 92 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {label}
      </Typography>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function TrendChart({ trend, stats, loading, error, isDigital }: Props) {
  const unit = trend?.unit ?? stats?.unit ?? '';
  const title = trend?.display_name ?? trend?.tag_name ?? 'Trend';

  const data =
    trend?.points.map((p) => ({
      t: dayjs(p.timestamp).valueOf(),
      value: p.value,
    })) ?? [];

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
        <Typography variant="h6">{title}</Typography>
        {unit && <Chip size="small" label={unit} variant="outlined" />}
        {trend?.aggregated && (
          <Chip
            size="small"
            color="info"
            variant="outlined"
            label={`downsampled · ${trend.interval} buckets`}
          />
        )}
        <Box sx={{ flexGrow: 1 }} />
        {trend && (
          <Typography variant="caption" color="text.secondary">
            {trend.point_count.toLocaleString()} points
          </Typography>
        )}
      </Box>

      {/* Statistics strip for the selected tag + range */}
      {stats && !loading && !error && (
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2 }}>
          <StatBox label="Current" value={fmtNumber(stats.current)} />
          <StatBox label="Min" value={fmtNumber(stats.minimum)} />
          <StatBox label="Max" value={fmtNumber(stats.maximum)} />
          <StatBox label="Average" value={fmtNumber(stats.average)} />
          <StatBox label="Std Dev" value={fmtNumber(stats.stddev)} />
          <StatBox label="Count" value={stats.count.toLocaleString()} />
        </Box>
      )}

      <Box sx={{ height: 360, position: 'relative' }}>
        {loading && (
          <Box sx={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        )}

        {!loading && error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && data.length === 0 && (
          <Box sx={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
            <Typography color="text.secondary">
              No data in the selected time range.
            </Typography>
          </Box>
        )}

        {!loading && !error && data.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" />
              <XAxis
                dataKey="t"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(v) => dayjs(v).format('DD MMM HH:mm')}
                minTickGap={60}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                width={64}
                tick={{ fontSize: 12 }}
                domain={isDigital ? [0, 1] : ['auto', 'auto']}
                allowDecimals={!isDigital}
              />
              <Tooltip
                labelFormatter={(v) => dayjs(Number(v)).format('DD MMM YYYY HH:mm')}
                formatter={(value) => {
                  const n = typeof value === 'number' ? value : Number(value);
                  return [`${fmtNumber(n)}${unit ? ' ' + unit : ''}`, title];
                }}
              />
              <Line
                type={isDigital ? 'stepAfter' : 'monotone'}
                dataKey="value"
                stroke="#1565c0"
                strokeWidth={1.6}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Box>
    </Paper>
  );
}
