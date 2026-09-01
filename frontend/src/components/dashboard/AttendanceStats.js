import React, { useState, useEffect } from 'react';
import { Users, UserX, Clock, Calendar, Briefcase, Home, AlertTriangle, Camera, Scan } from 'lucide-react';
import useAuthStore from '../../store/authStore';
import { API_BASE_URL } from '../../utils/apiConfig';
import './AttendanceStats.css';

const AttendanceStats = ({ setActiveTab }) => {
    const { token } = useAuthStore();
    const [stats, setStats] = useState({
        present_today: 0,
        absent: 0,
        late: 0,
        total_employees: 0,
        cameras_active: 0,
        recognitions_today: 0
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE_URL}/api/events/dashboard-stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setStats(data);
            }
        } catch (error) {
            console.error("Error fetching attendance stats:", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="attendance-stats-loading">Loading stats...</div>;
    }

    const handleCardClick = (label) => {
        if (!setActiveTab) return;
        let filterStatus = '';
        if (label === 'Known Faces') filterStatus = 'Present';

        if (filterStatus) {
            localStorage.setItem('attendanceFilter', filterStatus);
            setActiveTab('month-report'); // Changed to month-report as default report tab
        }
    };

    const statCards = [
        { label: 'Known Faces', value: stats.present_today, color: '#10b981', icon: <Users size={20} /> },
        { label: 'Total Criminals', value: stats.total_employees, color: '#0f172a', icon: <Users size={20} /> },
        { label: 'Cameras Active', value: stats.cameras_active, color: '#3b82f6', icon: <Camera size={20} /> },
        { label: 'Recognitions Today', value: stats.recognitions_today, color: '#8b5cf6', icon: <Scan size={20} /> }
    ];

    return (
        <div className="attendance-stats-grid">
            {statCards.map((stat, idx) => {
                const isClickable = ['Known Faces'].includes(stat.label);
                return (
                    <div
                        className="stat-card"
                        key={idx}
                        style={{ '--stat-color': stat.color, cursor: isClickable ? 'pointer' : 'default' }}
                        onClick={() => handleCardClick(stat.label)}
                    >
                        <div className="stat-icon-wrapper" style={{ color: stat.color, backgroundColor: `${stat.color}15` }}>
                            {stat.icon}
                        </div>
                        <div className="stat-info">
                            <span className="stat-value">{stat.value}</span>
                            <span className="stat-label">{stat.label}</span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default AttendanceStats;
