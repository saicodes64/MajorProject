import { createTheme } from '@mui/material/styles';

// Clean, readable industrial theme. Light surface, calm blues, clear status colors.
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1565c0' },
    secondary: { main: '#00838f' },
    background: { default: '#f4f6f8', paper: '#ffffff' },
  },
  typography: {
    fontFamily:
      '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h6: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { root: { border: '1px solid #e3e8ee' } } },
    MuiCard: { styleOverrides: { root: { border: '1px solid #e3e8ee' } } },
  },
});

// Map a backend status string to an MUI color + hex (shared by chips/cards).
export function statusColor(status: string): {
  color: 'success' | 'warning' | 'error' | 'info' | 'default';
  hex: string;
} {
  switch (status) {
    case 'Normal':
      return { color: 'success', hex: '#2e7d32' };
    case 'Warning':
      return { color: 'warning', hex: '#ed6c02' };
    case 'Critical':
      return { color: 'error', hex: '#d32f2f' };
    case 'Monitoring':
      return { color: 'info', hex: '#0288d1' };
    default:
      return { color: 'default', hex: '#607d8b' };
  }
}
