import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import BoltIcon from '@mui/icons-material/Bolt';
import CompressIcon from '@mui/icons-material/Compress';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import type { SummaryItem } from '../api/types';
import { fmtWithUnit } from '../format';
import { statusColor } from '../theme';

interface Props {
  summary: SummaryItem[];
  overallStatus: string;
}

// KPI cards use REAL MetroPT-3 tags only (no invented values):
//   Oil Temperature, Motor Current, Pneumatic Panel Pressure (TP3), System Status.
const KPI_TAGS: { tagName: string; label: string; icon: React.ReactNode }[] = [
  { tagName: 'Oil_temperature', label: 'Oil Temperature', icon: <ThermostatIcon /> },
  { tagName: 'Motor_current', label: 'Motor Current', icon: <BoltIcon /> },
  { tagName: 'TP3', label: 'Panel Pressure (TP3)', icon: <CompressIcon /> },
];

function KpiCard(props: {
  label: string;
  value: string;
  icon: React.ReactNode;
  status?: string;
  accent: string;
}) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Box sx={{ color: props.accent, display: 'flex' }}>{props.icon}</Box>
          <Typography variant="subtitle2" color="text.secondary">
            {props.label}
          </Typography>
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: props.status ? 1 : 0 }}>
          {props.value}
        </Typography>
        {props.status && (
          <Chip
            size="small"
            label={props.status}
            color={statusColor(props.status).color}
            variant="outlined"
          />
        )}
      </CardContent>
    </Card>
  );
}

export default function KpiCards({ summary, overallStatus }: Props) {
  const byName = new Map(summary.map((s) => [s.tag_name, s]));
  const sc = statusColor(overallStatus);

  return (
    <Grid container spacing={2}>
      {KPI_TAGS.map((k) => {
        const s = byName.get(k.tagName);
        return (
          <Grid key={k.tagName} size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiCard
              label={k.label}
              value={s ? fmtWithUnit(s.current, s.unit) : '—'}
              icon={k.icon}
              status={s?.status}
              accent="#1565c0"
            />
          </Grid>
        );
      })}
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        <KpiCard
          label="System Status"
          value={overallStatus}
          icon={<MonitorHeartIcon />}
          accent={sc.hex}
        />
      </Grid>
    </Grid>
  );
}
