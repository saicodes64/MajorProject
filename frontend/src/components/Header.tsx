import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import type { Health, Machine } from '../api/types';
import { fmtTimestamp } from '../format';

interface Props {
  health: Health | null;
  machine: Machine | null;
}

export default function Header({ health, machine }: Props) {
  const connected = health?.status === 'ok' && health?.database === 'connected';

  return (
    <AppBar position="sticky" color="default" sx={{ bgcolor: '#0d1b2a', color: '#fff' }}>
      <Toolbar sx={{ gap: 2, flexWrap: 'wrap' }}>
        <PrecisionManufacturingIcon sx={{ color: '#4fc3f7' }} />
        <Box sx={{ flexGrow: 1, minWidth: 220 }}>
          <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
            Industrial Monitoring Platform
          </Typography>
          <Typography variant="caption" sx={{ color: '#90a4ae' }}>
            {machine ? `${machine.name} · ${machine.machine_code}` : 'No machine selected'}
            {machine?.location ? ` · ${machine.location}` : ''}
          </Typography>
        </Box>

        <Box sx={{ textAlign: 'right', mr: 1 }}>
          <Typography variant="caption" sx={{ color: '#90a4ae', display: 'block' }}>
            Last data timestamp
          </Typography>
          <Typography variant="body2">
            {fmtTimestamp(health?.latest_data_timestamp ?? machine?.latest_data_timestamp)}
          </Typography>
        </Box>

        <Chip
          size="small"
          icon={<FiberManualRecordIcon sx={{ fontSize: 14 }} />}
          label={connected ? 'Connected' : 'Disconnected'}
          color={connected ? 'success' : 'error'}
          variant="filled"
          sx={{ color: '#fff', fontWeight: 600 }}
        />
      </Toolbar>
    </AppBar>
  );
}
