import React from 'react';
import type { DatasetMode } from '../../types';
import { Database, FlaskConical, ShieldCheck, Info } from 'lucide-react';

interface DatasetModeToggleProps {
  mode: DatasetMode;
  onChange: (mode: DatasetMode) => void;
  referenceCount?: number;
  syntheticCount?: number;
}

export const DatasetModeToggle: React.FC<DatasetModeToggleProps> = ({
  mode,
  onChange,
  referenceCount = 10,
  syntheticCount = 30,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        padding: '10px 14px',
        background: '#ffffff',
        border: '1px solid #ECD9E2',
        borderRadius: '14px',
        boxShadow: '0 1px 3px rgba(53, 29, 49, 0.04)',
      }}
    >
      {/* Left: Interactive Button Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: '#896F81',
            marginRight: '4px',
          }}
        >
          Data Scope:
        </span>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: '#FFF5F7',
            padding: '3px',
            borderRadius: '10px',
            border: '1px solid #F3E0E9',
          }}
          role="group"
          aria-label="Dataset Mode Toggle"
        >
          {/* Real Data Option */}
          <button
            type="button"
            id="toggle-real-data-mode"
            onClick={() => onChange('real')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '7px',
              fontSize: '12px',
              fontWeight: mode === 'real' ? 700 : 500,
              cursor: 'pointer',
              border: 'none',
              transition: 'all 0.15s ease',
              background:
                mode === 'real'
                  ? 'linear-gradient(135deg, #8A2F5B 0%, #AA4777 100%)'
                  : 'transparent',
              color: mode === 'real' ? '#ffffff' : '#5A3D52',
              boxShadow:
                mode === 'real' ? '0 2px 6px rgba(138, 47, 91, 0.25)' : 'none',
            }}
          >
            <Database size={13} strokeWidth={mode === 'real' ? 2.2 : 1.8} />
            <span>Real Data</span>
            <span
              style={{
                fontSize: '10px',
                padding: '1px 5px',
                borderRadius: '5px',
                background: mode === 'real' ? 'rgba(255,255,255,0.22)' : '#ECD9E2',
                color: mode === 'real' ? '#ffffff' : '#8A2F5B',
                fontWeight: 700,
              }}
            >
              {referenceCount} ref
            </span>
          </button>

          {/* Synthetic Data Option */}
          <button
            type="button"
            id="toggle-synthetic-data-mode"
            onClick={() => onChange('synthetic')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '7px',
              fontSize: '12px',
              fontWeight: mode === 'synthetic' ? 700 : 500,
              cursor: 'pointer',
              border: 'none',
              transition: 'all 0.15s ease',
              background:
                mode === 'synthetic'
                  ? 'linear-gradient(135deg, #351D31 0%, #4D2B47 100%)'
                  : 'transparent',
              color: mode === 'synthetic' ? '#ffffff' : '#5A3D52',
              boxShadow:
                mode === 'synthetic' ? '0 2px 6px rgba(53, 29, 49, 0.25)' : 'none',
            }}
          >
            <FlaskConical size={13} strokeWidth={mode === 'synthetic' ? 2.2 : 1.8} />
            <span>Synthetic Data</span>
            <span
              style={{
                fontSize: '10px',
                padding: '1px 5px',
                borderRadius: '5px',
                background:
                  mode === 'synthetic' ? 'rgba(255,255,255,0.22)' : '#ECD9E2',
                color: mode === 'synthetic' ? '#ffffff' : '#351D31',
                fontWeight: 700,
              }}
            >
              {syntheticCount} demo
            </span>
          </button>
        </div>
      </div>

      {/* Right: Explicit Status & Classification Notice */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {mode === 'real' ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#F0FDF4',
              border: '1px solid #BBF7D0',
              padding: '4px 10px',
              borderRadius: '8px',
            }}
          >
            <ShieldCheck size={13} color="#16A34A" strokeWidth={2} />
            <span style={{ fontSize: '11px', color: '#15803D', fontWeight: 600 }}>
              Verified Public Reference Directory · AICTE & AISHE 2024–2025
            </span>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#FFF5F7',
              border: '1px solid #F3D4E2',
              padding: '4px 10px',
              borderRadius: '8px',
            }}
          >
            <Info size={13} color="#C14E83" strokeWidth={2} />
            <span style={{ fontSize: '11px', color: '#8A2F5B', fontWeight: 600 }}>
              Synthetic Demo Dataset · 30 Simulated Institutions (Demo Timeline 2026)
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
