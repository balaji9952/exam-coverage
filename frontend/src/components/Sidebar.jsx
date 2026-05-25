import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
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
                <motion.div 
                    className="sidebar-logo-icon"
                    animate={{ 
                        boxShadow: ["0 0 16px rgba(99, 102, 241, 0.2)", "0 0 32px rgba(99, 102, 241, 0.4)", "0 0 16px rgba(99, 102, 241, 0.2)"] 
                    }}
                    transition={{ duration: 3, repeat: Infinity }}
                >
                    🎯
                </motion.div>
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
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <motion.div
                                    whileHover={{ x: 4 }}
                                    style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}
                                >
                                    <item.icon size={18} />
                                    <span style={{ flex: 1 }}>{item.label}</span>
                                    {isActive && <ChevronRight size={14} style={{ opacity: 0.8 }} />}
                                </motion.div>
                            </NavLink>
                        </div>
                    );
                })}
            </nav>

            <div style={{ padding: '20px', borderTop: '1px solid var(--color-border)' }}>
                <div style={{ 
                    fontSize: 11, 
                    color: 'var(--color-text-dim)', 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 8,
                    background: 'rgba(255,255,255,0.03)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)'
                }}>
                    <GraduationCap size={14} />
                    <span>AI-Powered • v1.1.0</span>
                </div>
            </div>
        </aside>
    );
}
