import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { getSubjects, getUnits, uploadQuestionBank, importJsonQuestionBank, getStagingQuestions, updateStagingQuestions, approveStaging } from '../api';
import { UploadCloud, CheckCircle2, Save, ChevronRight, AlertTriangle, RefreshCw, Settings2 } from 'lucide-react';
import LoadingOverlay from '../components/LoadingOverlay';

const BLOOMS = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6'];

export default function UploadBank() {
    const [step, setStep] = useState(1);
    const [subjects, setSubjects] = useState([]);
    const [subjectsLoading, setSubjectsLoading] = useState(true);
    const [subjectsError, setSubjectsError] = useState('');
    const [units, setUnits] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedUnit, setSelectedUnit] = useState('');
    const [file, setFile] = useState(null);
    const [dragOver, setDragOver] = useState(false);
    
    // Progress States
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [phase, setPhase] = useState('');
    
    const [staging, setStaging] = useState([]);
    const [docId, setDocId] = useState(null);
    const [msg, setMsg] = useState({ type: '', text: '' });
    const [zeroWarning, setZeroWarning] = useState(null);
    const fileRef = useRef();

    const flash = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 6000); };

    const loadSubjects = async () => {
        setSubjectsLoading(true);
        setSubjectsError('');
        try {
            const r = await getSubjects();
            const items = Array.isArray(r.data) ? r.data : [];
            setSubjects(items);
            
            // Auto-select from URL
            const urlParams = new URLSearchParams(window.location.search);
            const subId = urlParams.get('subject_id');
            if (subId) {
                setSelectedSubject(subId);
            } else if (items.length === 1 && !selectedSubject) {
                setSelectedSubject(String(items[0].id));
            }
        } catch (err) {
            setSubjects([]);
            setSubjectsError('Could not load subjects from the backend.');
        } finally {
            setSubjectsLoading(false);
        }
    };

    useEffect(() => { loadSubjects(); }, []);

    useEffect(() => {
        if (!selectedSubject) { setUnits([]); return; }
        getUnits(selectedSubject).then(r => setUnits(r.data)).catch(() => setUnits([]));
    }, [selectedSubject]);

    const handleUpload = async () => {
        if (!file || !selectedSubject) { flash('error', 'Please select a subject and file'); return; }
        
        setUploading(true);
        setProgress(0);
        setPhase('Initializing...');
        setZeroWarning(null);

        const progressInterval = setInterval(() => {
            setProgress(prev => {
                if (prev < 20) { setPhase('Uploading file...'); return prev + 2; }
                if (prev < 50) { setPhase('Analyzing layout & OCR...'); return prev + 1; }
                if (prev < 85) { setPhase('Extracting structured questions...'); return prev + 0.5; }
                if (prev < 98) { setPhase('Generating semantic embeddings...'); return prev + 0.2; }
                return prev;
            });
        }, 300);

        const fd = new FormData();
        fd.append('file', file);
        fd.append('subject_id', selectedSubject);
        if (selectedUnit) fd.append('unit_id', selectedUnit);
        fd.append('uploaded_by', 'faculty');

        try {
            if (file.name.endsWith('.json')) {
                const r = await importJsonQuestionBank(fd);
                flash('success', `✅ Successfully imported ${r.data.imported_count} questions!`);
                setStep(3);
                return;
            }

            const r = await uploadQuestionBank(fd);
            const data = r.data;
            setDocId(data.doc_id);

            if (data.extracted_count === 0) {
                setZeroWarning({
                    warning: data.warning || '0 questions extracted.',
                    raw_text_preview: data.raw_text_preview || '',
                });
            } else {
                setPhase('Finalizing review state...');
                setProgress(100);
                const stagingRes = await getStagingQuestions(data.doc_id);
                setStaging(stagingRes.data.map(q => ({ ...q, _edited: false })));
                setTimeout(() => setStep(2), 500);
            }
        } catch (err) {
            flash('error', err.response?.data?.detail || 'Upload failed');
        } finally {
            clearInterval(progressInterval);
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
        await handleFinalApproveCall(toApprove);
    };

    const handleFinalApproveCall = async (ids) => {
        const edited = staging.filter(q => q._edited);
        if (edited.length > 0) {
            await updateStagingQuestions(edited.map(q => ({
                id: q.id, question_text: q.question_text, marks: q.marks,
                blooms_level: q.blooms_level, unit_id: q.unit_id ? parseInt(q.unit_id) : null,
                review_status: q.review_status
            })));
        }
        await approveStaging(ids);
        setStep(3);
    };

    const approvedCount = staging.filter(q => q.review_status === 'approved').length;

    return (
        <div className="fade-in">
            <LoadingOverlay isVisible={uploading} phase={phase} progress={progress} />
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
                                    <label className="form-label">Unit (optional)</label>
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
                                onDrop={(e) => { e.preventDefault(); setDragOver(false); setFile(e.dataTransfer.files[0]); }}
                                onClick={() => fileRef.current.click()}
                            >
                                <div className="upload-zone-icon">📄</div>
                                {file ? (
                                    <><h3 style={{ color: 'var(--color-success)' }}>✓ {file.name}</h3><p>{(file.size / 1024).toFixed(1)} KB — ready</p></>
                                ) : (
                                    <><h3>Drop your question bank here</h3><p>PDF, JSON, or image</p></>
                                )}
                                <input type="file" ref={fileRef} onChange={e => setFile(e.target.files[0])} style={{ display: 'none' }} />
                            </div>

                            <button className="btn btn-lg btn-primary w-full mt-2" disabled={!file || !selectedSubject || uploading} onClick={handleUpload}>
                                <UploadCloud size={18} /> Upload & Extract Questions
                            </button>
                        </div>
                        
                        {zeroWarning && (
                            <div className="card mt-2 alert alert-error">
                                <div style={{ fontWeight: 600 }}>{zeroWarning.warning}</div>
                                {zeroWarning.raw_text_preview && (
                                    <pre style={{ marginTop: 10, fontSize: 11, background: 'rgba(0,0,0,0.1)', padding: 10, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                                        {zeroWarning.raw_text_preview}
                                    </pre>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {step === 2 && (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <div>
                                <div style={{ fontWeight: 600 }}>{staging.length} questions extracted</div>
                                <div style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{approvedCount} approved</div>
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
                                        <th>✓</th><th>Q.No</th><th>Text</th><th>Marks</th><th>Bloom</th><th>Unit</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {staging.map(q => (
                                        <tr key={q.id}>
                                            <td><input type="checkbox" checked={q.review_status === 'approved'} onChange={() => toggleApprove(q.id)} /></td>
                                            <td>{q.question_no}</td>
                                            <td><textarea className="form-control" value={q.question_text} onChange={e => updateLocal(q.id, 'question_text', e.target.value)} /></td>
                                            <td><input type="number" className="form-control" style={{ width: 60 }} value={q.marks || ''} onChange={e => updateLocal(q.id, 'marks', e.target.value)} /></td>
                                            <td>
                                                <select className="form-control" value={q.blooms_level || ''} onChange={e => updateLocal(q.id, 'blooms_level', e.target.value)}>
                                                    <option value="">—</option>
                                                    {BLOOMS.map(b => <option key={b} value={b}>{b}</option>)}
                                                </select>
                                            </td>
                                            <td>
                                                <select className="form-control" value={q.unit_id || ''} onChange={e => updateLocal(q.id, 'unit_id', e.target.value)}>
                                                    <option value="">—</option>
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

                {step === 3 && (
                    <div className="card" style={{ textAlign: 'center', padding: 60 }}>
                        <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
                        <h2 style={{ marginBottom: 8 }}>Question Bank Updated!</h2>
                        <p style={{ color: 'var(--color-text-muted)', marginBottom: 24 }}>Your master question bank is ready for analysis.</p>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                            <button className="btn btn-secondary" onClick={() => { setStep(1); setFile(null); }}>
                                <RefreshCw size={18} /> Upload Another
                            </button>
                            <Link to="/analyze" className="btn btn-primary">
                                <ChevronRight size={18} /> Go to Exam Analysis
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
