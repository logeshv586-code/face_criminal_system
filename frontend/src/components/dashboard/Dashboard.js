import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import {
  Users, UserCheck, UserX, Clock, Camera, AlertTriangle,
  Activity, Search, Filter, Download, ChevronLeft, ChevronRight,
  ShieldAlert, Server, Cpu, HardDrive, Maximize2, Loader2, FileText
} from 'lucide-react';
import useAuthStore from '../../store/authStore';
import FaceRecognitionAnalytics from './FaceRecognitionAnalytics';
import {
  fetchDashboardStats,
  fetchWeeklyAttendance,
  fetchCategories,
  fetchCriminals,
  fetchAlerts,
  fetchLiveRecognitions
} from '../../services/api';
import { API_BASE_URL } from '../../utils/apiConfig';
import './Dashboard.css';

// --- COMPONENTS ---

// 1. Animated Number Component
const AnimatedNumber = ({ value }) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    if (value === undefined || value === null) {
      setDisplayValue(0);
      return;
    }

    let start = 0;
    const end = parseInt(value.toString().replace(/,/g, ''), 10);
    if (isNaN(end)) {
      setDisplayValue(value);
      return;
    }
    const duration = 1000;
    const increment = end / (duration / 16);

    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        clearInterval(timer);
        setDisplayValue(end);
      } else {
        setDisplayValue(Math.floor(start));
      }
    }, 16);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{displayValue.toLocaleString()}</span>;
};

// 2. Advanced KPI Card
const KPICard = ({ title, value, trend, trendValue, icon: Icon, colorClass, data = [], gradient }) => (
  <div
    className={`glass-panel kpi-card`}
    style={{ borderColor: 'var(--border-color)' }}
  >
    <div className="kpi-card__top">
      <div className="kpi-card__content">
        <p className="kpi-card__label" style={{ color: 'var(--text-secondary)' }}>{title}</p>
        <h2 className={`kpi-card__value ${colorClass}`}>
          <AnimatedNumber value={value} />
        </h2>
        <div className="kpi-card__trend">
          <span
            className={`kpi-card__trend-value ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}
            style={{ backgroundColor: trend === 'up' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}
          >
            {trend === 'up' ? '↑' : '↓'} {trendValue}
          </span>
        </div>
      </div>

      {/* Advanced Icon Wrapper with prominent dynamic background */}
      <div className={`icon-wrapper-advanced ${colorClass}`}>
        <Icon size={22} strokeWidth={2} />
      </div>
    </div>

    <div className="kpi-card__sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`color-${title.replace(/\s+/g, '')}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colorClass.replace('text-', '').split(' ')[0]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={colorClass.replace('text-', '').split(' ')[0]} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="value" stroke="currentColor" fill={`url(#color-${title.replace(/\s+/g, '')})`} className={colorClass} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

// --- MAIN APP ---
export default function Dashboard({ setActiveTab }) {
  const { user: currentUser, company_id } = useAuthStore();

  // --- APPLICATION STATE ---
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Dashboard Data
  const [stats, setStats] = useState({
    recognized: 0, unrecognized: 0, total: 0, cameras: 0, alerts: 0,
    recognized_change: "0%", unrecognized_change: "0%"
  });
  const [criminals, setCriminals] = useState([]);
  const [weeklyData, setWeeklyData] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [sparklines, setSparklines] = useState({
    recognized: [{ value: 0 }, { value: 5 }, { value: 3 }, { value: 8 }],
    unrecognized: [{ value: 0 }, { value: 2 }, { value: 1 }, { value: 3 }],
    total: [{ value: 100 }, { value: 100 }, { value: 100 }],
    cameras: [{ value: 2 }, { value: 2 }, { value: 2 }],
    alerts: [{ value: 0 }, { value: 1 }, { value: 0 }]
  });

  // Real-time Data
  const [liveRecognitions, setLiveRecognitions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cameras, setCameras] = useState([]);


  // --- API DATA FETCHING ---
  const loadData = async () => {
    try {
      const statsData = await fetchDashboardStats();
      const weekly = await fetchWeeklyAttendance();
      const cats = await fetchCategories();
      const crim = await fetchCriminals(); // Backend still uses fetchCriminals for criminals
      const alertData = await fetchAlerts();
      const live = await fetchLiveRecognitions();

      setStats({
        recognized: statsData.present_today || 0,
        unrecognized: statsData.absent || 0,
        total: statsData.total_criminals || statsData.total_employees || 0,
        cameras: statsData.cameras_active || 0,
        alerts: statsData.recognitions_today || 0,
        recognized_change: statsData.present_change || "0%",
        unrecognized_change: statsData.absent_change || "0%"
      });

      // Update sparklines if backend provides trend data
      if (statsData.present_trend) {
        setSparklines(prev => ({ ...prev, recognized: statsData.present_trend }));
      }

      setWeeklyData(weekly);
      setCategoryData(cats);
      setCriminals(crim);
      setAlerts(alertData);
      setLiveRecognitions(live);
    } catch (err) {
      console.error("Dashboard fetch error", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  // --- REAL-TIME WEBSOCKET CONNECTION ---
  useEffect(() => {
    if (!company_id) return;

    const wsUrl = API_BASE_URL.replace('http', 'ws');
    const socket = new WebSocket(`${wsUrl}/ws/recognitions/${company_id}`);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'RECOGNITION') {
          setLiveRecognitions(prev => [data.payload, ...prev].slice(0, 5));
          // Optionally update criminal list if present
          setCriminals(prevCrim => prevCrim.map(crim =>
            crim.emp_id === data.payload.empId || crim.name === data.payload.name
              ? { ...crim, status: 'Recognized', punch_in: data.payload.time } : crim
          ));
        } else if (data.type === 'ALERT') {
          setAlerts(prev => [data.payload, ...prev].slice(0, 5));
          setStats(prev => ({ ...prev, alerts: prev.alerts + 1 }));
        }
      } catch (e) {
        console.error("WebSocket message error", e);
      }
    };

    socket.onerror = (error) => console.error("WebSocket error", error);

    return () => socket.close();
  }, [company_id]);

  // --- FILTERING ---
  const filteredCriminals = criminals.filter(crim =>
    crim?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    crim?.emp_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    crim?.criminal_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // --- EXPORT ---
  const exportCSV = () => {
    const csvHeaders = "CRIMINAL ID,NAME,CATEGORY,RECOGNITION TIME\n";
    const csvRows = criminals.map(e =>
      `${e.emp_id || e.criminal_id || ''},${e.name || ''},${e.category || 'Criminal'},${e.punch_in || e.timestamp || ''}`
    ).join("\n");

    const blob = new Blob([csvHeaders + csvRows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `recognitions_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- RENDER LOADING STATE ---
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-4" style={{ backgroundColor: 'var(--bg-main)' }}>
        <div className="relative">
          <div className="w-12 h-12 border-4 border-blue-200 rounded-full"></div>
          <div className="w-12 h-12 border-4 border-blue-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
        </div>
        <p className="font-medium animate-pulse" style={{ color: 'var(--text-secondary)' }}>Connecting to VisionAI Engine...</p>
      </div>
    );
  }

  // --- RENDER DASHBOARD ---
  return (
    <div className="dashboard-modern">

      {/* TOP NAVIGATION INFO (Internal to Dashboard) */}
      <div className="dashboard-modern__header">
        <div>
          <h1 className="dashboard-modern__title">Dashboard Overview</h1>
          <p className="dashboard-modern__subtitle">Real-time criminal recognition and security analytics</p>
        </div>
        <div className="dashboard-modern__actions">
          <div className="dashboard-online-status">
            <div className="dashboard-online-status__dot"></div>
            <span>System Online</span>
          </div>
          <div className="dashboard-export-actions">
            <button
              onClick={exportCSV}
              className="flex items-center gap-2 px-3 py-1.5 transition rounded-lg shadow-sm border text-xs font-semibold"
              style={{ color: 'var(--text-secondary)', backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border-color)' }}
              title="Export recognitions as CSV"
            >
              <Download size={16} /> Export CSV
            </button>
            <button
              onClick={async () => {
                try {
                  const response = await fetch(`${API_BASE_URL}/api/events/export/dashboard-pdf`, {
                    headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` }
                  });
                  if (!response.ok) throw new Error('Failed to generate PDF');
                  const blob = await response.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `criminal_report_${new Date().toISOString().split('T')[0]}.pdf`;
                  a.click();
                } catch (err) {
                  console.error("Dashboard PDF Export Error", err);
                }
              }}
              className="flex items-center gap-2 px-3 py-1.5 transition rounded-lg shadow-sm border text-xs font-semibold"
              style={{ color: 'var(--text-secondary)', backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border-color)' }}
              title="Export dashboard as premium PDF"
            >
              <FileText size={16} /> Export PDF
            </button>
            <button
              onClick={loadData}
              className="p-2 transition rounded-lg shadow-sm border"
              style={{ color: 'var(--text-secondary)', backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border-color)' }}
            >
              <Activity size={20} />
            </button>
          </div>
        </div>
      </div>

      <div className="dashboard-modern__body">

        {/* ROW 1: KPI CARDS */}
        <div className="dashboard-kpi-grid">
          <KPICard title="Recognized Today" value={stats.recognized} trend="up" trendValue={stats.recognized_change} icon={UserCheck} colorClass="text-green-600" data={sparklines.recognized} gradient="from-green-400 to-emerald-500" />
          <KPICard title="Total Criminals" value={stats.total} trend="up" trendValue="0%" icon={Users} colorClass="text-blue-400" data={sparklines.total} gradient="from-blue-400 to-indigo-500" />
          <KPICard title="Active Cameras" value={stats.cameras} trend="up" trendValue="0%" icon={Camera} colorClass="text-purple-600" data={sparklines.cameras} gradient="from-purple-400 to-violet-500" />
          <KPICard title="Total Recognitions" value={stats.alerts} trend="up" trendValue="0" icon={Activity} colorClass="text-rose-600" data={sparklines.alerts} gradient="from-rose-500 to-red-600" />
        </div>

        {/* ROW 2: SYSTEM HEALTH */}
        <div className="dashboard-system-row">
          {/* System Health */}
          <div className="glass-panel dashboard-system-card">
            <h3 className="font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Server size={18} style={{ color: 'var(--text-secondary)' }} /> System Health
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 rounded-xl border border-transparent hover:border-[var(--border-color)] transition-all" style={{ backgroundColor: 'var(--bg-input)' }}>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg shadow-sm bg-blue-500/20"><Cpu size={16} className="text-blue-500" /></div>
                  <span className="text-xs font-bold uppercase tracking-tight" style={{ color: 'var(--text-primary)' }}>VisionAI Engine</span>
                </div>
                <span className="text-xs font-bold text-green-600 bg-green-100 px-2 py-1 rounded-md">Running</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl" style={{ backgroundColor: 'var(--bg-input)' }}>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg shadow-sm" style={{ backgroundColor: 'var(--bg-panel)' }}><Camera size={16} className="text-purple-500" /></div>
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Camera Streams ({stats.cameras}/{stats.cameras})</span>
                </div>
                <span className="text-xs font-bold text-green-600 bg-green-100 px-2 py-1 rounded-md">Active</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl" style={{ backgroundColor: 'var(--bg-input)' }}>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg shadow-sm" style={{ backgroundColor: 'var(--bg-panel)' }}><HardDrive size={16} className="text-orange-500" /></div>
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Data Store</span>
                </div>
                <span className="text-xs font-bold text-green-600 bg-green-100 px-2 py-1 rounded-md">Ready</span>
              </div>

            </div>
          </div>
        </div>

        {/* ROW 3: ANALYTICS & ALERTS */}
        <div className="dashboard-insights-grid">

          {/* Weekly Chart */}
          <div className="glass-panel dashboard-weekly-card">
            <h3 className="font-bold mb-6 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Activity size={18} className="text-blue-500" />
              <span className="text-xs uppercase tracking-widest">Weekly Recognition Analytics</span>
            </h3>
            <div className="dashboard-weekly-chart">
              {weeklyData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeklyData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 12 }} />
                    <RechartsTooltip
                      cursor={{ fill: '#f3f4f6' }}
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                    <Bar dataKey="present" name="Recognized" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-400 text-sm border-2 border-dashed border-gray-800 rounded-xl">
                  Waiting for chart data...
                </div>
              )}
            </div>
          </div>

          {/* Activity & Insights Panel */}
          <div className="dashboard-side-stack">

            {/* Live Feed */}
            <div className="glass-panel dashboard-live-card">
              <h3 className="font-bold text-[var(--text-primary)] mb-4 flex justify-between items-center">
                <span className="text-xs uppercase tracking-widest">Live Recognition Feed</span>
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-400"></span>
                </span>
              </h3>
              <div className="space-y-3">
                {liveRecognitions.length > 0 ? liveRecognitions.map(rec => (
                  <div key={rec.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--bg-hover)] transition-all border border-transparent hover:border-[var(--border-color)] group">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-inner relative overflow-hidden ${rec.imgColor || 'bg-gray-400'}`}>
                      <div className="absolute inset-0 bg-black/10"></div>
                      <span className="relative z-10">{rec.name === 'Unknown Person' ? '?' : rec?.name?.charAt(0) || 'U'}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-bold truncate group-hover:text-[var(--primary-color)] transition-colors ${rec.status === 'Alert' ? 'text-red-600' : 'text-[var(--text-primary)]'}`}>{rec.name}</p>
                      <p className="text-xs text-gray-400 flex items-center gap-1">
                        {rec.time} • {rec.camera}
                      </p>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${rec.status === 'Recognized' || rec.status === 'Present' ? 'bg-green-100 text-green-600 border border-green-200' : 'bg-red-100 text-red-600 animate-pulse border border-red-200'
                      }`}>
                      {rec.status === 'Present' ? 'Recognized' : rec.status}
                    </span>
                  </div>
                )) : (
                  <div className="text-center py-8 text-sm text-gray-400">Listening for recognitions...</div>
                )}
              </div>
            </div>

            {/* Alerts Panel */}
            <div className="dashboard-alerts-card">
              <h3 className="font-bold text-rose-500 mb-3 flex items-center gap-2">
                <ShieldAlert size={18} />
                <span className="text-xs uppercase tracking-widest">Security Alerts</span>
              </h3>
              <div className="space-y-2">
                {alerts.length > 0 ? alerts.map(alert => (
                  <div key={alert.id} className="p-3 rounded-xl border-l-4 border-rose-500 shadow-sm text-sm" style={{ backgroundColor: 'var(--bg-input)' }}>
                    <div className="flex justify-between font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                      <span>{alert.type}</span>
                      <span className="text-xs text-gray-400 font-normal">{alert.time}</span>
                    </div>
                    <p className="text-xs flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                      <Camera size={12} /> {alert.location}
                    </p>
                  </div>
                )) : (
                  <div className="text-center py-4 text-sm text-rose-400/70">No active security alerts</div>
                )}
              </div>
            </div>

          </div>
        </div>

        {/* PERSISTED COMPONENT AS REQUESTED */}
        <div className="dashboard-analytics-section">
          <FaceRecognitionAnalytics />
        </div>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes fade-in-down {
          0% { opacity: 0; transform: translateY(-10px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in-down { animation: fade-in-down 0.4s ease-out forwards; }
      `}} />
    </div>
  );
}
