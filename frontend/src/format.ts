// Small shared formatting helpers.

export function fmtNumber(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '—';
  return v.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtWithUnit(
  v: number | null | undefined,
  unit: string | null | undefined,
  digits = 2,
): string {
  const n = fmtNumber(v, digits);
  if (n === '—') return n;
  return unit ? `${n} ${unit}` : n;
}

// The dataset is historical (2020). Show the real data timestamp clearly.
export function fmtTimestamp(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Digital tags are 0/1 states; show them as ON/OFF for readability.
export function isDigital(dataType: string | null | undefined): boolean {
  return dataType === 'digital';
}
