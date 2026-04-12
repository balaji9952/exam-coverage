import { useState, useEffect, useRef } from 'react';
import { getSubjects, uploadAndAnalyzeExam } from '../api';
import { UploadCloud, FileSearch, CheckCircle2, XCircle, HelpCircle, TrendingUp } from 'lucide-react';
import {
    RadialBarChart, RadialBar, ResponsiveContainer, Tooltip,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, Legend
} from 'recharts';

const BLOOMS_COLORS = {
    K1: '#38bdf8', K2: '#22c55e', K3: '#f59e0b',
    K4: '#a78bfa', K5: '#ef4444', K6: '#fb7185'
};

function CoverageRing({ pct, label, size = 160 }) {
    const r = 60;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (pct / 100) * circ;
    const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';

    return (
        <div className="coverage-ring-container">
            <div className="coverage-ring" style={{ width: size, height: size }}>
                <svg width={size} height={size} viewBox="0 0 160 160">
                    <circle cx="80" cy="80" r={r} fill="none" stroke="var(--color-surface-2)" strokeWidth="14" />
                    <circle cx="80" cy="80" r={r} fill="none" stroke={color} strokeWidth="14"
                        strokeDasharray={circ} strokeDashoffset={dashOffset} strokeLinecap="round"
                        style={{ filter: `drop-shadow(0 0 8px ${color}88)`, transition: 'stroke-dashoffset 1s ease' }} />
                </svg>
                <div className="coverage-ring-label">
                    <div className="coverage-ring-pct" style={{ color }}>{pct.toFixed(1)}%</div>
                    <div className="coverage-ring-sub">{label || 'Coverage'}</div>
                </div>
            </div>
        </div>
    );
}

function MatchBadge({ status }) {
    if (status === 'matched') return <span className="badge badge-success">✓ Matched</span>;
    if (status === 'possible') return <span className="badge badge-warning">~ Possible</span>;
    return <span className="badge badge-danger">✗ Not Matched</span>;
}

export default function Analyze() {
    const [subjects, setSubjects] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState('');
    const [examType, setExamType] = useState('Internal');
    const [examDate, setExamDate] = useState('');
    const [file, setFile] = useState(null);
    const [dragOver, setDragOver] = useState(false);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [msg, setMsg] = useState({ type: '', text: '' });
    const [activeTab, setActiveTab] = useState('overview');
    const fileRef = useRef();

    const flash = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 5000); };

    useEffect(() => { getSubjects().then(r => setSubjects(r.data)); }, []);

    const handleAnalyze = async () => {
        if (!file || !selectedSubject) { flash('error', 'Select subject and upload exam paper'); return; }
        setLoading(true);
        setResult(null);
        const fd = new FormData();
        fd.append('file', file);
        fd.append('subject_id', selectedSubject);
        fd.append('exam_type', examType);
        if (examDate) fd.append('exam_date', examDate);
        try {
            const r = await uploadAndAnalyzeExam(fd);
            setResult(r.data);
            flash('success', 'Analysis complete!');
        } catch (err) {
            flash('error', err.response?.data?.detail || 'Analysis failed. Ensure question bank exists for this subject.');
        } finally {
            setLoading(false);
        }
    };

    const cov = result?.coverage;

    const bloomsData = cov ? Object.entries(cov.blooms_coverage)
        .filter(([, v]) => v.exam > 0)
        .map(([k, v]) => ({ name: k, exam: v.exam, matched: v.matched, pct: v.pct })) : [];

    const unitData = cov ? Object.entries(cov.unit_coverage).map(([u, v]) => ({
        name: u.length > 20 ? u.slice(0, 20) + '…' : u, pct: v.pct, covered: v.covered, total: v.total
    })) : [];

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Analyze Exam Paper</div>
                <div className="page-subtitle">Upload exam paper → AI matches with question bank → Coverage report</div>
            </div>
            <div className="page-body">

                {msg.text && <div className={`alert alert-${msg.type === 'success' ? 'success' : 'error'}`}>{msg.text}</div>}

                {/* Upload Form */}
                <div className="card mb-2">
                    <div className="card-title" style={{ marginBottom: 20 }}><FileSearch size={16} /> Upload Exam Paper</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 20 }}>
                        <div className="form-group mb-0">
                            <label className="form-label">Subject *</label>
                            <select className="form-control" value={selectedSubject} onChange={e => setSelectedSubject(e.target.value)}>
                                <option value="">Select subject...</option>
                                {subjects.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
                            </select>
                        </div>
                        <div className="form-group mb-0">
                            <label className="form-label">Exam Type</label>
                            <select className="form-control" value={examType} onChange={e => setExamType(e.target.value)}>
                                <option>Internal</option><option>University Exam</option><option>CAT</option><option>Model Exam</option>
                            </select>
                        </div>
                        <div className="form-group mb-0">
                            <label className="form-label">Exam Date (optional)</label>
                            <input type="date" className="form-control" value={examDate} onChange={e => setExamDate(e.target.value)} />
                        </div>
                    </div>

                    <div
                        className={`upload-zone ${dragOver ? 'dragover' : ''}`}
                        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                        onDragLeave={() => setDragOver(false)}
                        onDrop={e => { e.preventDefault(); setDragOver(false); setFile(e.dataTransfer.files[0]); }}
                        onClick={() => fileRef.current.click()}
                        style={{ padding: 32 }}
                    >
                        <div className="upload-zone-icon" style={{ fontSize: 36 }}>📋</div>
                        {file ? (
                            <><h3 style={{ color: 'var(--color-success)' }}>✓ {file.name}</h3><p>{(file.size / 1024).toFixed(1)} KB</p></>
                        ) : (
                            <><h3>Drop exam paper here</h3><p>PDF or image — questions extracted automatically</p></>
                        )}
                        <input type="file" ref={fileRef} accept=".pdf,.jpg,.jpeg,.png" onChange={e => setFile(e.target.files[0])} style={{ display: 'none' }} />
                    </div>

                    <button
                        className="btn btn-primary btn-lg w-full"
                        style={{ marginTop: 16 }}
                        disabled={!file || !selectedSubject || loading}
                        onClick={handleAnalyze}
                    >
                        {loading
                            ? <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Analyzing — this may take a minute...</>
                            : <><TrendingUp size={18} /> Run Coverage Analysis</>}
                    </button>
                </div>

                {/* Results */}
                {result && cov && (
                    <div className="fade-in">
                        {/* Tabs */}
                        <div className="tabs">
                            {[['overview', '📊 Overview'], ['questions', '🔍 Question Match'], ['units', '📐 Unit Coverage'], ['blooms', '🎯 Bloom\'s Coverage']].map(([id, label]) => (
                                <div key={id} className={`tab ${activeTab === id ? 'active' : ''}`} onClick={() => setActiveTab(id)}>{label}</div>
                            ))}
                        </div>

                        {/* Overview */}
                        {activeTab === 'overview' && (
                            <div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
                                    <div className="stat-card"><div className="stat-label">Exam Questions</div><div className="stat-value">{cov.total_exam_questions}</div></div>
                                    <div className="stat-card success"><div className="stat-label">Matched</div><div className="stat-value">{cov.matched}</div></div>
                                    <div className="stat-card warning"><div className="stat-label">Possible Match</div><div className="stat-value">{cov.possible}</div></div>
                                    <div className="stat-card danger"><div className="stat-label">Not Matched</div><div className="stat-value">{cov.not_matched}</div></div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                                        <div className="card-title">Question Count Coverage</div>
                                        <CoverageRing pct={cov.overall_coverage_pct} label="Count" />
                                        <div style={{ fontSize: 13, color: 'var(--color-text-muted)', textAlign: 'center' }}>
                                            {cov.matched} of {cov.total_exam_questions} exam questions found in bank
                                        </div>
                                    </div>
                                    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                                        <div className="card-title">Marks-Weighted Coverage</div>
                                        <CoverageRing pct={cov.weighted_coverage_pct} label="Weighted" />
                                        <div style={{ fontSize: 13, color: 'var(--color-text-muted)', textAlign: 'center' }}>
                                            Coverage weighted by question marks
                                        </div>
                                    </div>
                                </div>

                                {cov.uncovered_bank_topics?.length > 0 && (
                                    <div className="card mt-2">
                                        <div className="card-title mb-2" style={{ marginBottom: 12 }}>⚠️ Uncovered Bank Topics</div>
                                        {cov.uncovered_bank_topics.map((u, i) => (
                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-danger-bg)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                                <span>{u.unit}</span>
                                                <span className="badge badge-danger">{u.uncovered_count} uncovered</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Question Matches */}
                        {activeTab === 'questions' && (
                            <div className="table-container">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>#</th><th style={{ minWidth: 260 }}>Exam Question</th>
                                            <th>Bloom</th><th>Marks</th>
                                            <th>Status</th><th>Score</th><th style={{ minWidth: 260 }}>Best Match in Bank</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.match_results.map((mr, i) => (
                                            <tr key={i} style={{
                                                background: mr.match_status === 'matched' ? 'rgba(34,197,94,0.04)'
                                                    : mr.match_status === 'possible' ? 'rgba(245,158,11,0.04)' : 'rgba(239,68,68,0.04)'
                                            }}>
                                                <td style={{ color: 'var(--color-text-dim)', fontSize: 12 }}>{i + 1}</td>
                                                <td style={{ fontSize: 13 }}>{mr.exam_question_text}</td>
                                                <td>{mr.blooms_level ? <span className="badge badge-info">{mr.blooms_level}</span> : '—'}</td>
                                                <td>{mr.marks ? <span className="badge badge-muted">{mr.marks}M</span> : '—'}</td>
                                                <td><MatchBadge status={mr.match_status} /></td>
                                                <td style={{ fontFamily: 'Space Grotesk', fontSize: 13, fontWeight: 600 }}>
                                                    <span style={{ color: mr.similarity_score >= 0.72 ? 'var(--color-success)' : mr.similarity_score >= 0.5 ? 'var(--color-warning)' : 'var(--color-danger)' }}>
                                                        {(mr.similarity_score * 100).toFixed(1)}%
                                                    </span>
                                                </td>
                                                <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                                                    {mr.bank_question_text || <em style={{ color: 'var(--color-danger)', opacity: 0.7 }}>No match found</em>}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Unit Coverage */}
                        {activeTab === 'units' && (
                            <div>
                                {unitData.length === 0 ? (
                                    <div className="empty-state"><div className="empty-state-icon">📐</div><h3>No unit data</h3><p>Assign units to question bank entries to see unit-wise coverage</p></div>
                                ) : (
                                    <div>
                                        <div className="card mb-2">
                                            <div className="card-title mb-2" style={{ marginBottom: 16 }}>Unit-wise Coverage</div>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <BarChart data={unitData} margin={{ top: 0, right: 20, left: 0, bottom: 60 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                                    <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} angle={-20} textAnchor="end" />
                                                    <YAxis stroke="var(--color-text-muted)" fontSize={11} domain={[0, 100]} unit="%" />
                                                    <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }} />
                                                    <Bar dataKey="pct" name="Coverage %" radius={[4, 4, 0, 0]}>
                                                        {unitData.map((entry, i) => (
                                                            <Cell key={i} fill={entry.pct >= 70 ? '#22c55e' : entry.pct >= 40 ? '#f59e0b' : '#ef4444'} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>

                                        {unitData.map((u, i) => (
                                            <div key={i} style={{ marginBottom: 12 }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                                                    <span>{u.name}</span>
                                                    <span style={{ color: u.pct >= 70 ? 'var(--color-success)' : u.pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)', fontWeight: 600 }}>
                                                        {u.covered}/{u.total} ({u.pct}%)
                                                    </span>
                                                </div>
                                                <div className="progress-bar">
                                                    <div className={`progress-fill ${u.pct >= 70 ? 'success' : u.pct >= 40 ? 'warning' : 'danger'}`} style={{ width: `${u.pct}%` }} />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Bloom's Coverage */}
                        {activeTab === 'blooms' && (
                            <div>
                                {bloomsData.length === 0 ? (
                                    <div className="empty-state"><div className="empty-state-icon">🎯</div><h3>No Bloom's data</h3><p>Ensure questions have Bloom's level assigned</p></div>
                                ) : (
                                    <div className="grid-2">
                                        <div className="card">
                                            <div className="card-title mb-2" style={{ marginBottom: 16 }}>Bloom's Distribution</div>
                                            <ResponsiveContainer width="100%" height={280}>
                                                <BarChart data={bloomsData}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                                                    <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={12} />
                                                    <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                                                    <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }} />
                                                    <Legend />
                                                    <Bar dataKey="exam" name="In Exam" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                                    <Bar dataKey="matched" name="Matched" fill="#22c55e" radius={[4, 4, 0, 0]} />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>

                                        <div className="card">
                                            <div className="card-title mb-2" style={{ marginBottom: 16 }}>Bloom's Match Rate</div>
                                            {bloomsData.map(b => (
                                                <div key={b.name} style={{ marginBottom: 14 }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                                                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                                            <span className="badge badge-primary">{b.name}</span>
                                                            <span>{b.matched}/{b.exam} questions</span>
                                                        </div>
                                                        <span style={{ fontWeight: 600, color: b.pct >= 70 ? 'var(--color-success)' : b.pct >= 40 ? 'var(--color-warning)' : 'var(--color-danger)' }}>
                                                            {b.pct.toFixed(1)}%
                                                        </span>
                                                    </div>
                                                    <div className="progress-bar">
                                                        <div className={`progress-fill ${b.pct >= 70 ? 'success' : b.pct >= 40 ? 'warning' : 'danger'}`} style={{ width: `${b.pct}%` }} />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
