import { useState } from 'react';
import { UploadCloud, FileText, Settings, Loader2, CheckCircle, Edit2, Trash2, CheckSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const mockGeneratedQuestions = [
  {
    id: 1,
    stem: "Which of the following is the most commonly used index number to measure inflation in India at the retail level?",
    options: ["Wholesale Price Index (WPI)", "Consumer Price Index (CPI)", "Index of Industrial Production (IIP)", "GDP Deflator"],
    correct: 1,
    difficulty: "L2",
    topic: "Index Numbers"
  },
  {
    id: 2,
    stem: "In stratified random sampling, the population is divided into strata that are internally:",
    options: ["Heterogeneous", "Homogeneous", "Overlapping", "Randomly distributed"],
    correct: 1,
    difficulty: "L3",
    topic: "Sampling Theory"
  },
  {
    id: 3,
    stem: "The base year currently used for calculating National Income in India is:",
    options: ["2004-05", "2011-12", "2015-16", "2020-21"],
    correct: 1,
    difficulty: "L1",
    topic: "National Accounts"
  },
  {
    id: 4,
    stem: "Which method of national income estimation is used for the agriculture sector in India?",
    options: ["Income Method", "Expenditure Method", "Value Added (Product) Method", "Consumption Method"],
    correct: 2,
    difficulty: "L3",
    topic: "National Accounts"
  },
  {
    id: 5,
    stem: "Under the Periodic Labour Force Survey (PLFS), 'Usual Status' refers to a reference period of:",
    options: ["7 days", "30 days", "365 days", "Current day"],
    correct: 2,
    difficulty: "L4",
    topic: "Survey Methodology"
  }
];

export default function TrainerConsole() {
  const [file, setFile] = useState(null);
  const [numQuestions, setNumQuestions] = useState(10);
  const [difficulty, setDifficulty] = useState('L3');
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);
  const [questions, setQuestions] = useState([]);
  
  const [isPushing, setIsPushing] = useState(false);
  const [pushSuccess, setPushSuccess] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const generateAssessment = async () => {
    if (!file) return alert("Please upload a file first");
    
    setIsGenerating(true);
    setQuestions([]);
    
    const steps = ["Extracting text...", "Chunking content...", "Generating questions..."];
    for (let i = 0; i < steps.length; i++) {
      setGenerationStep(i);
      await new Promise(r => setTimeout(r, 800)); // Mock delay
    }
    
    setIsGenerating(false);
    setQuestions(mockGeneratedQuestions);
    setSelectedIds(mockGeneratedQuestions.map(q => q.id)); // Select all by default
  };

  const pushToIgot = async () => {
    setIsPushing(true);
    await new Promise(r => setTimeout(r, 1200));
    setIsPushing(false);
    setPushSuccess(true);
    setTimeout(() => setPushSuccess(false), 3000);
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6">
      
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-navy mb-2 flex items-center">
          <Settings className="w-8 h-8 mr-3 text-orange" />
          Trainer Console
        </h1>
        <p className="text-gray-600">Ingest source material and generate AI-driven assessments for iGOT.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Upload & Config */}
        <div className="space-y-6">
          {/* Upload Zone */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold mb-4 text-navy">1. Source Material</h2>
            <div 
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-orange hover:bg-orange/5 transition-all cursor-pointer group"
              onClick={() => {
                // Mocking file select
                setFile({ name: 'NSSTA_Training_Manual_2025.pdf', size: 2450000 });
              }}
            >
              {file ? (
                <div className="flex flex-col items-center">
                  <FileText className="w-12 h-12 text-blue-steel mb-3" />
                  <p className="font-medium text-navy">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <UploadCloud className="w-12 h-12 text-gray-400 group-hover:text-orange mb-3 transition-colors" />
                  <p className="font-medium text-navy">Drag & drop or click to upload</p>
                  <p className="text-sm text-gray-500 mt-1">PDF, DOCX up to 50MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Config Controls */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold mb-4 text-navy">2. Generation Settings</h2>
            
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Number of Questions</label>
                <input 
                  type="range" 
                  min="5" max="50" 
                  value={numQuestions} 
                  onChange={(e) => setNumQuestions(e.target.value)}
                  className="w-full accent-orange"
                />
                <div className="text-right text-sm font-semibold text-orange mt-1">{numQuestions} MCQs</div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Target Difficulty</label>
                <div className="flex bg-gray-100 rounded-lg p-1">
                  {['L1', 'L2', 'L3', 'L4', 'L5'].map(level => (
                    <button
                      key={level}
                      onClick={() => setDifficulty(level)}
                      className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${
                        difficulty === level ? 'bg-white shadow-sm text-orange' : 'text-gray-500 hover:text-navy'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              <button 
                onClick={generateAssessment}
                disabled={isGenerating || !file}
                className="w-full bg-orange hover:bg-orange/90 text-white font-medium py-3 rounded-xl transition-all shadow-md shadow-orange/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isGenerating ? (
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                ) : (
                  <CheckSquare className="w-5 h-5 mr-2" />
                )}
                Generate Assessment
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Results & Review */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 h-full flex flex-col overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h2 className="text-lg font-semibold text-navy">3. Review & Approve</h2>
              
              {questions.length > 0 && (
                <button 
                  onClick={pushToIgot}
                  disabled={isPushing || selectedIds.length === 0}
                  className="bg-green hover:bg-green/90 text-white px-4 py-2 rounded-lg font-medium transition-all shadow-sm flex items-center disabled:opacity-50"
                >
                  {isPushing ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle className="w-4 h-4 mr-2" />
                  )}
                  Push to iGOT ({selectedIds.length})
                </button>
              )}
            </div>

            <div className="p-6 flex-grow overflow-y-auto relative min-h-[400px]">
              <AnimatePresence>
                {pushSuccess && (
                  <motion.div 
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-green text-white px-6 py-3 rounded-full shadow-lg font-medium flex items-center z-10"
                  >
                    <CheckCircle className="w-5 h-5 mr-2" />
                    {selectedIds.length} questions pushed to iGOT Course Bank
                  </motion.div>
                )}
              </AnimatePresence>

              {isGenerating ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-500">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Loader2 className="w-12 h-12 text-orange mb-4" />
                  </motion.div>
                  <p className="text-lg font-medium text-navy animate-pulse">
                    {["Extracting text...", "Chunking content...", "Generating questions..."][generationStep]}
                  </p>
                </div>
              ) : questions.length > 0 ? (
                <div className="space-y-4">
                  {questions.map((q) => (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      key={q.id} 
                      className={`border rounded-xl p-4 transition-all ${
                        selectedIds.includes(q.id) ? 'border-orange/30 bg-orange/5' : 'border-gray-100 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(q.id)}
                          onChange={() => toggleSelect(q.id)}
                          className="mt-1.5 w-5 h-5 rounded text-orange accent-orange cursor-pointer"
                        />
                        <div className="flex-grow">
                          <div className="flex flex-wrap gap-2 mb-2">
                            <span className="px-2 py-0.5 bg-blue-steel/10 text-blue-steel rounded text-xs font-semibold">{q.difficulty}</span>
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-semibold">{q.topic}</span>
                          </div>
                          <p className="font-medium text-navy mb-3">{q.stem}</p>
                          <div className="space-y-2">
                            {q.options.map((opt, idx) => (
                              <div key={idx} className={`text-sm p-2 rounded-md ${idx === q.correct ? 'bg-green/10 border border-green/20 text-green font-medium' : 'bg-gray-50 text-gray-600 border border-transparent'}`}>
                                {String.fromCharCode(65 + idx)}. {opt}
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <button className="p-2 text-gray-400 hover:text-navy hover:bg-gray-100 rounded-lg transition-colors">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <FileText className="w-16 h-16 mb-4 opacity-20" />
                  <p>Upload a document and generate to see results here.</p>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
