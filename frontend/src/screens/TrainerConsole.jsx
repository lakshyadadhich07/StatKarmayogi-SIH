import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud, FileText, Loader2, RefreshCw, Wand2,
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2, Trash2,
} from 'lucide-react';
import { api } from '../api/client';
import AppShell from '../components/AppShell';
import {
  Card, Button, Input, Select, Alert,
  DocStatusBadge, QuestionStatusBadge, DifficultyBadge,
  SectionHeader, EmptyState, Spinner,
} from '../components/ui';

// ── Document Upload ───────────────────────────────────────────────────────────
function UploadZone({ onUploaded }) {
  const inputRef = useRef();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const MAX_MB = 20;

  const doUpload = async (file) => {
    setError('');
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'pptx'].includes(ext)) {
      setError('Only PDF and PPTX files are accepted.');
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File exceeds the ${MAX_MB} MB limit. Please choose a smaller file.`);
      return;
    }
    setUploading(true);
    try {
      const doc = await api.documents.upload(file);
      onUploaded(doc);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); doUpload(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all
          ${dragging ? 'border-[#c97d2e] bg-[#c97d2e]/5' : 'border-gray-200 hover:border-[#c97d2e] hover:bg-[#c97d2e]/5'}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.pptx"
          className="hidden"
          id="doc-file-input"
          onChange={e => doUpload(e.target.files[0])}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3 text-[#c97d2e]">
            <Spinner size="lg" />
            <p className="text-sm font-medium">Uploading & processing…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-gray-400">
            <UploadCloud className={`w-12 h-12 transition-colors ${dragging ? 'text-[#c97d2e]' : ''}`} />
            <div>
              <p className="font-semibold text-gray-600">Drag &amp; drop or click to upload</p>
              <p className="text-xs mt-1">PDF or PPTX · Max {MAX_MB} MB</p>
            </div>
          </div>
        )}
      </div>
      <AnimatePresence>
        {error && <Alert type="error" message={error} onDismiss={() => setError('')} />}
      </AnimatePresence>
    </div>
  );
}

// ── Document List ─────────────────────────────────────────────────────────────
function DocumentList({ docs, onRefresh, onSelectDoc }) {
  const [polling, setPolling] = useState(false);

  // Auto-poll while any doc is PROCESSING
  useEffect(() => {
    const hasProcessing = docs.some(d => d.status === 'PROCESSING' || d.status === 'UPLOADED');
    if (hasProcessing) {
      const t = setTimeout(onRefresh, 3000);
      return () => clearTimeout(t);
    }
  }, [docs, onRefresh]);

  if (docs.length === 0) {
    return <EmptyState icon={FileText} title="No documents uploaded yet" description="Upload a PDF or PPTX above to get started." />;
  }

  return (
    <div className="space-y-3">
      {docs.map(doc => (
        <motion.div
          key={doc.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 p-4 border border-gray-100 rounded-xl bg-gray-50/50 hover:bg-white transition-colors"
        >
          <FileText className="w-8 h-8 text-[#1a2e4a] flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-[#1a2e4a] truncate">{doc.filename}</div>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <DocStatusBadge status={doc.status} />
              {doc.generation_count > 0 && (
                <span className="text-xs text-gray-400">{doc.generation_count} generations</span>
              )}
              {doc.processing_error && (
                <span className="text-xs text-red-500 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> {doc.processing_error}
                </span>
              )}
            </div>
          </div>
          {doc.status === 'PROCESSED' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectDoc(doc)}
            >
              Generate MCQs
            </Button>
          )}
        </motion.div>
      ))}
    </div>
  );
}

// ── Generate MCQ Panel ────────────────────────────────────────────────────────
function GeneratePanel({ doc, onGenerated }) {
  const [numQuestions, setNumQuestions] = useState(5);
  const [difficulty, setDifficulty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setError('');
    setLoading(true);
    try {
      const questions = await api.questions.generate({
        document_id: doc.id,
        num_questions: numQuestions,
        ...(difficulty ? { difficulty } : {}),
      });
      onGenerated(questions);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="p-4 bg-[#1a2e4a]/5 rounded-xl border border-[#1a2e4a]/10">
        <div className="text-xs text-gray-500 mb-1">Selected Document</div>
        <div className="font-semibold text-[#1a2e4a] text-sm truncate">{doc.filename}</div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Number of Questions: <span className="text-[#c97d2e] font-bold">{numQuestions}</span>
        </label>
        <input
          type="range" min={1} max={20} value={numQuestions}
          onChange={e => setNumQuestions(Number(e.target.value))}
          className="w-full accent-[#c97d2e]"
          id="num-questions-slider"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>1</span><span>20</span>
        </div>
      </div>

      <Select
        id="gen-difficulty"
        label="Difficulty (optional)"
        value={difficulty}
        onChange={e => setDifficulty(e.target.value)}
      >
        <option value="">Any Difficulty</option>
        <option value="EASY">Easy</option>
        <option value="MEDIUM">Medium</option>
        <option value="HARD">Hard</option>
      </Select>

      <AnimatePresence>
        {error && <Alert type="error" message={error} onDismiss={() => setError('')} />}
      </AnimatePresence>

      <Button loading={loading} onClick={handleGenerate} className="w-full" size="lg">
        <Wand2 className="w-5 h-5" />
        Generate {numQuestions} MCQ{numQuestions > 1 ? 's' : ''}
      </Button>
    </div>
  );
}

// ── Generated Questions List ──────────────────────────────────────────────────
function GeneratedQuestions({ questions }) {
  const [expanded, setExpanded] = useState(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-[#1a2e4a] font-semibold">
        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        {questions.length} questions generated — awaiting SME review
      </div>
      {questions.map((q, i) => (
        <motion.div
          key={q.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="border border-gray-100 rounded-xl overflow-hidden"
        >
          <button
            className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-50 transition-colors"
            onClick={() => setExpanded(expanded === q.id ? null : q.id)}
          >
            <span className="text-xs font-bold text-gray-400 mt-0.5 w-5 flex-shrink-0">Q{i+1}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[#1a2e4a] line-clamp-2">{q.question_text}</p>
              <div className="flex gap-2 mt-2 flex-wrap">
                <QuestionStatusBadge status={q.status} />
                <DifficultyBadge difficulty={q.difficulty} />
                {q.source_page && (
                  <span className="text-xs text-gray-400">p.{q.source_page}</span>
                )}
              </div>
            </div>
            {expanded === q.id
              ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
              : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />}
          </button>

          <AnimatePresence>
            {expanded === q.id && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-4 space-y-3 border-t border-gray-100 bg-gray-50/50">
                  <div className="grid grid-cols-2 gap-2 mt-3">
                    {['A','B','C','D'].map(opt => (
                      <div
                        key={opt}
                        className={`p-2.5 rounded-lg text-xs border ${
                          q.correct_option === opt
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700 font-semibold'
                            : 'bg-white border-gray-100 text-gray-600'
                        }`}
                      >
                        <span className="font-bold mr-1">{opt}.</span>
                        {q[`option_${opt.toLowerCase()}`]}
                      </div>
                    ))}
                  </div>
                  {q.explanation && (
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                      <p className="text-xs text-blue-700 font-medium mb-1">Explanation</p>
                      <p className="text-xs text-blue-600">{q.explanation}</p>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </div>
  );
}

// ── Main Trainer Dashboard ────────────────────────────────────────────────────
export default function TrainerDashboard() {
  const [docs, setDocs] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [generatedQuestions, setGeneratedQuestions] = useState([]);
  const [tab, setTab] = useState('upload'); // 'upload' | 'generate' | 'questions'
  const [docsError, setDocsError] = useState('');

  const fetchDocs = async () => {
    try {
      const data = await api.documents.list();
      setDocs(data);
    } catch (err) {
      setDocsError(err.message);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleDocUploaded = (doc) => {
    setDocs(prev => [doc, ...prev]);
    setTab('upload');
  };

  const handleSelectDoc = (doc) => {
    setSelectedDoc(doc);
    setGeneratedQuestions([]);
    setTab('generate');
  };

  const handleGenerated = (questions) => {
    setGeneratedQuestions(questions);
    setTab('questions');
  };

  const TABS = [
    { id: 'upload',    label: 'Documents' },
    { id: 'generate',  label: 'Generate MCQs', disabled: !selectedDoc },
    { id: 'questions', label: `Results (${generatedQuestions.length})`, disabled: generatedQuestions.length === 0 },
  ];

  return (
    <AppShell>
      <SectionHeader
        icon={Wand2}
        title="Trainer Console"
        subtitle="Upload MoSPI documents, generate AI-grounded MCQs, and push to the review queue"
      />

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-xl w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            disabled={t.disabled}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed
              ${tab === t.id ? 'bg-white shadow-sm text-[#1a2e4a]' : 'text-gray-500 hover:text-gray-700'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {tab === 'upload' && (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6">
                <h2 className="text-base font-bold text-[#1a2e4a] mb-4">Upload Document</h2>
                <UploadZone onUploaded={handleDocUploaded} />
              </Card>

              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-[#1a2e4a]">Uploaded Documents</h2>
                  <button onClick={fetchDocs} className="text-gray-400 hover:text-[#1a2e4a] transition-colors">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
                {loadingDocs ? (
                  <div className="flex items-center justify-center py-12">
                    <Spinner size="md" className="text-[#c97d2e]" />
                  </div>
                ) : docsError ? (
                  <Alert type="error" message={docsError} />
                ) : (
                  <DocumentList docs={docs} onRefresh={fetchDocs} onSelectDoc={handleSelectDoc} />
                )}
              </Card>
            </div>
          </motion.div>
        )}

        {tab === 'generate' && selectedDoc && (
          <motion.div key="generate" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="max-w-xl">
              <Card className="p-6">
                <h2 className="text-base font-bold text-[#1a2e4a] mb-4">Generate MCQs via RAG</h2>
                <GeneratePanel doc={selectedDoc} onGenerated={handleGenerated} />
              </Card>
            </div>
          </motion.div>
        )}

        {tab === 'questions' && generatedQuestions.length > 0 && (
          <motion.div key="questions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Card className="p-6">
              <h2 className="text-base font-bold text-[#1a2e4a] mb-4">Generated Questions</h2>
              <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-4">
                These questions are <strong>PENDING_REVIEW</strong>. An SME must approve them before they can be used in assessments.
                Trainers cannot approve their own questions — this is enforced by the backend.
              </p>
              <GeneratedQuestions questions={generatedQuestions} />
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </AppShell>
  );
}
