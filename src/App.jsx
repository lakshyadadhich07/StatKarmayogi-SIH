import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import TrainerConsole from './screens/TrainerConsole';
import DiagnosticQuiz from './screens/DiagnosticQuiz';
import GapAnalysis from './screens/GapAnalysis';
import { LayoutDashboard, FileQuestion, LineChart } from 'lucide-react';

function Navigation() {
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <span className="font-bold text-xl text-navy">StatKarmayogi</span>
            </div>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-orange text-navy'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <LayoutDashboard className="w-4 h-4 mr-2" />
                Trainer Console
              </NavLink>
              <NavLink
                to="/diagnostic"
                className={({ isActive }) =>
                  `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-orange text-navy'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <FileQuestion className="w-4 h-4 mr-2" />
                Take Diagnostic
              </NavLink>
              <NavLink
                to="/gap-analysis"
                className={({ isActive }) =>
                  `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-orange text-navy'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`
                }
              >
                <LineChart className="w-4 h-4 mr-2" />
                My Gap Analysis
              </NavLink>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile Nav */}
      <div className="sm:hidden flex justify-around border-t border-gray-200 bg-white">
        <NavLink to="/" className={({ isActive }) => `p-3 text-sm font-medium flex flex-col items-center ${isActive ? 'text-orange' : 'text-gray-500'}`}>
           <LayoutDashboard className="w-5 h-5 mb-1" />
           Trainer
        </NavLink>
        <NavLink to="/diagnostic" className={({ isActive }) => `p-3 text-sm font-medium flex flex-col items-center ${isActive ? 'text-orange' : 'text-gray-500'}`}>
           <FileQuestion className="w-5 h-5 mb-1" />
           Quiz
        </NavLink>
        <NavLink to="/gap-analysis" className={({ isActive }) => `p-3 text-sm font-medium flex flex-col items-center ${isActive ? 'text-orange' : 'text-gray-500'}`}>
           <LineChart className="w-5 h-5 mb-1" />
           Analysis
        </NavLink>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-bg-soft flex flex-col">
        <Navigation />
        <main className="flex-grow w-full">
          <Routes>
            <Route path="/" element={<TrainerConsole />} />
            <Route path="/diagnostic" element={<DiagnosticQuiz />} />
            <Route path="/gap-analysis" element={<GapAnalysis />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
