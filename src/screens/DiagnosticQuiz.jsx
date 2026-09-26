import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, BookOpen, CheckCircle, ArrowRight, BarChart2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const diagnosticQuestions = [
  {
    id: 1,
    topic: "Index Numbers",
    stem: "Which formula is known as the 'ideal' index number because it satisfies both the time reversal and factor reversal tests?",
    options: ["Laspeyres' Index", "Paasche's Index", "Fisher's Index", "Marshall-Edgeworth Index"],
    correct: 2
  },
  {
    id: 2,
    topic: "Sampling Techniques",
    stem: "In a survey of 10,000 households, drawing a sample of 500 households completely at random is an example of:",
    options: ["Stratified Sampling", "Simple Random Sampling", "Cluster Sampling", "Systematic Sampling"],
    correct: 1
  },
  {
    id: 3,
    topic: "National Accounts",
    stem: "Gross Domestic Product (GDP) at factor cost is equal to:",
    options: ["GDP at market prices - Indirect taxes + Subsidies", "GNP - Depreciation", "NDP + Depreciation", "Total National Income"],
    correct: 0
  }
];

export default function DiagnosticQuiz() {
  const [started, setStarted] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [finished, setFinished] = useState(false);
  
  const navigate = useNavigate();

  const handleNext = () => {
    const isCorrect = selectedOption === diagnosticQuestions[currentIndex].correct;
    setAnswers([...answers, { qId: diagnosticQuestions[currentIndex].id, isCorrect, topic: diagnosticQuestions[currentIndex].topic }]);
    
    if (currentIndex < diagnosticQuestions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedOption(null);
    } else {
      setFinished(true);
    }
  };

  const calculateScore = () => {
    const correctCount = answers.filter(a => a.isCorrect).length;
    return Math.round((correctCount / diagnosticQuestions.length) * 100);
  };

  if (!started) {
    return (
      <div className="max-w-md mx-auto px-4 py-12 sm:px-6 h-full flex flex-col justify-center min-h-[calc(100vh-64px)]">
        <div className="bg-white rounded-3xl p-8 shadow-xl shadow-navy/5 border border-gray-100 text-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-orange to-blue-steel"></div>
          
          <div className="w-20 h-20 bg-blue-steel/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <BookOpen className="w-10 h-10 text-blue-steel" />
          </div>
          
          <h1 className="text-2xl font-bold text-navy mb-2">Foundation Diagnostic</h1>
          <p className="text-gray-500 mb-8">Assess your baseline knowledge across core statistical competencies.</p>
          
          <div className="flex justify-center gap-6 mb-10 text-sm font-medium text-navy bg-gray-50 p-4 rounded-2xl">
            <div className="flex items-center">
              <BookOpen className="w-4 h-4 text-orange mr-2" />
              {diagnosticQuestions.length} Questions
            </div>
            <div className="flex items-center">
              <Clock className="w-4 h-4 text-orange mr-2" />
              ~5 Mins
            </div>
          </div>
          
          <button 
            onClick={() => setStarted(true)}
            className="w-full bg-navy hover:bg-navy/90 text-white font-medium py-4 rounded-xl transition-all shadow-md flex items-center justify-center text-lg group"
          >
            Start Assessment
            <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    );
  }

  if (finished) {
    const score = calculateScore();
    const circumference = 2 * Math.PI * 45;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    return (
      <div className="max-w-md mx-auto px-4 py-8 sm:px-6 h-full flex flex-col min-h-[calc(100vh-64px)]">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white rounded-3xl p-6 sm:p-8 shadow-xl shadow-navy/5 border border-gray-100"
        >
          <h2 className="text-xl font-bold text-navy text-center mb-8">Diagnostic Complete</h2>
          
          {/* Circular Progress */}
          <div className="relative w-40 h-40 mx-auto mb-10">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#F3F4F6" strokeWidth="10" />
              <motion.circle 
                cx="50" cy="50" r="45" fill="none" 
                stroke={score >= 70 ? "#2E8B57" : "#E8792E"} 
                strokeWidth="10"
                strokeLinecap="round"
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 1.5, ease: "easeOut" }}
                style={{ strokeDasharray: circumference }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-bold text-navy">{score}%</span>
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">Score</span>
            </div>
          </div>

          {/* Topic Breakdown */}
          <div className="space-y-5 mb-10">
            <h3 className="font-semibold text-navy mb-3">Topic Breakdown</h3>
            
            {/* Mock breakdown bars */}
            <div>
              <div className="flex justify-between text-sm font-medium mb-1.5">
                <span className="text-gray-700">Index Numbers</span>
                <span className="text-green">100%</span>
              </div>
              <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ delay: 0.5 }} className="h-full bg-green rounded-full" />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm font-medium mb-1.5">
                <span className="text-gray-700">Sampling Techniques</span>
                <span className="text-orange">0%</span>
              </div>
              <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: "5%" }} transition={{ delay: 0.7 }} className="h-full bg-orange rounded-full" />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm font-medium mb-1.5">
                <span className="text-gray-700">National Accounts</span>
                <span className="text-red-500">33%</span>
              </div>
              <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: "33%" }} transition={{ delay: 0.9 }} className="h-full bg-red-500 rounded-full" />
              </div>
            </div>
          </div>

          <button 
            onClick={() => navigate('/gap-analysis')}
            className="w-full bg-blue-steel hover:bg-navy text-white font-medium py-4 rounded-xl transition-all shadow-md flex items-center justify-center"
          >
            <BarChart2 className="w-5 h-5 mr-2" />
            View Detailed Analysis
          </button>
        </motion.div>
      </div>
    );
  }

  const q = diagnosticQuestions[currentIndex];

  return (
    <div className="max-w-md mx-auto px-4 py-6 sm:py-12 h-full flex flex-col min-h-[calc(100vh-64px)]">
      
      {/* Progress */}
      <div className="mb-8">
        <div className="flex justify-between text-sm font-semibold text-gray-500 mb-2">
          <span>{q.topic}</span>
          <span>{currentIndex + 1} of {diagnosticQuestions.length}</span>
        </div>
        <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-orange transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / diagnosticQuestions.length) * 100}%` }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
          className="flex-grow flex flex-col"
        >
          <h2 className="text-xl sm:text-2xl font-semibold text-navy mb-8 leading-snug">
            {q.stem}
          </h2>

          <div className="space-y-3 flex-grow">
            {q.options.map((opt, idx) => {
              const isSelected = selectedOption === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setSelectedOption(idx)}
                  className={`w-full text-left p-5 rounded-2xl border-2 transition-all duration-200 flex items-start ${
                    isSelected 
                      ? 'border-orange bg-orange/5 shadow-md shadow-orange/10' 
                      : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className={`flex-shrink-0 w-6 h-6 rounded-full border-2 mr-4 mt-0.5 flex items-center justify-center ${
                    isSelected ? 'border-orange bg-orange' : 'border-gray-300'
                  }`}>
                    {isSelected && <div className="w-2 h-2 bg-white rounded-full" />}
                  </div>
                  <span className={`font-medium sm:text-lg ${isSelected ? 'text-navy' : 'text-gray-700'}`}>
                    {opt}
                  </span>
                </button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="pt-6 mt-auto">
        <button
          onClick={handleNext}
          disabled={selectedOption === null}
          className="w-full bg-navy hover:bg-navy/90 disabled:bg-gray-300 disabled:text-gray-500 text-white font-medium py-4 rounded-xl transition-all shadow-md flex items-center justify-center text-lg"
        >
          {currentIndex === diagnosticQuestions.length - 1 ? 'Finish Assessment' : 'Next Question'}
          <ArrowRight className="w-5 h-5 ml-2" />
        </button>
      </div>
      
    </div>
  );
}
