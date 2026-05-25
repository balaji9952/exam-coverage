import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getExamPapers, getExamReport, getSubjects, deleteExamPaper } from '../api';
import { BarChart2, FileText, ChevronRight, Calendar, Tag, Search, Trash2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import Skeleton from '../components/Skeleton';

function CoverageRing({ pct, size = 80 }) {
    const r = (size / 2) - 9;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (pct / 100) * circ;
    const color = pct >= 70 ? 'var(--color-success)' : pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)';
    
    return (
        <div className="coverage-ring" style={{ width: size, height: size }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                <defs>
                    <filter id={`glow-${size}`}>
                        <feGaussianBlur stdDeviation="2" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                </defs>
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-surface-3)" strokeWidth="8" opacity="0.3" />
                <circle 
                    cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8"
                    strokeDasharray={circ} strokeDashoffset={dashOffset} strokeLinecap="round"
                    filter={`url(#glow-${size})`}
                    style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
                />
            </svg>
            <div className="coverage-ring-label" style={{ color }}>
                {pct.toFixed(0)}%
            </div>
        </div>
    );
}

export default function Reports() {
    const [papers, setPapers] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedReport, setSelectedReport] = useState(null);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const params = {};
            if (selectedSubject) params.subject_id = selectedSubject;
            const r = await getExamPapers(params);
            setPapers(r.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { getSubjects().then(r => setSubjects(r.data)); }, []);
    useEffect(() => { load(); }, [selectedSubject]);

    const viewReport = async (paperId) => {
        try {
            const r = await getExamReport(paperId);
            setSelectedReport({ ...r.data, exam_paper_id: paperId });
        } catch {
            alert('No report found for this exam. Please re-run analysis.');
        }
    };

    const handleDelete = async (e, paperId) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this exam analysis history?")) return;
        
        try {
            await deleteExamPaper(paperId);
            setPapers(papers.filter(p => p.id !== paperId));
            if (selectedReport?.exam_paper_id === paperId) {
                setSelectedReport(null);
            }
        } catch (err) {
            alert('Failed to delete exam paper.');
        }
    };

    const cov = selectedReport?.coverage;
    const unitData = cov ? Object.entries(cov.unit_coverage).map(([u, v]) => ({
        name: u.split('-')[0].trim(), pct: v.pct, fullName: u
    })) : [];

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, x: -20 },
        show: { opacity: 1, x: 0 }
    };

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Coverage Reports</div>
                <div className="page-subtitle">View historical exam analysis and coverage trends</div>
            </div>
            
            <div className="page-body">
                <div className="card mb-2" style={{ padding: '16px 24px', marginBottom: 24 }}>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                        <Search size={18} style={{ color: 'var(--color-text-dim)' }} />
                        <div style={{ flex: 1, maxWidth: 400 }}>
                            <select 
                                className="form-control" 
                                value={selectedSubject} 
                                onChange={e => setSelectedSubject(e.target.value)}
                                style={{ background: 'transparent', border: 'none', paddingLeft: 0 }}
                            >
                                <option value="">All subjects</option>
                                {subjects.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
                    {/* Paper List */}
                    <div className="glass-card" style={{ padding: 12 }}>
                        <div className="section-title" style={{ padding: '12px 16px', fontSize: 14 }}>Analyzed Exam Papers</div>
                        {loading ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {[1, 2, 3, 4, 5].map(i => (
                                    <div key={i} style={{ padding: 16, background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--color-border)' }}>
                                        <Skeleton variant="text" width="60%" className="mb-2" />
                                        <Skeleton variant="text" width="40%" height="12px" />
                                    </div>
                                ))}
                            </div>
                        ) : papers.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon"><FileText size={40} /></div>
                                <h3>No papers found</h3>
                            </div>
                        ) : (
                            <motion.div 
                                variants={containerVariants}
                                initial="hidden"
                                animate="show"
                                style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
                            >
                                {papers.map(p => (
                                    <motion.div
                                        key={p.id}
                                        variants={itemVariants}
                                        onClick={() => p.has_report && viewReport(p.id)}
                                        className={`nav-item ${selectedReport?.exam_paper_id === p.id ? 'active' : ''}`}
                                        style={{ 
                                            margin: 0, 
                                            padding: '16px', 
                                            cursor: p.has_report ? 'pointer' : 'default',
                                            opacity: p.has_report ? 1 : 0.6,
                                            background: selectedReport?.exam_paper_id === p.id ? 'var(--color-primary)' : 'rgba(255,255,255,0.02)',
                                            border: '1px solid var(--color-border)'
                                        }}
                                    >
                                        <div style={{ width: '100%' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                                <div style={{ fontWeight: 600 }}>{p.subject_name}</div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                    <button 
                                                        onClick={(e) => handleDelete(e, p.id)}
                                                        style={{ background: 'transparent', border: 'none', color: 'var(--color-danger)', cursor: 'pointer', padding: 4, display: 'flex' }}
                                                        title="Delete history"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                    {p.has_report && <ChevronRight size={14} />}
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', gap: 12, fontSize: 11, color: selectedReport?.exam_paper_id === p.id ? 'rgba(255,255,255,0.8)' : 'var(--color-text-dim)' }}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Tag size={12} /> {p.exam_type}</span>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Calendar size={12} /> {new Date(p.analyzed_at).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}
                    </div>

                    {/* Report Detail */}
                    <AnimatePresence mode="wait">
                        {!selectedReport ? (
                            <motion.div 
                                key="empty"
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="empty-state" style={{ height: 400, background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-lg)' }}
                            >
                                <div className="empty-state-icon"><BarChart2 size={48} /></div>
                                <h3>Select an exam</h3>
                                <p>View detailed AI analysis report</p>
                            </motion.div>
                        ) : (
                            <motion.div 
                                key={selectedReport.exam_paper_id}
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.4 }}
                            >
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                                        <CoverageRing pct={cov.overall_coverage_pct} size={110} />
                                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Count Coverage</div>
                                    </div>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                                        <CoverageRing pct={cov.weighted_coverage_pct} size={110} />
                                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Marks Coverage</div>
                                    </div>
                                </div>

                                <div className="card mb-2" style={{ background: 'var(--color-primary-glow)', borderColor: 'var(--color-primary-light)' }}>
                                    <div style={{ display: 'flex', gap: 20 }}>
                                        {[
                                            { label: 'Matched', val: cov.matched, color: 'var(--color-success)' },
                                            { label: 'Possible', val: cov.possible, color: 'var(--color-warning)' },
                                            { label: 'Not Matched', val: cov.not_matched, color: 'var(--color-danger)' },
                                            { label: 'Total Qs', val: cov.total_exam_questions, color: 'var(--color-text)' }
                                        ].map(s => (
                                            <div key={s.label} style={{ textAlign: 'center', flex: 1 }}>
                                                <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.val}</div>
                                                <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginTop: 4 }}>{s.label}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {unitData.length > 0 && (
                                    <div className="card">
                                        <div className="card-title" style={{ marginBottom: 20, fontSize: 14 }}>Unit-wise Analysis</div>
                                        <div style={{ height: 240 }}>
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={unitData} margin={{ top: 0, right: 10, left: -20, bottom: 20 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                                                    <XAxis dataKey="name" stroke="var(--color-text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                                                    <YAxis stroke="var(--color-text-dim)" fontSize={10} tickLine={false} axisLine={false} domain={[0, 100]} />
                                                    <Tooltip 
                                                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                                        contentStyle={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 12, boxShadow: 'var(--shadow-xl)' }}
                                                        labelStyle={{ fontWeight: 600, marginBottom: 4 }}
                                                    />
                                                    <Bar dataKey="pct" radius={[4, 4, 0, 0]} barSize={32}>
                                                        {unitData.map((e, i) => (
                                                            <Cell key={i} fill={e.pct >= 70 ? 'var(--color-success)' : e.pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)'} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
