import React, { useState, useEffect, useId } from 'react';
import {
  ShieldCheck,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  AlertCircle,
  FileSearch,
  GitCompare,
  CheckCircle2,
  FlaskConical,
  User,
  Clock,
  Info,
} from 'lucide-react';
import {
  loginReviewer,
  loginWithGoogle,
  registerReviewer,
  fetchAuthConfig,
  type AuthConfig,
} from '../../services/api';
import type { ReviewerProfile } from '../../types';

interface LoginScreenProps {
  onAuthenticated: (reviewer: ReviewerProfile) => void;
}

// ─── SVG Google Logo ──────────────────────────────────────────────────────────

// SIH Judge demo credentials — Adhav's reviewer account.
// Override at build time via VITE_DEMO_EMAIL / VITE_DEMO_PASSWORD env vars if needed.
const DEMO_EMAIL: string =
  (import.meta as any).env?.VITE_DEMO_EMAIL ?? 'adhav.sri123@gmail.com';
const DEMO_PASSWORD: string =
  (import.meta as any).env?.VITE_DEMO_PASSWORD ?? 'VerifyAI@Adhav123!';

function GoogleLogoSVG() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.03h3.88c2.27-2.09 3.665-5.17 3.665-9.12z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.03c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.13C3.25 21.37 7.31 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.57H1.26C.46 8.16 0 9.98 0 12s.46 3.84 1.26 5.43l4.02-3.14z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.63 1.26 6.57l4.02 3.14c.95-2.83 3.6-4.96 6.72-4.96z"
      />
    </svg>
  );
}

// ─── SVG document-network illustration ────────────────────────────────────────

function DocumentNetworkSVG() {
  return (
    <svg
      viewBox="0 0 340 320"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: '100%', maxWidth: 280, maxHeight: 180, opacity: 0.92, display: 'block' }}
      aria-hidden="true"
    >
      <line x1="170" y1="90" x2="80"  y2="155" stroke="rgba(193,78,131,0.35)" strokeWidth="1.2" strokeDasharray="4 3"/>
      <line x1="170" y1="90" x2="260" y2="155" stroke="rgba(193,78,131,0.35)" strokeWidth="1.2" strokeDasharray="4 3"/>
      <line x1="80"  y1="155" x2="50"  y2="240" stroke="rgba(193,78,131,0.25)" strokeWidth="1" strokeDasharray="4 3"/>
      <line x1="80"  y1="155" x2="170" y2="245" stroke="rgba(193,78,131,0.25)" strokeWidth="1" strokeDasharray="4 3"/>
      <line x1="260" y1="155" x2="170" y2="245" stroke="rgba(193,78,131,0.25)" strokeWidth="1" strokeDasharray="4 3"/>
      <line x1="260" y1="155" x2="295" y2="240" stroke="rgba(193,78,131,0.25)" strokeWidth="1" strokeDasharray="4 3"/>

      <rect x="148" y="54" width="44" height="54" rx="5" fill="rgba(193,78,131,0.12)" stroke="rgba(193,78,131,0.55)" strokeWidth="1.4"/>
      <line x1="158" y1="72" x2="182" y2="72" stroke="rgba(193,78,131,0.7)" strokeWidth="1.2"/>
      <line x1="158" y1="79" x2="182" y2="79" stroke="rgba(193,78,131,0.5)" strokeWidth="1.2"/>
      <line x1="158" y1="86" x2="174" y2="86" stroke="rgba(193,78,131,0.4)" strokeWidth="1.2"/>
      <polyline points="183,54 192,54 192,64" stroke="rgba(193,78,131,0.5)" strokeWidth="1.2" fill="none"/>

      <rect x="52" y="122" width="38" height="48" rx="5" fill="rgba(138,47,91,0.12)" stroke="rgba(138,47,91,0.5)" strokeWidth="1.2"/>
      <line x1="61" y1="137" x2="81" y2="137" stroke="rgba(138,47,91,0.7)" strokeWidth="1.2"/>
      <line x1="61" y1="144" x2="81" y2="144" stroke="rgba(138,47,91,0.5)" strokeWidth="1.2"/>
      <line x1="61" y1="151" x2="74" y2="151" stroke="rgba(138,47,91,0.4)" strokeWidth="1.2"/>

      <rect x="248" y="122" width="38" height="48" rx="5" fill="rgba(138,47,91,0.12)" stroke="rgba(138,47,91,0.5)" strokeWidth="1.2"/>
      <line x1="257" y1="137" x2="277" y2="137" stroke="rgba(138,47,91,0.7)" strokeWidth="1.2"/>
      <line x1="257" y1="144" x2="277" y2="144" stroke="rgba(138,47,91,0.5)" strokeWidth="1.2"/>
      <line x1="257" y1="151" x2="270" y2="151" stroke="rgba(138,47,91,0.4)" strokeWidth="1.2"/>

      <rect x="22" y="210" width="32" height="40" rx="4" fill="rgba(53,29,49,0.3)" stroke="rgba(193,78,131,0.3)" strokeWidth="1"/>
      <line x1="30" y1="222" x2="46" y2="222" stroke="rgba(193,78,131,0.5)" strokeWidth="1"/>
      <line x1="30" y1="229" x2="46" y2="229" stroke="rgba(193,78,131,0.35)" strokeWidth="1"/>

      <rect x="151" y="214" width="38" height="48" rx="4" fill="rgba(53,29,49,0.3)" stroke="rgba(193,78,131,0.3)" strokeWidth="1"/>
      <line x1="159" y1="226" x2="181" y2="226" stroke="rgba(193,78,131,0.5)" strokeWidth="1"/>
      <line x1="159" y1="233" x2="181" y2="233" stroke="rgba(193,78,131,0.35)" strokeWidth="1"/>

      <rect x="283" y="210" width="32" height="40" rx="4" fill="rgba(53,29,49,0.3)" stroke="rgba(193,78,131,0.3)" strokeWidth="1"/>
      <line x1="291" y1="222" x2="307" y2="222" stroke="rgba(193,78,131,0.5)" strokeWidth="1"/>
      <line x1="291" y1="229" x2="307" y2="229" stroke="rgba(193,78,131,0.35)" strokeWidth="1"/>

      <circle cx="170" cy="155" r="18" fill="rgba(193,78,131,0.18)" stroke="rgba(193,78,131,0.6)" strokeWidth="1.5"/>
      <polyline points="162,155 168,162 180,148" stroke="#C14E83" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>

      <circle cx="80" cy="200" r="8" fill="rgba(193,78,131,0.15)" stroke="rgba(193,78,131,0.4)" strokeWidth="1"/>
      <polyline points="76,200 79,203 85,196" stroke="#C14E83" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" fill="none"/>

      <circle cx="260" cy="200" r="8" fill="rgba(193,78,131,0.15)" stroke="rgba(193,78,131,0.4)" strokeWidth="1"/>
      <polyline points="256,200 259,203 265,196" stroke="#C14E83" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    </svg>
  );
}

// ─── Animated background shapes ───────────────────────────────────────────────

function LeftPanelBg() {
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      <div style={{
        position: 'absolute', top: '-60px', left: '-40px',
        width: 320, height: 320,
        background: 'radial-gradient(circle, rgba(193,78,131,0.12) 0%, transparent 70%)',
        borderRadius: '50%',
      }} />
      <div style={{
        position: 'absolute', bottom: '-40px', right: '-40px',
        width: 260, height: 260,
        background: 'radial-gradient(circle, rgba(138,47,91,0.15) 0%, transparent 70%)',
        borderRadius: '50%',
      }} />
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.06 }} aria-hidden="true">
        <defs>
          <pattern id="lg-grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#C14E83" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#lg-grid)"/>
      </svg>
    </div>
  );
}

function FeaturePill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 7,
      background: 'rgba(255,255,255,0.06)',
      border: '1px solid rgba(193,78,131,0.22)',
      borderRadius: 8, padding: '6px 12px',
    }}>
      <span style={{ color: '#C14E83', display: 'flex' }}>{icon}</span>
      <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.78)', fontWeight: 500, letterSpacing: '0.01em' }}>
        {label}
      </span>
    </div>
  );
}

// ─── Main Login Screen ────────────────────────────────────────────────────────

export const LoginScreen: React.FC<LoginScreenProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'signin' | 'register'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);
  const [configNotice, setConfigNotice] = useState<string | null>(null);
  const [emailTouched, setEmailTouched] = useState(false);
  const [pwTouched, setPwTouched] = useState(false);
  const [nameTouched, setNameTouched] = useState(false);
  const [confirmTouched, setConfirmTouched] = useState(false);
  const [visible, setVisible] = useState(false);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);

  const nameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const confirmPasswordId = useId();

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 40);

    // Fetch auth config and dynamically ensure Google Identity Services is ready
    fetchAuthConfig()
      .then((cfg) => {
        setAuthConfig(cfg);
        if (cfg.googleClientId && !document.getElementById('google-gsi-client')) {
          const s = document.createElement('script');
          s.id = 'google-gsi-client';
          s.src = 'https://accounts.google.com/gsi/client';
          s.async = true;
          s.defer = true;
          document.head.appendChild(s);
        }
      })
      .catch(() => {});

    return () => clearTimeout(t);
  }, []);

  // ── Validation ──────────────────────────────────────────────────────────────
  const emailError = emailTouched && !email.trim()
    ? 'Email is required.'
    : emailTouched && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    ? 'Enter a valid email address.'
    : null;

  const pwError = pwTouched && !password
    ? 'Password is required.'
    : pwTouched && mode === 'register' && password.length < 8
    ? 'Password must be at least 8 characters long.'
    : null;

  const nameError = mode === 'register' && nameTouched && (!name.trim() || name.trim().length < 2)
    ? 'Full name is required (min 2 chars).'
    : null;

  const confirmError = mode === 'register' && confirmTouched && password !== confirmPassword
    ? 'Passwords do not match.'
    : null;

  const canSubmit = mode === 'signin'
    ? !emailError && !pwError && email.trim() && password && !loading
    : !emailError && !pwError && !nameError && !confirmError && email.trim() && password && name.trim() && !loading;

  // ── Email/Password Submit ───────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailTouched(true);
    setPwTouched(true);
    if (mode === 'register') {
      setNameTouched(true);
      setConfirmTouched(true);
      if (password !== confirmPassword) return;
    }
    if (!email.trim() || !password) return;

    setLoading(true);
    setError(null);
    setPendingNotice(null);
    setConfigNotice(null);

    if (mode === 'signin') {
      const result = await loginReviewer(email.trim(), password);
      setLoading(false);
      if (result.success && result.reviewer) {
        setVisible(false);
        setTimeout(() => onAuthenticated(result.reviewer!), 260);
      } else {
        setError(result.error ?? 'Sign-in failed. Please check your credentials.');
      }
    } else {
      const result = await registerReviewer(email.trim(), password, name.trim());
      setLoading(false);
      if (result.success && result.reviewer) {
        setVisible(false);
        setTimeout(() => onAuthenticated(result.reviewer!), 260);
      } else {
        const msg = result.error ?? 'Registration failed.';
        if (msg.toLowerCase().includes('pending') || msg.toLowerCase().includes('restricted')) {
          setPendingNotice(msg);
        } else {
          setError(msg);
        }
      }
    }
  };

  // ── Google OAuth Trigger ───────────────────────────────────────────────────
  const handleGoogleSignIn = () => {
    setError(null);
    setPendingNotice(null);
    setConfigNotice(null);

    const clientId = authConfig?.googleClientId || (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID;

    if (!clientId) {
      setConfigNotice(
        'Google OAuth client ID is not configured on this server. Set GOOGLE_CLIENT_ID or sign in below with your approved email.'
      );
      return;
    }

    const google = (window as any).google;
    if (!google?.accounts?.id) {
      setError('Google Identity Services SDK is loading. Please try again in a moment.');
      return;
    }

    // Shared callback — handles the ID token returned by any GSI flow
    const handleCredential = async (response: { credential: string }) => {
      setLoading(true);
      setError(null);
      setPendingNotice(null);
      const res = await loginWithGoogle(response.credential, clientId);
      setLoading(false);

      if (res.success && res.reviewer) {
        setVisible(false);
        setTimeout(() => onAuthenticated(res.reviewer!), 260);
      } else {
        const errDetail = res.error ?? 'Google authentication failed.';
        if (
          errDetail.toLowerCase().includes('restricted') ||
          errDetail.toLowerCase().includes('not in the approved') ||
          errDetail.toLowerCase().includes('not approved')
        ) {
          setError(`Access denied: ${errDetail}`);
        } else {
          setError(errDetail);
        }
      }
    };

    try {
      // Initialize GSI with our callback
      google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredential,
        // Use "select_account" UX hint so users can pick a Google account even
        // if they are already signed in — avoids silent account auto-selection.
        ux_mode: 'popup',
      });

      // Try One Tap first. If it is suppressed (localhost, dismissed, 3P cookies
      // disabled, or the user is not signed into Google in the browser) we fall
      // back to the GSI renderButton flow which opens a reliable popup window.
      google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          // One Tap was suppressed — render the GSI button into a hidden
          // container and programmatically click it to open the popup.
          const containerId = '__gsi_btn_fallback__';
          let container = document.getElementById(containerId);
          if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'position:fixed;opacity:0;pointer-events:none;top:-9999px;left:-9999px;';
            document.body.appendChild(container);
          }
          google.accounts.id.renderButton(container, {
            type: 'standard',
            theme: 'outline',
            size: 'large',
          });
          // Click the rendered button to trigger the popup
          const btn = container.querySelector('div[role="button"]') as HTMLElement | null;
          if (btn) btn.click();
        }
      });
    } catch {
      setError('Failed to initialize Google Sign-In. Please try again.');
    }
  };

  // ── Input style factory ─────────────────────────────────────────────────────
  const inputBase: React.CSSProperties = {
    width: '100%',
    background: '#FFFAFC',
    border: '1.5px solid #ECD9E2',
    borderRadius: 10,
    padding: '11px 14px',
    fontSize: 13.5,
    color: '#351D31',
    outline: 'none',
    fontFamily: 'inherit',
    transition: 'border-color 0.18s, box-shadow 0.18s',
    boxSizing: 'border-box',
  };

  const inputError: React.CSSProperties = {
    ...inputBase,
    borderColor: '#E74C6E',
    boxShadow: '0 0 0 3px rgba(231,76,110,0.12)',
  };

  return (
    <>
      <style>{`
        @keyframes loginFadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulseRing {
          0%,100% { box-shadow: 0 0 0 0 rgba(193,78,131,0.25); }
          50%      { box-shadow: 0 0 0 8px rgba(193,78,131,0); }
        }
        .ls-input:focus {
          border-color: #C14E83 !important;
          box-shadow: 0 0 0 3px rgba(193,78,131,0.15) !important;
        }
        .ls-btn-primary:hover:not(:disabled) {
          transform: translateY(-1px) !important;
          box-shadow: 0 8px 24px rgba(193,78,131,0.38) !important;
        }
        .ls-btn-google:hover:not(:disabled) {
          border-color: #C14E83 !important;
          background: #FFF7FA !important;
          box-shadow: 0 4px 14px rgba(193,78,131,0.16) !important;
        }
        .ls-btn-primary:active:not(:disabled) {
          transform: translateY(0) !important;
        }
        .ls-btn-primary:disabled {
          opacity: 0.72;
          cursor: not-allowed;
        }
        .ls-pw-toggle:hover {
          color: #C14E83 !important;
        }
        @media (max-width: 860px) {
          .ls-left-panel { display: none !important; }
          .ls-mobile-brand { display: flex !important; }
          .ls-card {
            max-width: 480px !important;
            margin: 16px auto !important;
            border-radius: 18px !important;
          }
          .ls-right-panel {
            padding: 24px 20px !important;
          }
        }
      `}</style>

      <div style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: '#180B16',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px 16px', overflowY: 'auto',
      }}>
        <div
          className="ls-card"
          style={{
            width: '100%', maxWidth: 940, minHeight: 560,
            background: '#fff', borderRadius: 24,
            boxShadow: '0 24px 64px rgba(0,0,0,0.48), 0 0 0 1px rgba(193,78,131,0.25)',
            display: 'flex', overflow: 'hidden',
            opacity: visible ? 1 : 0,
            transform: visible ? 'translateY(0)' : 'translateY(16px)',
            transition: 'opacity 0.28s cubic-bezier(0.16, 1, 0.3, 1), transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          {/* ── Left panel: Branding & Visuals ─────────────────────────────── */}
          <div
            className="ls-left-panel"
            style={{
              flex: '0 0 44%',
              background: 'linear-gradient(150deg, #351D31 0%, #200D1D 55%, #180B16 100%)',
              position: 'relative', overflow: 'hidden',
              padding: 'clamp(28px, 4vh, 44px) clamp(24px, 3.2vw, 38px)',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            }}
          >
            <LeftPanelBg />

            {/* Top brand */}
            <div style={{ position: 'relative', zIndex: 2 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 18 }}>
                <div style={{
                  width: 42, height: 42, borderRadius: 12,
                  background: 'linear-gradient(135deg, #8A2F5B 0%, #C14E83 100%)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 4px 16px rgba(193,78,131,0.4)',
                }}>
                  <ShieldCheck size={22} color="#fff" strokeWidth={1.8} />
                </div>
                <div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: '#fff', letterSpacing: '-0.01em' }}>
                    VerifyAI
                  </div>
                  <div style={{ fontSize: 10, color: '#C14E83', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>
                    AICTE Regulatory Engine
                  </div>
                </div>
              </div>

              <h1 style={{
                fontFamily: "'DM Serif Display', Georgia, serif",
                fontSize: 'clamp(22px, 2.5vw, 28px)',
                fontWeight: 400, color: '#fff',
                lineHeight: 1.25, margin: '0 0 10px',
                letterSpacing: '-0.015em',
              }}>
                Regulatory Document Verification & Audit
              </h1>
              <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.68)', lineHeight: 1.5, margin: 0 }}>
                Automated compliance checking, cross-document reconciliation, and tamper detection.
              </p>
            </div>

            {/* Center: Network diagram */}
            <div style={{
              flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative', zIndex: 2, padding: '4px 0', minHeight: 0,
            }}>
              <DocumentNetworkSVG />
            </div>

            {/* Feature badges */}
            <div style={{ position: 'relative', zIndex: 2, display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
              <FeaturePill icon={<GitCompare size={12} />} label="Cross-Doc Reconciliation" />
              <FeaturePill icon={<FileSearch size={12} />} label="Tamper Detection" />
              <FeaturePill icon={<CheckCircle2 size={12} />} label="Restricted Allowlist" />
            </div>

            {/* Footer descriptor */}
            <div style={{
              position: 'relative', zIndex: 2,
              borderTop: '1px solid rgba(193,78,131,0.18)',
              paddingTop: 10,
            }}>
              <p style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.4)', margin: 0, letterSpacing: '0.03em' }}>
                AICTE VerifyAI · Smart India Hackathon 2026 · Restricted Access
              </p>
            </div>
          </div>

          {/* ── Right panel: Auth Form ──────────────────────────────────────── */}
          <div
            className="ls-right-panel"
            style={{
              flex: 1,
              background: '#FFFAFC',
              padding: 'clamp(24px, 3.4vh, 38px) clamp(24px, 3.8vw, 44px)',
              display: 'flex', flexDirection: 'column',
              justifyContent: 'center',
            }}
          >
            {/* Header */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <h2 style={{
                  fontFamily: "'DM Serif Display', Georgia, serif",
                  fontSize: 'clamp(22px, 2.6vw, 28px)',
                  fontWeight: 400, color: '#351D31',
                  margin: 0, letterSpacing: '-0.015em',
                }}>
                  {mode === 'signin' ? 'Welcome back' : 'Create Account'}
                </h2>
                <div style={{
                  display: 'flex', background: '#F5EBF0', borderRadius: 8, padding: 2,
                }}>
                  <button
                    type="button"
                    onClick={() => { setMode('signin'); setError(null); setPendingNotice(null); }}
                    style={{
                      background: mode === 'signin' ? '#8A2F5B' : 'transparent',
                      color: mode === 'signin' ? '#fff' : '#896F81',
                      border: 'none', borderRadius: 6, padding: '4px 10px',
                      fontSize: 11.5, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s',
                    }}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => { setMode('register'); setError(null); setPendingNotice(null); }}
                    style={{
                      background: mode === 'register' ? '#8A2F5B' : 'transparent',
                      color: mode === 'register' ? '#fff' : '#896F81',
                      border: 'none', borderRadius: 6, padding: '4px 10px',
                      fontSize: 11.5, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s',
                    }}
                  >
                    Register
                  </button>
                </div>
              </div>
              <p style={{ fontSize: 13, color: '#896F81', margin: 0, lineHeight: 1.4 }}>
                {mode === 'signin'
                  ? 'Sign in to access your AICTE regulatory compliance workspace.'
                  : 'Register reviewer account. Access is restricted to approved emails.'}
              </p>
            </div>

            {/* Google Sign-In Button */}
            <button
              type="button"
              className="ls-btn-google"
              onClick={handleGoogleSignIn}
              disabled={loading}
              style={{
                width: '100%',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                background: '#fff',
                border: '1.5px solid #ECD9E2',
                borderRadius: 10, padding: '10px 16px',
                fontSize: 13.5, fontWeight: 600, color: '#351D31',
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                transition: 'all 0.18s ease',
                marginBottom: 16,
              }}
            >
              <GoogleLogoSVG />
              <span>{mode === 'signin' ? 'Continue with Google' : 'Sign up with Google'}</span>
            </button>

            {/* SIH Judge Demo Account Banner — sign-in mode only */}
            {mode === 'signin' && (
              <div style={{
                background: 'linear-gradient(135deg, rgba(138,47,91,0.08) 0%, rgba(193,78,131,0.06) 100%)',
                border: '1.5px solid rgba(193,78,131,0.28)',
                borderRadius: 10, padding: '10px 13px', marginBottom: 16,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
                  <ShieldCheck size={14} style={{ color: '#8A2F5B', flexShrink: 0 }} />
                  <span style={{ fontSize: 11.5, fontWeight: 700, color: '#8A2F5B', letterSpacing: '0.02em' }}>
                    SIH Judge Demo Account
                  </span>
                  <span style={{
                    fontSize: 9.5, fontWeight: 700, color: '#C14E83',
                    background: 'rgba(193,78,131,0.12)', borderRadius: 4,
                    padding: '1px 5px', letterSpacing: '0.04em',
                  }}>
                    PRE-FILLED
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#55223F', lineHeight: 1.55, marginBottom: 7 }}>
                  Adhav's reviewer credentials (<code>adhav.sri123@gmail.com</code>) are pre-filled below. Click{' '}
                  <strong style={{ color: '#8A2F5B' }}>Sign In</strong> directly to access the full
                  AICTE VerifyAI reviewer workspace with synthetic demonstration data.
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginBottom: 6 }}>
                  <div style={{ fontSize: 10.5, color: '#896F81' }}>
                    <span style={{ fontWeight: 600, color: '#55223F' }}>Email: </span>
                    <code style={{ fontSize: 10.5, color: '#8A2F5B' }}>{DEMO_EMAIL}</code>
                  </div>
                  <div style={{ fontSize: 10.5, color: '#896F81' }}>
                    <span style={{ fontWeight: 600, color: '#55223F' }}>Password: </span>
                    <code style={{ fontSize: 10.5, color: '#8A2F5B' }}>{DEMO_PASSWORD}</code>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => { setEmail(DEMO_EMAIL); setPassword(DEMO_PASSWORD); setError(null); setPendingNotice(null); }}
                  style={{
                    fontSize: 10.5, color: '#C14E83', fontWeight: 600,
                    background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                    textDecoration: 'underline', textUnderlineOffset: 2,
                  }}
                >
                  ↺ Restore demo credentials
                </button>
              </div>
            )}

            {/* Divider */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
            }}>
              <div style={{ flex: 1, height: 1, background: '#ECD9E2' }} />
              <span style={{ fontSize: 11, color: '#9E8290', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                or with work email
              </span>
              <div style={{ flex: 1, height: 1, background: '#ECD9E2' }} />
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} noValidate>
              {/* Name field (register only) */}
              {mode === 'register' && (
                <div style={{ marginBottom: 12 }}>
                  <label htmlFor={nameId} style={{ display: 'block', fontSize: 11.5, fontWeight: 600, color: '#55223F', marginBottom: 4 }}>
                    Full Name
                  </label>
                  <div style={{ position: 'relative' }}>
                    <span style={{
                      position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                      color: nameError ? '#E74C6E' : '#B8929E', pointerEvents: 'none',
                    }}>
                      <User size={14} />
                    </span>
                    <input
                      id={nameId}
                      className="ls-input"
                      type="text"
                      autoComplete="name"
                      value={name}
                      onChange={e => { setName(e.target.value); setError(null); }}
                      onBlur={() => setNameTouched(true)}
                      placeholder="Namith Singh"
                      style={{
                        ...(nameError ? inputError : inputBase),
                        padding: '10px 12px 10px 36px',
                      }}
                      disabled={loading}
                    />
                  </div>
                  {nameError && (
                    <p style={{ margin: '3px 0 0', fontSize: 11, color: '#E74C6E', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <AlertCircle size={11} /> {nameError}
                    </p>
                  )}
                </div>
              )}

              {/* Email field */}
              <div style={{ marginBottom: 12 }}>
                <label htmlFor={emailId} style={{ display: 'block', fontSize: 11.5, fontWeight: 600, color: '#55223F', marginBottom: 4 }}>
                  Work Email
                </label>
                <div style={{ position: 'relative' }}>
                  <span style={{
                    position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                    color: emailError ? '#E74C6E' : '#B8929E', pointerEvents: 'none',
                  }}>
                    <Mail size={14} />
                  </span>
                  <input
                    id={emailId}
                    className="ls-input"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={e => { setEmail(e.target.value); setError(null); }}
                    onBlur={() => setEmailTouched(true)}
                    placeholder="adhav.sri123@gmail.com"
                    style={{
                      ...(emailError ? inputError : inputBase),
                      padding: '10px 12px 10px 36px',
                    }}
                    disabled={loading}
                  />
                </div>
                {emailError && (
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: '#E74C6E', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertCircle size={11} /> {emailError}
                  </p>
                )}
              </div>

              {/* Password field */}
              <div style={{ marginBottom: mode === 'register' ? 12 : 16 }}>
                <label htmlFor={passwordId} style={{ display: 'block', fontSize: 11.5, fontWeight: 600, color: '#55223F', marginBottom: 4 }}>
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <span style={{
                    position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                    color: pwError ? '#E74C6E' : '#B8929E', pointerEvents: 'none',
                  }}>
                    <Lock size={14} />
                  </span>
                  <input
                    id={passwordId}
                    className="ls-input"
                    type={showPw ? 'text' : 'password'}
                    autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                    value={password}
                    onChange={e => { setPassword(e.target.value); setError(null); }}
                    onBlur={() => setPwTouched(true)}
                    placeholder="••••••••••••"
                    style={{
                      ...(pwError ? inputError : inputBase),
                      padding: '10px 40px 10px 36px',
                    }}
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="ls-pw-toggle"
                    onClick={() => setShowPw(v => !v)}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                    style={{
                      position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: '#B8929E', padding: 4, display: 'flex', alignItems: 'center',
                    }}
                  >
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {pwError && (
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: '#E74C6E', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertCircle size={11} /> {pwError}
                  </p>
                )}
              </div>

              {/* Confirm Password (register only) */}
              {mode === 'register' && (
                <div style={{ marginBottom: 16 }}>
                  <label htmlFor={confirmPasswordId} style={{ display: 'block', fontSize: 11.5, fontWeight: 600, color: '#55223F', marginBottom: 4 }}>
                    Confirm Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <span style={{
                      position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                      color: confirmError ? '#E74C6E' : '#B8929E', pointerEvents: 'none',
                    }}>
                      <Lock size={14} />
                    </span>
                    <input
                      id={confirmPasswordId}
                      className="ls-input"
                      type={showPw ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={e => { setConfirmPassword(e.target.value); setError(null); }}
                      onBlur={() => setConfirmTouched(true)}
                      placeholder="••••••••••••"
                      style={{
                        ...(confirmError ? inputError : inputBase),
                        padding: '10px 12px 10px 36px',
                      }}
                      disabled={loading}
                    />
                  </div>
                  {confirmError && (
                    <p style={{ margin: '3px 0 0', fontSize: 11, color: '#E74C6E', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <AlertCircle size={11} /> {confirmError}
                    </p>
                  )}
                </div>
              )}

              {/* Alerts: Pending Approval */}
              {pendingNotice && (
                <div style={{
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                  background: '#FFFBEB',
                  border: '1px solid #FCD34D',
                  borderRadius: 9, padding: '9px 12px', marginBottom: 14,
                }}>
                  <Clock size={15} style={{ color: '#D97706', flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#92400E', marginBottom: 2 }}>
                      Access Pending Approval
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: '#78350F', lineHeight: 1.4 }}>
                      {pendingNotice}
                    </p>
                  </div>
                </div>
              )}

              {/* Alerts: Config Notice */}
              {configNotice && (
                <div style={{
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                  background: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  borderRadius: 9, padding: '9px 12px', marginBottom: 14,
                }}>
                  <Info size={15} style={{ color: '#2563EB', flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#1E40AF', marginBottom: 2 }}>
                      OAuth Configuration
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: '#1E3A8A', lineHeight: 1.4 }}>
                      {configNotice}
                    </p>
                  </div>
                </div>
              )}

              {/* Alerts: Server Error */}
              {error && (
                <div style={{
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                  background: 'rgba(231,76,110,0.07)',
                  border: '1px solid rgba(231,76,110,0.25)',
                  borderRadius: 9, padding: '9px 12px', marginBottom: 14,
                }}>
                  <AlertCircle size={14} style={{ color: '#C0294A', flexShrink: 0, marginTop: 1 }} />
                  <p style={{ margin: 0, fontSize: 12, color: '#9E1628', lineHeight: 1.4 }}>{error}</p>
                </div>
              )}

              {/* Submit button */}
              <button
                type="submit"
                className="ls-btn-primary"
                disabled={!canSubmit}
                style={{
                  width: '100%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  background: 'linear-gradient(135deg, #8A2F5B 0%, #B0406F 50%, #C14E83 100%)',
                  color: '#fff', border: 'none', borderRadius: 10,
                  padding: '11px 20px', fontSize: 13.5, fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  letterSpacing: '0.01em',
                  boxShadow: '0 6px 18px rgba(193,78,131,0.28)',
                  transition: 'transform 0.17s ease, box-shadow 0.17s ease, opacity 0.15s',
                  fontFamily: 'inherit',
                  marginBottom: 14,
                }}
              >
                {loading ? (
                  <>
                    <Loader2 size={15} style={{ animation: 'spin 0.8s linear infinite' }} />
                    {mode === 'signin' ? 'Signing in…' : 'Creating account…'}
                  </>
                ) : (
                  <>
                    {mode === 'signin' ? 'Sign In' : 'Create Account'}
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </form>

            {/* Switch Mode Footer */}
            <div style={{ textAlign: 'center', marginBottom: 14 }}>
              {mode === 'signin' ? (
                <span style={{ fontSize: 12, color: '#896F81' }}>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setMode('register'); setError(null); setPendingNotice(null); }}
                    style={{
                      background: 'none', border: 'none', padding: 0,
                      color: '#C14E83', fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    Create account
                  </button>
                </span>
              ) : (
                <span style={{ fontSize: 12, color: '#896F81' }}>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setMode('signin'); setError(null); setPendingNotice(null); }}
                    style={{
                      background: 'none', border: 'none', padding: 0,
                      color: '#C14E83', fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>

            {/* Prototype & Access Restriction Disclosure */}
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              background: '#FFFBF0',
              border: '1px solid rgba(253,186,116,0.45)',
              borderRadius: 8, padding: '7px 11px',
            }}>
              <FlaskConical size={12} style={{ color: '#92400E', flexShrink: 0, marginTop: 1.5 }} />
              <p style={{ fontSize: 10.5, color: '#78350F', margin: 0, lineHeight: 1.45 }}>
                <strong>SIH 2026 Demo.</strong> Use the pre-filled demo account above
                (<code>{DEMO_EMAIL}</code>) to explore the full reviewer workspace.
                New registrations require administrator approval.
              </p>
            </div>

            {/* SIH Footer */}
            <p style={{
              fontSize: 10.5, color: '#C0A8B4',
              textAlign: 'center', letterSpacing: '0.02em', margin: '10px 0 0',
            }}>
              AICTE VerifyAI · Smart India Hackathon 2026
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </>
  );
};
