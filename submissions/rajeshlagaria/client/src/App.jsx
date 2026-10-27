import { Routes, Route, Link, useLocation } from 'react-router-dom';
import GroupListPage from './pages/GroupListPage';
import GroupDetailPage from './pages/GroupDetailPage';
import ExpenseFormPage from './pages/ExpenseFormPage';
import BatchUploadPage from './pages/BatchUploadPage';
import SettlementsPage from './pages/SettlementsPage';

function NotFound() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold text-gray-300 mb-4">404</h1>
      <p className="text-gray-500 mb-4">Page not found</p>
      <Link to="/" className="text-indigo-600 hover:underline text-sm">
        &larr; Back to Groups
      </Link>
    </div>
  );
}

const navLinks = [
  { to: '/', label: 'Groups' },
];

function NavBar() {
  const location = useLocation();

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="text-lg font-bold text-indigo-600">
          💰 Splitwise
        </Link>
        <nav className="flex gap-4 text-sm">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`${
                location.pathname === to
                  ? 'text-indigo-600 font-medium'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<GroupListPage />} />
          <Route path="/groups/:groupId" element={<GroupDetailPage />} />
          <Route path="/groups/:groupId/expenses/new" element={<ExpenseFormPage />} />
          <Route path="/groups/:groupId/expenses/batch" element={<BatchUploadPage />} />
          <Route path="/groups/:groupId/settlements" element={<SettlementsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}