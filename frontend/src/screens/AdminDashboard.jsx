import { useState, useEffect } from 'react';
import { Users, FileText, BarChart3, Database } from 'lucide-react';
import { api } from '../api/client';
import AppShell from '../components/AppShell';
import { Card, SectionHeader, Spinner, Alert } from '../components/ui';

export default function AdminDashboard() {
  // We'll just fetch some basic counts and lists for the demo
  const [data, setData] = useState({
    documents: [],
    assessments: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [docs, assts] = await Promise.all([
          api.documents.list({ limit: 10 }),
          api.assessments.list({ limit: 10 }),
        ]);
        setData({ documents: docs || [], assessments: assts.items || [] });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <AppShell>
      <SectionHeader
        icon={Database}
        title="Admin Oversight"
        subtitle="System-wide visibility for users, documents, and assessments"
      />

      {error && <Alert type="error" message={error} className="mb-6" />}

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" className="text-[#c97d2e]" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Documents Table */}
          <Card className="p-6">
            <h2 className="text-base font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" /> Recent Documents
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-100">
                    <th className="pb-2 font-medium">Filename</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium text-right">Generations</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.documents.map(d => (
                    <tr key={d.id}>
                      <td className="py-3 font-medium text-[#1a2e4a] truncate max-w-[200px]" title={d.filename}>{d.filename}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          d.status === 'PROCESSED' ? 'bg-green-100 text-green-700' :
                          d.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {d.status}
                        </span>
                      </td>
                      <td className="py-3 text-right text-gray-500">{d.generation_count}</td>
                    </tr>
                  ))}
                  {data.documents.length === 0 && (
                    <tr><td colSpan="3" className="py-4 text-center text-gray-400">No documents found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Assessments Table */}
          <Card className="p-6">
            <h2 className="text-base font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-500" /> Recent Assessments
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-100">
                    <th className="pb-2 font-medium">Title</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {data.assessments.map(a => (
                    <tr key={a.id}>
                      <td className="py-3 font-medium text-[#1a2e4a] truncate max-w-[200px]" title={a.title}>{a.title}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          a.status === 'COMPLETED' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
                        }`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3 text-right font-bold text-gray-600">
                        {a.status === 'COMPLETED' ? `${a.score_percentage.toFixed(1)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                  {data.assessments.length === 0 && (
                    <tr><td colSpan="3" className="py-4 text-center text-gray-400">No assessments found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
