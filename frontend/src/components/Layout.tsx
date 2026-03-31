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
    <div style={rootStyle}>
      {/* Header */}
      <header style={headerStyle}>
        <div style={headerInner}>
          <div style={headerLeft}>
            <button
              type="button"
              style={hamburgerBtn}
              onClick={() => setMenuOpen((o) => !o)}
              aria-label={t('nav.menu', 'Menu')}
            >
              <span style={hamburgerLine} />
              <span style={hamburgerLine} />
              <span style={hamburgerLine} />
            </button>
            <span
              style={logoStyle}
              onClick={() => navigate('/')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate('/');
              }}
            >
              LMJM
            </span>
          </div>

          <div style={headerRight}>
            {(userName || userEmail) && (
              <span style={userDisplay}>
                {userName || userEmail}
              </span>
            )}
            {onLogout && (
              <button type="button" style={logoutBtn} onClick={onLogout}>
                {t('common.logout')}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Mobile nav overlay */}
      {menuOpen && (
        <div
          style={overlayStyle}
          onClick={() => setMenuOpen(false)}
          role="presentation"
        />
      )}

      {/* Mobile sidebar nav */}
      <nav
        style={{
          ...sidebarStyle,
          transform: menuOpen ? 'translateX(0)' : 'translateX(-100%)',
        }}
        aria-hidden={!menuOpen}
      >
        <NavLink
          label={t('nav.home')}
          onClick={() => { navigate('/'); setMenuOpen(false); }}
        />
        <NavLink
          label={t('nav.cattle')}
          onClick={() => { navigate('/cattle'); setMenuOpen(false); }}
        />
        <NavLink
          label={t('nav.pigs')}
          onClick={() => { navigate('/pigs'); setMenuOpen(false); }}
        />
      </nav>

      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav style={breadcrumbBar} aria-label="breadcrumb">
          {breadcrumbs.map((bc, i) => (
            <span key={i} style={breadcrumbItem}>
              {i > 0 && <span style={breadcrumbSep}>/</span>}
              {bc.to ? (
                <span
                  style={breadcrumbLink}
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
                <span style={breadcrumbCurrent}>{bc.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}

      {/* Main content */}
      <main style={mainStyle}>{children}</main>
    </div>
  );
}

function NavLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" style={navLinkStyle} onClick={onClick}>
      {label}
    </button>
  );
}

/* ---- Styles ---- */

const rootStyle: React.CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
};

const headerStyle: React.CSSProperties = {
  backgroundColor: '#1976d2',
  color: '#fff',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

const headerInner: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 0.75rem',
  minHeight: '56px',
};

const headerLeft: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
};

const headerRight: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.75rem',
};

const hamburgerBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '10px',
  minWidth: '44px',
  minHeight: '44px',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  gap: '4px',
};

const hamburgerLine: React.CSSProperties = {
  display: 'block',
  width: '22px',
  height: '2px',
  backgroundColor: '#fff',
  borderRadius: '1px',
};

const logoStyle: React.CSSProperties = {
  fontWeight: 700,
  fontSize: '1.25rem',
  cursor: 'pointer',
  letterSpacing: '0.5px',
};

const userDisplay: React.CSSProperties = {
  fontSize: '0.85rem',
  maxWidth: '140px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const logoutBtn: React.CSSProperties = {
  background: 'rgba(255,255,255,0.15)',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.3)',
  borderRadius: '4px',
  padding: '8px 14px',
  minWidth: '44px',
  minHeight: '44px',
  cursor: 'pointer',
  fontSize: '0.85rem',
};

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  backgroundColor: 'rgba(0,0,0,0.4)',
  zIndex: 200,
};

const sidebarStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  bottom: 0,
  width: '260px',
  backgroundColor: '#fff',
  zIndex: 300,
  transition: 'transform 0.2s ease',
  paddingTop: '1rem',
  boxShadow: '2px 0 8px rgba(0,0,0,0.15)',
  display: 'flex',
  flexDirection: 'column',
};

const navLinkStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  background: 'none',
  border: 'none',
  padding: '14px 1.25rem',
  fontSize: '1rem',
  cursor: 'pointer',
  minHeight: '44px',
  color: '#333',
};

const breadcrumbBar: React.CSSProperties = {
  padding: '0.5rem 0.75rem',
  fontSize: '0.85rem',
  backgroundColor: '#fafafa',
  borderBottom: '1px solid #eee',
};

const breadcrumbItem: React.CSSProperties = {
  display: 'inline',
};

const breadcrumbSep: React.CSSProperties = {
  margin: '0 0.4rem',
  color: '#999',
};

const breadcrumbLink: React.CSSProperties = {
  color: '#1976d2',
  cursor: 'pointer',
  textDecoration: 'underline',
};

const breadcrumbCurrent: React.CSSProperties = {
  color: '#666',
};

const mainStyle: React.CSSProperties = {
  flex: 1,
  padding: '1rem 0.75rem',
  maxWidth: '1200px',
  width: '100%',
  margin: '0 auto',
  boxSizing: 'border-box',
};
