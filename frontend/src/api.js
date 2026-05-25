// Last Updated: 2026-04-28T11:02:00Z
import axios from 'axios';

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 60000,
});

export default API;

// ── Departments & Setup ─────────────────────────────────────────────────────
export const getDepartments = () => API.get('/departments');
export const createDepartment = (data) => API.post('/departments', data);
export const getRegulations = () => API.get('/regulations');
export const createRegulation = (data) => API.post('/regulations', data);
export const getSubjects = (params) => API.get('/subjects', { params });
export const createSubject = (data) => API.post('/subjects', data);
export const deleteSubject = (id) => API.delete(`/subjects/${id}`);
export const updateSubject = (id, data) => API.patch(`/subjects/${id}`, data);
export const getUnits = (subjectId) => API.get(`/subjects/${subjectId}/units`);
export const createUnit = (data) => API.post('/syllabus-units', data);

// ── Question Bank ───────────────────────────────────────────────────────────
export const uploadQuestionBank = (formData) =>
    API.post('/question-bank/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
    });
export const importJsonQuestionBank = (formData) =>
    API.post('/question-bank/import-json', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
    });
export const getStagingQuestions = (docId) =>
    API.get(`/question-bank/staging/${docId}`);
export const updateStagingQuestions = (updates) =>
    API.patch('/question-bank/staging/update', updates);
export const approveStaging = (stagingIds) =>
    API.post('/question-bank/staging/approve', { staging_ids: stagingIds });
export const getBankQuestions = (params) =>
    API.get('/question-bank', { params });
export const getBankDocuments = () =>
    API.get('/question-bank/documents');
export const deleteBankDocument = (docId) =>
    API.delete(`/question-bank/documents/${docId}`);
export const manualAddQuestion = (data) =>
    API.post('/question-bank/manual-add', data);
export const deleteBankQuestion = (id) =>
    API.delete(`/question-bank/${id}`);
export const clearAllBankQuestions = (subjectId) =>
    API.delete('/question-bank/clear', { params: subjectId ? { subject_id: subjectId } : {} });

// ── Exam Paper Analysis ─────────────────────────────────────────────────────
export const uploadAndAnalyzeExam = (formData) =>
    API.post('/exam-paper/upload-analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000,
    });
export const getExamReport = (examId) =>
    API.get(`/exam-paper/${examId}/report`);
export const getExamPapers = (params) =>
    API.get('/exam-papers', { params });
export const deleteExamPaper = (id) =>
    API.delete(`/exam-papers/${id}`);

// ── Dashboard ───────────────────────────────────────────────────────────────
export const getDashboardSummary = () => API.get('/dashboard/summary');
