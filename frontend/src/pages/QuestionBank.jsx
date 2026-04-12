import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { getBankQuestions, deleteBankQuestion, getSubjects, getUnits, clearAllBankQuestions } from '../api';
import { Trash2, Search, Database, AlertTriangle } from 'lucide-react';

const BLOOMS = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6'];

export default function QuestionBank() {
    const [questions, setQuestions] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [units, setUnits] = useState([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({ subject_id: '', unit_id: '', blooms_level: '' });
    const [search, setSearch] = useState('');
    const [showClearModal, setShowClearModal] = useState(false);
    const [clearing, setClearing] = useState(false);
    const [clearError, setClearError] = useState('');

    const load = async () => {
        setLoading(true);
        const params = {};
        if (filters.subject_id) params.subject_id = filters.subject_id;
        if (filters.unit_id) params.unit_id = filters.unit_id;
        if (filters.blooms_level) params.blooms_level = filters.blooms_level;
        const r = await getBankQuestions(params);
        setQuestions(r.data);
        setLoading(false);
    };

    useEffect(() => { getSubjects().then(r => setSubjects(r.data)); }, []);
    useEffect(() => { if (filters.subject_id) getUnits(filters.subject_id).then(r => setUnits(r.data)); else setUnits([]); }, [filters.subject_id]);
    useEffect(() => { load(); }, [filters]);

    const handleDelete = async (id) => {
        if (!confirm('Delete this question?')) return;
        await deleteBankQuestion(id);
        setQuestions(q => q.filter(x => x.id !== id));
    };

    const handleClearAll = async () => {
        setClearing(true);
        setClearError('');
        try {
            await clearAllBankQuestions(filters.subject_id || null);
            setShowClearModal(false);
            await load();
        } catch (err) {
            const msg = err?.response?.data?.detail || err?.message || 'Unknown error';
            setClearError(msg);
        } finally {
            setClearing(false);
        }
    };

    const filtered = questions.filter(q =>
        !search || q.question_text.toLowerCase().includes(search.toLowerCase())
    );

    const bloomBadge = (b) => {
        const map = { K1: 'info', K2: 'success', K3: 'warning', K4: 'primary', K5: 'danger', K6: 'muted' };
        return map[b] || 'muted';
    };

    const marksBadge = (m) => {
        if (!m) return 'muted';
        if (m <= 2) return 'info';
        if (m <= 8) return 'warning';
        return 'primary';
    };

    // Stats
    const totalMarks = questions.reduce((a, q) => a + (q.marks || 0), 0);
    const bloomCounts = BLOOMS.reduce((a, b) => ({ ...a, [b]: questions.filter(q => q.blooms_level === b).length }), {});

    // Modal rendered via portal so CSS transform on .fade-in doesn't break position:fixed
    const modal = showClearModal && createPortal(
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.70)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, backdropFilter: 'blur(6px)'
        }}>
            <div style={{
                background: '#111827', border: '1px solid rgba(99,130,201,0.25)',
                borderRadius: 16, padding: 32, maxWidth: 440, width: '90%',
                boxShadow: '0 24px 64px rgba(0,0,0,0.7)'
            }}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                    <div style={{
                        width: 44, height: 44, borderRadius: 10,
                        background: 'rgba(239,68,68,0.15)', display: 'flex',
                        alignItems: 'center', justifyContent: 'center', flexShrink: 0
                    }}>
                        <AlertTriangle size={22} color="#ef4444" />
                    </div>
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 17, color: '#e2e8f0' }}>Clear Question Bank</div>
                        <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 2 }}>
                            This action cannot be undone
                        </div>
                    </div>
                </div>

                {/* Body */}
                <p style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.6, marginBottom: 24 }}>
                    You are about to permanently delete&nbsp;
                    <strong style={{ color: '#e2e8f0' }}>{questions.length} question{questions.length !== 1 ? 's' : ''}</strong>
                    {filters.subject_id
                        ? ` for the selected subject`
                        : ` from the entire question bank`
                    }.
                </p>

                {/* Error */}
                {clearError && (
                    <div style={{
                        background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.35)',
                        borderRadius: 8, padding: '10px 14px', marginBottom: 16,
                        fontSize: 13, color: '#ef4444'
                    }}>
                        ⚠ {clearError}
                    </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                    <button
                        className="btn btn-secondary"
                        onClick={() => { setShowClearModal(false); setClearError(''); }}
                        disabled={clearing}
                    >
                        Cancel
                    </button>
                    <button
                        className="btn btn-danger"
                        onClick={handleClearAll}
                        disabled={clearing}
                        style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                        {clearing
                            ? <span className="spinner" style={{ width: 14, height: 14 }} />
                            : <Trash2 size={14} />
                        }
                        {clearing ? 'Clearing…' : 'Yes, Delete All'}
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );

    return (
        <div className="fade-in">
            <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                    <div className="page-title">Question Bank</div>
                    <div className="page-subtitle">Browse and manage all approved questions in the database</div>
                </div>
                {questions.length > 0 && (
                    <button
                        className="btn btn-danger"
                        onClick={() => setShowClearModal(true)}
                        style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', marginTop: 4 }}
                    >
                        <Trash2 size={15} />
                        Clear All{filters.subject_id ? ' (Subject)' : ''}
                    </button>
                )}
            </div>
            <div className="page-body">

                {/* mini stats */}
                <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
                    <div className="stat-card" style={{ padding: 16 }}>
                        <div className="stat-label">Total Questions</div>
                        <div className="stat-value">{questions.length}</div>
                    </div>
                    <div className="stat-card success" style={{ padding: 16 }}>
                        <div className="stat-label">Total Marks</div>
                        <div className="stat-value">{totalMarks}</div>
                    </div>
                    {BLOOMS.map(b => (
                        <div key={b} className="stat-card" style={{ padding: 16 }}>
                            <div className="stat-label">{b}</div>
                            <div className="stat-value" style={{ fontSize: 24 }}>{bloomCounts[b]}</div>
                        </div>
                    ))}
                </div>

                {/* Filters */}
                <div className="card mb-2">
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                        <div style={{ flex: 1, minWidth: 180 }}>
                            <label className="form-label">Subject</label>
                            <select className="form-control" value={filters.subject_id} onChange={e => setFilters(p => ({ ...p, subject_id: e.target.value, unit_id: '' }))}>
                                <option value="">All subjects</option>
                                {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                            </select>
                        </div>
                        <div style={{ flex: 1, minWidth: 150 }}>
                            <label className="form-label">Unit</label>
                            <select className="form-control" value={filters.unit_id} onChange={e => setFilters(p => ({ ...p, unit_id: e.target.value }))} disabled={!filters.subject_id}>
                                <option value="">All units</option>
                                {units.map(u => <option key={u.id} value={u.id}>Unit {u.unit_no}: {u.unit_title}</option>)}
                            </select>
                        </div>
                        <div style={{ minWidth: 120 }}>
                            <label className="form-label">Bloom's Level</label>
                            <select className="form-control" value={filters.blooms_level} onChange={e => setFilters(p => ({ ...p, blooms_level: e.target.value }))}>
                                <option value="">All levels</option>
                                {BLOOMS.map(b => <option key={b} value={b}>{b}</option>)}
                            </select>
                        </div>
                        <div style={{ flex: 2, minWidth: 200 }}>
                            <label className="form-label">Search</label>
                            <div style={{ position: 'relative' }}>
                                <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                                <input className="form-control" style={{ paddingLeft: 32 }} placeholder="Search questions..." value={search} onChange={e => setSearch(e.target.value)} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Table */}
                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><div className="spinner spinner-lg" /></div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon"><Database size={48} /></div>
                        <h3>No questions found</h3>
                        <p>Upload a question bank PDF to get started</p>
                    </div>
                ) : (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th><th>Section</th><th style={{ minWidth: 380 }}>Question</th>
                                    <th>Bloom</th><th>Marks</th><th>Unit</th><th>Type</th><th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((q, i) => (
                                    <tr key={q.id}>
                                        <td style={{ color: 'var(--color-text-dim)', fontSize: 12 }}>{q.question_no || i + 1}</td>
                                        <td><span className="badge badge-muted">{q.section_name || '—'}</span></td>
                                        <td style={{ maxWidth: 400 }}>
                                            <div style={{ fontSize: 13, lineHeight: 1.5 }}>{q.question_text}</div>
                                        </td>
                                        <td>
                                            {q.blooms_level ? (
                                                <span className={`badge badge-${bloomBadge(q.blooms_level)}`}>{q.blooms_level}</span>
                                            ) : <span className="text-dim">—</span>}
                                        </td>
                                        <td>
                                            {q.marks ? (
                                                <span className={`badge badge-${marksBadge(q.marks)}`}>{q.marks}M</span>
                                            ) : <span className="text-dim">—</span>}
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                                            {q.unit_title ? `Unit: ${q.unit_title.slice(0, 25)}...` : <span className="text-dim">—</span>}
                                        </td>
                                        <td><span className="badge badge-muted">{q.question_type || '—'}</span></td>
                                        <td>
                                            <button className="btn btn-danger btn-sm" onClick={() => handleDelete(q.id)}>
                                                <Trash2 size={13} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Portal modal — rendered into document.body to escape .fade-in transform context */}
            {modal}
        </div>
    );
}
