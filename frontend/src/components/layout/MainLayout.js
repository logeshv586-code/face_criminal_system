import React from 'react';
import useAuthStore from '../../store/authStore';
import {
  LayoutDashboard, Users, Camera, Image, Bell, Search, Video, MonitorPlay,
  LogOut, ChevronLeft, ChevronRight, ChevronDown, Menu, Settings, Palette,
  Database, FileText, Building2, UserPlus, ShieldCheck, X
} from 'lucide-react';
import './MainLayout.css';

const ROLE_ALLOWED = {
  SuperAdmin: ['dashboard','companies','registration','matching','reports','gallery','events','camera','stream-viewer','video','users','settings','backup'],
  Admin: ['dashboard','registration','matching','reports','gallery','events','camera','stream-viewer','video','users','settings','backup'],
  Supervisor: ['dashboard','registration','matching','reports','gallery','events','camera','stream-viewer','video'],
};

const normalizeMenu = (menu) => ({
  cameras: 'camera', admin: 'users', backupmgmt: 'backup', analytics: 'dashboard',
  'week-report': 'reports', 'month-report': 'reports'
}[menu] || menu);

const ACCENTS = [
  { id: 'sapphire', label: 'Sapphire', color: '#2563eb' },
  { id: 'teal', label: 'Teal', color: '#0f9d94' },
  { id: 'indigo', label: 'Indigo', color: '#6366f1' },
  { id: 'graphite', label: 'Graphite', color: '#475569' },
];

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'companies', label: 'Companies', icon: Building2 },
  { id: 'registration', label: 'Criminal Database', icon: UserPlus },
  { id: 'matching', label: 'Face Matching', icon: Search, subItems: [
    { id: 'matching-1to1', label: 'One to One' },
    { id: 'matching-1toM', label: 'One to Many' },
  ]},
  { id: 'reports', label: 'Recognition Reports', icon: FileText, subItems: [
    { id: 'week-report', label: 'Weekly Report' },
    { id: 'month-report', label: 'Monthly Report' },
  ]},
  { id: 'gallery', label: 'Gallery', icon: Image },
  { id: 'events', label: 'Events', icon: Bell },
  { id: 'camera', label: 'Cameras', icon: Camera },
  { id: 'stream-viewer', label: 'Live Streams', icon: MonitorPlay },
  { id: 'video', label: 'Video Processing', icon: Video },
  { id: 'users', label: 'Users & Roles', icon: Users },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'backup', label: 'Backup', icon: Database },
];

const MainLayout = ({ children, activeTab, onTabChange }) => {
  const { user, logout, isLicenseExpired } = useAuthStore();
  const [collapsed, setCollapsed] = React.useState(() => localStorage.getItem('frs-sidebar-collapsed') === '1');
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [accentOpen, setAccentOpen] = React.useState(false);
  const [expanded, setExpanded] = React.useState({ matching: true, reports: false });
  const [accent, setAccent] = React.useState(() => localStorage.getItem('frs-accent') || 'sapphire');

  React.useEffect(() => {
    localStorage.setItem('frs-sidebar-collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  React.useEffect(() => {
    document.documentElement.setAttribute('data-accent', accent);
    localStorage.setItem('frs-accent', accent);
  }, [accent]);

  const roleAllowed = new Set(ROLE_ALLOWED[user?.role] || ['dashboard']);
  const assigned = (user?.assigned_menus || []).map(normalizeMenu);
  const assignedSet = new Set(assigned);
  const hasAssignedRestrictions = assigned.length > 0;

  const visibleTabs = TABS.filter((tab) => {
    if (!roleAllowed.has(tab.id)) return false;
    if (!hasAssignedRestrictions) return true;
    return assignedSet.has(tab.id);
  });

  const currentTab = TABS.find(tab => tab.id === activeTab || tab.subItems?.some(item => item.id === activeTab));
  const pageTitle = currentTab?.subItems?.find(item => item.id === activeTab)?.label || currentTab?.label || 'Dashboard';

  const changeTab = (id) => {
    onTabChange(id);
    setMobileOpen(false);
  };

  const initials = (user?.username || 'FRS').slice(0,2).toUpperCase();

  return (
    <div className={`main-layout ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      {mobileOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className="sidebar">
        <div className="sidebar-header">
          <button className="brand" onClick={() => changeTab('dashboard')} title="Face Recognition System">
            <span className="brand-mark"><ShieldCheck size={20} /></span>
            {!collapsed && <span className="brand-copy"><strong>FRS</strong><small>Criminal Identification</small></span>}
          </button>
          <button className="collapse-btn desktop-only" onClick={() => setCollapsed(v => !v)} aria-label="Toggle sidebar">
            {collapsed ? <ChevronRight size={17}/> : <ChevronLeft size={17}/>} 
          </button>
          <button className="collapse-btn mobile-only" onClick={() => setMobileOpen(false)} aria-label="Close sidebar"><X size={18}/></button>
        </div>

        <div className="user-profile-section">
          <div className="user-avatar">{initials}</div>
          {!collapsed && <div className="user-info">
            <span className="user-name">{user?.username || 'Operator'}</span>
            <span className="user-role-badge">{user?.role || 'User'}</span>
          </div>}
        </div>

        <nav className="sidebar-nav">
          {!collapsed && <div className="nav-section-label">Workspace</div>}
          {visibleTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === activeTab || tab.subItems?.some(item => item.id === activeTab);
            return (
              <div className="nav-group" key={tab.id}>
                <button
                  className={`nav-item ${isActive ? 'active' : ''}`} data-tooltip={tab.label}
                  onClick={() => tab.subItems ? (collapsed ? changeTab(tab.subItems[0].id) : setExpanded(prev => ({...prev, [tab.id]: !prev[tab.id]}))) : changeTab(tab.id)}
                  title={collapsed ? tab.label : undefined}
                >
                  <span className="nav-icon"><Icon size={18}/></span>
                  {!collapsed && <><span className="nav-label">{tab.label}</span>{tab.subItems && <ChevronDown size={15} className={`nav-chevron ${expanded[tab.id] ? 'open' : ''}`}/>}</>}
                </button>
                {!collapsed && tab.subItems && expanded[tab.id] && (
                  <div className="nav-subitems">
                    {tab.subItems.map(item => (
                      <button key={item.id} className={`nav-subitem ${activeTab === item.id ? 'active' : ''}`} onClick={() => changeTab(item.id)}>
                        <span className="sub-dot" />{item.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {!collapsed && <div className="sidebar-health"><span className="status-dot"/><span>Recognition service</span><strong>Ready</strong></div>}
          <button className="logout-btn" onClick={logout} title="Sign out"><LogOut size={17}/>{!collapsed && <span>Sign out</span>}</button>
        </div>
      </aside>

      <section className="content-area">
        <header className="top-header">
          <div className="header-left">
            <button className="mobile-menu-btn" onClick={() => setMobileOpen(true)}><Menu size={20}/></button>
            <div className="page-heading"><h1>{pageTitle}</h1><span>Face Recognition System</span></div>
          </div>
          <div className="header-right">
            {isLicenseExpired?.() && <div className="license-warning">License expired</div>}
            <div className="system-status"><span className="status-dot"/><span className="status-text">System online</span></div>
            <div className="theme-switcher-container">
              <button className="theme-toggle-btn" onClick={() => setAccentOpen(v => !v)} title="Accent color"><Palette size={18}/></button>
              {accentOpen && <div className="theme-menu">
                <div className="theme-menu-header">Accent color</div>
                {ACCENTS.map(item => (
                  <button key={item.id} className={`theme-option ${accent === item.id ? 'active' : ''}`} onClick={() => {setAccent(item.id); setAccentOpen(false);}}>
                    <span className="theme-preview" style={{background:item.color}} />
                    <span>{item.label}</span>
                    {accent === item.id && <span className="theme-check">✓</span>}
                  </button>
                ))}
              </div>}
            </div>
          </div>
        </header>
        <main className="content-wrapper">{children}</main>
      </section>
    </div>
  );
};

export default MainLayout;
