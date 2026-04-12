import { useState, useEffect, useRef } from 'react';
import { getSubjects, getUnits, uploadQuestionBank, getStagingQuestions, updateStagingQuestions, approveStaging } from '../api';
import { UploadCloud, CheckCircle2, Save, ChevronRight, AlertTriangle } from 'lucide-react';

const BLOOMS = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6'];

export default function UploadBank() {
    const [step, setStep] = useState(1);
    const [subjects, setSubjects] = useState([]);
    const [units, setUnits] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedUnit, setSelectedUnit] = useState('');
    const [file, setFile] = useState(null);
    const [dragOver, setDragOver] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [staging, setStaging] = useState([]);
    const [docId, setDocId] = useState(null);
    const [msg, setMsg] = useState({ type: '', text: '' });
    const [zeroWarning, setZeroWarning] = useState(null);
    const fileRef = useRef();

    const flash = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 6000); };

    useEffect(() => { getSubjects().then(r => setSubjects(r.data)); }, []);
    useEffect(() => { if (selectedSubject) getUnits(selectedSubject).then(r => setUnits(r.data)); }, [selectedSubject]);

    const handleDrop = (e) => {
        e.preventDefault(); setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f) setFile(f);
    };

    const handleUpload = async () => {
        if (!file || !selectedSubject) { flash('error', 'Please select a subject and file'); return; }
        setUploading(true);
        setZeroWarning(null);
        const fd = new FormData();
        fd.append('file', file);
        fd.append('subject_id', selectedSubject);
        if (selectedUnit) fd.append('unit_id', selectedUnit);
        fd.append('uploaded_by', 'faculty');
        try {
            const r = await uploadQuestionBank(fd);
            const data = r.data;
            setDocId(data.doc_id);

            if (data.extracted_count === 0) {
                // Show warning + raw text debug info, stay on step 1
                setZeroWarning({
                    warning: data.warning || data.message || '0 questions extracted.',
                    raw_text_preview: data.raw_text_preview || '',
                    status: data.status,
                });
                flash('error', '0 questions extracted — see the diagnosis below');
            } else {
                const stagingRes = await getStagingQuestions(data.doc_id);
                setStaging(stagingRes.data.map(q => ({ ...q, _edited: false })));
                setStep(2);
                flash('success', `✅ Extracted ${data.extracted_count} questions — please review`);
            }
        } catch (err) {
            flash('error', err.response?.data?.detail || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const updateLocal = (id, field, val) => {
        setStaging(s => s.map(q => q.id === id ? { ...q, [field]: val, _edited: true } : q));
    };

    const saveEdits = async () => {
        const edited = staging.filter(q => q._edited);
        if (edited.length === 0) { flash('info', 'No changes to save'); return; }
        await updateStagingQuestions(edited.map(q => ({
            id: q.id, question_text: q.question_text, marks: q.marks,
            blooms_level: q.blooms_level, unit_id: q.unit_id ? parseInt(q.unit_id) : null
        })));
        setStaging(s => s.map(q => ({ ...q, _edited: false })));
        flash('success', 'Changes saved');
    };

    const toggleApprove = (id) => {
        setStaging(s => s.map(q => q.id === id ? { ...q, review_status: q.review_status === 'approved' ? 'pending' : 'approved', _edited: true } : q));
    };

    const approveAll = () => {
        setStaging(s => s.map(q => ({ ...q, review_status: 'approved', _edited: true })));
    };

    const handleFinalApprove = async () => {
        const toApprove = staging.filter(q => q.review_status === 'approved').map(q => q.id);
        if (toApprove.length === 0) { flash('error', 'No questions marked as approved'); return; }
        const edited = staging.filter(q => q._edited);
        if (edited.length > 0) {
            await updateStagingQuestions(edited.map(q => ({
                id: q.id, question_text: q.question_text, marks: q.marks,
                blooms_level: q.blooms_level, unit_id: q.unit_id ? parseInt(q.unit_id) : null,
                review_status: q.review_status
            })));
        }
        await approveStaging(toApprove);
        setStep(3);
    };

    const approvedCount = staging.filter(q => q.review_status === 'approved').length;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Upload Question Bank</div>
                <div className="page-subtitle">Upload PDF or image → AI extracts questions → Review → Save to database</div>
            </div>
            <div className="page-body">

                {/* Progress Steps */}
                <div style={{ display: 'flex', gap: 0, marginBottom: 28, alignItems: 'center' }}>
                    {[['1', 'Upload'], ['2', 'Review'], ['3', 'Done']].map(([n, label], i) => (
                        <div key={n} style={{ display: 'flex', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{
                                    width: 32, height: 32, borderRadius: '50%',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: 13, fontWeight: 700,
                                    backgroundImage: step > i + 1 ? 'var(--gradient-success)' : step === i + 1 ? 'var(--gradient-primary)' : 'none',
                                    background: step > i + 1 ? undefined : step === i + 1 ? undefined : 'var(--color-surface-2)',
                                    color: step >= i + 1 ? '#fff' : 'var(--color-text-muted)',
                                    border: step < i + 1 ? '1px solid var(--color-border)' : 'none'
                                }}>{step > i + 1 ? '✓' : n}</div>
                                <span style={{
                                    fontSize: 13,
                                    color: step === i + 1 ? 'var(--color-text)' : 'var(--color-text-muted)',
                                    fontWeight: step === i + 1 ? 600 : 400
                                }}>{label}</span>
                            </div>
                            {i < 2 && <ChevronRight size={16} style={{ color: 'var(--color-text-dim)', margin: '0 12px' }} />}
                        </div>
                    ))}
                </div>

                {msg.text && (
                    <div className={`alert alert-${msg.type === 'success' ? 'success' : msg.type === 'error' ? 'error' : 'info'}`}>
                        {msg.text}
                    </div>
                )}

                {/* Step 1: Upload */}
                {step === 1 && (
                    <div>
                        <div className="card">
                            <div className="grid-2">
                                <div className="form-group">
                                    <label className="form-label">Subject *</label>
                                    <select className="form-control" value={selectedSubject} onChange={e => setSelectedSubject(e.target.value)} required>
                                        <option value="">Select subject...</option>
                                        {subjects.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Unit (optional — can assign in review)</label>
                                    <select className="form-control" value={selectedUnit} onChange={e => setSelectedUnit(e.target.value)} disabled={!selectedSubject}>
                                        <option value="">All units / assign later</option>
                                        {units.map(u => <option key={u.id} value={u.id}>Unit {u.unit_no}: {u.unit_title}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div
                                className={`upload-zone ${dragOver ? 'dragover' : ''}`}
                                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleDrop}
                                onClick={() => fileRef.current.click()}
                            >
                                <div className="upload-zone-icon">📄</div>
                                {file ? (
                                    <><h3 style={{ color: 'var(--color-success)' }}>✓ {file.name}</h3><p>{(file.size / 1024).toFixed(1)} KB — ready to upload</p></>
                                ) : (
                                    <><h3>Drop your question bank here</h3><p>PDF or image (JPG, PNG) — AI will extract questions automatically</p></>
                                )}
                                <input type="file" ref={fileRef} accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.txt" onChange={e => setFile(e.target.files[0])} style={{ display: 'none' }} />
                            </div>

                            <button
                                className="btn btn-primary btn-lg w-full"
                                disabled={!file || !selectedSubject || uploading}
                                onClick={handleUpload}
                                style={{ marginTop: 20 }}
                            >
                                {uploading
                                    ? <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Extracting questions — please wait...</>
                                    : <><UploadCloud size={18} /> Upload & Extract Questions</>}
                            </button>
                        </div>

                        {/* 0-question warning box */}
                        {zeroWarning && (
                            <div className="card" style={{ marginTop: 16, border: '1px solid var(--color-warning)', background: 'rgba(245,158,11,0.06)' }}>
                                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 14 }}>
                                    <AlertTriangle size={20} style={{ color: 'var(--color-warning)', flexShrink: 0, marginTop: 2 }} />
                                    <div>
                                        <div style={{ fontWeight: 600, color: 'var(--color-warning)', marginBottom: 6 }}>No questions extracted</div>
                                        <div style={{ fontSize: 13, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>{zeroWarning.warning}</div>
                                    </div>
                                </div>

                                <div style={{ marginBottom: 12 }}>
                                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        Possible Reasons & Fixes
                                    </div>
                                    {[
                                        ['📄 Typed PDF', 'If pdfplumber extracted text → check that questions have numbers like "1." "1)" "Q1" "(1)" "(a)" "a."'],
                                        ['🖼️ Scanned / image PDF', 'Install Tesseract OCR → https://github.com/UB-Mannheim/tesseract/wiki — then restart backend'],
                                        ['📋 Non-standard format', 'Questions without numbers were not detected. Try adding numbers to your question bank before upload, or use the Manual Add feature.'],
                                        ['🔤 .txt file', 'You can also paste your questions into a .txt file with one question per line, each starting with a number like "1. Define..."'],
                                    ].map(([title, desc]) => (
                                        <div key={title} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
                                            <span style={{ fontSize: 13, minWidth: 140 }}>{title}</span>
                                            <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{desc}</span>
                                        </div>
                                    ))}
                                </div>

                                {zeroWarning.raw_text_preview && (
                                    <div>
                                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Raw Text Extracted by OCR (first 2000 chars)
                                        </div>
                                        <pre style={{
                                            background: 'var(--color-surface-2)', padding: 12,
                                            borderRadius: 'var(--radius-sm)', fontSize: 11,
                                            color: 'var(--color-text-muted)', overflowX: 'auto',
                                            whiteSpace: 'pre-wrap', maxHeight: 280, overflowY: 'auto',
                                            border: '1px solid var(--color-border)'
                                        }}>
                                            {zeroWarning.raw_text_preview || '(empty — no text was extracted from the file)'}
                                        </pre>
                                    </div>
                                )}

                                {/* Quick debug link */}
                                <div style={{ marginTop: 14, fontSize: 12, color: 'var(--color-text-dim)' }}>
                                    💡 Advanced: Use the <a href="http://localhost:8000/docs#/default/preview_raw_text_debug_raw_text_post" target="_blank" rel="noreferrer" style={{ color: 'var(--color-primary-light)' }}>
                                        /debug/raw-text endpoint in Swagger UI
                                    </a> to inspect what OCR sees from your file.
                                </div>
                            </div>
                        )}

                        {/* Tips */}
                        <div className="card" style={{ marginTop: 16 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>✅ Supported Question Formats</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                {[
                                    ['1. Question text', '1) Question text'],
                                    ['Q1. Question text', 'Q.1 Question text'],
                                    ['(1) Question text', '(a) Question text'],
                                    ['a. Question text', 'i. Question text'],
                                ].map(([a, b]) => (
                                    <div key={a} style={{ display: 'flex', gap: 16 }}>
                                        <code style={{ fontSize: 11, color: 'var(--color-success)', background: 'var(--color-success-bg)', padding: '2px 6px', borderRadius: 4 }}>{a}</code>
                                        <code style={{ fontSize: 11, color: 'var(--color-success)', background: 'var(--color-success-bg)', padding: '2px 6px', borderRadius: 4 }}>{b}</code>
                                    </div>
                                ))}
                            </div>
                            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--color-text-dim)' }}>
                                Bloom's levels auto-detected: K1–K6 labels, or BTL-1 through BTL-6, or command verbs (define, explain, analyze, design...)
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 2: Review Table */}
                {step === 2 && (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <div>
                                <div style={{ fontWeight: 600 }}>{staging.length} questions extracted — review before saving</div>
                                <div style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{approvedCount} approved • {staging.length - approvedCount} pending</div>
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button className="btn btn-secondary btn-sm" onClick={approveAll}>✓ Approve All</button>
                                <button className="btn btn-secondary btn-sm" onClick={saveEdits}><Save size={14} /> Save Edits</button>
                                <button className="btn btn-success btn-sm" onClick={handleFinalApprove} disabled={approvedCount === 0}>
                                    <CheckCircle2 size={14} /> Approve & Save ({approvedCount})
                                </button>
                            </div>
                        </div>

                        <div className="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>✓</th><th>Q.No</th><th>Section</th><th style={{ minWidth: 320 }}>Question Text</th>
                                        <th>Marks</th><th>Bloom</th><th>Unit</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {staging.map(q => (
                                        <tr key={q.id} style={{ background: q.review_status === 'approved' ? 'rgba(34,197,94,0.05)' : undefined }}>
                                            <td>
                                                <input type="checkbox" checked={q.review_status === 'approved'} onChange={() => toggleApprove(q.id)}
                                                    style={{ accentColor: 'var(--color-primary)', width: 16, height: 16 }} />
                                            </td>
                                            <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{q.question_no || '—'}</td>
                                            <td><span className="badge badge-muted">{q.section_name || '—'}</span></td>
                                            <td>
                                                <textarea rows={2} className="form-control"
                                                    value={q.question_text}
                                                    onChange={e => updateLocal(q.id, 'question_text', e.target.value)}
                                                    style={{ resize: 'vertical', minHeight: 56 }} />
                                                {q._edited && <div style={{ fontSize: 10, color: 'var(--color-warning)', marginTop: 2 }}>• Edited</div>}
                                            </td>
                                            <td>
                                                <input type="number" className="form-control" style={{ width: 70 }}
                                                    value={q.marks || ''} placeholder="—"
                                                    onChange={e => updateLocal(q.id, 'marks', parseFloat(e.target.value) || null)} />
                                            </td>
                                            <td>
                                                <select className="form-control" style={{ width: 80 }}
                                                    value={q.blooms_level || ''} onChange={e => updateLocal(q.id, 'blooms_level', e.target.value)}>
                                                    <option value="">—</option>
                                                    {BLOOMS.map(b => <option key={b} value={b}>{b}</option>)}
                                                </select>
                                            </td>
                                            <td>
                                                <select className="form-control" style={{ width: 160 }}
                                                    value={q.unit_id || ''} onChange={e => updateLocal(q.id, 'unit_id', e.target.value)}>
                                                    <option value="">— Assign —</option>
                                                    {units.map(u => <option key={u.id} value={u.id}>Unit {u.unit_no}</option>)}
                                                </select>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Step 3: Done */}
                {step === 3 && (
                    <div className="card" style={{ textAlign: 'center', padding: 60 }}>
                        <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
                        <h2 style={{ fontFamily: 'Space Grotesk', fontSize: 24, marginBottom: 8 }}>Question Bank Updated!</h2>
                        <p style={{ color: 'var(--color-text-muted)', marginBottom: 24 }}>
                            {approvedCount} questions have been approved and saved to the database.
                        </p>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                            <button className="btn btn-primary" onClick={() => { setStep(1); setFile(null); setStaging([]); setZeroWarning(null); }}>
                                <UploadCloud size={16} /> Upload Another
                            </button>
                            <a href="/question-bank" className="btn btn-secondary">View Question Bank</a>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
