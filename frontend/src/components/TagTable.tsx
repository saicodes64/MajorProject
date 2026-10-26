import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import Link from '@mui/material/Link';
import type { SummaryItem } from '../api/types';
import { fmtNumber, isDigital } from '../format';
import { statusColor } from '../theme';

interface Props {
  summary: SummaryItem[];
  selectedTagId: number | '';
  onSelectTag: (tagId: number) => void;
}

// Digital 0/1 shown as OFF/ON for the "Current" column; analog shows the number.
function currentDisplay(s: SummaryItem): string {
  if (s.current == null) return '—';
  if (isDigital(s.data_type)) return s.current >= 0.5 ? 'ON (1)' : 'OFF (0)';
  return fmtNumber(s.current);
}

export default function TagTable({ summary, selectedTagId, onSelectTag }: Props) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Tags — current values & statistics
      </Typography>
      <TableContainer sx={{ maxHeight: 440 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Tag</TableCell>
              <TableCell>Unit</TableCell>
              <TableCell align="right">Current</TableCell>
              <TableCell align="right">Min</TableCell>
              <TableCell align="right">Max</TableCell>
              <TableCell align="right">Average</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {summary.map((s) => {
              const selected = s.tag_id === selectedTagId;
              return (
                <TableRow
                  key={s.tag_id}
                  hover
                  selected={selected}
                  sx={{ cursor: 'pointer' }}
                  onClick={() => onSelectTag(s.tag_id)}
                >
                  <TableCell>
                    <Link
                      component="button"
                      underline={selected ? 'always' : 'hover'}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTag(s.tag_id);
                      }}
                      sx={{ fontWeight: selected ? 700 : 500, textAlign: 'left' }}
                    >
                      {s.display_name ?? s.tag_name}
                    </Link>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      {s.tag_name} · {s.data_type}
                    </Typography>
                  </TableCell>
                  <TableCell>{s.unit ?? '—'}</TableCell>
                  <TableCell align="right">{currentDisplay(s)}</TableCell>
                  <TableCell align="right">{fmtNumber(s.minimum)}</TableCell>
                  <TableCell align="right">{fmtNumber(s.maximum)}</TableCell>
                  <TableCell align="right">{fmtNumber(s.average)}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={s.status}
                      color={statusColor(s.status).color}
                      variant="outlined"
                    />
                  </TableCell>
                </TableRow>
              );
            })}
            {summary.length === 0 && (
              <TableRow>
                <TableCell colSpan={7}>
                  <Box sx={{ py: 3, textAlign: 'center' }}>
                    <Typography color="text.secondary">No tags available.</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
