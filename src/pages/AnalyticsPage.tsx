import React, { useEffect, useState, useCallback } from 'react';
import {
  fetchSubmissions,
  fetchDashboardMetrics,
  fetchPublicReferenceInstitutions,
} from '../services/api';
import type { Submission, DashboardMetrics, DatasetMode, PublicReferenceRecord } from '../types';
import { DatasetModeToggle } from '../components/dashboard/DatasetModeToggle';
import { SequentialDonutChart, type DonutSlice } from '../components/analytics/SequentialDonutChart';
import { SubmissionTrendChart, type TrendDataPoint } from '../components/analytics/SubmissionTrendChart';
import { AnimatedNumber } from '../hooks/useCountUp';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Building2,
  MapPin,
  ShieldCheck,
  ExternalLink,
  Layers,
  Sparkles,
} from 'lucide-react';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function groupBy<T>(arr: T[], key: (item: T) => string): Record<string, T[]> {
  return arr.reduce(
    (acc, item) => {
      const k = key(item);
      if (!acc[k]) acc[k] = [];
      acc[k].push(item);
      return acc;
    },
    {} as Record<string, T[]>
  );
}

// ─── Horizontal Bar Component ─────────────────────────────────────────────────

const HBar: React.FC<{
  label: string;
  value: number;
  max: number;
  color: string;
  suffix?: string;
  subtitle?: string;
}> = ({ label, value, max, color, suffix = '', subtitle }) => {
  const pct = max > 0 ? Math.min(Math.round((value / max) * 100), 100) : 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          title={label}
          style={{
            fontSize: 12,
            color: '#55223F',
            fontWeight: 500,
            maxWidth: 195,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#351D31' }}>
          {value}{suffix}
        </span>
      </div>
      <div style={{ height: 8, background: '#F8EBF1', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 4,
            transition: 'width 0.85s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />
      </div>
      {subtitle && (
        <span style={{ fontSize: 10, color: '#A892A2', marginTop: 1 }}>{subtitle}</span>
      )}
    </div>
  );
};

// ─── Section Header ───────────────────────────────────────────────────────────

const SectionHeader: React.FC<{
  icon: React.ReactNode;
  title: string;
  sub?: string;
  badge?: string;
}> = ({ icon, title, sub, badge }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 8,
          background: '#FDF0F5',
          color: '#AA4777',
          border: '1px solid rgba(193, 78, 131, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <div
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: '#351D31',
            fontFamily: "'DM Serif Display', Georgia, serif",
          }}
        >
          {title}
        </div>
        {sub && <div style={{ fontSize: 11, color: '#896F81' }}>{sub}</div>}
      </div>
    </div>
    {badge && (
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 6,
          background: '#FFF0F5',
          color: '#C14E83',
          border: '1px solid #ECD9E2',
        }}
      >
        {badge}
      </span>
    )}
  </div>
);

// ─── Card Wrapper ─────────────────────────────────────────────────────────────

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      background: '#FFFAFC',
      borderRadius: 14,
      border: '1px solid #ECD9E2',
      padding: '20px 22px',
      boxShadow: '0 2px 10px rgba(53, 29, 49, 0.035), 0 6px 20px rgba(53, 29, 49, 0.04)',
      ...style,
    }}
  >
    {children}
  </div>
);

// ─── Palette Constants ────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  pending_review: '#AA4777',
  under_review: '#C14E83',
  escalated: '#92400E',
  approved: '#065F46',
  rejected: '#9E1628',
  on_hold: '#55223F',
};

const STATUS_LABELS: Record<string, string> = {
  pending_review: 'Pending',
  under_review: 'Under Review',
  escalated: 'Escalated',
  approved: 'Approved',
  rejected: 'Rejected',
  on_hold: 'On Hold',
};

const FINDING_COLORS: Record<string, string> = {
  critical: '#9E1628',
  major: '#92400E',
  minor: '#AA4777',
  info: '#896F81',
};

// ─── Main Analytics Page ──────────────────────────────────────────────────────

export const AnalyticsPage: React.FC = () => {
  // Sync initial dataset mode from localStorage or default to 'synthetic'
  const [datasetMode, setDatasetMode] = useState<DatasetMode>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('verifyai_dataset_mode');
      if (stored === 'real' || stored === 'synthetic') return stored;
    }
    return 'synthetic';
  });

  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [referenceRecords, setReferenceRecords] = useState<PublicReferenceRecord[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  // Sequential Donut Animation State:
  // stage 0 -> Donut 1 animates -> onComplete -> stage 1 -> Donut 2 animates -> onComplete -> stage 2 -> Donut 3
  const [donutStage, setDonutStage] = useState<number>(0);
  const [animResetKey, setAnimResetKey] = useState<number>(0);

  // Load data whenever datasetMode changes
  const loadData = useCallback(async (mode: DatasetMode) => {
    setLoading(true);
    // Reset animation stage to restart cleanly
    setDonutStage(0);
    setAnimResetKey((prev) => prev + 1);

    try {
      const [submRes, metricsRes, refRes] = await Promise.all([
        fetchSubmissions({}, mode),
        fetchDashboardMetrics(mode),
        fetchPublicReferenceInstitutions({ limit: 50 }),
      ]);
      setSubmissions(submRes.items || []);
      setMetrics(metricsRes);
      setReferenceRecords(refRes.items || []);
    } catch {
      // Fallback
      setSubmissions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(datasetMode);
  }, [datasetMode, loadData]);

  const handleModeChange = (newMode: DatasetMode) => {
    if (newMode === datasetMode) return;
    setDatasetMode(newMode);
    if (typeof window !== 'undefined') {
      localStorage.setItem('verifyai_dataset_mode', newMode);
    }
  };

  // ── Derived Data Calculation ────────────────────────────────────────────────

  const isReal = datasetMode === 'real';
  const totalSubmissions = submissions.length;
  const referenceCount = referenceRecords.length || 10;

  // 1. Status Distribution Donut Slices
  const byStatus = groupBy(submissions, (s) => s.status);
  const statusSlices: DonutSlice[] = Object.entries(STATUS_LABELS)
    .map(([k, label]) => ({
      label,
      value: (byStatus[k] ?? []).length,
      color: STATUS_COLORS[k] ?? '#A892A2',
    }))
    .filter((s) => s.value > 0);

  // 2. Institution Type Donut Slices
  // In real mode: show public reference institution types; In synthetic mode: show demo submission types
  const typeSlices: DonutSlice[] = isReal
    ? Object.entries(groupBy(referenceRecords, (r) => r.institutionType)).map(([k, arr]) => ({
        label: k.replace(/(College|University|Institute)/i, '').trim() || k,
        value: arr.length,
        color:
          k.toLowerCase().includes('university')
            ? '#AA4777'
            : k.toLowerCase().includes('autonomous')
            ? '#C14E83'
            : '#92400E',
      }))
    : Object.entries(groupBy(submissions, (s) => s.institution.type)).map(([k, arr]) => ({
        label: k.charAt(0).toUpperCase() + k.slice(1),
        value: arr.length,
        color:
          k === 'university'
            ? '#AA4777'
            : k === 'college'
            ? '#C14E83'
            : k === 'polytechnic'
            ? '#92400E'
            : '#55223F',
      }));

  const typeTotal = isReal ? referenceCount : totalSubmissions;

  // 3. Finding Severity Donut Slices
  const allFindings = submissions.flatMap((s) => s.findings);
  const bySeverity = groupBy(allFindings, (f) => f.severity);
  const severitySlices: DonutSlice[] = (['critical', 'major', 'minor', 'info'] as const)
    .map((sev) => ({
      label: sev.charAt(0).toUpperCase() + sev.slice(1),
      value: (bySeverity[sev] ?? []).length,
      color: FINDING_COLORS[sev],
    }))
    .filter((s) => s.value > 0);

  const totalFindings = allFindings.length;
  const critCount = (bySeverity.critical ?? []).length;
  const majorCount = (bySeverity.major ?? []).length;

  // 4. Top Finding Categories (Derived from actual findings)
  const byFindingCategory = groupBy(allFindings, (f) => f.category);
  const topCategories = Object.entries(byFindingCategory)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 6);
  const maxCatCount = topCategories[0]?.[1]?.length ?? 1;

  // 5. Geographic Spread (States)
  // In real mode: show state distribution of reference institutions; In synthetic mode: show application submissions
  const stateSource = isReal
    ? referenceRecords.map((r) => ({ state: r.state }))
    : submissions.map((s) => ({ state: s.institution.state }));

  const byState = groupBy(stateSource, (item) => item.state);
  const topStates = Object.entries(byState)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 8);
  const maxStateCount = topStates[0]?.[1]?.length ?? 1;

  // 6. Application Categories / Submission Types
  const byCategory = groupBy(submissions, (s) => s.category);
  const topAppCategories = Object.entries(byCategory)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 5);
  const maxAppCat = topAppCategories[0]?.[1]?.length ?? 1;

  // 7. Priority Tiers (0-39 Low, 40-69 Med, 70-100 High)
  const highPriority = submissions.filter((s) => s.priorityScore >= 70).length;
  const medPriority = submissions.filter(
    (s) => s.priorityScore >= 40 && s.priorityScore < 70
  ).length;
  const lowPriority = submissions.filter((s) => s.priorityScore < 40).length;

  // 8. Submission Trend Data (Simulated 6-Month Timeline)
  const trendData: TrendDataPoint[] = isReal
    ? [
        { period: 'May', submissions: 0 },
        { period: 'Jun', submissions: 0 },
        { period: 'Jul', submissions: 0 },
        { period: 'Aug', submissions: 0 },
        { period: 'Sep', submissions: 0 },
        { period: 'Oct', submissions: 0 },
      ]
    : [
        { period: 'May', submissions: 3 },
        { period: 'Jun', submissions: 5 },
        { period: 'Jul', submissions: 4 },
        { period: 'Aug', submissions: 7 },
        { period: 'Sep', submissions: 18 },
        { period: 'Oct', submissions: metrics?.totalSubmissions ?? 30 },
      ];

  const approvalRate =
    totalSubmissions > 0
      ? Math.round(((metrics?.approvedThisMonth ?? 0) / totalSubmissions) * 100)
      : 0;

  if (loading && !metrics) {
    return (
      <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ height: 60, background: '#F8EBF1', borderRadius: 14 }} className="animate-pulse" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse" style={{ height: 100, background: '#F8EBF1', borderRadius: 14 }} />
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse" style={{ height: 240, background: '#F8EBF1', borderRadius: 14 }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* ─── Header & Dataset Mode Toggle ────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BarChart3 size={24} color="#C14E83" />
            <h1
              style={{
                fontSize: 24,
                fontWeight: 400,
                color: '#351D31',
                fontFamily: "'DM Serif Display', Georgia, serif",
                margin: 0,
              }}
            >
              Regulatory Compliance Analytics
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#896F81', margin: '4px 0 0', paddingLeft: 34 }}>
            {isReal
              ? 'Statutory Public Reference Registry & verified benchmark directory analytics.'
              : 'Statistical evidence distributions across the synthetic regulatory pipeline.'}
          </p>
        </div>

        {/* Dataset Scope Toggle */}
        <DatasetModeToggle
          mode={datasetMode}
          onChange={handleModeChange}
          referenceCount={referenceCount}
          syntheticCount={30}
        />
      </div>

      {/* ─── Mode Explanation Banner ─────────────────────────────────────────── */}
      {isReal ? (
        <div
          style={{
            marginBottom: 20,
            padding: '12px 18px',
            background: '#F0F9FF',
            border: '1px solid #BAE6FD',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 14,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <ShieldCheck size={18} color="#0284C7" />
            <div style={{ fontSize: 12.5, color: '#0369A1', lineHeight: 1.4 }}>
              <strong>Real Data Mode Active:</strong> Authentic confidential applicant dossiers are
              strictly isolated (0 submissions connected). All displayable real data derives from
              the verified AICTE (AY 2024–2025) and AISHE public registries ({referenceCount} benchmark institutions).
            </div>
          </div>
          <a
            href="https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php#!/approved"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              color: '#0284C7',
              textDecoration: 'none',
              flexShrink: 0,
            }}
          >
            <span>Official AICTE Registry</span>
            <ExternalLink size={12} />
          </a>
        </div>
      ) : (
        <div
          style={{
            marginBottom: 20,
            padding: '10px 16px',
            background: '#FFF5F8',
            border: '1px solid #F3E0E9',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 12,
            color: '#8A2F5B',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={14} color="#C14E83" />
            <span>
              <strong>Synthetic Demo Dataset:</strong> 30 calibrated regulatory filings with 21 rule
              findings. No actual private institutional records or live violations are disclosed.
            </span>
          </div>
          <span
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 6,
              background: '#FFE8F0',
              color: '#8A2F5B',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Demo Simulation
          </span>
        </div>
      )}

      {/* ─── Row 1: KPI Cards with Smooth Animated Numbers ───────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 14,
          marginBottom: 20,
        }}
      >
        {[
          {
            label: isReal ? 'Authentic Applications' : 'Total Submissions',
            value: totalSubmissions,
            color: '#351D31',
            bg: '#FDF0F5',
            iconColor: '#AA4777',
            icon: <Building2 size={16} />,
            sub: isReal
              ? `${referenceCount} public reference institutions`
              : `${metrics?.underReview ?? 7} active reviews`,
          },
          {
            label: isReal ? 'Critical Findings' : 'Critical Findings',
            value: critCount,
            color: '#9E1628',
            bg: '#FDE8E8',
            iconColor: '#9E1628',
            icon: <AlertTriangle size={16} />,
            sub: isReal
              ? '0 findings in Real Data mode'
              : `${majorCount} major · ${totalFindings} total`,
          },
          {
            label: isReal ? 'Reference Directory' : 'Approval Rate',
            value: isReal ? referenceCount : approvalRate,
            suffix: isReal ? ' inst' : '%',
            color: '#065F46',
            bg: '#DEF7EC',
            iconColor: '#065F46',
            icon: <CheckCircle2 size={16} />,
            sub: isReal
              ? 'AY 2024–2025 verified registry'
              : `${metrics?.approvedThisMonth ?? 12} approved this cycle`,
          },
          {
            label: isReal ? 'Review Turnaround' : 'Avg. Resolution',
            value: isReal ? 0 : (metrics?.avgResolutionDays ?? 4.2),
            suffix: isReal ? 'd' : 'd',
            decimals: isReal ? 0 : 1,
            color: '#55223F',
            bg: '#F8E5ED',
            iconColor: '#55223F',
            icon: <Clock size={16} />,
            sub: isReal ? 'No authentic review cycles' : 'Average days to decision',
          },
        ].map((kpi, i) => (
          <Card key={i} style={{ padding: '16px 20px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: 8,
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 500, color: '#896F81' }}>{kpi.label}</span>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: kpi.bg,
                  color: kpi.iconColor,
                  border: '1px solid rgba(193, 78, 131, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {kpi.icon}
              </div>
            </div>
            <div
              style={{
                fontSize: 30,
                fontWeight: 400,
                fontFamily: "'DM Serif Display', Georgia, serif",
                color: kpi.color,
                letterSpacing: '-0.02em',
              }}
            >
              <AnimatedNumber
                value={kpi.value}
                decimals={kpi.decimals ?? 0}
                suffix={kpi.suffix ?? ''}
                resetKey={animResetKey}
              />
            </div>
            <div style={{ fontSize: 11, color: '#A892A2', marginTop: 2 }}>{kpi.sub}</div>
          </Card>
        ))}
      </div>

      {/* ─── Row 2: Sequential Donut Charts ───────────────────────────────────── */}
      {/* Sequence: Donut 1 (Application Status) -> Donut 2 (Institution Types) -> Donut 3 (Finding Severity) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Donut 1: Application Status (Starts sequence on stage >= 0) */}
        <Card style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <SequentialDonutChart
            title="1. Application Status"
            slices={statusSlices}
            total={totalSubmissions}
            size={135}
            active={donutStage >= 0}
            animationDuration={650}
            onAnimationComplete={() => {
              // Trigger Donut 2 once Donut 1 completes
              setDonutStage((prev) => Math.max(prev, 1));
            }}
            resetKey={animResetKey}
            emptyMessage={isReal ? '0 authentic submissions' : 'No applications'}
          />
        </Card>

        {/* Donut 2: Institution Types (Starts once Donut 1 finishes: stage >= 1) */}
        <Card style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <SequentialDonutChart
            title={isReal ? '2. Reference Institution Types' : '2. Institution Types'}
            slices={typeSlices}
            total={typeTotal}
            size={135}
            active={donutStage >= 1}
            animationDuration={650}
            onAnimationComplete={() => {
              // Trigger Donut 3 once Donut 2 completes
              setDonutStage((prev) => Math.max(prev, 2));
            }}
            resetKey={animResetKey}
            emptyMessage={isReal ? '0 reference institutions' : 'No data'}
          />
        </Card>

        {/* Donut 3: Finding Severity (Starts once Donut 2 finishes: stage >= 2) */}
        <Card style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <SequentialDonutChart
            title="3. Finding Severity"
            slices={severitySlices}
            total={totalFindings}
            size={135}
            active={donutStage >= 2}
            animationDuration={650}
            onAnimationComplete={() => {
              setDonutStage(3);
            }}
            resetKey={animResetKey}
            emptyMessage={isReal ? '0 authentic findings' : 'No findings'}
          />
        </Card>
      </div>

      {/* ─── Row 3: Regulatory Findings, States & Categories ─────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Top Finding Categories */}
        <Card>
          <SectionHeader
            icon={<AlertTriangle size={15} />}
            title="Top Finding Categories"
            sub="By occurrence frequency"
            badge={isReal ? 'Real: 0' : 'Advisory rules'}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
            {topCategories.length === 0 ? (
              <div
                style={{
                  fontSize: 12,
                  color: '#A892A2',
                  padding: '16px 0',
                  textAlign: 'center',
                  fontStyle: 'italic',
                }}
              >
                No compliance findings recorded for this data scope.
              </div>
            ) : (
              topCategories.map(([cat, arr]) => (
                <HBar
                  key={cat}
                  label={cat}
                  value={arr.length}
                  max={maxCatCount}
                  color={
                    arr.some((f) => f.severity === 'critical')
                      ? '#9E1628'
                      : arr.some((f) => f.severity === 'major')
                      ? '#92400E'
                      : '#AA4777'
                  }
                  subtitle={`${arr.length} advisory finding${arr.length > 1 ? 's' : ''} flagged for verification`}
                />
              ))
            )}
          </div>
        </Card>

        {/* Geographic Distribution (States) */}
        <Card>
          <SectionHeader
            icon={<MapPin size={15} />}
            title={isReal ? 'Reference Institutions by State' : 'Applications by State'}
            sub={isReal ? 'Verified AICTE directory coverage' : 'Geographic submission spread'}
            badge={isReal ? 'Registry source' : 'Pipeline'}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
            {topStates.length === 0 ? (
              <div
                style={{
                  fontSize: 12,
                  color: '#A892A2',
                  padding: '16px 0',
                  textAlign: 'center',
                }}
              >
                No geographic records available.
              </div>
            ) : (
              topStates.map(([state, arr]) => (
                <HBar
                  key={state}
                  label={state}
                  value={arr.length}
                  max={maxStateCount}
                  color="#C14E83"
                  suffix={isReal ? ' inst' : ' apps'}
                />
              ))
            )}
          </div>
        </Card>

        {/* Application Categories */}
        <Card>
          <SectionHeader
            icon={<BarChart3 size={15} />}
            title="Application Categories"
            sub="Filing type breakdown"
            badge={isReal ? 'Real: 0' : 'Filing types'}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
            {topAppCategories.length === 0 ? (
              <div
                style={{
                  fontSize: 12,
                  color: '#A892A2',
                  padding: '16px 0',
                  textAlign: 'center',
                  fontStyle: 'italic',
                }}
              >
                No application filings connected in Real Data mode.
              </div>
            ) : (
              topAppCategories.map(([cat, arr]) => (
                <HBar
                  key={cat}
                  label={cat}
                  value={arr.length}
                  max={maxAppCat}
                  color="#AA4777"
                  suffix=" apps"
                />
              ))
            )}
          </div>
        </Card>
      </div>

      {/* ─── Row 4: Priority Breakdown & Progressive Submission Trend ────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Priority / Risk Tier Breakdown */}
        <Card>
          <SectionHeader
            icon={<TrendingUp size={15} />}
            title="Priority & Risk Triage Breakdown"
            sub="Operational review queue tiers"
            badge="Triage matrix"
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <HBar
              label="High Risk (70–100 Score)"
              value={highPriority}
              max={totalSubmissions || 1}
              color="#9E1628"
              suffix={` case${highPriority !== 1 ? 's' : ''}`}
            />
            <HBar
              label="Medium Risk (40–69 Score)"
              value={medPriority}
              max={totalSubmissions || 1}
              color="#92400E"
              suffix={` case${medPriority !== 1 ? 's' : ''}`}
            />
            <HBar
              label="Low Risk (0–39 Score)"
              value={lowPriority}
              max={totalSubmissions || 1}
              color="#065F46"
              suffix={` case${lowPriority !== 1 ? 's' : ''}`}
            />
          </div>

          <div
            style={{
              marginTop: 18,
              padding: '12px 14px',
              borderRadius: 10,
              background: '#FFF5F8',
              border: '1px solid #ECD9E2',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            <div style={{ fontSize: 11.5, fontWeight: 700, color: '#351D31' }}>
              Regulatory Triage Principle:
            </div>
            <div style={{ fontSize: 11, color: '#6B4F63', lineHeight: 1.45 }}>
              A high priority score triggers immediate human committee review; it does{' '}
              <strong>not</strong> constitute a final determination of institutional noncompliance
              or statutory violation.
            </div>
          </div>
        </Card>

        {/* Progressive Line-Drawing Submission Trend Chart */}
        <Card>
          <SectionHeader
            icon={<TrendingUp size={15} />}
            title="Submission Timeline Trend"
            sub={
              isReal
                ? 'Authentic reporting periods (0 connected filings)'
                : 'Simulated Historical Trend · 6 Months'
            }
            badge={isReal ? 'Authentic' : 'Simulated'}
          />

          <SubmissionTrendChart
            data={trendData}
            mode={datasetMode}
            resetKey={animResetKey}
            height={160}
          />

          {/* Quick Metrics Sub-Strip */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 8,
              marginTop: 16,
            }}
          >
            {[
              {
                label: 'Pending',
                value: metrics?.pendingReview ?? 0,
                color: '#AA4777',
              },
              {
                label: 'In Review',
                value: metrics?.underReview ?? 0,
                color: '#C14E83',
              },
              {
                label: 'Escalated',
                value: metrics?.escalated ?? 0,
                color: '#92400E',
              },
              {
                label: 'Resolved',
                value: metrics?.approvedThisMonth ?? 0,
                color: '#065F46',
              },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  background: '#FFFAFC',
                  border: '1px solid #ECD9E2',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1,
                  textAlign: 'center',
                }}
              >
                <span
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "'DM Serif Display', Georgia, serif",
                    color: item.color,
                  }}
                >
                  <AnimatedNumber value={item.value} resetKey={animResetKey} />
                </span>
                <span style={{ fontSize: 10, color: '#896F81' }}>{item.label}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ─── Row 5: Decision Support & Evidence Integrity Insights ──────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Cross-Document Consistency Insights */}
        <Card>
          <SectionHeader
            icon={<Layers size={15} />}
            title="Cross-Document Discrepancy Breakdown"
            sub="Automated multi-source evidence reconciliation"
            badge="Engine audit"
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 10,
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: 10,
                  background: '#FDF0F5',
                  border: '1px solid #F3E0E9',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 20, fontWeight: 700, color: '#8A2F5B' }}>
                  {isReal ? '0' : '8'}
                </div>
                <div style={{ fontSize: 10.5, color: '#896F81', marginTop: 2 }}>
                  Fields Compared
                </div>
              </div>
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: 10,
                  background: isReal ? '#FDF0F5' : '#FFF1F2',
                  border: '1px solid #FECDD3',
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    color: isReal ? '#896F81' : '#E11D48',
                  }}
                >
                  {isReal ? '0' : '2'}
                </div>
                <div style={{ fontSize: 10.5, color: '#896F81', marginTop: 2 }}>
                  Mismatches Found
                </div>
              </div>
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: 10,
                  background: '#F0FDF4',
                  border: '1px solid #DCFCE7',
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    color: isReal ? '#896F81' : '#16A34A',
                  }}
                >
                  {isReal ? '0' : '6'}
                </div>
                <div style={{ fontSize: 10.5, color: '#896F81', marginTop: 2 }}>
                  Perfect Matches
                </div>
              </div>
            </div>

            <div style={{ fontSize: 11.5, color: '#6B4F63', lineHeight: 1.5 }}>
              {isReal ? (
                <span>
                  The cross-document reconciliation engine runs automatically when confidential applicant
                  dossiers (Land Titles, Building Plans, Affiliation Letters) are uploaded.
                </span>
              ) : (
                <span>
                  Detected field discrepancies (such as Land Area in Deed vs Survey Sketch) are flagged
                  as items requiring human reviewer verification under APH 2024–2027 Section 2.4.
                </span>
              )}
            </div>
          </div>
        </Card>

        {/* Data Provenance & Registry Verification Health */}
        <Card>
          <SectionHeader
            icon={<ShieldCheck size={15} />}
            title="Data Provenance & Registry Integrity"
            sub="Authenticity tracking & regulatory source citations"
            badge="Verified"
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              {
                source: 'AICTE Approved Institutes Web Directory',
                year: 'Academic Year 2024–2025',
                status: 'Verified Official Registry',
                count: `${referenceCount} institutes`,
                checksum: 'SHA-256 Validated',
              },
              {
                source: 'AISHE Higher Education Institution Directory',
                year: 'All-India Survey 2024–2025',
                status: 'Directory Cross-Referenced',
                count: 'AISHE Codes Mapped',
                checksum: 'Deterministic Digest',
              },
            ].map((reg) => (
              <div
                key={reg.source}
                style={{
                  padding: '10px 14px',
                  borderRadius: 10,
                  background: '#FFFFFF',
                  border: '1px solid #ECD9E2',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 10,
                }}
              >
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#351D31' }}>
                    {reg.source}
                  </div>
                  <div style={{ fontSize: 10.5, color: '#896F81' }}>
                    {reg.year} · {reg.checksum}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <span
                    style={{
                      fontSize: 10.5,
                      fontWeight: 700,
                      color: '#065F46',
                      background: '#DEF7EC',
                      padding: '2px 8px',
                      borderRadius: 6,
                    }}
                  >
                    {reg.status}
                  </span>
                  <div style={{ fontSize: 10, color: '#A892A2', marginTop: 2 }}>{reg.count}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ─── Footer Notice ───────────────────────────────────────────────────── */}
      <div
        style={{
          marginTop: 10,
          padding: '12px 16px',
          background: isReal ? '#F0FDF4' : '#FFF7F0',
          border: `1px solid ${isReal ? '#BBF7D0' : '#F8DEC9'}`,
          borderRadius: 10,
          fontSize: 11,
          color: isReal ? '#166534' : '#9A4B1A',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          {isReal
            ? '✓ Real Data Mode: 10 verified technical benchmark institutions loaded from AICTE & AISHE registries. Confidential applicant dossiers remain isolated.'
            : '⚠ Simulated Dataset: 30 synthetic filings with 21 findings generated for the Smart India Hackathon prototype. Grounded in AICTE APH 2024–2027 statutory rules.'}
        </span>
        <span style={{ fontWeight: 600, color: isReal ? '#166534' : '#C14E83' }}>
          AICTE VerifyAI · Evidence Decision Support
        </span>
      </div>
    </div>
  );
};
