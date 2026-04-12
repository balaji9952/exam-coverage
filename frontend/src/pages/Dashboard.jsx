import { useState, useEffect } from 'react';
import { getDashboardSummary } from '../api';
import { BarChart3, Database, FileText, BookOpen, TrendingUp, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

function CoverageRing({ pct, size = 160 }) {
    const r = 60;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (pct / 100) * circ;
    const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';

    return (
        <div className="coverage-ring">
            <svg width={size} height={size} viewBox="0 0 160 160">
                <circle cx="80" cy="80" r={r} fill="none" stroke="var(--color-surface-2)" strokeWidth="14" />
                <circle
                    cx="80" cy="80" r={r}
                    fill="none"
                    stroke={color}
                    strokeWidth="14"
                    strokeDasharray={circ}
                    strokeDashoffset={dashOffset}
                    strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 8px ${color}88)`, transition: 'stroke-dashoffset 1s ease' }}
                />
            </svg>
            <div className="coverage-ring-label">
                <div className="coverage-ring-pct" style={{ color }}>{pct.toFixed(1)}%</div>
                <div className="coverage-ring-sub">Coverage</div>
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

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
            <div className="spinner spinner-lg" />
        </div>
    );

    const stats = [
        { label: 'Bank Questions', value: summary.total_bank_questions, icon: '📚', variant: '' },
        { label: 'Exam Papers Analyzed', value: summary.total_exam_papers, icon: '📄', variant: 'success' },
        { label: 'Subjects Configured', value: summary.total_subjects, icon: '📖', variant: 'info' },
        { label: 'Documents Uploaded', value: summary.total_documents, icon: '☁️', variant: 'warning' },
    ];

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="page-title">Dashboard</div>
                <div className="page-subtitle">AI-powered exam coverage analysis overview</div>
            </div>

            <div className="page-body">
                {/* Stat Cards */}
                <div className="stat-grid">
                    {stats.map(s => (
                        <div key={s.label} className={`stat-card ${s.variant}`}>
                            <div className="stat-label">{s.label}</div>
                            <div className="stat-value">{s.value}</div>
                            <div className="stat-icon">{s.icon}</div>
                        </div>
                    ))}
                </div>

                {/* Recent Reports */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-title"><BarChart3 size={16} /> Recent Coverage Reports</div>
                    </div>

                    {summary.recent_coverage.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">📊</div>
                            <h3>No reports yet</h3>
                            <p>Upload an exam paper to generate your first coverage report</p>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {summary.recent_coverage.map(r => {
                                const pct = r.overall_coverage_pct || 0;
                                const color = pct >= 70 ? 'success' : pct >= 40 ? 'warning' : 'danger';
                                return (
                                    <div key={r.exam_id} style={{
                                        display: 'flex', alignItems: 'center', gap: 16,
                                        padding: '16px', background: 'var(--color-surface-2)',
                                        borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)'
                                    }}>
                                        <CoverageRing pct={pct} size={80} />
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{r.subject}</div>
                                            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                                                <span className="badge badge-muted">{r.exam_type}</span>
                                                <span className={`badge badge-${color}`}>{pct}% match</span>
                                                <span className="badge badge-info">{r.weighted_coverage_pct}% weighted</span>
                                            </div>
                                            <div style={{ fontSize: 12, color: 'var(--color-text-dim)' }}>
                                                {new Date(r.analyzed_at).toLocaleString()}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Quick Info */}
                <div className="grid-2 mt-2">
                    <div className="card">
                        <div className="card-title mb-2" style={{ marginBottom: 16 }}>🚀 How It Works</div>
                        {[
                            ['1. Setup', 'Add departments, regulations, subjects & syllabus units'],
                            ['2. Question Bank', 'Upload question bank PDFs — AI extracts & structures them'],
                            ['3. Review', 'Review extracted questions, assign units, approve'],
                            ['4. Analyze', 'Upload exam paper — AI matches & computes coverage'],
                            ['5. Report', 'Get unit-wise & Bloom\'s taxonomy coverage breakdowns'],
                        ].map(([step, desc]) => (
                            <div key={step} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                                <span className="badge badge-primary">{step}</span>
                                <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{desc}</span>
                            </div>
                        ))}
                    </div>

                    <div className="card">
                        <div className="card-title mb-2" style={{ marginBottom: 16 }}>📈 Coverage Standards</div>
                        {[
                            ['≥ 70%', 'Excellent coverage', 'success'],
                            ['40–70%', 'Moderate coverage', 'warning'],
                            ['< 40%', 'Low coverage', 'danger'],
                        ].map(([range, label, cls]) => (
                            <div key={range} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                                <div style={{ width: 80 }}>
                                    <span className={`badge badge-${cls}`}>{range}</span>
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: 13, marginBottom: 4 }}>{label}</div>
                                    <div className="progress-bar">
                                        <div
                                            className={`progress-fill ${cls}`}
                                            style={{ width: cls === 'success' ? '85%' : cls === 'warning' ? '55%' : '25%' }}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
