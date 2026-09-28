import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCheck, CheckCircle2, XCircle, ChevronDown, ChevronUp,
  MessageSquare, RefreshCw, Filter,
} from 'lucide-react';
import { api } from '../api/client';
import AppShell from '../components/AppShell';
import {
  Card, Button, Alert, QuestionStatusBadge, DifficultyBadge,
  SectionHeader, EmptyState, Spinner, Badge,
} from '../components/ui';

// ── Question Review Card ──────────────────────────────────────────────────────
function QuestionCard({ question, onReviewed }) {
  const [expanded, setExpanded] = useState(false);
  const [action, setAction] = useState(null); // 'APPROVE' | 'REJECT'
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);
    try {
      await api.questions.review(question.id, action, comment || null);
      onReviewed(question.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="border border-gray-100 rounded-2xl overflow-hidden bg-white shadow-sm"
    >
      {/* Header row */}
      <button
        className="w-full flex items-start gap-4 p-5 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-2 mb-2">
            <QuestionStatusBadge status={question.status} />
            <DifficultyBadge difficulty={question.difficulty} />
            {question.competency_id && (
              <Badge label={`Competency #${question.competency_id}`} color="navy" />
            )}
            {question.source_page && (
              <Badge label={`Page ${question.source_page}`} color="gray" />
            )}
          </div>
          <p className="text-sm font-semibold text-[#1a2e4a] leading-snug line-clamp-3">
            {question.question_text}
          </p>
        </div>
        {expanded
          ? <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
          : <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-gray-100 bg-gray-50/50">
              {/* Options */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
                {['A','B','C','D'].map(opt => (
                  <div
                    key={opt}
                    className={`p-3 rounded-xl text-sm border ${
                      question.correct_option === opt
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800 font-semibold'
                        : 'bg-white border-gray-100 text-gray-700'
                    }`}
                  >
                    <span className="font-bold mr-2">{opt}.</span>
                    {question[`option_${opt.toLowerCase()}`]}
                    {question.correct_option === opt && (
                      <span className="ml-2 text-xs text-emerald-600">✓ Correct</span>
                    )}
                  </div>
                ))}
              </div>

              {/* Explanation */}
              {question.explanation && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-xl">
                  <p className="text-xs font-semibold text-blue-600 mb-1">RAG Explanation</p>
                  <p className="text-sm text-blue-700">{question.explanation}</p>
                </div>
              )}

              {/* Review action */}
              <div className="mt-5 space-y-3">
                <div className="flex gap-2">
                  <button
                    onClick={() => setAction(action === 'APPROVE' ? null : 'APPROVE')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border-2 transition-all
                      ${action === 'APPROVE'
                        ? 'bg-emerald-500 border-emerald-500 text-white shadow-md'
                        : 'border-emerald-300 text-emerald-600 hover:bg-emerald-50'}`}
                  >
                    <CheckCircle2 className="w-4 h-4" /> Approve
                  </button>
                  <button
                    onClick={() => setAction(action === 'REJECT' ? null : 'REJECT')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border-2 transition-all
                      ${action === 'REJECT'
                        ? 'bg-red-500 border-red-500 text-white shadow-md'
                        : 'border-red-300 text-red-600 hover:bg-red-50'}`}
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>

                {action && (
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <MessageSquare className="w-4 h-4 text-gray-400" />
                      <label className="text-xs font-medium text-gray-600">
                        Comment {action === 'REJECT' ? '(recommended for rejection)' : '(optional)'}
                      </label>
                    </div>
                    <textarea
                      id={`review-comment-${question.id}`}
                      value={comment}
                      onChange={e => setComment(e.target.value)}
                      rows={2}
                      placeholder="Add your review notes…"
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-[#c97d2e]/30"
                    />
                  </div>
                )}

                <AnimatePresence>
                  {error && <Alert type="error" message={error} onDismiss={() => setError('')} />}
                </AnimatePresence>

                {action && (
                  <Button
                    loading={submitting}
                    onClick={handleSubmit}
                    variant={action === 'APPROVE' ? 'success' : 'danger'}
                    className="w-full"
                  >
                    Confirm {action === 'APPROVE' ? 'Approval' : 'Rejection'}
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── SME Dashboard ─────────────────────────────────────────────────────────────
export default function SMEDashboard() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('PENDING_REVIEW');
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 });

  const fetchQuestions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.questions.list({ status: statusFilter, limit: 100 });
      setQuestions(data.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const [pending, approved, rejected] = await Promise.all([
        api.questions.list({ status: 'PENDING_REVIEW', limit: 1 }),
        api.questions.list({ status: 'APPROVED', limit: 1 }),
        api.questions.list({ status: 'REJECTED', limit: 1 }),
      ]);
      setStats({
        pending:  pending.total  || 0,
        approved: approved.total || 0,
        rejected: rejected.total || 0,
      });
    } catch { /* non-critical */ }
  };

  useEffect(() => { fetchQuestions(); }, [statusFilter]);
  useEffect(() => { fetchStats(); }, []);

  const handleReviewed = (questionId) => {
    setQuestions(prev => prev.filter(q => q.id !== questionId));
    fetchStats();
  };

  const FILTERS = ['PENDING_REVIEW', 'APPROVED', 'REJECTED'];

  return (
    <AppShell>
      <SectionHeader
        icon={ClipboardCheck}
        title="SME Review Portal"
        subtitle="Review, approve, or reject AI-generated MCQs before they enter the assessment pool"
      />

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Pending Review', value: stats.pending,  color: 'amber' },
          { label: 'Approved',        value: stats.approved, color: 'green' },
          { label: 'Rejected',        value: stats.rejected, color: 'red'   },
        ].map(s => (
          <Card key={s.label} className="p-4 text-center">
            <div className={`text-3xl font-bold ${
              s.color === 'amber' ? 'text-amber-500' :
              s.color === 'green' ? 'text-emerald-500' : 'text-red-500'
            }`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-1">{s.label}</div>
          </Card>
        ))}
      </div>

      {/* Filter + Refresh */}
      <div className="flex items-center gap-3 mb-5">
        <Filter className="w-4 h-4 text-gray-400" />
        <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
                ${statusFilter === f ? 'bg-white shadow-sm text-[#1a2e4a]' : 'text-gray-500 hover:text-gray-700'}`}
            >
              {f.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button onClick={fetchQuestions} className="ml-auto text-gray-400 hover:text-[#1a2e4a] transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Question list */}
      {error && <Alert type="error" message={error} className="mb-4" />}

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" className="text-[#c97d2e]" />
        </div>
      ) : questions.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title={statusFilter === 'PENDING_REVIEW' ? 'No questions awaiting review' : `No ${statusFilter.toLowerCase()} questions`}
          description="All caught up! New questions will appear here when Trainers generate them."
        />
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {questions.map(q => (
              <QuestionCard
                key={q.id}
                question={q}
                onReviewed={handleReviewed}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </AppShell>
  );
}
