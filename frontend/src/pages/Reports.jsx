import { useState, useEffect } from 'react';
import { getExamPapers, getExamReport, getSubjects } from '../api';
import { BarChart2, FileText } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';

function CoverageRing({ pct, size = 80 }) {
    const r = (size / 2) - 9;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (pct / 100) * circ;
    const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';
    return (
        <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-surface-2)" strokeWidth="8" />
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8"
                    strokeDasharray={circ} strokeDashoffset={dashOffset} strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease' }} />
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color }}>
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
        const params = {};
        if (selectedSubject) params.subject_id = selectedSubject;
        const r = await getExamPapers(params);
        setPapers(r.data);
        setLoading(false);
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

    const cov = selectedReport?.coverage;

    const unitData = cov ? Object.entries(cov.unit_coverage).map(([u, v]) => ({
        name: u.length > 18 ? u.slice(0, 18) + '…' : u, pct: v.pct
    })) : [];

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Coverage Reports</div>
                <div className="page-subtitle">View historical exam analysis and coverage trends</div>
            </div>
            <div className="page-body">

                <div style={{ display: 'flex', gap: 16, marginBottom: 16, alignItems: 'flex-end' }}>
                    <div style={{ flex: 1, maxWidth: 300 }}>
                        <label className="form-label">Filter by Subject</label>
                        <select className="form-control" value={selectedSubject} onChange={e => setSelectedSubject(e.target.value)}>
                            <option value="">All subjects</option>
                            {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                    </div>
                </div>

                <div className="grid-2" style={{ gap: 20 }}>
                    {/* Paper List */}
                    <div>
                        <div className="section-title mb-2" style={{ marginBottom: 12 }}>Analyzed Exam Papers</div>
                        {loading ? (
                            <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><div className="spinner" /></div>
                        ) : papers.length === 0 ? (
                            <div className="empty-state"><div className="empty-state-icon"><FileText size={48} /></div><h3>No papers analyzed</h3><p>Use Analyze Exam Paper to get started</p></div>
                        ) : (
                            papers.map(p => (
                                <div
                                    key={p.id}
                                    onClick={() => p.has_report && viewReport(p.id)}
                                    style={{
                                        padding: '14px 16px', background: 'var(--color-surface)',
                                        border: `1px solid ${selectedReport?.exam_paper_id === p.id ? 'var(--color-primary)' : 'var(--color-border)'}`,
                                        borderRadius: 'var(--radius-md)', marginBottom: 10,
                                        cursor: p.has_report ? 'pointer' : 'default',
                                        transition: 'var(--transition)',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
                                    onMouseLeave={e => e.currentTarget.style.borderColor = selectedReport?.exam_paper_id === p.id ? 'var(--color-primary)' : 'var(--color-border)'}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div>
                                            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{p.subject_name}</div>
                                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                                <span className="badge badge-muted">{p.exam_type}</span>
                                                {p.exam_date && <span className="badge badge-muted">{p.exam_date}</span>}
                                                {!p.has_report && <span className="badge badge-warning">No report</span>}
                                            </div>
                                            <div style={{ fontSize: 11, color: 'var(--color-text-dim)', marginTop: 4 }}>
                                                {new Date(p.analyzed_at).toLocaleString()}
                                            </div>
                                        </div>
                                        {p.has_report && <span style={{ fontSize: 12, color: 'var(--color-primary-light)' }}>View →</span>}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Report Detail */}
                    <div>
                        {!selectedReport ? (
                            <div className="empty-state" style={{ paddingTop: 80 }}>
                                <div className="empty-state-icon"><BarChart2 size={48} /></div>
                                <h3>Select an exam to view report</h3>
                            </div>
                        ) : (
                            <div className="fade-in">
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: 20 }}>
                                        <CoverageRing pct={cov.overall_coverage_pct} size={100} />
                                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)', textAlign: 'center' }}>Count Coverage</div>
                                    </div>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: 20 }}>
                                        <CoverageRing pct={cov.weighted_coverage_pct} size={100} />
                                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)', textAlign: 'center' }}>Marks Coverage</div>
                                    </div>
                                </div>

                                <div className="card mb-2">
                                    <div style={{ display: 'flex', gap: 20 }}>
                                        <div style={{ textAlign: 'center', flex: 1 }}>
                                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-success)' }}>{cov.matched}</div>
                                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Matched</div>
                                        </div>
                                        <div style={{ textAlign: 'center', flex: 1 }}>
                                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-warning)' }}>{cov.possible}</div>
                                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Possible</div>
                                        </div>
                                        <div style={{ textAlign: 'center', flex: 1 }}>
                                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-danger)' }}>{cov.not_matched}</div>
                                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Not Matched</div>
                                        </div>
                                        <div style={{ textAlign: 'center', flex: 1 }}>
                                            <div style={{ fontSize: 24, fontWeight: 700 }}>{cov.total_exam_questions}</div>
                                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Total</div>
                                        </div>
                                    </div>
                                </div>

                                {unitData.length > 0 && (
                                    <div className="card">
                                        <div className="card-title" style={{ marginBottom: 16 }}>Unit Coverage</div>
                                        <ResponsiveContainer width="100%" height={200}>
                                            <BarChart data={unitData} margin={{ top: 0, right: 10, left: 0, bottom: 44 }}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={10} angle={-20} textAnchor="end" />
                                                <YAxis stroke="var(--color-text-muted)" fontSize={10} domain={[0, 100]} unit="%" />
                                                <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }} />
                                                <Bar dataKey="pct" name="Coverage %" radius={[4, 4, 0, 0]}>
                                                    {unitData.map((e, i) => (
                                                        <Cell key={i} fill={e.pct >= 70 ? '#22c55e' : e.pct >= 40 ? '#f59e0b' : '#ef4444'} />
                                                    ))}
                                                </Bar>
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
