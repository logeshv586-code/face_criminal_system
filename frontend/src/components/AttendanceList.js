import React, { useState, useEffect } from 'react';
import axios from 'axios';
import useAuthStore from '../store/authStore';
import {
    Search,
    Calendar as CalendarIcon,
    Filter,
    RefreshCw,
    User,
    Clock,
    ChevronLeft,
    ChevronRight,
    TrendingUp,
    AlertCircle,
    Download
} from 'lucide-react';
import './AttendanceList.css';
import { API_BASE_URL } from '../utils/apiConfig';

const AttendanceList = () => {
    const { token } = useAuthStore();
    const [attendance, setAttendance] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [filterStatus, setFilterStatus] = useState('All');
    const [stats, setStats] = useState({ present: 0, absent: 0, late: 0 });
    const [selectedRecord, setSelectedRecord] = useState(null);

    const fetchAttendance = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/events/attendance`, {
                params: { target_date: selectedDate },
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setAttendance(response.data);

            // Calculate stats
            const newStats = response.data.reduce((acc, curr) => {
                if (curr.status === 'Present') acc.present++;
                else if (curr.status === 'Absent') acc.absent++;
                else if (curr.status === 'Late') acc.late++;
                return acc;
            }, { present: 0, absent: 0, late: 0 });
            setStats(newStats);

        } catch (err) {
            console.error('Error fetching attendance:', err);
            setError('Failed to load attendance records. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAttendance();
    }, [selectedDate]);

    const filteredAttendance = attendance.filter(item => {
        const matchesSearch = (item?.name || '').toLowerCase().includes(searchQuery.toLowerCase());
        const matchesStatus = filterStatus === 'All' || item.status === filterStatus;
        return matchesSearch && matchesStatus;
    });

    const formatTime = (isoString) => {
        if (!isoString) return '--:--';
        const date = new Date(isoString.replace('Z', '+00:00'));
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };

    const handleDateChange = (days) => {
        const date = new Date(selectedDate);
        date.setDate(date.getDate() + days);
        setSelectedDate(date.toISOString().split('T')[0]);
    };

    const exportCsv = () => {
        const escapeCsv = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
        const rows = [
            ['Criminal', 'Category', 'Status', 'First Recognition', 'Last Recognition', 'Total Recognitions'],
            ...filteredAttendance.map(record => [
                record.name,
                record.category || 'Criminal',
                record.status === 'Present' ? 'Recognized' : (record.status || 'Not Recognized'),
                record.first_in || '',
                record.last_out || '',
                record.total_punches ?? 0,
            ])
        ];
        const blob = new Blob([rows.map(row => row.map(escapeCsv).join(',')).join('\n')], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `criminal_recognition_${selectedDate}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="attendance-container">
            <div className="attendance-header-card">
                <div className="header-info">
                <h1>Criminal Recognition Log</h1>
                <p>Track criminal recognition events and detection timestamps</p>
                </div>

                <div className="date-controls">
                    <button className="date-btn" onClick={() => handleDateChange(-1)}>
                        <ChevronLeft size={20} />
                    </button>
                    <div className="date-display">
                        <CalendarIcon size={18} />
                        <input
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            className="date-input"
                        />
                    </div>
                    <button className="date-btn" onClick={() => handleDateChange(1)}>
                        <ChevronRight size={20} />
                    </button>
                    <button className="refresh-btn" onClick={fetchAttendance} title="Refresh">
                        <RefreshCw size={18} className={loading ? 'spinning' : ''} />
                    </button>
                </div>
            </div>

            <div className="attendance-stats-grid">
                <div className="stat-card total">
                    <div className="stat-icon"><User size={24} /></div>
                    <div className="stat-value">{attendance.length}</div>
                    <div className="stat-label">Total Records</div>
                </div>
                <div className="stat-card present">
                    <div className="stat-icon"><TrendingUp size={24} /></div>
                    <div className="stat-value">{stats.present}</div>
                    <div className="stat-label">Total Recognitions</div>
                </div>
                <div className="stat-card late" style={{ opacity: 0.5, pointerEvents: 'none', display: 'none' }}>
                    <div className="stat-icon"><Clock size={24} /></div>
                    <div className="stat-value">0</div>
                    <div className="stat-label">N/A</div>
                </div>
                <div className="stat-card absent" style={{ opacity: 0.5, pointerEvents: 'none', display: 'none' }}>
                    <div className="stat-icon"><AlertCircle size={24} /></div>
                    <div className="stat-value">0</div>
                    <div className="stat-label">N/A</div>
                </div>
            </div>

            <div className="attendance-content-card">
                <div className="table-filters">
                    <div className="search-box">
                        <Search size={18} />
                        <input
                            type="text"
                            placeholder="Search criminal..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <div className="filter-item">
                            <Filter size={16} />
                            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                                <option value="All">All Status</option>
                                <option value="Present">Recognized</option>
                                <option value="Not Recognized">Not Recognized</option>
                            </select>
                        </div>
                        <button className="export-btn" onClick={exportCsv} disabled={filteredAttendance.length === 0} title="Export visible records to CSV">
                            <Download size={16} />
                            <span>Export CSV</span>
                        </button>
                    </div>
                </div>

                <div className="attendance-table-wrapper">
                    {loading ? (
                        <div className="table-loader">
                            <RefreshCw className="spinning" size={32} />
                            <p>Fetching records...</p>
                        </div>
                    ) : error ? (
                        <div className="table-empty">
                            <AlertCircle size={48} color="#ef4444" />
                            <p>{error}</p>
                        </div>
                    ) : filteredAttendance.length === 0 ? (
                        <div className="table-empty">
                            <User size={48} />
                            <p>No records found for this date</p>
                        </div>
                    ) : (
                        <table className="attendance-table">
                            <thead>
                                <tr>
                                    <th>Criminal</th>
                                    <th>Category</th>
                                    <th>Status</th>
                                    <th>First Recognition</th>
                                    <th>Last Recognition</th>
                                    <th>Total Recognitions</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAttendance.map((record, index) => (
                                    <tr key={index} className="table-row">
                                        <td>
                                            <div className="employee-info">
                                                <div className="employee-avatar">
                                                    {record.photo_url ? (
                                                        <img src={record.photo_url} alt={record.name} />
                                                    ) : (
                                                        <div className="avatar-placeholder">{record.name.charAt(0)}</div>
                                                    )}
                                                </div>
                                                <span className="employee-name">{record.name}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="category-badge">{record.category || 'Criminal'}</span>
                                        </td>
                                        <td>
                                            <span className={`status-badge ${record.status === 'Present' ? 'present' : 'absent'}`}>
                                                {record.status === 'Present' ? 'Recognized' : 'Not Recognized'}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="time-entry">
                                                <Clock size={14} />
                                                <span>{formatTime(record.first_in)}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="time-entry">
                                                <Clock size={14} />
                                                <span>{formatTime(record.last_out)}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="punches-count">{record.total_punches}</span>
                                        </td>
                                        <td>
                                            <button className="view-detail-btn" title="View recognition details" onClick={() => setSelectedRecord(record)}>
                                                <TrendingUp size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {selectedRecord && (
                <div className="attendance-detail-backdrop" role="presentation" onMouseDown={() => setSelectedRecord(null)}>
                    <div className="attendance-detail-modal" role="dialog" aria-modal="true" aria-label="Recognition details" onMouseDown={(event) => event.stopPropagation()}>
                        <div className="attendance-detail-header">
                            <div>
                                <h3>{selectedRecord.name || 'Recognition details'}</h3>
                                <p>{selectedRecord.category || 'Criminal'} · {selectedDate}</p>
                            </div>
                            <button type="button" onClick={() => setSelectedRecord(null)} aria-label="Close details">×</button>
                        </div>
                        <div className="attendance-detail-grid">
                            <div><span>Status</span><strong>{selectedRecord.status === 'Present' ? 'Recognized' : (selectedRecord.status || 'Not Recognized')}</strong></div>
                            <div><span>First recognition</span><strong>{formatTime(selectedRecord.first_in)}</strong></div>
                            <div><span>Last recognition</span><strong>{formatTime(selectedRecord.last_out)}</strong></div>
                            <div><span>Total recognitions</span><strong>{selectedRecord.total_punches ?? 0}</strong></div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AttendanceList;
