import { useState, useEffect } from 'react';
import {
    getDepartments, createDepartment,
    getRegulations, createRegulation,
    getSubjects, createSubject,
    getUnits, createUnit
} from '../api';
import { Plus, Building2, BookOpen, Layers, Tag } from 'lucide-react';

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

export default function Setup() {
    const [departments, setDepartments] = useState([]);
    const [regulations, setRegulations] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [units, setUnits] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState(null);

    const [deptForm, setDeptForm] = useState({ name: '', code: '' });
    const [regForm, setRegForm] = useState({ name: '' });
    const [subjForm, setSubjForm] = useState({ name: '', code: '', semester: 1, department_id: '', regulation_id: '' });
    const [unitForm, setUnitForm] = useState({ subject_id: '', unit_no: '', unit_title: '', keywords: '' });

    const [msg, setMsg] = useState({ type: '', text: '' });

    const flash = (type, text) => {
        setMsg({ type, text });
        setTimeout(() => setMsg({ type: '', text: '' }), type === 'error' ? 6000 : 3000);
    };

    const reload = () => {
        getDepartments().then(r => setDepartments(r.data));
        getRegulations().then(r => setRegulations(r.data));
        getSubjects().then(r => setSubjects(r.data));
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

    const submitUnit = async (e) => {
        e.preventDefault();
        try {
            await createUnit({ ...unitForm, subject_id: parseInt(unitForm.subject_id), unit_no: parseInt(unitForm.unit_no) });
            flash('success', 'Unit created'); setUnitForm({ subject_id: unitForm.subject_id, unit_no: '', unit_title: '', keywords: '' });
            if (selectedSubject) getUnits(selectedSubject).then(r => setUnits(r.data));
        } catch { flash('error', 'Failed to create unit'); }
    };

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Setup</div>
                <div className="page-subtitle">Configure departments, regulations, subjects, and syllabus units</div>
            </div>
            <div className="page-body">
                {msg.text && <div className={`alert alert-${msg.type === 'success' ? 'success' : 'error'}`}>{msg.text}</div>}

                <div className="grid-2">
                    {/* Department */}
                    <FormCard title="Add Department" icon={Building2}>
                        <form onSubmit={submitDept}>
                            <div className="form-group">
                                <label className="form-label">Department Name</label>
                                <input className="form-control" placeholder="e.g. Computer Science & Engineering" value={deptForm.name} onChange={e => setDeptForm(p => ({ ...p, name: e.target.value }))} required />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Department Code</label>
                                <input className="form-control" placeholder="e.g. CSE" value={deptForm.code} onChange={e => setDeptForm(p => ({ ...p, code: e.target.value }))} required />
                            </div>
                            <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Department</button>
                        </form>

                        {departments.length > 0 && (
                            <div style={{ marginTop: 20 }}>
                                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Departments</div>
                                {departments.map(d => (
                                    <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                        <span>{d.name}</span>
                                        <span className="badge badge-muted">{d.code}</span>
                                    </div>
                                ))}
                            </div>
                        )}
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

                        {regulations.length > 0 && (
                            <div style={{ marginTop: 20 }}>
                                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Existing Regulations</div>
                                {regulations.map(r => (
                                    <div key={r.id} style={{ padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                        {r.name}
                                    </div>
                                ))}
                            </div>
                        )}
                    </FormCard>
                </div>

                <div className="grid-2 mt-2">
                    {/* Subject */}
                    <FormCard title="Add Subject" icon={BookOpen}>
                        <form onSubmit={submitSubj}>
                            <div className="form-group">
                                <label className="form-label">Subject Name</label>
                                <input className="form-control" placeholder="e.g. Data Structures and Algorithms" value={subjForm.name} onChange={e => setSubjForm(p => ({ ...p, name: e.target.value }))} required />
                            </div>
                            <div className="grid-2">
                                <div className="form-group">
                                    <label className="form-label">Subject Code</label>
                                    <input className="form-control" placeholder="e.g. CS3301" value={subjForm.code} onChange={e => setSubjForm(p => ({ ...p, code: e.target.value }))} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Semester</label>
                                    <select className="form-control" value={subjForm.semester} onChange={e => setSubjForm(p => ({ ...p, semester: e.target.value }))}>
                                        {[1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                </div>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Department</label>
                                <select className="form-control" value={subjForm.department_id} onChange={e => setSubjForm(p => ({ ...p, department_id: e.target.value }))} required>
                                    <option value="">Select department...</option>
                                    {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Regulation</label>
                                <select className="form-control" value={subjForm.regulation_id} onChange={e => setSubjForm(p => ({ ...p, regulation_id: e.target.value }))} required>
                                    <option value="">Select regulation...</option>
                                    {regulations.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                </select>
                            </div>
                            <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Subject</button>
                        </form>
                    </FormCard>

                    {/* Syllabus Units */}
                    <FormCard title="Add Syllabus Unit" icon={Layers}>
                        <div className="form-group">
                            <label className="form-label">Select Subject</label>
                            <select className="form-control" value={selectedSubject || ''} onChange={e => { setSelectedSubject(e.target.value); setUnitForm(p => ({ ...p, subject_id: e.target.value })); }}>
                                <option value="">Select subject...</option>
                                {subjects.map(s => (
                                    <option key={s.id} value={s.id}>
                                        {s.name} ({s.code}){s.department_code ? ` — ${s.department_code}` : ''}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {selectedSubject && (
                            <form onSubmit={submitUnit}>
                                <div className="grid-2">
                                    <div className="form-group">
                                        <label className="form-label">Unit Number</label>
                                        <input type="number" className="form-control" placeholder="1" min="1" max="10" value={unitForm.unit_no} onChange={e => setUnitForm(p => ({ ...p, unit_no: e.target.value }))} required />
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Unit Title</label>
                                    <input className="form-control" placeholder="e.g. Sorting and Searching Algorithms" value={unitForm.unit_title} onChange={e => setUnitForm(p => ({ ...p, unit_title: e.target.value }))} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Keywords (comma-separated, for auto-detection)</label>
                                    <input className="form-control" placeholder="e.g. sorting, binary search, hashing" value={unitForm.keywords} onChange={e => setUnitForm(p => ({ ...p, keywords: e.target.value }))} />
                                </div>
                                <button type="submit" className="btn btn-primary w-full"><Plus size={16} /> Add Unit</button>
                            </form>
                        )}

                        {units.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                {units.map(u => (
                                    <div key={u.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 12px', background: 'var(--color-surface-2)', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                                        <span className="badge badge-primary">Unit {u.unit_no}</span>
                                        <div>
                                            <div>{u.unit_title}</div>
                                            {u.keywords && <div style={{ fontSize: 11, color: 'var(--color-text-dim)', marginTop: 2 }}>{u.keywords}</div>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </FormCard>
                </div>
            </div>
        </div>
    );
}
