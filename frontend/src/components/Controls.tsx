import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import RefreshIcon from '@mui/icons-material/Refresh';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import dayjs, { Dayjs } from 'dayjs';
import type { Machine, Tag } from '../api/types';

export type RangePreset = '1h' | '6h' | '24h' | 'custom';

interface Props {
  machines: Machine[];
  selectedMachineId: number | '';
  onMachineChange: (id: number) => void;
  tags: Tag[];
  selectedTagId: number | '';
  onTagChange: (id: number) => void;
  preset: RangePreset;
  onPresetChange: (p: RangePreset) => void;
  customStart: Dayjs | null;
  customEnd: Dayjs | null;
  onCustomStart: (d: Dayjs | null) => void;
  onCustomEnd: (d: Dayjs | null) => void;
  dataMin: string | null; // earliest available data (for picker bounds)
  dataMax: string | null; // latest available data
  onRefresh: () => void;
}

export default function Controls(props: Props) {
  const minDate = props.dataMin ? dayjs(props.dataMin) : undefined;
  const maxDate = props.dataMax ? dayjs(props.dataMax) : undefined;

  return (
    <Paper sx={{ p: 2 }}>
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          flexWrap: 'wrap',
          alignItems: 'flex-end',
        }}
      >
        <TextField
          select
          label="Machine"
          size="small"
          value={props.selectedMachineId}
          onChange={(e) => props.onMachineChange(Number(e.target.value))}
          sx={{ minWidth: 220 }}
        >
          {props.machines.map((m) => (
            <MenuItem key={m.id} value={m.id}>
              {m.name} ({m.machine_code})
            </MenuItem>
          ))}
        </TextField>

        <TextField
          select
          label="Tag / Signal"
          size="small"
          value={props.selectedTagId}
          onChange={(e) => props.onTagChange(Number(e.target.value))}
          sx={{ minWidth: 260 }}
        >
          {props.tags.map((t) => (
            <MenuItem key={t.id} value={t.id}>
              {t.display_name ?? t.tag_name}
              {t.unit ? ` (${t.unit})` : ''}
            </MenuItem>
          ))}
        </TextField>

        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            Time range
          </Typography>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={props.preset}
            onChange={(_, v) => v && props.onPresetChange(v as RangePreset)}
          >
            <ToggleButton value="1h">Last 1h</ToggleButton>
            <ToggleButton value="6h">Last 6h</ToggleButton>
            <ToggleButton value="24h">Last 24h</ToggleButton>
            <ToggleButton value="custom">Custom</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {props.preset === 'custom' && (
          <>
            <DateTimePicker
              label="Start"
              value={props.customStart}
              onChange={props.onCustomStart}
              minDateTime={minDate}
              maxDateTime={maxDate}
              slotProps={{ textField: { size: 'small' } }}
            />
            <DateTimePicker
              label="End"
              value={props.customEnd}
              onChange={props.onCustomEnd}
              minDateTime={minDate}
              maxDateTime={maxDate}
              slotProps={{ textField: { size: 'small' } }}
            />
          </>
        )}

        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="outlined"
          size="medium"
          startIcon={<RefreshIcon />}
          onClick={props.onRefresh}
        >
          Refresh
        </Button>
      </Box>
      {maxDate && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Note: MetroPT-3 is historical data (Feb–Sep 2020); time ranges are relative to
          the latest available reading ({maxDate.format('DD MMM YYYY HH:mm')}).
        </Typography>
      )}
    </Paper>
  );
}
