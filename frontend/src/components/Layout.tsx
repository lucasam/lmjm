import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface Breadcrumb {
  label: string;
  to?: string;
}

interface LayoutProps {
  children: ReactNode;
  breadcrumbs?: Breadcrumb[];
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
}

export default function Layout({
  children,
  breadcrumbs,
  userName,
  userEmail,
  onLogout,
}: LayoutProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="layout-root">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="header-left">
            <button
              type="button"
              className="hamburger-btn"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label={t('nav.menu', 'Menu')}
            >
              <span className="hamburger-line" />
              <span className="hamburger-line" />
              <span className="hamburger-line" />
            </button>
            <span
              className="logo"
              onClick={() => navigate('/')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate('/');
              }}
            >
              <span className="logo-icon">🌿</span> LMJM
            </span>
          </div>

          <div className="header-right">
            {(userName || userEmail) && (
              <span className="user-display">
                {userName || userEmail}
              </span>
            )}
            {onLogout && (
              <button type="button" className="logout-btn" onClick={onLogout}>
                {t('common.logout')}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Mobile nav overlay */}
      {menuOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setMenuOpen(false)}
          role="presentation"
        />
      )}

      {/* Mobile sidebar nav */}
      <nav
        className={`sidebar ${menuOpen ? 'sidebar-open' : 'sidebar-closed'}`}
        aria-hidden={!menuOpen}
      >
        <div className="sidebar-header">
          <span className="sidebar-brand">🌿 LMJM</span>
        </div>
        <NavLink
          label={`🏠  ${t('nav.home')}`}
          onClick={() => { navigate('/'); setMenuOpen(false); }}
        />
        <NavLink
          label={`🐄  ${t('nav.cattle')}`}
          onClick={() => { navigate('/cattle'); setMenuOpen(false); }}
        />
        <NavLink
          label={`🐖  ${t('nav.pigs')}`}
          onClick={() => { navigate('/pigs'); setMenuOpen(false); }}
        />
      </nav>

      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="breadcrumb-bar" aria-label="breadcrumb">
          {breadcrumbs.map((bc, i) => (
            <span key={i} style={{ display: 'inline' }}>
              {i > 0 && <span className="breadcrumb-sep">/</span>}
              {bc.to ? (
                <span
                  className="breadcrumb-link"
                  role="link"
                  tabIndex={0}
                  onClick={() => navigate(bc.to!)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') navigate(bc.to!);
                  }}
                >
                  {bc.label}
                </span>
              ) : (
                <span className="breadcrumb-current">{bc.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}

      {/* Main content */}
      <main className="main-content">{children}</main>
    </div>
  );
}

function NavLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="nav-link" onClick={onClick}>
      {label}
    </button>
  );
}
