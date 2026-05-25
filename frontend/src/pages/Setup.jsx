// Last Updated: 2026-04-28T11:02:00Z
import { useState, useEffect } from 'react';
import {
    getDepartments, createDepartment,
    getRegulations, createRegulation,
    getSubjects, createSubject, deleteSubject, updateSubject,
    getUnits, createUnit
} from '../api';
import { Plus, Building2, BookOpen, Layers, Tag, Trash2, Edit2, Check, X } from 'lucide-react';

import Skeleton from '../components/Skeleton';

function FormCard({ title, icon: Icon, children }) {
    return (
        <div className="card">
            <div className="card-header">
                <div className="card-title"><Icon size={16} /> {title}</div>
            </div>
            {children}
        </div>
    );
}

const COMMON_DEPARTMENTS = [
    { name: 'Computer Science and Engineering', code: 'CSE' },
    { name: 'Information Technology', code: 'IT' },
    { name: 'Artificial Intelligence and Data Science', code: 'AIDS' },
    { name: 'Electrical and Electronics Engineering', code: 'EEE' },
    { name: 'Electronics and Communication Engineering', code: 'ECE' },
    { name: 'Civil Engineering', code: 'CIVIL' },
    { name: 'Mechanical Engineering', code: 'MECH' },
];

export default function Setup() {
    const [departments, setDepartments] = useState([]);
    const [regulations, setRegulations] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [units, setUnits] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedSubject, setSelectedSubject] = useState(null);

    const [isCustomDept, setIsCustomDept] = useState(false);
    const [deptForm, setDeptForm] = useState({ name: '', code: '' });
    const [regForm, setRegForm] = useState({ name: '' });
    const [subjForm, setSubjForm] = useState({ name: '', code: '', semester: 1, department_id: '', regulation_id: '' });
    const [unitForm, setUnitForm] = useState({ subject_id: '', unit_no: '', unit_title: '', keywords: '' });

    const [editingSubj, setEditingSubj] = useState(null);
    const [editForm, setEditForm] = useState({ name: '', code: '' });

    const [msg, setMsg] = useState({ type: '', text: '' });

    const flash = (type, text) => {
        setMsg({ type, text });
        setTimeout(() => setMsg({ type: '', text: '' }), type === 'error' ? 6000 : 3000);
    };

    const reload = async () => {
        setLoading(true);
        try {
            const [d, r, s] = await Promise.all([getDepartments(), getRegulations(), getSubjects()]);
            setDepartments(d.data);
            setRegulations(r.data);
            setSubjects(s.data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { reload(); }, []);

    useEffect(() => {
        if (selectedSubject) getUnits(selectedSubject).then(r => setUnits(r.data));
    }, [selectedSubject]);

    const submitDept = async (e) => {
        e.preventDefault();
        try { await createDepartment(deptForm); flash('success', 'Department created'); setDeptForm({ name: '', code: '' }); reload(); }
        catch { flash('error', 'Failed to create department'); }
    };

    const submitReg = async (e) => {
        e.preventDefault();
        try { await createRegulation(regForm); flash('success', 'Regulation created'); setRegForm({ name: '' }); reload(); }
        catch { flash('error', 'Failed to create regulation'); }
    };

    const submitSubj = async (e) => {
        e.preventDefault();
        try {
            await createSubject({ ...subjForm, semester: parseInt(subjForm.semester), department_id: parseInt(subjForm.department_id), regulation_id: parseInt(subjForm.regulation_id) });
            flash('success', 'Subject created successfully!');
            setSubjForm({ name: '', code: '', semester: 1, department_id: '', regulation_id: '' });
            reload();
        } catch (err) {
            const detail = err?.response?.data?.detail;
            flash('error', detail || 'Failed to create subject');
        }
    };

    const handleDeleteSubj = async (id) => {
        if (!confirm('Delete this subject? This will also remove associated syllabus units.')) return;
        try {
            await deleteSubject(id);
            flash('success', 'Subject deleted');
            reload();
        } catch {
            flash('error', 'Failed to delete subject');
        }
    };

    const startEdit = (s) => {
        setEditingSubj(s.id);
        setEditForm({ name: s.name, code: s.code });
    };

    const saveEdit = async (id) => {
        try {
            await updateSubject(id, editForm);
            flash('success', 'Subject updated');
            setEditingSubj(null);
            reload();
        } catch {
            flash('error', 'Failed to update subject');
        }
    };

    const submitUnit = async (e) => {
        e.preventDefault();
        try {
            await createUnit({ ...unitForm, subject_id: parseInt(unitForm.subject_id), unit_no: parseInt(unitForm.unit_no) });
            flash('success', 'Syllabus unit added!');
            setUnitForm({ ...unitForm, unit_no: '', unit_title: '', keywords: '' });
            if (selectedSubject == unitForm.subject_id) {
                getUnits(selectedSubject).then(r => setUnits(r.data));
            }
        } catch {
            flash('error', 'Failed to add syllabus unit');
        }
    };

    return (
        <div className="fade-in">
            {msg.text && (
                <div className={`alert alert-${msg.type === 'success' ? 'success' : 'error'}`} style={{ position: 'fixed', top: 24, right: 24, zIndex: 9999 }}>
                    {msg.text}
                </div>
            )}

            <div className="page-header">
                <div className="page-title">System Setup</div>
                <div className="page-subtitle">Configure institutional parameters and curriculum structure</div>
            </div>

            <div className="page-body">
                <div className="grid-2">
                    {/* Department */}
                    <FormCard title="Add Department" icon={Building2}>
                        <form onSubmit={submitDept}>
                            <div className="form-group">
                                <label className="form-label">Select Template</label>
                                <select className="form-control" onChange={e => {
                                    if (e.target.value === 'custom') { setIsCustomDept(true); setDeptForm({ name: '', code: '' }); }
                                    else {
                                        setIsCustomDept(false);
                                        const d = COMMON_DEPARTMENTS.find(x => x.code === e.target.value);
                                        if (d) setDeptForm({ name: d.name, code: d.code });
                                    }
                                }}>
                                    <option value="">Select a department...</option>
                                    {COMMON_DEPARTMENTS.map(d => <option key={d.code} value={d.code}>{d.name}</option>)}
                                    <option value="custom">-- Custom Department --</option>
                                </select>
                            </div>

                            {isCustomDept && (
                                <div className="fade-in">
                                    <div className="form-group">
                                        <label className="form-label">Department Name</label>
                                        <input className="form-control" placeholder="e.g. Aerospace Engineering" value={deptForm.name} onChange={e => setDeptForm(p => ({ ...p, name: e.target.value }))} required />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Department Code</label>
                                        <input className="form-control" placeholder="e.g. AERO" value={deptForm.code} onChange={e => setDeptForm(p => ({ ...p, code: e.target.value }))} required />
                                    </div>
                                </div>
                            )}

                            <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Department</button>
                        </form>

                        <div style={{ marginTop: 20 }}>
                            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Departments</div>
                            {loading ? (
                                [1, 2, 3].map(i => <Skeleton key={i} variant="rect" height="36px" className="mb-2" />)
                            ) : departments.length > 0 ? (
                                departments.map(d => (
                                    <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                        <span>{d.name}</span>
                                        <span className="badge badge-muted">{d.code}</span>
                                    </div>
                                ))
                            ) : (
                                <div style={{ fontSize: 12, color: 'var(--color-text-dim)', textAlign: 'center', padding: 10 }}>No departments added</div>
                            )}
                        </div>
                    </FormCard>

                    {/* Regulation */}
                    <FormCard title="Add Regulation" icon={Tag}>
                        <form onSubmit={submitReg}>
                            <div className="form-group">
                                <label className="form-label">Regulation Name</label>
                                <input className="form-control" placeholder="e.g. R2021, R2017" value={regForm.name} onChange={e => setRegForm({ name: e.target.value })} required />
                            </div>
                            <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Regulation</button>
                        </form>

                        <div style={{ marginTop: 20 }}>
                            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Regulations</div>
                            {loading ? (
                                [1, 2].map(i => <Skeleton key={i} variant="rect" height="36px" className="mb-2" />)
                            ) : regulations.length > 0 ? (
                                regulations.map(r => (
                                    <div key={r.id} style={{ padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                        {r.name}
                                    </div>
                                ))
                            ) : (
                                <div style={{ fontSize: 12, color: 'var(--color-text-dim)', textAlign: 'center', padding: 10 }}>No regulations added</div>
                            )}
                        </div>
                    </FormCard>
                </div>

                <div className="grid-2 mt-2">
                    {/* Subject */}
                    <FormCard title="Manage Subjects" icon={BookOpen}>
                        <form onSubmit={submitSubj} style={{ paddingBottom: 20, borderBottom: '1px solid var(--color-border)', marginBottom: 20 }}>
                            <div className="form-group">
                                <label className="form-label">Add New Subject</label>
                                <input className="form-control" placeholder="Subject Name" value={subjForm.name} onChange={e => setSubjForm(p => ({ ...p, name: e.target.value }))} required />
                            </div>
                            <div className="grid-2">
                                <input className="form-control" placeholder="Code (e.g. CS3301)" value={subjForm.code} onChange={e => setSubjForm(p => ({ ...p, code: e.target.value }))} required />
                                <select className="form-control" value={subjForm.semester} onChange={e => setSubjForm(p => ({ ...p, semester: e.target.value }))}>
                                    {[1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={s}>Sem {s}</option>)}
                                </select>
                            </div>
                            <div className="grid-2 mt-1">
                                <select className="form-control" value={subjForm.department_id} onChange={e => setSubjForm(p => ({ ...p, department_id: e.target.value }))} required>
                                    <option value="">Dept...</option>
                                    {departments.map(d => <option key={d.id} value={d.id}>{d.code}</option>)}
                                </select>
                                <select className="form-control" value={subjForm.regulation_id} onChange={e => setSubjForm(p => ({ ...p, regulation_id: e.target.value }))} required>
                                    <option value="">Reg...</option>
                                    {regulations.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                </select>
                            </div>
                            <button type="submit" className="btn btn-primary w-full mt-1"><Plus size={16} /> Add Subject</button>
                        </form>

                        <div style={{ maxHeight: 400, overflowY: 'auto', paddingRight: 8 }}>
                            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Subjects</div>
                            {loading ? (
                                [1, 2, 3, 4].map(i => <Skeleton key={i} variant="rect" height="48px" className="mb-2" />)
                            ) : subjects.length > 0 ? (
                                subjects.map(s => (
                                    <div key={s.id} style={{ 
                                        padding: '10px 12px', background: 'var(--color-surface-2)', borderRadius: 8, marginBottom: 8, 
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center' 
                                    }}>
                                        {editingSubj === s.id ? (
                                            <div style={{ display: 'flex', gap: 8, flex: 1 }}>
                                                <input className="form-control form-control-sm" value={editForm.name} onChange={e => setEditForm(p => ({ ...p, name: e.target.value }))} />
                                                <input className="form-control form-control-sm" style={{ width: 80 }} value={editForm.code} onChange={e => setEditForm(p => ({ ...p, code: e.target.value }))} />
                                                <button className="btn btn-ghost btn-sm" onClick={() => saveEdit(s.id)}><Check size={14} color="var(--color-success)" /></button>
                                                <button className="btn btn-ghost btn-sm" onClick={() => setEditingSubj(null)}><X size={14} color="var(--color-danger)" /></button>
                                            </div>
                                        ) : (
                                            <>
                                                <div>
                                                    <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
                                                    <div style={{ fontSize: 11, color: 'var(--color-text-dim)' }}>{s.code} • Sem {s.semester}</div>
                                                </div>
                                                <div style={{ display: 'flex', gap: 4 }}>
                                                    <button className="btn btn-ghost btn-sm" onClick={() => startEdit(s)}><Edit2 size={14} /></button>
                                                    <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-danger)' }} onClick={() => handleDeleteSubj(s.id)}><Trash2 size={14} /></button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div style={{ fontSize: 12, color: 'var(--color-text-dim)', textAlign: 'center', padding: 20 }}>No subjects found</div>
                            )}
                        </div>
                    </FormCard>

                    {/* Syllabus Units */}
                    <FormCard title="Add Syllabus Units" icon={Layers}>
                         <div className="form-group">
                             <label className="form-label">Target Subject</label>
                             <select className="form-control" value={unitForm.subject_id} onChange={e => {
                                 setUnitForm(p => ({ ...p, subject_id: e.target.value }));
                                 setSelectedSubject(e.target.value);
                             }}>
                                 <option value="">Select a subject...</option>
                                 {subjects.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
                             </select>
                         </div>

                         {unitForm.subject_id && (
                             <form onSubmit={submitUnit} className="fade-in">
                                 <div className="grid-2">
                                     <div className="form-group">
                                         <label className="form-label">Unit No.</label>
                                         <input type="number" className="form-control" value={unitForm.unit_no} onChange={e => setUnitForm(p => ({ ...p, unit_no: e.target.value }))} required />
                                     </div>
                                     <div className="form-group">
                                         <label className="form-label">Unit Title</label>
                                         <input className="form-control" value={unitForm.unit_title} onChange={e => setUnitForm(p => ({ ...p, unit_title: e.target.value }))} required />
                                     </div>
                                 </div>
                                 <div className="form-group">
                                     <label className="form-label">Keywords (optional)</label>
                                     <textarea className="form-control" placeholder="comma separated..." value={unitForm.keywords} onChange={e => setUnitForm(p => ({ ...p, keywords: e.target.value }))} />
                                 </div>
                                 <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Unit</button>
                             </form>
                         )}

                         <div style={{ marginTop: 20 }}>
                             <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Units</div>
                             {selectedSubject ? (
                                 units.length > 0 ? (
                                     units.map(u => (
                                         <div key={u.id} style={{ padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                             <strong>Unit {u.unit_no}:</strong> {u.unit_title}
                                         </div>
                                     ))
                                 ) : (
                                     <div style={{ fontSize: 12, color: 'var(--color-text-dim)', textAlign: 'center', padding: 10 }}>No units added for this subject</div>
                                 )
                             ) : (
                                 <div style={{ fontSize: 12, color: 'var(--color-text-dim)', textAlign: 'center', padding: 10 }}>Select a subject to see units</div>
                             )}
                         </div>
                    </FormCard>
                </div>
            </div>
        </div>
    );
}
