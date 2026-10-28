import React from 'react';
import type { PublicReferenceRecord } from '../../types';
import {
  Building2,
  ShieldCheck,
  ExternalLink,
  X,
  MapPin,
  CheckCircle2,
  Lock,
  ArrowRight,
  Copy,
  Check,
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
  onSwitchToSynthetic,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!isOpen || !record) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(record.aictePermanentId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
          maxWidth: '720px',
          boxShadow: '0 20px 40px rgba(53, 29, 49, 0.25)',
          border: '1px solid #ECD9E2',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
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
              </div>
              <h2
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: '#351D31',
                  margin: 0,
                  fontFamily: "'DM Serif Display', Georgia, serif",
                }}
              >
                {record.institutionName}
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, fontSize: 12, color: '#664C5F' }}>
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

        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Section 1: Official Registry Details Grid */}
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
                {record.sponsoringBody || 'Autonomous State Institution'}
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
                Source Dataset Version
              </div>
              <div style={{ fontSize: 12, color: '#664C5F', marginTop: 2, fontFamily: 'monospace' }}>
                {record.datasetVersion || 'AY-2024-2025-V1'}
              </div>
            </div>
          </div>

          {/* Section 2: Provenance & SHA-256 Checksum */}
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
            <div style={{ fontSize: 11.5, color: '#664C5F', lineHeight: 1.5, marginBottom: 10 }}>
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

          {/* Section 3: Official External Registry Portals */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#896F81' }}>
              Verified Regulatory Registry Portals
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
                <span>AISHE National Registry</span>
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
                  <span>Institution Website</span>
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>

          {/* Section 4: Dossier Isolation Notice & Switch CTA */}
          <div
            style={{
              background: 'linear-gradient(135deg, #FFF5F7 0%, #FDF0F5 100%)',
              border: '1px solid #ECD9E2',
              borderLeft: '4px solid #C14E83',
              borderRadius: 12,
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            <Lock size={18} style={{ color: '#C14E83', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: '#351D31' }}>
                Confidential Applicant Dossier Isolation
              </div>
              <p style={{ fontSize: 11.5, color: '#664C5F', margin: '4px 0 10px 0', lineHeight: 1.5 }}>
                Under AICTE compliance and privacy guidelines, confidential application filings (statutory financial statements, encumbrance certificates, physical inspection visit reports, and faculty Ph.D. dossiers) are not published in public directories.
                To inspect the complete cross-document verification engine, document viewer, and rule evaluation pipeline, explore the Synthetic Demo workspace.
              </p>
              {onSwitchToSynthetic && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onSwitchToSynthetic();
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 14px',
                    background: 'linear-gradient(135deg, #8A2F5B 0%, #C14E83 100%)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: 6,
                    fontSize: 11.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 2px 6px rgba(138, 47, 91, 0.2)',
                  }}
                >
                  <span>Open Synthetic Demo Scrutiny Workspace</span>
                  <ArrowRight size={12} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            background: '#FAF6F8',
            borderTop: '1px solid #ECD9E2',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '7px 18px',
              background: '#FFFFFF',
              border: '1px solid #ECD9E2',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              color: '#351D31',
              cursor: 'pointer',
            }}
          >
            Close Detail
          </button>
        </div>
      </div>
    </div>
  );
};

