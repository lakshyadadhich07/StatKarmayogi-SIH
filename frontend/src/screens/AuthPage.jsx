import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap, Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Input, Select, Spinner } from '../components/ui';

const ROLE_ROUTES = {
  OFFICER: '/officer',
  TRAINER: '/trainer',
  SME:     '/sme',
  ADMIN:   '/admin',
};

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Login form state
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });

  // Register form state
  const [regForm, setRegForm] = useState({
    name: '', email: '', password: '', confirm: '',
    role: 'OFFICER', department: '', designation: '',
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(loginForm.email, loginForm.password);
      navigate(ROLE_ROUTES[user.role] || '/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (regForm.password !== regForm.confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (regForm.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      await register({
        name:        regForm.name,
        email:       regForm.email,
        password:    regForm.password,
        role:        regForm.role,
        department:  regForm.department,
        designation: regForm.designation,
      });
      // Switch to login with success hint
      setMode('login');
      setLoginForm({ email: regForm.email, password: '' });
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0d1b2a] via-[#1a2e4a] to-[#0d2318] flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center p-12 text-white relative overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#c97d2e]/10 rounded-full -translate-y-1/3 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-60 h-60 bg-emerald-500/10 rounded-full translate-y-1/3 -translate-x-1/3" />

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="relative z-10 text-center"
        >
          <div className="w-20 h-20 bg-[#c97d2e] rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-2xl shadow-[#c97d2e]/30">
            <GraduationCap className="w-11 h-11 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-3">StatKarmayogi</h1>
          <p className="text-white/60 text-lg mb-8 max-w-sm">
            AI-Driven Competency Assessment & Adaptive Learning Platform for MoSPI Statistical Officers
          </p>

          <div className="space-y-3 text-left">
            {[
              ['RAG-Grounded MCQs', 'Questions generated from official MoSPI documents'],
              ['Closed Learning Loop', 'Assess → Gap → Learn → Reassess'],
              ['Explainable Recommendations', 'iGOT courses mapped to your exact skill gaps'],
            ].map(([title, desc]) => (
              <div key={title} className="flex items-start gap-3 bg-white/5 rounded-xl px-4 py-3">
                <div className="w-2 h-2 bg-[#c97d2e] rounded-full mt-1.5 flex-shrink-0" />
                <div>
                  <div className="font-semibold text-sm">{title}</div>
                  <div className="text-xs text-white/50">{desc}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 text-xs text-white/30">
            Smart India Hackathon 2026 · Problem SIH26101 · Team Zero Risk
          </div>
        </motion.div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="bg-white rounded-3xl shadow-2xl overflow-hidden">
            {/* Tab switcher */}
            <div className="flex">
              {['login', 'register'].map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setError(''); }}
                  className={`flex-1 py-4 text-sm font-semibold transition-all
                    ${mode === m
                      ? 'bg-[#1a2e4a] text-white'
                      : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                >
                  {m === 'login' ? (
                    <span className="flex items-center justify-center gap-2">
                      <LogIn className="w-4 h-4" /> Sign In
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <UserPlus className="w-4 h-4" /> Register
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="p-8">
              <AnimatePresence mode="wait">
                {error && (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mb-5"
                  >
                    <Alert type="error" message={error} onDismiss={() => setError('')} />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── LOGIN FORM ── */}
              {mode === 'login' && (
                <form onSubmit={handleLogin} className="space-y-5" id="login-form">
                  <div>
                    <h2 className="text-2xl font-bold text-[#1a2e4a]">Welcome back</h2>
                    <p className="text-sm text-gray-400 mt-1">Sign in to your StatKarmayogi account</p>
                  </div>

                  <Input
                    id="login-email"
                    label="Institutional Email"
                    type="email"
                    placeholder="you@mospi.gov.in"
                    value={loginForm.email}
                    onChange={e => setLoginForm(p => ({ ...p, email: e.target.value }))}
                    required
                    autoComplete="email"
                  />

                  <div className="relative">
                    <Input
                      id="login-password"
                      label="Password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Your password"
                      value={loginForm.password}
                      onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
                      required
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(s => !s)}
                      className="absolute right-3 top-[34px] text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  <Button type="submit" loading={loading} className="w-full" size="lg">
                    Sign In
                  </Button>
                </form>
              )}

              {/* ── REGISTER FORM ── */}
              {mode === 'register' && (
                <form onSubmit={handleRegister} className="space-y-4" id="register-form">
                  <div>
                    <h2 className="text-2xl font-bold text-[#1a2e4a]">Create account</h2>
                    <p className="text-sm text-gray-400 mt-1">
                      ADMIN accounts cannot be self-registered (backend policy).
                    </p>
                  </div>

                  <Input
                    id="reg-name"
                    label="Full Name"
                    type="text"
                    placeholder="Ramesh Kumar"
                    value={regForm.name}
                    onChange={e => setRegForm(p => ({ ...p, name: e.target.value }))}
                    required
                  />

                  <Input
                    id="reg-email"
                    label="Email Address"
                    type="email"
                    placeholder="you@mospi.gov.in"
                    value={regForm.email}
                    onChange={e => setRegForm(p => ({ ...p, email: e.target.value }))}
                    required
                  />

                  {/* Role selector — only 3 allowed, ADMIN deliberately excluded */}
                  <Select
                    id="reg-role"
                    label="Role"
                    value={regForm.role}
                    onChange={e => setRegForm(p => ({ ...p, role: e.target.value }))}
                    required
                  >
                    <option value="OFFICER">OFFICER — Statistical Officer (takes assessments)</option>
                    <option value="TRAINER">TRAINER — Uploads documents, generates MCQs</option>
                    <option value="SME">SME — Reviews &amp; approves MCQs</option>
                  </Select>

                  <div className="grid grid-cols-2 gap-3">
                    <Input
                      id="reg-department"
                      label="Department"
                      type="text"
                      placeholder="e.g. NSO"
                      value={regForm.department}
                      onChange={e => setRegForm(p => ({ ...p, department: e.target.value }))}
                    />
                    <Input
                      id="reg-designation"
                      label="Designation"
                      type="text"
                      placeholder="e.g. STS"
                      value={regForm.designation}
                      onChange={e => setRegForm(p => ({ ...p, designation: e.target.value }))}
                    />
                  </div>

                  <div className="relative">
                    <Input
                      id="reg-password"
                      label="Password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min 8 characters"
                      value={regForm.password}
                      onChange={e => setRegForm(p => ({ ...p, password: e.target.value }))}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(s => !s)}
                      className="absolute right-3 top-[34px] text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  <Input
                    id="reg-confirm"
                    label="Confirm Password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Re-enter password"
                    value={regForm.confirm}
                    onChange={e => setRegForm(p => ({ ...p, confirm: e.target.value }))}
                    required
                  />

                  <Button type="submit" loading={loading} className="w-full" size="lg">
                    Create Account
                  </Button>
                </form>
              )}
            </div>
          </div>

          {/* Footer note */}
          <p className="text-center text-xs text-white/30 mt-6">
            Ministry of Statistics &amp; Programme Implementation · Government of India
          </p>
        </motion.div>
      </div>
    </div>
  );
}
