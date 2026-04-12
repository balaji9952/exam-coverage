import { NavLink, useLocation } from 'react-router-dom';
import {
    LayoutDashboard, BookOpen, UploadCloud, FileSearch,
    BarChart3, Settings, ChevronRight, GraduationCap, Database
} from 'lucide-react';

const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/setup', icon: Settings, label: 'Setup', section: 'MANAGEMENT' },
    { to: '/question-bank', icon: Database, label: 'Question Bank' },
    { to: '/upload-bank', icon: UploadCloud, label: 'Upload Question Bank' },
    { to: '/analyze', icon: FileSearch, label: 'Analyze Exam Paper', section: 'ANALYSIS' },
    { to: '/reports', icon: BarChart3, label: 'Coverage Reports' },
];

export default function Sidebar() {
    const location = useLocation();
    let lastSection = null;

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">🎯</div>
                <div className="sidebar-logo-text">
                    <h2>ExamCoverage</h2>
                    <span>AI Analysis Platform</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                {navItems.map((item) => {
                    const showSection = item.section && item.section !== lastSection;
                    if (item.section) lastSection = item.section;
                    const isActive = location.pathname === item.to ||
                        (item.to !== '/' && location.pathname.startsWith(item.to));

                    return (
                        <div key={item.to}>
                            {showSection && (
                                <div className="nav-section-label">{item.section}</div>
                            )}
                            <NavLink
                                to={item.to}
                                className={`nav-item ${isActive ? 'active' : ''}`}
                            >
                                <item.icon size={16} />
                                {item.label}
                                {isActive && <ChevronRight size={14} style={{ marginLeft: 'auto' }} />}
                            </NavLink>
                        </div>
                    );
                })}
            </nav>

            <div style={{ padding: '16px', borderTop: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: 12, color: 'var(--color-text-dim)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <GraduationCap size={14} />
                    AI-Powered • v1.0.0
                </div>
            </div>
        </aside>
    );
}
