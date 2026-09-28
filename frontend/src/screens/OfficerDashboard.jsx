import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCheck, Play, Trophy, BookOpen, RefreshCw,
  ChevronRight, ChevronLeft, AlertTriangle, TrendingUp,
  CheckCircle2, Clock, ArrowRight, BarChart2, Target,
} from 'lucide-react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell,
} from 'recharts';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import AppShell from '../components/AppShell';
import {
  Card, Button, Select, Alert, Spinner,
  ProficiencyBadge, GapLevelBadge, RecommendationStatusBadge,
  SectionHeader, EmptyState, Badge,
} from '../components/ui';

// ── Start Assessment Dialog ───────────────────────────────────────────────────
function StartAssessmentPanel({ onStarted }) {
  const [questionCount, setQuestionCount] = useState(10);
  const [competencyId, setCompetencyId] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.documents.list()
      .then(data => setDocs(data.filter(d => d.status === 'PROCESSED')))
      .catch(() => {});
  }, []);

  const handleStart = async () => {
    setError('');
    setLoading(true);
    try {
      const payload = { question_count: questionCount };
      if (competencyId) payload.competency_id = Number(competencyId);
      if (documentId)   payload.document_id   = Number(documentId);
      const assessment = await api.assessments.create(payload);
      const detail     = await api.assessments.get(assessment.id);
      onStarted(detail);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 max-w-lg">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-[#1a2e4a] rounded-xl flex items-center justify-center">
          <Play className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-base font-bold text-[#1a2e4a]">Start Diagnostic Assessment</h2>
          <p className="text-xs text-gray-400">Draws from approved question bank</p>
        </div>
      </div>

      <div className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Questions: <span className="text-[#c97d2e] font-bold">{questionCount}</span>
          </label>
          <input
            type="range" min={1} max={50} value={questionCount}
            onChange={e => setQuestionCount(Number(e.target.value))}
            className="w-full accent-[#c97d2e]"
            id="assessment-question-count"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1</span><span>50</span>
          </div>
        </div>

        <Select
          id="assessment-doc"
          label="Filter by Document (optional)"
          value={documentId}
          onChange={e => setDocumentId(e.target.value)}
        >
          <option value="">All Documents</option>
          {docs.map(d => (
            <option key={d.id} value={d.id}>{d.filename}</option>
          ))}
        </Select>

        <AnimatePresence>
          {error && <Alert type="error" message={error} onDismiss={() => setError('')} />}
        </AnimatePresence>

        <Button loading={loading} onClick={handleStart} className="w-full" size="lg">
          <Play className="w-4 h-4" /> Begin Assessment
        </Button>
      </div>
    </Card>
  );
}

// ── Active Exam View ──────────────────────────────────────────────────────────
// Backend MASKS correct_option and explanation while IN_PROGRESS — we intentionally
// do not show "correct answer" feedback per question; only submit reveals results.
function ExamView({ assessment, onSubmitted }) {
  const questions = assessment.questions || [];
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState({}); // { question_id: 'A'|'B'|'C'|'D' }
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const current = questions[currentIdx];
  const answered = Object.keys(answers).length;
  const progress = (answered / questions.length) * 100;

  const selectOption = (questionId, opt) => {
    setAnswers(prev => ({ ...prev, [questionId]: opt }));
  };

  const handleSubmit = async () => {
    setError('');
    const payload = Object.entries(answers).map(([question_id, selected_option]) => ({
      question_id: Number(question_id),
      selected_option,
    }));
    setSubmitting(true);
    try {
      const result = await api.assessments.submit(assessment.id, payload);
      onSubmitted(result);
    } catch (err) {
      setError(err.message); // Surface backend error verbatim (e.g. "already completed")
    } finally {
      setSubmitting(false);
    }
  };

  if (!current) return null;

  const opts = [
    { key: 'A', text: current.option_a },
    { key: 'B', text: current.option_b },
    { key: 'C', text: current.option_c },
    { key: 'D', text: current.option_d },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress header */}
      <Card className="p-5 mb-4">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-3">
          <span className="font-semibold text-[#1a2e4a]">{assessment.title}</span>
          <span>{answered}/{questions.length} answered</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2">
          <motion.div
            className="bg-[#c97d2e] h-2 rounded-full"
            animate={{ width: `${progress}%` }}
            transition={{ type: 'spring', stiffness: 200 }}
          />
        </div>
        {/* Question dots */}
        <div className="flex gap-1.5 mt-3 flex-wrap">
          {questions.map((q, i) => (
            <button
              key={q.id}
              onClick={() => setCurrentIdx(i)}
              className={`w-7 h-7 rounded-lg text-xs font-bold transition-all
                ${i === currentIdx
                  ? 'bg-[#1a2e4a] text-white'
                  : answers[q.id]
                    ? 'bg-[#c97d2e] text-white'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
            >
              {i+1}
            </button>
          ))}
        </div>
      </Card>

      {/* Question card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIdx}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Badge label={`Q ${currentIdx + 1} of ${questions.length}`} color="navy" />
              <Badge label={current.difficulty} color="gray" />
              {current.competency_name && (
                <Badge label={current.competency_name} color="blue" />
              )}
            </div>

            <p className="text-base font-semibold text-[#1a2e4a] mb-5 leading-relaxed">
              {current.question_text}
            </p>

            <div className="space-y-3">
              {opts.map(({ key, text }) => {
                const selected = answers[current.id] === key;
                return (
                  <button
                    key={key}
                    onClick={() => selectOption(current.id, key)}
                    className={`w-full flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all
                      ${selected
                        ? 'border-[#c97d2e] bg-[#c97d2e]/10 shadow-sm'
                        : 'border-gray-100 hover:border-gray-300 hover:bg-gray-50'}`}
                  >
                    <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0
                      ${selected ? 'bg-[#c97d2e] text-white' : 'bg-gray-100 text-gray-500'}`}>
                      {key}
                    </span>
                    <span className={`text-sm leading-relaxed ${selected ? 'text-[#1a2e4a] font-medium' : 'text-gray-700'}`}>
                      {text}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6">
              <Button
                variant="ghost" size="sm"
                onClick={() => setCurrentIdx(i => Math.max(0, i - 1))}
                disabled={currentIdx === 0}
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </Button>

              {currentIdx < questions.length - 1 ? (
                <Button
                  size="sm"
                  onClick={() => setCurrentIdx(i => Math.min(questions.length - 1, i + 1))}
                >
                  Next <ChevronRight className="w-4 h-4" />
                </Button>
              ) : (
                <div className="flex flex-col items-end gap-2">
                  {answered < questions.length && (
                    <p className="text-xs text-amber-600">
                      {questions.length - answered} question{questions.length - answered > 1 ? 's' : ''} unanswered
                    </p>
                  )}
                  <Button
                    variant="secondary" size="sm" loading={submitting}
                    onClick={handleSubmit}
                    disabled={answered === 0}
                  >
                    Submit Assessment <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>

            <AnimatePresence>
              {error && (
                <div className="mt-4">
                  <Alert type="error" message={error} onDismiss={() => setError('')} />
                </div>
              )}
            </AnimatePresence>
          </Card>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// ── Results Screen ────────────────────────────────────────────────────────────
function ResultsView({ result, onRequestReassessment }) {
  const { competency_results = [], skill_gaps = [] } = result;
  const [recommendations, setRecommendations] = useState([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState('');
  const [reassessing, setReassessing] = useState(false);
  const [reassessmentError, setReassessmentError] = useState('');

  // Fetch or generate recommendations
  useEffect(() => {
    const load = async () => {
      setLoadingRecs(true);
      try {
        // Try to get existing recommendations first
        const existing = await api.assessments.listRecommendations(result.assessment_id);
        if (existing && existing.length > 0) {
          setRecommendations(existing);
        } else if (skill_gaps.length > 0) {
          // Generate them
          const recs = await api.assessments.generateRecommendations(result.assessment_id);
          setRecommendations(recs);
        }
      } catch (err) {
        setRecsError(err.message);
      } finally {
        setLoadingRecs(false);
      }
    };
    load();
  }, [result.assessment_id]);

  const handleStatusUpdate = async (recId, newStatus) => {
    try {
      const updated = await api.recommendations.updateStatus(recId, newStatus);
      setRecommendations(prev => prev.map(r => r.id === recId ? updated : r));
    } catch (err) {
      alert(err.message); // Surface backend's error message directly
    }
  };

  const handleReassess = async () => {
    setReassessing(true);
    setReassessmentError('');
    try {
      const newAssessment = await api.assessments.reassess(result.assessment_id);
      onRequestReassessment(newAssessment);
    } catch (err) {
      setReassessmentError(err.message);
    } finally {
      setReassessing(false);
    }
  };

  // Radar chart data
  const radarData = competency_results.map(cr => ({
    subject: cr.competency_name || `C${cr.competency_id}`,
    score: cr.score_percentage,
  }));

  const scoreColor = result.score_percentage >= 80 ? '#10b981'
    : result.score_percentage >= 65 ? '#3b82f6'
    : result.score_percentage >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="space-y-6">
      {/* Score banner */}
      <Card className="p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-[#1a2e4a] to-[#243d5e] opacity-5" />
        <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="text-center">
            <div className="text-5xl font-black" style={{ color: scoreColor }}>
              {result.score_percentage.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500 mt-1">Overall Score</div>
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-[#1a2e4a]">{result.title}</h2>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-sm text-gray-500">{result.total_correct}/{result.total_questions} correct</span>
              <span className="text-sm text-gray-300">·</span>
              <span className="text-sm text-gray-500">{skill_gaps.length} skill gap{skill_gaps.length !== 1 ? 's' : ''} identified</span>
            </div>
          </div>
          {skill_gaps.length > 0 && (
            <Button
              variant="outline" size="sm"
              loading={reassessing} onClick={handleReassess}
            >
              <RefreshCw className="w-4 h-4" /> Request Reassessment
            </Button>
          )}
        </div>
        {reassessmentError && (
          <div className="mt-3">
            <Alert type="error" message={reassessmentError} />
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Competency radar */}
        {radarData.length > 0 && (
          <Card className="p-5">
            <h3 className="text-sm font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-[#c97d2e]" /> Competency Profile
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#6b7280' }} />
                <Radar dataKey="score" stroke="#1a2e4a" fill="#1a2e4a" fillOpacity={0.2} strokeWidth={2} />
                <Tooltip formatter={v => `${v.toFixed(1)}%`} />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* Per-competency bar chart */}
        {competency_results.length > 0 && (
          <Card className="p-5">
            <h3 className="text-sm font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-[#c97d2e]" /> Competency Scores
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={competency_results} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="competency_name" width={110} tick={{ fontSize: 10 }} />
                <Tooltip formatter={v => `${v.toFixed(1)}%`} />
                <Bar dataKey="score_percentage" radius={[0, 6, 6, 0]}>
                  {competency_results.map((cr, i) => (
                    <Cell key={i} fill={
                      cr.score_percentage >= 80 ? '#10b981' :
                      cr.score_percentage >= 65 ? '#3b82f6' :
                      cr.score_percentage >= 50 ? '#f59e0b' : '#ef4444'
                    } />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}
      </div>

      {/* Competency breakdown table */}
      <Card className="p-5">
        <h3 className="text-sm font-bold text-[#1a2e4a] mb-4">Competency Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400 border-b border-gray-100">
                <th className="text-left pb-2 font-medium">Competency</th>
                <th className="text-right pb-2 font-medium">Score</th>
                <th className="text-right pb-2 font-medium">Questions</th>
                <th className="text-right pb-2 font-medium">Proficiency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {competency_results.map(cr => (
                <tr key={cr.competency_id} className="py-2">
                  <td className="py-2.5 text-[#1a2e4a] font-medium">
                    {cr.competency_name || `Competency ${cr.competency_id}`}
                  </td>
                  <td className="py-2.5 text-right font-bold" style={{
                    color: cr.score_percentage >= 80 ? '#10b981' :
                           cr.score_percentage >= 65 ? '#3b82f6' :
                           cr.score_percentage >= 50 ? '#f59e0b' : '#ef4444'
                  }}>
                    {cr.score_percentage.toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-right text-gray-500">
                    {cr.questions_correct}/{cr.questions_attempted}
                  </td>
                  <td className="py-2.5 text-right">
                    <ProficiencyBadge level={cr.proficiency_level} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Skill Gaps */}
      {skill_gaps.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Identified Skill Gaps ({skill_gaps.length})
          </h3>
          <div className="space-y-3">
            {skill_gaps.map(gap => (
              <div key={gap.competency_id}
                className={`p-4 rounded-xl border-l-4 ${
                  gap.gap_level === 'HIGH'   ? 'bg-red-50 border-red-400' :
                  gap.gap_level === 'MEDIUM' ? 'bg-amber-50 border-amber-400' :
                                               'bg-blue-50 border-blue-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-[#1a2e4a]">
                    {gap.competency_name || `Competency ${gap.competency_id}`}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-600">
                      {gap.score_percentage.toFixed(1)}%
                    </span>
                    <GapLevelBadge level={gap.gap_level} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      <Card className="p-5">
        <h3 className="text-sm font-bold text-[#1a2e4a] mb-4 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[#c97d2e]" />
          Learning Recommendations
        </h3>
        {recsError && <Alert type="error" message={recsError} className="mb-3" />}
        {loadingRecs ? (
          <div className="flex justify-center py-8">
            <Spinner size="md" className="text-[#c97d2e]" />
          </div>
        ) : recommendations.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title={skill_gaps.length === 0 ? 'No gaps — no recommendations needed!' : 'No recommendations available yet'}
          />
        ) : (
          <div className="space-y-4">
            {recommendations.map(rec => (
              <RecommendationCard
                key={rec.id}
                rec={rec}
                onStatusUpdate={handleStatusUpdate}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

// ── Recommendation Card ───────────────────────────────────────────────────────
// Implements the state machine: RECOMMENDED→STARTED, RECOMMENDED→DISMISSED, STARTED→COMPLETED
// Invalid transitions are not offered in UI (e.g., no Dismiss once STARTED)
function RecommendationCard({ rec, onStatusUpdate }) {
  const [loading, setLoading] = useState(false);

  const doUpdate = async (status) => {
    setLoading(true);
    await onStatusUpdate(rec.id, status);
    setLoading(false);
  };

  const priorityColors = { 1: 'red', 2: 'amber', 3: 'blue' };
  const priorityLabels = { 1: 'High Priority', 2: 'Medium Priority', 3: 'Low Priority' };

  return (
    <div className="border border-gray-100 rounded-xl p-4 bg-gray-50/50 hover:bg-white transition-colors">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-[#1a2e4a]/10 rounded-xl flex items-center justify-center flex-shrink-0">
          <BookOpen className="w-5 h-5 text-[#1a2e4a]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-sm text-[#1a2e4a]">{rec.course_title}</p>
              {rec.course_provider && (
                <p className="text-xs text-gray-400 mt-0.5">{rec.course_provider}</p>
              )}
            </div>
            <div className="flex gap-1.5 flex-shrink-0">
              <Badge label={`${rec.match_score.toFixed(0)}% match`} color="green" />
              <Badge label={priorityLabels[rec.priority] || `P${rec.priority}`} color={priorityColors[rec.priority] || 'gray'} />
            </div>
          </div>

          {/* Backend's own reason text — displayed verbatim, not replaced */}
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">{rec.reason}</p>

          {/* Meta */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
            {rec.course_duration_minutes && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {rec.course_duration_minutes} min
              </span>
            )}
            {rec.course_difficulty && <span>{rec.course_difficulty}</span>}
            {rec.competency_name && <span className="text-[#c97d2e]">{rec.competency_name}</span>}
          </div>

          {/* Status + Action buttons — respecting state machine */}
          <div className="flex items-center gap-2 mt-3">
            <RecommendationStatusBadge status={rec.status} />

            {/* RECOMMENDED → STARTED or DISMISSED */}
            {rec.status === 'RECOMMENDED' && (
              <>
                <Button size="sm" variant="secondary" loading={loading} onClick={() => doUpdate('STARTED')}>
                  Start Course
                </Button>
                <Button size="sm" variant="ghost" loading={loading} onClick={() => doUpdate('DISMISSED')}>
                  Dismiss
                </Button>
              </>
            )}

            {/* STARTED → COMPLETED only (no dismiss once started — backend enforces this) */}
            {rec.status === 'STARTED' && (
              <Button size="sm" variant="success" loading={loading} onClick={() => doUpdate('COMPLETED')}>
                <CheckCircle2 className="w-3 h-3" /> Mark Complete
              </Button>
            )}

            {/* COMPLETED / DISMISSED — no actions */}
            {rec.course_url && (
              <a
                href={rec.course_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-xs text-[#c97d2e] hover:underline"
              >
                View on iGOT →
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Comparison View ───────────────────────────────────────────────────────────
function ComparisonView({ reassessment }) {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.assessments.comparison(reassessment.id)
      .then(data => setComparison(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [reassessment.id]);

  if (loading) return <div className="flex justify-center py-16"><Spinner size="lg" className="text-[#c97d2e]" /></div>;
  if (error) return <Alert type="error" message={error} />;
  if (!comparison) return null;

  const loopColors = {
    LOOP_CLOSED:       'bg-emerald-50 border-emerald-300 text-emerald-700',
    PARTIALLY_CLOSED:  'bg-amber-50 border-amber-300 text-amber-700',
    LOOP_OPEN:         'bg-red-50 border-red-300 text-red-700',
  };

  return (
    <div className="space-y-5">
      {/* Summary card */}
      <Card className="p-6">
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border font-semibold text-sm mb-4 ${loopColors[comparison.loop_status]}`}>
          <TrendingUp className="w-4 h-4" />
          {comparison.loop_status.replace('_', ' ')}
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-black text-[#1a2e4a]">{comparison.baseline_overall_score.toFixed(1)}%</div>
            <div className="text-xs text-gray-400">Baseline</div>
          </div>
          <div>
            <div className={`text-2xl font-black ${comparison.overall_delta >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
              {comparison.overall_delta >= 0 ? '+' : ''}{comparison.overall_delta.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400">Delta</div>
          </div>
          <div>
            <div className="text-2xl font-black text-[#1a2e4a]">{comparison.reassessment_overall_score.toFixed(1)}%</div>
            <div className="text-xs text-gray-400">Reassessment</div>
          </div>
        </div>
        {/* Backend's non-causal disclaimer text — displayed verbatim as required */}
        {comparison.summary_narrative && (
          <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-100">
            <p className="text-xs text-gray-500 italic">{comparison.summary_narrative}</p>
          </div>
        )}
      </Card>

      {/* Per-competency comparisons */}
      {comparison.competency_comparisons?.map(cc => (
        <div key={cc.competency_id} className="border border-gray-100 rounded-xl p-4 bg-white">
          <div className="flex items-center justify-between mb-3">
            <span className="font-semibold text-sm text-[#1a2e4a]">
              {cc.competency_name}
            </span>
            <Badge
              label={cc.gap_resolution_status}
              color={
                cc.gap_resolution_status === 'RESOLVED'  ? 'green' :
                cc.gap_resolution_status === 'REDUCED'   ? 'blue'  :
                cc.gap_resolution_status === 'PERSISTENT'? 'amber' : 'red'
              }
            />
          </div>
          <div className="grid grid-cols-3 text-center text-sm gap-2">
            <div>
              <div className="font-bold text-gray-500">{cc.baseline_score.toFixed(1)}%</div>
              <div className="text-xs text-gray-400">Before</div>
            </div>
            <div>
              <div className={`font-black ${cc.delta >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {cc.delta >= 0 ? '+' : ''}{cc.delta.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400">Delta</div>
            </div>
            <div>
              <div className="font-bold text-gray-500">{cc.reassessment_score.toFixed(1)}%</div>
              <div className="text-xs text-gray-400">After</div>
            </div>
          </div>
          {/* Associated learning with non-causal correlation note */}
          {cc.associated_learning?.map((al, i) => (
            <div key={i} className="mt-2 p-2 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-xs text-blue-600 italic">{al.correlation_note}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Assessment History ────────────────────────────────────────────────────────
function AssessmentHistory({ onReview }) {
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.assessments.list({ limit: 20 })
      .then(data => setAssessments(data.items || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-8"><Spinner size="md" className="text-[#c97d2e]" /></div>;
  if (error) return <Alert type="error" message={error} />;
  if (assessments.length === 0) return <EmptyState icon={ClipboardCheck} title="No assessments yet" />;

  return (
    <div className="space-y-3">
      {assessments.map(a => (
        <div key={a.id} className="flex items-center gap-4 p-4 border border-gray-100 rounded-xl bg-gray-50/50 hover:bg-white transition-colors">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{
            background: a.score_percentage >= 80 ? '#10b981' :
                        a.score_percentage >= 65 ? '#3b82f6' :
                        a.score_percentage >= 50 ? '#f59e0b' : '#ef4444',
          }}>
            <span className="text-white text-xs font-bold">
              {a.status === 'IN_PROGRESS' ? '…' : `${Math.round(a.score_percentage)}%`}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-[#1a2e4a] truncate">{a.title}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {a.status === 'IN_PROGRESS' ? 'In Progress' : `${a.total_correct}/${a.total_questions} correct`}
            </p>
          </div>
          {a.status === 'COMPLETED' && (
            <Button size="sm" variant="outline" onClick={() => onReview(a)}>
              Review
            </Button>
          )}
          {a.status === 'IN_PROGRESS' && (
            <Badge label="In Progress" color="amber" />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Officer Dashboard (main) ──────────────────────────────────────────────────
export default function OfficerDashboard() {
  const [view, setView] = useState('home'); // 'home' | 'exam' | 'result' | 'comparison'
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [result, setResult] = useState(null);
  const [reassessment, setReassessment] = useState(null);

  const handleStarted = (assessment) => {
    setActiveAssessment(assessment);
    setView('exam');
  };

  const handleSubmitted = (res) => {
    setResult(res);
    setView('result');
  };

  const handleRequestReassessment = (newAssessment) => {
    setActiveAssessment(newAssessment);
    setView('exam');
  };

  const handleReviewHistoric = async (a) => {
    try {
      const res = await api.assessments.result(a.id);
      setResult(res);
      setView('result');
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <AppShell>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
        <button onClick={() => setView('home')} className="hover:text-[#1a2e4a] transition-colors">
          Dashboard
        </button>
        {view === 'exam' && <><ChevronRight className="w-3 h-3" /><span className="text-[#1a2e4a]">Assessment</span></>}
        {view === 'result' && <><ChevronRight className="w-3 h-3" /><span className="text-[#1a2e4a]">Results</span></>}
        {view === 'comparison' && <><ChevronRight className="w-3 h-3" /><span className="text-[#1a2e4a]">Comparison</span></>}
      </div>

      <AnimatePresence mode="wait">
        {view === 'home' && (
          <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <SectionHeader
              icon={Trophy}
              title="Officer Workspace"
              subtitle="Diagnose your competencies, complete your personalized learning path, and close the loop"
            />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <StartAssessmentPanel onStarted={handleStarted} />
              <Card className="p-5">
                <h2 className="text-base font-bold text-[#1a2e4a] mb-4">Assessment History</h2>
                <AssessmentHistory onReview={handleReviewHistoric} />
              </Card>
            </div>
          </motion.div>
        )}

        {view === 'exam' && activeAssessment && (
          <motion.div key="exam" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ExamView assessment={activeAssessment} onSubmitted={handleSubmitted} />
          </motion.div>
        )}

        {view === 'result' && result && (
          <motion.div key="result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <SectionHeader icon={Trophy} title="Assessment Results" />
            <ResultsView result={result} onRequestReassessment={handleRequestReassessment} />
          </motion.div>
        )}

        {view === 'comparison' && reassessment && (
          <motion.div key="comparison" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <SectionHeader icon={TrendingUp} title="Before / After Comparison" />
            <ComparisonView reassessment={reassessment} />
          </motion.div>
        )}
      </AnimatePresence>
    </AppShell>
  );
}
