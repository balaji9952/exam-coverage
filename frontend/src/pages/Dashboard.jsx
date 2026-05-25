import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getDashboardSummary } from '../api';
import { BarChart3, Database, FileText, BookOpen, Layout, CheckCircle2, AlertCircle, Clock, ChevronRight } from 'lucide-react';
import Skeleton from '../components/Skeleton';

function CoverageRing({ pct, size = 120 }) {
    const strokeWidth = size / 10;
    const r = (size - strokeWidth) / 2;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (pct / 100) * circ;
    const color = pct >= 70 ? 'var(--color-success)' : pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)';

    return (
        <div className="coverage-ring" style={{ width: size, height: size }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                <defs>
                    <filter id={`glow-dash-${size}`}>
                        <feGaussianBlur stdDeviation={size/30} result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                </defs>
                <circle 
                    cx={size/2} cy={size/2} r={r} 
                    fill="none" 
                    stroke="var(--color-surface-3)" 
                    strokeWidth={strokeWidth} 
                    opacity="0.2"
                />
                <motion.circle
                    cx={size/2} cy={size/2} r={r}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    animate={{ strokeDashoffset: dashOffset }}
                    strokeLinecap="round"
                    filter={`url(#glow-dash-${size})`}
                    transition={{ duration: 2, ease: "easeOut" }}
                />
            </svg>
            <div className="coverage-ring-label">
                <div className="coverage-ring-pct" style={{ fontSize: size/4.5, color, fontWeight: 800 }}>{pct.toFixed(1)}%</div>
                <div className="coverage-ring-sub" style={{ fontSize: size/12, letterSpacing: '0.1em' }}>MATCH</div>
            </div>
        </div>
    );
}

export default function Dashboard() {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getDashboardSummary()
            .then(r => setSummary(r.data))
            .catch(() => setSummary({
                total_bank_questions: 0, total_exam_papers: 0,
                total_subjects: 0, total_documents: 0, recent_coverage: []
            }))
            .finally(() => setLoading(false));
    }, []);

    const LoadingSkeleton = () => (
        <div className="fade-in">
            <div className="page-header">
                <Skeleton variant="text" width="150px" height="32px" className="mb-2" />
                <Skeleton variant="text" width="300px" height="18px" />
            </div>
            <div className="page-body">
                <div className="stat-grid">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="card" style={{ height: 110 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <div style={{ flex: 1 }}>
                                    <Skeleton variant="text" width="60%" className="mb-3" />
                                    <Skeleton variant="text" width="40%" height="32px" />
                                </div>
                                <Skeleton variant="rect" width="44px" height="44px" />
                            </div>
                        </div>
                    ))}
                </div>
                <div className="card" style={{ marginTop: 24, height: 300 }}>
                    <div className="card-header">
                        <Skeleton variant="text" width="200px" height="24px" />
                        <Skeleton variant="rect" width="80px" height="32px" />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 20, padding: 20 }}>
                        {[1, 2].map(i => (
                            <div key={i} className="card" style={{ display: 'flex', gap: 20, padding: 20, background: 'transparent' }}>
                                <Skeleton variant="circle" width="90px" height="90px" />
                                <div style={{ flex: 1 }}>
                                    <Skeleton variant="text" width="80%" className="mb-3" />
                                    <Skeleton variant="text" width="50%" className="mb-2" />
                                    <Skeleton variant="text" width="30%" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );

    if (loading) return <LoadingSkeleton />;

    const stats = [
        { label: 'Bank Questions', value: summary.total_bank_questions, icon: <Database size={24} />, color: 'var(--color-primary)' },
        { label: 'Question Banks', value: summary.total_bank_docs, icon: <Layout size={24} />, color: 'var(--color-secondary)' },
        { label: 'Exam Papers', value: summary.total_exam_papers, icon: <FileText size={24} />, color: 'var(--color-success)' },
        { label: 'Subjects', value: summary.total_subjects, icon: <BookOpen size={24} />, color: 'var(--color-warning)' },
    ];

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Dashboard</div>
                <div className="page-subtitle">AI-powered exam coverage analysis overview</div>
            </div>

            <div className="page-body">
                {/* Stat Cards */}
                <motion.div 
                    className="stat-grid"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ staggerChildren: 0.1 }}
                >
                    {stats.map((s) => (
                        <motion.div 
                            key={s.label} 
                            whileHover={{ y: -5 }}
                            className="card"
                            style={{ position: 'relative', overflow: 'hidden' }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                <div>
                                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-dim)', textTransform: 'uppercase', marginBottom: 8 }}>{s.label}</div>
                                    <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--color-text)' }}>{s.value}</div>
                                </div>
                                <div style={{ 
                                    padding: 10, borderRadius: 12, 
                                    background: `${s.color}15`, color: s.color,
                                    border: `1px solid ${s.color}30`
                                }}>
                                    {s.icon}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </motion.div>

                {/* Recent Reports */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="card" 
                    style={{ marginTop: 24 }}
                >
                    <div className="card-header">
                        <div className="card-title">
                            <BarChart3 size={20} color="var(--color-primary-light)" />
                            Recent Coverage Reports
                        </div>
                        <button className="btn btn-sm btn-secondary">View All</button>
                    </div>

                    {summary.recent_coverage.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon" style={{ fontSize: 40 }}>📊</div>
                            <h3>No reports yet</h3>
                            <p>Upload an exam paper to generate your first coverage report</p>
                        </div>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 20 }}>
                            {summary.recent_coverage.map((r, idx) => {
                                const pct = r.overall_coverage_pct || 0;
                                const color = pct >= 70 ? 'var(--color-success)' : pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)';
                                return (
                                    <motion.div 
                                        key={r.exam_id} 
                                        whileHover={{ scale: 1.01 }}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: 24,
                                            padding: '20px', background: 'rgba(255,255,255,0.02)',
                                            borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)',
                                            transition: 'border-color 0.3s ease'
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.borderColor = color}
                                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border)'}
                                    >
                                        <CoverageRing pct={pct} size={90} />
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 8, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {r.subject}
                                            </div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                                                <span className="badge badge-muted" style={{ fontSize: 10 }}>{r.exam_type}</span>
                                                <span className="badge" style={{ fontSize: 10, background: `${color}20`, color: color }}>{pct.toFixed(1)}% Match</span>
                                                <span className="badge badge-primary" style={{ fontSize: 10 }}>{r.weighted_coverage_pct.toFixed(1)}% Weighted</span>
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--color-text-dim)' }}>
                                                <Clock size={12} />
                                                {new Date(r.analyzed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}
                </motion.div>

                {/* Information Grid */}
                <div className="grid-2 mt-2" style={{ marginTop: 24, gap: 24 }}>
                    <motion.div 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 }}
                        className="card"
                    >
                        <div className="card-title" style={{ marginBottom: 20 }}>🚀 Quick Guide</div>
                        {[
                            { step: '1', label: 'Setup', desc: 'Configure Subjects & Units' },
                            { step: '2', label: 'Bank', desc: 'Upload Master Question Bank' },
                            { step: '3', label: 'Review', desc: 'Verify AI Extraction' },
                            { step: '4', label: 'Analyze', desc: 'Upload Exam for Coverage' },
                        ].map((s) => (
                            <div key={s.step} style={{ display: 'flex', gap: 16, marginBottom: 16, alignItems: 'center' }}>
                                <div style={{ 
                                    width: 28, height: 28, borderRadius: '50%', 
                                    background: 'var(--color-primary)', color: '#fff',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: 12, fontWeight: 700
                                }}>{s.step}</div>
                                <div>
                                    <div style={{ fontSize: 13, fontWeight: 600 }}>{s.label}</div>
                                    <div style={{ fontSize: 11, color: 'var(--color-text-dim)' }}>{s.desc}</div>
                                </div>
                            </div>
                        ))}
                    </motion.div>

                    <motion.div 
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 }}
                        className="card"
                    >
                        <div className="card-title" style={{ marginBottom: 20 }}>📊 Coverage Insights</div>
                        {[
                            { range: '≥ 70%', label: 'Excellent Alignment', color: 'var(--color-success)', pct: 85 },
                            { range: '40–70%', label: 'Moderate Coverage', color: 'var(--color-warning)', pct: 55 },
                            { range: '< 40%', label: 'Significant Gaps', color: 'var(--color-danger)', pct: 25 },
                        ].map((s) => (
                            <div key={s.range} style={{ marginBottom: 18 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 12 }}>
                                    <span style={{ fontWeight: 600, color: s.color }}>{s.range}</span>
                                    <span style={{ color: 'var(--color-text-muted)' }}>{s.label}</span>
                                </div>
                                <div className="progress-bar" style={{ height: 6 }}>
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${s.pct}%` }}
                                        transition={{ duration: 1.5, delay: 0.8 }}
                                        className="progress-fill"
                                        style={{ background: s.color }}
                                    />
                                </div>
                            </div>
                        ))}
                    </motion.div>
                </div>
            </div>
        </div>
    );
}
