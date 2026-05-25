import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, Book, Building2, Database, FileText, Filter, Search, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { clearAllBankQuestions, deleteBankDocument, deleteBankQuestion, getBankDocuments, getBankQuestions, getDepartments, getSubjects, getUnits } from '../api';

const BLOOMS = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6'];

import Skeleton from '../components/Skeleton';

export default function QuestionBank() {
    const [questions, setQuestions] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [units, setUnits] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({ department_id: '', subject_id: '', unit_id: '', blooms_level: '', doc_id: '' });
    const [search, setSearch] = useState('');
    const [showClearModal, setShowClearModal] = useState(false);
    const [clearing, setClearing] = useState(false);
    const [clearError, setClearError] = useState('');

    const load = async () => {
        setLoading(true);
        try {
            const params = {};
            if (filters.subject_id) params.subject_id = filters.subject_id;
            if (filters.unit_id) params.unit_id = filters.unit_id;
            if (filters.blooms_level) params.blooms_level = filters.blooms_level;
            if (filters.doc_id) params.doc_id = filters.doc_id;
            const r = await getBankQuestions(params);
            setQuestions(r.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const loadDocs = async () => {
        try {
            const r = await getBankDocuments();
            setDocuments(r.data);
        } catch (err) {
            console.error("Doc load error", err);
        }
    };

    useEffect(() => {
        getDepartments().then(r => setDepartments(r.data));
        getSubjects().then(r => setSubjects(r.data));
        loadDocs();
    }, []);

    useEffect(() => {
        if (filters.subject_id) getUnits(filters.subject_id).then(r => setUnits(r.data));
        else setUnits([]);
    }, [filters.subject_id]);

    useEffect(() => { load(); }, [filters]);

    const handleDelete = async (id) => {
        if (!confirm('Delete this question?')) return;
        await deleteBankQuestion(id);
        setQuestions(q => q.filter(x => x.id !== id));
    };

    const handleDeleteDoc = async (e, docId) => {
        e.stopPropagation();
        if (!confirm('Delete this entire document and all its questions?')) return;
        try {
            await deleteBankDocument(docId);
            setDocuments(d => d.filter(x => x.id !== docId));
            if (String(filters.doc_id) === String(docId)) {
                setFilters(p => ({ ...p, doc_id: '' }));
            } else {
                load();
            }
        } catch (err) {
            alert('Failed to delete document');
        }
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

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { duration: 0.2 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 10 },
        show: { opacity: 1, y: 0 }
    };

    const modal = showClearModal && createPortal(
        <AnimatePresence>
            <div style={{
                position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 9999, backdropFilter: 'blur(8px)'
            }}>
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    style={{
                        background: 'var(--color-surface-1)', border: '1px solid var(--color-danger)',
                        borderRadius: 20, padding: 32, maxWidth: 440, width: '90%',
                        boxShadow: '0 24px 64px rgba(0,0,0,0.8)',
                        background: 'linear-gradient(135deg, var(--color-surface-1) 0%, #1a1010 100%)'
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
                        <div style={{
                            width: 50, height: 50, borderRadius: 12,
                            background: 'rgba(239,68,68,0.15)', display: 'flex',
                            alignItems: 'center', justifyContent: 'center', flexShrink: 0
                        }}>
                            <AlertTriangle size={26} color="#ef4444" />
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: 18, color: '#fff' }}>Confirm Destruction</div>
                            <div style={{ fontSize: 13, color: 'var(--color-text-dim)', marginTop: 2 }}>
                                Permanent database operation
                            </div>
                        </div>
                    </div>

                    <p style={{ fontSize: 14, color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: 24 }}>
                        You are about to purge&nbsp;
                        <strong style={{ color: '#fff' }}>{questions.length} question{questions.length !== 1 ? 's' : ''}</strong>
                        {filters.subject_id ? ` for the active subject filter` : ` from the entire global bank`}.
                        This cannot be undone.
                    </p>

                    {clearError && (
                        <div style={{
                            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                            borderRadius: 10, padding: '12px 16px', marginBottom: 20,
                            fontSize: 13, color: '#f87171'
                        }}>
                            Error: {clearError}
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                        <button
                            className="btn btn-secondary"
                            onClick={() => { setShowClearModal(false); setClearError(''); }}
                            disabled={clearing}
                            style={{ borderRadius: 10 }}
                        >
                            Abort
                        </button>
                        <button
                            className="btn btn-danger"
                            onClick={handleClearAll}
                            disabled={clearing}
                            style={{ borderRadius: 10, display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px' }}
                        >
                            {clearing ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Trash2 size={16} />}
                            {clearing ? 'Purging…' : 'Execute Clear'}
                        </button>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>,
        document.body
    );

    return (
        <div className="fade-in">
            <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                    <div className="page-title">Question Bank</div>
                    <div className="page-subtitle">Browse and manage structured database content</div>
                </div>
                {questions.length > 0 && (
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="btn btn-danger"
                        onClick={() => setShowClearModal(true)}
                        style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, padding: '10px 16px', borderRadius: 12 }}
                    >
                        <Trash2 size={16} />
                        Clear Database
                    </motion.button>
                )}
            </div>

            <div className="page-body">
                {/* Stats */}
                <motion.div
                    className="stat-grid"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', marginBottom: 24 }}
                >
                    <div className="card" style={{ padding: '16px 20px' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-dim)', textTransform: 'uppercase', marginBottom: 4 }}>Volume</div>
                        <div style={{ fontSize: 28, fontWeight: 800 }}>{questions.length}</div>
                    </div>
                    {BLOOMS.map(b => (
                        <div key={b} className="card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-dim)', textTransform: 'uppercase', marginBottom: 4 }}>{b}</div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: `var(--color-${bloomBadge(b)})` }}>{bloomCounts[b]}</div>
                        </div>
                    ))}
                </motion.div>

                {/* Filters */}
                <div className="card mb-2" style={{ padding: 20 }}>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 200 }}>
                            <Building2 size={18} color="var(--color-text-dim)" />
                            <select className="form-control" style={{ background: 'transparent', border: 'none', fontWeight: 600 }}
                                value={filters.department_id} onChange={e => setFilters(p => ({ ...p, department_id: e.target.value, subject_id: '' }))}>
                                <option value="">All Departments</option>
                                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                            </select>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 200 }}>
                            <Filter size={18} color="var(--color-text-dim)" />
                            <select className="form-control" style={{ background: 'transparent', border: 'none', fontWeight: 600 }}
                                value={filters.subject_id} onChange={e => setFilters(p => ({ ...p, subject_id: e.target.value, unit_id: '' }))}>
                                <option value="">Global Subject List</option>
                                {subjects
                                    .filter(s => !filters.department_id || String(s.department_id) === String(filters.department_id))
                                    .map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)
                                }
                            </select>
                        </div>

                        <div style={{ position: 'relative', flex: 2, minWidth: 300 }}>
                            <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-dim)' }} />
                            <input className="form-control" style={{ paddingLeft: 40, borderRadius: 12, background: 'rgba(255,255,255,0.03)' }}
                                placeholder="Search knowledge base..." value={search} onChange={e => setSearch(e.target.value)} />
                        </div>
                    </div>
                </div>                {/* Layout Container */}
                <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>

                    {/* Left Sidebar: Source Documents */}
                    <div style={{ width: 320, flexShrink: 0 }}>
                        <div className="card" style={{ padding: 20, position: 'sticky', top: 20 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                                <FileText size={20} color="var(--color-primary)" />
                                <h3 style={{ fontSize: 16, fontWeight: 700 }}>Source Documents</h3>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <button
                                    className={`btn ${!filters.doc_id ? 'btn-primary' : 'btn-ghost'}`}
                                    onClick={() => setFilters(p => ({ ...p, doc_id: '' }))}
                                    style={{ justifyContent: 'flex-start', textAlign: 'left', padding: '10px 14px', color: !filters.doc_id ? '#fff' : 'var(--color-text-dim)' }}
                                >
                                    <Database size={16} /> All Questions
                                </button>

                                {documents.filter(d => !filters.subject_id || String(d.subject_id) === String(filters.subject_id)).map(doc => (
                                    <motion.button
                                        key={doc.id}
                                        whileHover={{ x: 4 }}
                                        className={`card ${String(filters.doc_id) === String(doc.id) ? 'active-doc' : ''}`}
                                        onClick={() => setFilters(p => ({ ...p, doc_id: doc.id }))}
                                        style={{
                                            padding: '12px 14px',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            border: String(filters.doc_id) === String(doc.id) ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                                            background: String(filters.doc_id) === String(doc.id) ? 'rgba(99,102,241,0.05)' : 'transparent',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: 4,
                                            position: 'relative'
                                        }}
                                    >
                                        <div
                                            onClick={(e) => handleDeleteDoc(e, doc.id)}
                                            style={{
                                                position: 'absolute', top: 8, right: 8,
                                                width: 24, height: 24, borderRadius: 6,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                color: 'var(--color-text-dim)',
                                                transition: 'all 0.2s'
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = '#ef4444'; }}
                                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-dim)'; }}
                                        >
                                            <Trash2 size={14} />
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, paddingRight: 20, color: '#fff' }}>
                                            <Book size={14} color="var(--color-primary-light)" />
                                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: 'var(--color-text-dim)' }}>
                                            <span>{doc.subject_code}</span>
                                            <span className="badge badge-primary" style={{ padding: '2px 6px' }}>{doc.question_count} Qs</span>
                                        </div>
                                    </motion.button>
                                ))}

                                {documents.filter(d => !filters.subject_id || String(d.subject_id) === String(filters.subject_id)).length === 0 && (
                                    <div style={{
                                        textAlign: 'center', padding: '32px 16px',
                                        color: 'var(--color-text-dim)', fontSize: 13,
                                        border: '1px dashed var(--color-border)', borderRadius: 16,
                                        background: 'rgba(255,255,255,0.01)'
                                    }}>
                                        <div style={{ fontSize: 24, marginBottom: 12 }}>📂</div>
                                        <div style={{ marginBottom: 16 }}>No bank files found for this subject.</div>
                                        <button
                                            className="btn btn-primary btn-sm"
                                            style={{ width: '100%', borderRadius: 10 }}
                                            onClick={() => window.location.href = `/upload-bank?subject_id=${filters.subject_id}`}
                                        >
                                            Upload Now
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Content: Question Table */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <AnimatePresence>
                            {loading ? (
                                <motion.div
                                    key="loading"
                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                    className="table-container glass-card"
                                    style={{ borderRadius: 16, border: '1px solid var(--color-border)', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}
                                >
                                    {[1, 2, 3, 4, 5, 6].map(i => (
                                        <div key={i} style={{ display: 'flex', gap: 16, padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
                                            <Skeleton width={40} height={40} />
                                            <div style={{ flex: 1 }}><Skeleton height={20} width="60%" /></div>
                                            <Skeleton width={80} height={20} />
                                        </div>
                                    ))}
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="content"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="table-container glass-card shadow-lg"
                                    style={{ borderRadius: 16, overflow: 'hidden', border: '1px solid var(--color-border)' }}
                                >
                                    <table className="table" style={{ margin: 0 }}>
                                        <thead>
                                            <tr>
                                                <th style={{ width: 50, textAlign: 'center' }}>#</th>
                                                <th style={{ width: 120 }}>Scope</th>
                                                <th>Question Text</th>
                                                <th style={{ width: 140 }}>Properties</th>
                                                <th style={{ width: 120 }}>Unit</th>
                                                <th style={{ width: 80, textAlign: 'center' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <motion.tbody variants={containerVariants} initial="hidden" animate="show">
                                            {filtered.map((q, idx) => (
                                                <motion.tr key={q.id} variants={itemVariants}>
                                                    <td style={{ textAlign: 'center', color: 'var(--color-text-dim)', fontSize: 13 }}>{idx + 1}.</td>
                                                    <td>
                                                        <span className="badge badge-secondary" style={{ fontSize: 10, letterSpacing: '0.05em' }}>
                                                            {q.section_name || 'PART A'}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.5 }}>{q.question_text}</div>
                                                    </td>
                                                    <td>
                                                        <div style={{ display: 'flex', gap: 6 }}>
                                                            {q.blooms_level && <span className={`badge badge-${bloomBadge(q.blooms_level)}`} style={{ fontSize: 10 }}>{q.blooms_level}</span>}
                                                            {q.marks && <span className={`badge badge-${marksBadge(q.marks)}`} style={{ fontSize: 10 }}>{q.marks}M</span>}
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                                                            {q.unit_no ? `Unit ${q.unit_no}` : 'Unassigned'}
                                                        </div>
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-text-dim)' }} onClick={() => handleDelete(q.id)}>
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </td>
                                                </motion.tr>
                                            ))}
                                        </motion.tbody>
                                    </table>
                                    {filtered.length === 0 && (
                                        <div style={{ padding: 80, textAlign: 'center', color: 'var(--color-text-dim)' }}>
                                            <div style={{ fontSize: 48, marginBottom: 16 }}>📂</div>
                                            <h3 style={{ fontWeight: 600 }}>No questions found</h3>
                                            <p style={{ fontSize: 14 }}>Try adjusting your filters or search query</p>
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
            {modal}
        </div>
    );
}
