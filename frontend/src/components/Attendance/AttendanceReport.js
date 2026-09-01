import React, { useEffect, useMemo, useState } from 'react';
import { Search, Filter, Calendar, FileText, FileSpreadsheet, Users, Clock, ArrowLeft, RefreshCw } from 'lucide-react';
import useAuthStore from '../../store/authStore';
import { API_BASE_URL, fixImageUrl } from '../../utils/apiConfig';
import ProtectedImage from '../common/ProtectedImage';
import './AttendanceReport.css';

const AttendanceReport = ({ reportType, setActiveTab }) => {
  const { token } = useAuthStore();
  const [reportData, setReportData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [targetDate, setTargetDate] = useState(new Date().toISOString().split('T')[0]);
  const [startDate, setStartDate] = useState(() => { const d = new Date(); d.setDate(d.getDate() - 7); return d.toISOString().split('T')[0]; });
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  const isAggregate = reportType === 'week-report' || reportType === 'month-report';

  useEffect(() => {
    if (reportType === 'week-report') {
      const d = new Date(); d.setDate(d.getDate() - 7);
      setStartDate(d.toISOString().split('T')[0]); setEndDate(new Date().toISOString().split('T')[0]);
    } else if (reportType === 'month-report') {
      const d = new Date(); d.setDate(1);
      setStartDate(d.toISOString().split('T')[0]); setEndDate(new Date().toISOString().split('T')[0]);
    }
  }, [reportType]);

  const fetchAttendanceData = async () => {
    setLoading(true); setError(null);
    try {
      const url = isAggregate
        ? `${API_BASE_URL}/api/events/attendance/aggregate?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
        : `${API_BASE_URL}/api/events/attendance?target_date=${encodeURIComponent(targetDate)}`;
      const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Unable to load report (${response.status})`);
      setReportData(data.attendance || data.aggregate || []);
    } catch (err) {
      setError(err.message || 'Unable to load recognition report.');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchAttendanceData(); }, [targetDate, startDate, endDate, reportType]);

  const title = reportType === 'week-report' ? 'Weekly Recognition Report' : reportType === 'month-report' ? 'Monthly Recognition Report' : 'Recognition Report';
  const filteredData = useMemo(() => reportData.filter(record => {
    const name = String(record.name || '').toLowerCase();
    const id = String(record.emp_id || record.criminal_id || '').toLowerCase();
    const query = searchTerm.trim().toLowerCase();
    const matchesSearch = !query || name.includes(query) || id.includes(query);
    const recognized = isAggregate ? Number(record.total_recognitions || 0) > 0 : ['Present', 'Recognized'].includes(record.status) || Boolean(record.timestamp || record.punch_in);
    return matchesSearch && (statusFilter === 'All' || recognized);
  }), [reportData, searchTerm, statusFilter, isAggregate]);

  const totalRecognized = isAggregate ? reportData.reduce((sum, row) => sum + Number(row.total_recognitions || 0), 0) : reportData.length;

  const exportCSV = () => {
    if (!filteredData.length) return;
    const headers = ['S.No', 'Criminal ID', 'Name', 'Category', isAggregate ? 'Total Recognitions' : 'Recognition Time'];
    const quote = value => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const rows = filteredData.map((row, index) => [index + 1, row.emp_id || row.criminal_id || '', row.name || '', row.category || 'Criminal', isAggregate ? row.total_recognitions || 0 : row.punch_in || row.timestamp || '-'].map(quote).join(','));
    const blob = new Blob([[headers.join(','), ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.href = url; a.download = `${title.replace(/\s+/g, '_')}_${isAggregate ? `${startDate}_${endDate}` : targetDate}.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  const exportPDF = async () => {
    setExporting(true); setError(null);
    try {
      const endpoint = isAggregate
        ? `${API_BASE_URL}/api/events/export/attendance-aggregate-pdf?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
        : `${API_BASE_URL}/api/events/export/attendance-pdf?target_date=${encodeURIComponent(targetDate)}`;
      const response = await fetch(endpoint, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'PDF export failed'); }
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a');
      a.href = url; a.download = `recognition_report_${isAggregate ? `${startDate}_to_${endDate}` : targetDate}.pdf`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err.message || 'PDF export failed'); } finally { setExporting(false); }
  };

  return (
    <div className="attendance-report-container">
      <div className="report-title-row">
        <div className="report-title-block">
          {setActiveTab && <button type="button" className="report-back-btn" onClick={() => setActiveTab('dashboard')}><ArrowLeft size={16} />Back</button>}
          <div><h2>{title}</h2><p>Known-face recognition activity with export-ready filters.</p></div>
        </div>
        <button type="button" className="report-refresh-btn" onClick={fetchAttendanceData} disabled={loading}><RefreshCw size={15} className={loading ? 'spin-icon' : ''} />Refresh</button>
      </div>

      <section className="report-toolbar" aria-label="Report filters and exports">
        <div className="report-search"><Search size={15} /><input value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="Search ID or name" /></div>
        <label className="report-select"><Filter size={14} /><select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="All">All records</option><option value="Recognized">Recognized only</option></select></label>
        {isAggregate ? (
          <div className="report-date-range"><Calendar size={14} /><input type="date" value={startDate} max={endDate} onChange={e => setStartDate(e.target.value)} /><span>to</span><input type="date" value={endDate} min={startDate} onChange={e => setEndDate(e.target.value)} /></div>
        ) : (
          <label className="report-date-range"><Calendar size={14} /><input type="date" value={targetDate} onChange={e => setTargetDate(e.target.value)} /></label>
        )}
        <div className="report-export-group">
          <button type="button" className="report-export-btn" onClick={exportCSV} disabled={!filteredData.length}><FileSpreadsheet size={15} />CSV</button>
          <button type="button" className="report-export-btn primary" onClick={exportPDF} disabled={exporting}><FileText size={15} />{exporting ? 'Preparing…' : 'PDF'}</button>
        </div>
      </section>

      <div className="report-summary-grid">
        <div className="report-summary-card"><span className="summary-icon success"><Users size={16} /></span><div><small>Recognitions</small><strong>{totalRecognized}</strong></div></div>
        <div className="report-summary-card"><span className="summary-icon info"><Clock size={16} /></span><div><small>Profiles shown</small><strong>{filteredData.length}</strong></div></div>
        <div className="report-summary-card"><div><small>Date range</small><strong className="summary-date">{isAggregate ? `${startDate} → ${endDate}` : targetDate}</strong></div></div>
      </div>

      {error && <div className="report-error">{error}</div>}

      <section className="attendance-table-shell">
        {loading ? <div className="report-loading"><div className="spinner" /><span>Loading recognition records…</span></div> : (
          <div className="attendance-table-scroll">
            <table className="attendance-table">
              <thead><tr><th>#</th><th>Criminal ID</th><th>Name</th><th>Category</th><th>{isAggregate ? 'Total Recognitions' : 'Recognition Time'}</th></tr></thead>
              <tbody>
                {filteredData.length ? filteredData.map((record, index) => (
                  <tr key={`${record.emp_id || record.criminal_id || record.name || 'row'}-${index}`}>
                    <td>{index + 1}</td><td className="emp-id">{record.emp_id || record.criminal_id || '-'}</td>
                    <td><div className="name-cell">{record.photo_path ? <ProtectedImage src={fixImageUrl(record.photo_path)} alt={record.name || 'Profile'} className="mini-avatar" /> : <div className="mini-avatar-placeholder">{String(record.name || 'C').charAt(0).toUpperCase()}</div>}<span>{record.name || 'Unknown'}</span></div></td>
                    <td><span className="category-pill">{record.category || 'Criminal'}</span></td>
                    <td className={isAggregate ? 'recognition-count-cell' : 'time-cell'}>{isAggregate ? record.total_recognitions || 0 : record.punch_in || record.timestamp || '-'}</td>
                  </tr>
                )) : <tr><td colSpan="5" className="no-data">No recognition records match the selected filters.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default AttendanceReport;
