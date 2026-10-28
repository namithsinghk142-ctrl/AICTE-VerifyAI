import React from 'react';
import type { FindingSeverity } from '../../types';
import { SEVERITY_CONFIG } from '../../utils/helpers';

interface SeverityBadgeProps {
  severity: FindingSeverity | string;
  showIcon?: boolean;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  showIcon = true,
}) => {
  const raw = (severity || 'minor').toString().toLowerCase();
  let key: FindingSeverity = 'minor';
  if (raw === 'critical') {
    key = 'critical';
  } else if (raw === 'major' || raw === 'high' || raw === 'medium') {
    key = 'major';
  } else if (raw === 'minor' || raw === 'low') {
    key = 'minor';
  } else if (raw === 'info') {
    key = 'info';
  }

  const cfg = SEVERITY_CONFIG[key] ?? SEVERITY_CONFIG.minor;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      {showIcon && <span className="text-[10px]">{cfg.icon}</span>}
      {cfg.label}
    </span>
  );
};
