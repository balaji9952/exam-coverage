import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Setup from './pages/Setup';
import UploadBank from './pages/UploadBank';
import QuestionBank from './pages/QuestionBank';
import Analyze from './pages/Analyze';
import Reports from './pages/Reports';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="/upload-bank" element={<UploadBank />} />
            <Route path="/question-bank" element={<QuestionBank />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
