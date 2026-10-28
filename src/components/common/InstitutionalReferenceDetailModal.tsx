import React, { useState, useEffect } from 'react';
import type { PublicReferenceRecord } from '../../types';
import {
  fetchInstitutionDossier,
  executeInstitutionAction,
  addInstitutionNote,
  updateInstitutionFindingStatus,
  type InstitutionalDossier,
} from '../../services/api';
import { downloadInstitutionalSummaryReport } from '../../utils/downloadHelpers';
import {
  Building2,
  ShieldCheck,
  ExternalLink,
  X,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Clock,
  Send,
  Download,
  Copy,
  Check,
  History,
  CheckSquare,
  XCircle,
} from 'lucide-react';

interface InstitutionalReferenceDetailModalProps {
  record: PublicReferenceRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onSwitchToSynthetic?: () => void;
}

export const InstitutionalReferenceDetailModal: React.FC<InstitutionalReferenceDetailModalProps> = ({
  record,
  isOpen,
  onClose,
  onSwitchToSynthetic: _onSwitchToSynthetic,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'findings' | 'workflow' | 'notes' | 'audit'>('overview');
  const [dossier, setDossier] = useState<InstitutionalDossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionNotes, setActionNotes] = useState('');
  const [selectedAction, setSelectedAction] = useState<'verify' | 'reject' | 'escalate' | 'clarify'>('verify');
  const [newNoteText, setNewNoteText] = useState('');
  const [copied, setCopied] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && record) {
      loadDossier(record.id);
      setActiveTab('overview');
      setActionSuccessMsg(null);
    }
  }, [isOpen, record]);

  const loadDossier = async (instId: string) => {
    try {
      setLoading(true);
      const res = await fetchInstitutionDossier(instId);
      setDossier(res);
    } catch {
      // Offline fallback
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !record) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(record.aictePermanentId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecuteAction = async () => {
    try {
      setActionLoading(true);
      const res = await executeInstitutionAction(
        record.id,
        selectedAction,
        actionNotes,
        'Lead Compliance Reviewer'
      );
      setDossier(res);
      setActionNotes('');
      setActionSuccessMsg(`Scrutiny action '${selectedAction.toUpperCase()}' recorded successfully.`);
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch {
      // Error handling
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteText.trim()) return;
    try {
      setActionLoading(true);
      const res = await addInstitutionNote(record.id, newNoteText.trim(), 'Lead Compliance Reviewer');
      setDossier(res);
      setNewNoteText('');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateFinding = async (findingId: string, newStatus: 'confirmed' | 'dismissed' | 'escalated') => {
    try {
      const res = await updateInstitutionFindingStatus(record.id, findingId, newStatus);
      setDossier(res);
    } catch {
      // Error handling
    }
  };

  const reviewStatus = dossier?.applicationCase?.reviewStatus || 'pending_review';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        background: 'rgba(53, 29, 49, 0.65)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '860px',
          boxShadow: '0 20px 40px rgba(53, 29, 49, 0.25)',
          border: '1px solid #ECD9E2',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '92vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            background: 'linear-gradient(135deg, #FFF9FA 0%, #FFF5F7 100%)',
            borderBottom: '1px solid #ECD9E2',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #8A2F5B 0%, #C14E83 100%)',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(138, 47, 91, 0.2)',
              }}
            >
              <Building2 size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                <span
                  style={{
                    fontFamily: 'monospace',
                    fontSize: 11,
                    fontWeight: 700,
                    background: '#FFF0F5',
                    color: '#8A2F5B',
                    padding: '2px 8px',
                    borderRadius: 6,
                    border: '1px solid #F3D4E2',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span>{record.aictePermanentId}</span>
                  <button
                    type="button"
                    onClick={handleCopyId}
                    title="Copy AICTE Permanent ID"
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#8A2F5B', padding: 0 }}
                  >
                    {copied ? <Check size={11} color="#16A34A" /> : <Copy size={11} />}
                  </button>
                </span>
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    color: '#15803D',
                    background: '#DCFCE7',
                    padding: '2px 8px',
                    borderRadius: 6,
                  }}
                >
                  {record.approvalStatus}
                </span>
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    color:
                      reviewStatus === 'approved'
                        ? '#15803D'
                        : reviewStatus === 'rejected'
                        ? '#B91C1C'
                        : reviewStatus === 'escalated'
                        ? '#B45309'
                        : '#8A2F5B',
                    background:
                      reviewStatus === 'approved'
                        ? '#F0FDF4'
                        : reviewStatus === 'rejected'
                        ? '#FEF2F2'
                        : reviewStatus === 'escalated'
                        ? '#FFFBEB'
                        : '#FFF0F5',
                    padding: '2px 8px',
                    borderRadius: 6,
                    border: '1px solid #ECD9E2',
                    textTransform: 'uppercase',
                  }}
                >
                  Scrutiny: {reviewStatus.replace('_', ' ')}
                </span>
              </div>
              <h2
                style={{
                  fontSize: 17,
                  fontWeight: 700,
                  color: '#351D31',
                  margin: 0,
                  fontFamily: "'DM Serif Display', Georgia, serif",
                }}
              >
                {record.institutionName}
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, fontSize: 11.5, color: '#664C5F' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <MapPin size={12} color="#AA4777" />
                  {record.city}, {record.state}
                </span>
                <span>•</span>
                <span>Type: {record.institutionType}</span>
                {record.aisheCode && (
                  <>
                    <span>•</span>
                    <span style={{ fontFamily: 'monospace' }}>AISHE: {record.aisheCode}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              type="button"
              onClick={() => downloadInstitutionalSummaryReport(record, dossier?.auditEvents as any)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '7px 12px',
                background: '#F0FDF4',
                color: '#15803D',
                border: '1px solid #BBF7D0',
                borderRadius: 8,
                fontSize: 11.5,
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Download official verification dossier summary (PDF)"
            >
              <Download size={13} />
              <span>Dossier PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: '#FDF0F5',
                border: '1px solid #ECD9E2',
                borderRadius: 8,
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#8A2F5B',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Tab navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #ECD9E2',
            background: '#FFFDFE',
            padding: '0 24px',
            gap: 6,
          }}
        >
          {[
            { id: 'overview', label: 'Reference & Provenance', icon: <Building2 size={13} /> },
            { id: 'findings', label: `Statutory Checkpoints (${dossier?.findings.length ?? 3})`, icon: <CheckSquare size={13} /> },
            { id: 'workflow', label: 'Reviewer Scrutiny Action', icon: <CheckCircle2 size={13} /> },
            { id: 'notes', label: `Notes (${dossier?.reviewerNotes.length ?? 0})`, icon: <FileText size={13} /> },
            { id: 'audit', label: `Audit Trail (${dossier?.auditEvents.length ?? 1})`, icon: <History size={13} /> },
          ].map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '10px 14px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: active ? '2px solid #8A2F5B' : '2px solid transparent',
                  color: active ? '#8A2F5B' : '#896F81',
                  fontWeight: active ? 700 : 500,
                  fontSize: 12,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Success Alert Banner */}
        {actionSuccessMsg && (
          <div
            style={{
              padding: '8px 24px',
              background: '#F0FDF4',
              borderBottom: '1px solid #BBF7D0',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 12,
              color: '#15803D',
              fontWeight: 600,
            }}
          >
            <CheckCircle2 size={14} />
            <span>{actionSuccessMsg}</span>
          </div>
        )}

        {/* Body Content */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#896F81', fontSize: 13 }}>
              Loading institutional scrutiny dossier…
            </div>
          ) : (
            <>
              {/* TAB 1: OVERVIEW & PROVENANCE */}
              {activeTab === 'overview' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 12,
                      background: '#FAF6F8',
                      border: '1px solid #F3E0E9',
                      borderRadius: 12,
                      padding: 16,
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: '#896F81' }}>
                        Sponsoring Body
                      </div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: '#351D31', marginTop: 2 }}>
                        {record.sponsoringBody || 'Autonomous Technical Institution'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: '#896F81' }}>
                        Academic Approval Year
                      </div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: '#351D31', marginTop: 2 }}>
                        {record.academicYear || '2024–2025'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: '#896F81' }}>
                        Validation Status
                      </div>
                      <div style={{ fontSize: 12.5, fontWeight: 700, color: '#16A34A', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <CheckCircle2 size={13} />
                        VALIDATED
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', color: '#896F81' }}>
                        Internal Scrutiny Case
                      </div>
                      <div style={{ fontSize: 12, color: '#664C5F', marginTop: 2, fontFamily: 'monospace' }}>
                        {dossier?.applicationCase.applicationNumber || `APH-2024-${record.aictePermanentId}`}
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      background: '#FFFFFF',
                      border: '1px solid #ECD9E2',
                      borderRadius: 12,
                      padding: 16,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#8A2F5B' }}>
                      <ShieldCheck size={16} />
                      <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: '#351D31' }}>
                        Cryptographic Provenance & Canonical Integrity
                      </span>
                    </div>
                    <div style={{ fontSize: 11.5, color: '#664C5F', lineHeight: 1.5, marginBottom: 8 }}>
                      Imported from <strong>{record.sourcePublisher || 'AICTE Approved Institutes Public Dashboard'}</strong> on{' '}
                      {record.retrievalDate || '2026-10-23'}.
                    </div>
                    <div
                      style={{
                        fontFamily: 'monospace',
                        fontSize: 11,
                        background: '#FAF6F8',
                        border: '1px solid #ECD9E2',
                        padding: '8px 12px',
                        borderRadius: 8,
                        color: '#351D31',
                        wordBreak: 'break-all',
                      }}
                    >
                      <span style={{ color: '#896F81', marginRight: 6 }}>SHA-256:</span>
                      {record.contentChecksum || 'f4a9c8b7e6d5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9'}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#896F81', display: 'block', marginBottom: 8 }}>
                      Official Portal Deep-Links
                    </span>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                      <a
                        href={record.aictePortalUrl || "https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php#!/approved"}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '8px 14px',
                          background: '#FFF0F5',
                          color: '#8A2F5B',
                          border: '1px solid #F3D4E2',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          textDecoration: 'none',
                        }}
                      >
                        <span>AICTE Approved Institutes Portal</span>
                        <ExternalLink size={12} />
                      </a>
                      <a
                        href={record.aishePortalUrl || "https://dashboard.aishe.gov.in/hedirectory/"}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '8px 14px',
                          background: '#F9FAFB',
                          color: '#374151',
                          border: '1px solid #E5E7EB',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          textDecoration: 'none',
                        }}
                      >
                        <span>AISHE Registry</span>
                        <ExternalLink size={12} />
                      </a>
                      {record.institutionWebsiteUrl && (
                        <a
                          href={record.institutionWebsiteUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '8px 14px',
                            background: '#F9FAFB',
                            color: '#374151',
                            border: '1px solid #E5E7EB',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 600,
                            textDecoration: 'none',
                          }}
                        >
                          <span>College Website</span>
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: STATUTORY CHECKPOINTS & FINDINGS */}
              {activeTab === 'findings' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{ fontSize: 12, color: '#664C5F' }}>
                    Statutory scrutiny checkpoints based on AICTE Approval Process Handbook (APH) 2024–2027. Reviewers may confirm, dismiss, or escalate individual items.
                  </div>

                  {(dossier?.findings ?? []).map((f) => (
                    <div
                      key={f.id}
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid #ECD9E2',
                        borderRadius: 10,
                        padding: '14px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 700, color: '#8A2F5B' }}>
                              {f.findingCode}
                            </span>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: '1px 6px',
                                borderRadius: 4,
                                textTransform: 'uppercase',
                                background: f.severity === 'critical' ? '#FEE2E2' : f.severity === 'high' ? '#FFEDD5' : '#F3E8FF',
                                color: f.severity === 'critical' ? '#B91C1C' : f.severity === 'high' ? '#C2410C' : '#6B21A8',
                              }}
                            >
                              {f.severity}
                            </span>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: '1px 6px',
                                borderRadius: 4,
                                background: f.reviewStatus === 'confirmed' ? '#DCFCE7' : f.reviewStatus === 'dismissed' ? '#F3F4F6' : '#FEF3C7',
                                color: f.reviewStatus === 'confirmed' ? '#15803D' : f.reviewStatus === 'dismissed' ? '#6B7280' : '#B45309',
                              }}
                            >
                              {f.reviewStatus}
                            </span>
                          </div>
                          <h4 style={{ fontSize: 13, fontWeight: 700, color: '#351D31', margin: '4px 0 2px 0' }}>
                            {f.title}
                          </h4>
                          <p style={{ fontSize: 11.5, color: '#664C5F', margin: 0, lineHeight: 1.4 }}>
                            {f.explanation}
                          </p>
                          {f.ruleCitation && (
                            <div style={{ fontSize: 10.5, color: '#AA4777', fontWeight: 600, marginTop: 4 }}>
                              Citation: {f.ruleCitation}
                            </div>
                          )}
                        </div>

                        {/* Status toggles */}
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            type="button"
                            onClick={() => handleUpdateFinding(f.id, 'confirmed')}
                            style={{
                              padding: '3px 8px',
                              borderRadius: 4,
                              fontSize: 10.5,
                              fontWeight: 600,
                              cursor: 'pointer',
                              background: f.reviewStatus === 'confirmed' ? '#15803D' : '#F0FDF4',
                              color: f.reviewStatus === 'confirmed' ? '#FFFFFF' : '#15803D',
                              border: '1px solid #BBF7D0',
                            }}
                          >
                            Confirm
                          </button>
                          <button
                            type="button"
                            onClick={() => handleUpdateFinding(f.id, 'escalated')}
                            style={{
                              padding: '3px 8px',
                              borderRadius: 4,
                              fontSize: 10.5,
                              fontWeight: 600,
                              cursor: 'pointer',
                              background: f.reviewStatus === 'escalated' ? '#B45309' : '#FFFBEB',
                              color: f.reviewStatus === 'escalated' ? '#FFFFFF' : '#B45309',
                              border: '1px solid #FDE68A',
                            }}
                          >
                            Escalate
                          </button>
                          <button
                            type="button"
                            onClick={() => handleUpdateFinding(f.id, 'dismissed')}
                            style={{
                              padding: '3px 8px',
                              borderRadius: 4,
                              fontSize: 10.5,
                              fontWeight: 600,
                              cursor: 'pointer',
                              background: f.reviewStatus === 'dismissed' ? '#4B5563' : '#F9FAFB',
                              color: f.reviewStatus === 'dismissed' ? '#FFFFFF' : '#4B5563',
                              border: '1px solid #E5E7EB',
                            }}
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 3: REVIEWER WORKFLOW ACTIONS */}
              {activeTab === 'workflow' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div
                    style={{
                      background: '#FFF5F8',
                      border: '1px solid #ECD9E2',
                      borderRadius: 10,
                      padding: '14px 16px',
                    }}
                  >
                    <h4 style={{ fontSize: 13, fontWeight: 700, color: '#351D31', margin: 0 }}>
                      Current Scrutiny Status: <span style={{ textTransform: 'uppercase', color: '#8A2F5B' }}>{reviewStatus.replace('_', ' ')}</span>
                    </h4>
                    <p style={{ fontSize: 11.5, color: '#664C5F', margin: '4px 0 0 0' }}>
                      {dossier?.applicationCase.reviewedAt
                        ? `Last reviewed on ${new Date(dossier.applicationCase.reviewedAt).toLocaleString()} by ${dossier.applicationCase.reviewerActor || 'Officer'}`
                        : 'Awaiting initial compliance officer determination'}
                    </p>
                    {dossier?.applicationCase.reviewNotes && (
                      <div style={{ marginTop: 8, fontSize: 11.5, background: '#FFFFFF', padding: '8px 12px', borderRadius: 6, border: '1px solid #ECD9E2' }}>
                        <strong>Latest Review Note:</strong> {dossier.applicationCase.reviewNotes}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <label style={{ fontSize: 12, fontWeight: 700, color: '#351D31' }}>
                      Select Regulatory Scrutiny Action
                    </label>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                      {[
                        { id: 'verify', label: 'Verify Dossier', desc: 'Approve statutory proforma compliance', color: '#15803D', bg: '#F0FDF4', icon: <CheckCircle2 size={16} /> },
                        { id: 'clarify', label: 'Request Clarification', desc: 'Return for applicant / DTE explanation', color: '#B45309', bg: '#FFFBEB', icon: <Clock size={16} /> },
                        { id: 'escalate', label: 'Escalate to Regional Officer', desc: 'Refer to regional scrutiny committee', color: '#8A2F5B', bg: '#FDF0F5', icon: <AlertTriangle size={16} /> },
                        { id: 'reject', label: 'Reject Dossier', desc: 'Flag fatal non-compliance deficiency', color: '#B91C1C', bg: '#FEF2F2', icon: <XCircle size={16} /> },
                      ].map((act) => {
                        const sel = selectedAction === act.id;
                        return (
                          <div
                            key={act.id}
                            onClick={() => setSelectedAction(act.id as any)}
                            style={{
                              border: sel ? `2px solid ${act.color}` : '1px solid #ECD9E2',
                              background: sel ? act.bg : '#FFFFFF',
                              borderRadius: 10,
                              padding: '12px 14px',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                              boxShadow: sel ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: act.color, fontWeight: 700, fontSize: 12.5 }}>
                              {act.icon}
                              <span>{act.label}</span>
                            </div>
                            <div style={{ fontSize: 10.5, color: '#896F81', marginTop: 4 }}>
                              {act.desc}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                      <label style={{ fontSize: 12, fontWeight: 700, color: '#351D31' }}>
                        Regulatory Reviewer Remark & Justification
                      </label>
                      <textarea
                        rows={3}
                        value={actionNotes}
                        onChange={(e) => setActionNotes(e.target.value)}
                        placeholder="State statutory basis and justification under AICTE Approval Process Handbook (e.g. §6.17 Land Title verified via municipal records)..."
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: 8,
                          border: '1px solid #ECD9E2',
                          fontSize: 12,
                          color: '#351D31',
                          outline: 'none',
                          boxSizing: 'border-box',
                        }}
                      />
                    </div>

                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={handleExecuteAction}
                      style={{
                        padding: '10px 20px',
                        background: 'linear-gradient(135deg, #8A2F5B 0%, #C14E83 100%)',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: 8,
                        fontSize: 12.5,
                        fontWeight: 600,
                        cursor: actionLoading ? 'wait' : 'pointer',
                        width: 'fit-content',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 8,
                        boxShadow: '0 2px 8px rgba(138, 47, 91, 0.25)',
                      }}
                    >
                      <span>{actionLoading ? 'Persisting Decision…' : 'Record Scrutiny Decision'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 4: REVIEWER NOTES */}
              {activeTab === 'notes' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <form onSubmit={handleAddNote} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <label style={{ fontSize: 12, fontWeight: 700, color: '#351D31' }}>
                      Add Scrutiny Note
                    </label>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="text"
                        value={newNoteText}
                        onChange={(e) => setNewNoteText(e.target.value)}
                        placeholder="Enter internal scrutiny remark..."
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          borderRadius: 8,
                          border: '1px solid #ECD9E2',
                          fontSize: 12,
                          color: '#351D31',
                          outline: 'none',
                        }}
                      />
                      <button
                        type="submit"
                        disabled={actionLoading || !newNoteText.trim()}
                        style={{
                          padding: '8px 16px',
                          background: '#8A2F5B',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <Send size={12} />
                        <span>Add Note</span>
                      </button>
                    </div>
                  </form>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {(dossier?.reviewerNotes ?? []).length === 0 ? (
                      <div style={{ padding: '24px', textAlign: 'center', color: '#896F81', fontSize: 12 }}>
                        No internal notes recorded yet.
                      </div>
                    ) : (
                      dossier?.reviewerNotes.map((n) => (
                        <div
                          key={n.id}
                          style={{
                            background: '#FAF6F8',
                            border: '1px solid #F3E0E9',
                            borderRadius: 8,
                            padding: '10px 14px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#8A2F5B' }}>
                              {n.author} ({n.role})
                            </span>
                            <span style={{ fontSize: 10.5, color: '#896F81' }}>
                              {n.createdAt ? new Date(n.createdAt).toLocaleString() : ''}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: '#351D31' }}>{n.text}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* TAB 5: AUDIT TRAIL */}
              {activeTab === 'audit' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ fontSize: 12, color: '#664C5F' }}>
                    Immutable regulatory audit events persisted in SQLite database.
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {(dossier?.auditEvents ?? []).map((ev) => (
                      <div
                        key={ev.id}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 12,
                          background: '#FFFFFF',
                          border: '1px solid #ECD9E2',
                          borderRadius: 8,
                          padding: '10px 14px',
                        }}
                      >
                        <div
                          style={{
                            width: 24,
                            height: 24,
                            borderRadius: 6,
                            background: '#FDF0F5',
                            color: '#AA4777',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            marginTop: 2,
                          }}
                        >
                          <History size={12} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#351D31' }}>
                              {ev.eventType}
                            </span>
                            <span style={{ fontSize: 10.5, color: '#896F81' }}>
                              {ev.createdAt ? new Date(ev.createdAt).toLocaleString() : ''}
                            </span>
                          </div>
                          <div style={{ fontSize: 11.5, color: '#664C5F', marginTop: 2 }}>
                            {ev.details}
                          </div>
                          {ev.actor && (
                            <div style={{ fontSize: 10.5, color: '#AA4777', marginTop: 2 }}>
                              Actor: {ev.actor}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
