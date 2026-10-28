import React, { useState } from 'react';
import type { CrossDocComparisonField } from '../../types';
import {
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Info,
  RefreshCw,
  HelpCircle,
  XCircle,
} from 'lucide-react';
import { Button } from '../ui/Button';

interface CrossDocComparisonViewProps {
  comparisons?: CrossDocComparisonField[];
  onSelectDocumentByName?: (documentName: string) => void;
  onRefreshChecks?: () => Promise<void>;
  isRefreshing?: boolean;
}

type Verdict = 'MATCH' | 'MISMATCH' | 'MISSING' | 'UNABLE_TO_COMPARE' | 'NEEDS_REVIEW';

/** Derive the overall verdict for a field from the first entry that has one, or from hasDiscrepancy. */
function deriveVerdict(field: CrossDocComparisonField): Verdict {
  // Try to read from the first entry with a verdict
  const entryWithVerdict = field.entries.find((e) => e.verdict);
  if (entryWithVerdict?.verdict) return entryWithVerdict.verdict as Verdict;

  // Fallback: check if any entry is MISSING
  const hasMissing = field.entries.some(
    (e) => e.verdict === 'MISSING' || e.extractedValue === '— (not extracted)'
  );
  if (hasMissing && field.hasDiscrepancy) return 'MISSING';

  return field.hasDiscrepancy ? 'MISMATCH' : 'MATCH';
}

const VERDICT_CONFIG: Record<
  Verdict,
  {
    bg: string;
    border: string;
    text: string;
    label: string;
    icon: React.ReactNode;
    tabDot?: string;
  }
> = {
  MATCH: {
    bg: '#DEF7EC',
    border: '#B4E7D0',
    text: '#065F46',
    label: 'MATCH',
    icon: <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />,
  },
  MISMATCH: {
    bg: '#FEF3C7',
    border: '#FDE68A',
    text: '#92400E',
    label: 'MISMATCH',
    icon: <AlertTriangle size={16} className="text-amber-600 shrink-0" />,
    tabDot: 'bg-amber-500',
  },
  MISSING: {
    bg: '#FFF5F7',
    border: '#ECD9E2',
    text: '#7F1D4E',
    label: 'MISSING',
    icon: <XCircle size={16} className="text-[#C14E83] shrink-0" />,
    tabDot: 'bg-[#C14E83]',
  },
  UNABLE_TO_COMPARE: {
    bg: '#EFF6FF',
    border: '#BFDBFE',
    text: '#1E3A5F',
    label: 'UNABLE TO COMPARE',
    icon: <HelpCircle size={16} className="text-blue-500 shrink-0" />,
  },
  NEEDS_REVIEW: {
    bg: '#FAF5FF',
    border: '#E9D5FF',
    text: '#581C87',
    label: 'NEEDS REVIEW',
    icon: <AlertTriangle size={16} className="text-purple-600 shrink-0" />,
    tabDot: 'bg-purple-600',
  },
};

const ENTRY_VERDICT_BADGE: Record<string, string> = {
  MATCH: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
  MISMATCH: 'bg-amber-100 text-amber-800 border border-amber-300',
  MISSING: 'bg-[#FFF5F7] text-[#7F1D4E] border border-[#ECD9E2]',
  UNABLE_TO_COMPARE: 'bg-blue-50 text-blue-800 border border-blue-200',
  NEEDS_REVIEW: 'bg-purple-100 text-purple-800 border border-purple-200',
};

const ENTRY_VALUE_STYLE: Record<string, string> = {
  MATCH: 'bg-slate-100 text-slate-800 font-medium',
  MISMATCH: 'bg-amber-100 text-amber-900 font-bold border border-amber-300',
  MISSING: 'bg-[#FFF5F7] text-[#7F1D4E] font-semibold border border-[#ECD9E2] italic',
  UNABLE_TO_COMPARE: 'bg-blue-50 text-blue-900 font-medium border border-blue-200',
  NEEDS_REVIEW: 'bg-purple-50 text-purple-900 font-semibold border border-purple-200',
};

export const CrossDocComparisonView: React.FC<CrossDocComparisonViewProps> = ({
  comparisons = [],
  onSelectDocumentByName,
  onRefreshChecks,
  isRefreshing = false,
}) => {
  const [activeFieldIndex, setActiveFieldIndex] = useState<number>(0);

  const mismatches = comparisons.filter((c) => c.hasDiscrepancy).length;
  const unableCount = comparisons.filter((c) => {
    const v = deriveVerdict(c);
    return v === 'UNABLE_TO_COMPARE';
  }).length;

  if (comparisons.length === 0) {
    return (
      <div
        className="rounded-xl border p-8 text-center text-sm flex flex-col items-center gap-4"
        style={{
          background: '#FFFFFF',
          borderColor: 'var(--border-soft)',
          color: 'var(--text-secondary)',
        }}
      >
        <GitCompare size={32} className="text-slate-300" />
        <div>
          <p className="font-semibold text-slate-600 mb-1">No reconciliation data available</p>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Upload at least two documents with extractable fields (institution name, survey number,
            land area, application ID, etc.) and the engine will automatically compare them.
          </p>
        </div>
        {onRefreshChecks && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefreshChecks}
            loading={isRefreshing}
            icon={<RefreshCw size={13} />}
          >
            Run Checks Now
          </Button>
        )}
      </div>
    );
  }

  const currentField = comparisons[activeFieldIndex] ?? comparisons[0];
  const currentVerdict = deriveVerdict(currentField);
  const verdictConfig = VERDICT_CONFIG[currentVerdict] ?? VERDICT_CONFIG.MATCH;

  return (
    <div
      className="rounded-xl border shadow-xs overflow-hidden flex flex-col"
      style={{
        background: '#FFFFFF',
        borderColor: 'var(--border-soft)',
      }}
    >
      {/* Header - Cherry Blossom Noir */}
      <div
        className="p-5 border-b text-white"
        style={{
          background: 'linear-gradient(135deg, #1A0D18 0%, #351D31 60%, #55223F 100%)',
          borderBottom: '1px solid #55223F',
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <GitCompare size={18} className="text-[#C14E83]" />
            <h3 className="font-bold text-sm md:text-base tracking-tight">
              Cross-Document Entity & Parameter Reconciliation
            </h3>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Summary pills */}
            <span
              className="text-[11px] px-2.5 py-0.5 rounded-full font-mono font-medium"
              style={{
                background: 'rgba(193, 78, 131, 0.25)',
                color: '#F8E5ED',
                border: '1px solid rgba(193, 78, 131, 0.4)',
              }}
            >
              {comparisons.length} field{comparisons.length !== 1 ? 's' : ''} checked
            </span>
            {mismatches > 0 && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-200 border border-amber-500/30">
                {mismatches} discrepanc{mismatches !== 1 ? 'ies' : 'y'}
              </span>
            )}
            {onRefreshChecks && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefreshChecks}
                loading={isRefreshing}
                icon={<RefreshCw size={11} />}
                className="!text-[10px] !py-0.5 !px-2.5 !border-white/20 !text-white/80 hover:!text-white hover:!bg-white/10"
              >
                Refresh
              </Button>
            )}
          </div>
        </div>
        <p className="text-xs mt-1.5 leading-relaxed max-w-2xl" style={{ color: '#F8E5ED' }}>
          Automated comparison of extracted parameter values across independent statutory
          instruments. Values are normalised for whitespace, case, abbreviations and units before
          comparison.
        </p>
      </div>

      {/* Field Selector Tabs */}
      <div
        className="flex border-b overflow-x-auto text-xs"
        style={{
          background: 'var(--surface-alt)',
          borderColor: 'var(--border-soft)',
        }}
      >
        {comparisons.map((comp, idx) => {
          const isActive = idx === activeFieldIndex;
          const v = deriveVerdict(comp);
          const cfg = VERDICT_CONFIG[v] ?? VERDICT_CONFIG.MATCH;
          return (
            <button
              key={`${comp.fieldName}-${idx}`}
              type="button"
              onClick={() => setActiveFieldIndex(idx)}
              className="px-5 py-3 font-semibold whitespace-nowrap flex items-center gap-2 border-b-2 transition-all cursor-pointer"
              style={{
                borderColor: isActive ? '#C14E83' : 'transparent',
                color: isActive ? '#351D31' : '#896F81',
                background: isActive ? '#FFFFFF' : 'transparent',
                boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.03)' : undefined,
              }}
            >
              {v === 'MATCH' ? (
                <CheckCircle2 size={13} className="text-emerald-600" />
              ) : v === 'MISMATCH' ? (
                <AlertTriangle size={13} className="text-amber-600" />
              ) : v === 'MISSING' ? (
                <XCircle size={13} className="text-[#C14E83]" />
              ) : v === 'NEEDS_REVIEW' ? (
                <AlertTriangle size={13} className="text-purple-600" />
              ) : (
                <HelpCircle size={13} className="text-blue-500" />
              )}
              <span>{comp.fieldName}</span>
              {cfg.tabDot && (
                <span className={`w-1.5 h-1.5 rounded-full inline-block ${cfg.tabDot}`} />
              )}
            </button>
          );
        })}
      </div>

      {/* Field Details & Table */}
      <div className="p-6 flex flex-col gap-5">
        {/* Field Status & Recommendation Banner */}
        <div
          className="p-4 rounded-xl border flex flex-col md:flex-row gap-4 justify-between items-start"
          style={{
            background: verdictConfig.bg,
            borderColor: verdictConfig.border,
            color: verdictConfig.text,
          }}
        >
          <div className="flex gap-3">
            <div className="mt-0.5">{verdictConfig.icon}</div>
            <div>
              <div className="font-bold text-sm mb-0.5 flex items-center gap-2">
                <span
                  className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border"
                  style={{
                    background: 'rgba(255,255,255,0.6)',
                    borderColor: verdictConfig.border,
                    color: verdictConfig.text,
                  }}
                >
                  {verdictConfig.label}
                </span>
                <span>{currentField.statusText.replace(/^[✓⚠◌?]\s*[A-Z_\s]+\s*—\s*/, '')}</span>
              </div>
              <p className="text-xs leading-relaxed opacity-95 mt-0.5">
                {currentField.description}
              </p>
              <div
                className="mt-2.5 text-xs font-medium p-3 rounded-lg border"
                style={{
                  background: '#FFFFFF',
                  borderColor: verdictConfig.border,
                  color: '#351D31',
                }}
              >
                <span className="font-bold text-[#8A2F5B]">Scrutiny Guidance: </span>
                {currentField.humanReviewRecommendation}
              </div>
            </div>
          </div>
        </div>

        {/* Comparison Matrix Table */}
        <div
          className="rounded-xl overflow-hidden shadow-xs border"
          style={{ borderColor: 'var(--border-soft)' }}
        >
          <table className="w-full text-xs text-left">
            <thead
              className="border-b text-[11px] font-semibold uppercase tracking-wider"
              style={{
                background: 'var(--surface-alt)',
                borderColor: 'var(--border-soft)',
                color: '#896F81',
              }}
            >
              <tr>
                <th className="px-4 py-3 w-[28%]">Submitted Instrument</th>
                <th className="px-3 py-3 w-[16%]">Type</th>
                <th className="px-4 py-3 w-[36%]">Extracted Parameter Value</th>
                <th className="px-3 py-3 w-[10%] text-center">Confidence</th>
                <th className="px-3 py-3 w-[10%] text-center">Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--border-soft)' }}>
              {currentField.entries.map((entry, idx) => {
                const entryVerdict: string = entry.verdict ?? (entry.isMismatched ? 'MISMATCH' : 'MATCH');
                const badgeCls = ENTRY_VERDICT_BADGE[entryVerdict] ?? ENTRY_VERDICT_BADGE.MATCH;
                const valueCls = ENTRY_VALUE_STYLE[entryVerdict] ?? ENTRY_VALUE_STYLE.MATCH;
                const confidencePct = Math.min(100, Math.round(entry.confidenceScore > 1 ? entry.confidenceScore : (entry.confidenceScore ?? 0) * 100));
                return (
                  <tr
                    key={idx}
                    className={
                      entryVerdict === 'MISMATCH'
                        ? 'bg-amber-50/50'
                        : entryVerdict === 'MISSING'
                        ? 'bg-[#FFF5F7]/40'
                        : entryVerdict === 'UNABLE_TO_COMPARE'
                        ? 'bg-blue-50/30'
                        : entryVerdict === 'NEEDS_REVIEW'
                        ? 'bg-purple-50/30'
                        : 'bg-white hover:bg-slate-50/60'
                    }
                  >
                    <td className="px-4 py-3.5">
                      <button
                        type="button"
                        onClick={() => onSelectDocumentByName?.(entry.documentName)}
                        className="flex items-center gap-2 text-left hover:text-[#C14E83] transition-colors group cursor-pointer"
                        title="Inspect this document in viewer"
                      >
                        <FileText
                          size={14}
                          className={
                            entryVerdict === 'MISMATCH'
                              ? 'text-amber-600'
                              : entryVerdict === 'MISSING'
                              ? 'text-[#C14E83]'
                              : entryVerdict === 'NEEDS_REVIEW'
                              ? 'text-purple-600'
                              : 'text-[#C14E83]'
                          }
                        />
                        <span className="font-semibold text-slate-800 font-mono text-xs group-hover:underline">
                          {entry.documentName}
                        </span>
                      </button>
                    </td>
                    <td className="px-3 py-3.5 text-slate-600 font-medium">{entry.documentType}</td>
                    <td className="px-4 py-3.5">
                      <span
                        className={`inline-block font-mono px-2 py-1 rounded text-xs leading-relaxed ${valueCls}`}
                      >
                        {entry.extractedValue}
                      </span>
                      {entry.textSnippet && (
                        <p className="text-[10px] text-slate-500 mt-1 italic font-sans max-w-md line-clamp-2" title={entry.textSnippet}>
                          Context: "{entry.textSnippet}"
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-3.5 text-center">
                      {entry.sourcePage > 0 && confidencePct > 0 ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <span className="text-[10px] font-mono font-bold text-slate-700">
                            {confidencePct}%
                          </span>
                          <div className="w-10 h-1 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${confidencePct}%`,
                                background:
                                  confidencePct >= 80
                                    ? '#059669'
                                    : confidencePct >= 60
                                    ? '#D97706'
                                    : '#DC2626',
                              }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3.5 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${badgeCls}`}
                      >
                        {entryVerdict === 'UNABLE_TO_COMPARE' ? 'N/A' : entryVerdict}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Counts summary */}
        {(mismatches > 0 || unableCount > 0) && (
          <div className="flex flex-wrap gap-2 text-[11px]">
            {mismatches > 0 && (
              <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                <AlertTriangle size={11} />
                {mismatches} field{mismatches !== 1 ? 's' : ''} with discrepancies
              </span>
            )}
            {unableCount > 0 && (
              <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-800 border border-blue-200 font-semibold">
                <HelpCircle size={11} />
                {unableCount} field{unableCount !== 1 ? 's' : ''} require manual verification
              </span>
            )}
          </div>
        )}

        {/* Disclaimer */}
        <div
          className="p-3.5 rounded-xl border flex items-start gap-2.5 text-[11px]"
          style={{
            background: 'var(--surface-alt)',
            borderColor: 'var(--border-soft)',
            color: '#896F81',
          }}
        >
          <Info size={14} className="text-[#AA4777] mt-0.5 shrink-0" />
          <p className="leading-relaxed">
            <span className="font-bold text-[#351D31]">Reconciliation Advisory: </span>
            Comparison uses normalised values — whitespace, case, common abbreviations, and unit
            conversions are accounted for. MISMATCH and MISSING results are matters for human
            reviewer verification, not legal judgments or forgery assertions. UNABLE TO COMPARE
            means the engine could not reliably convert values to a common format.
          </p>
        </div>
      </div>
    </div>
  );
};
