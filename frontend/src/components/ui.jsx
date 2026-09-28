/**
 * Shared UI primitives — keeps component files lean.
 */
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

// ─── Alert / Toast ────────────────────────────────────────────────────────────
export function Alert({ type = 'info', message, onDismiss }) {
  const styles = {
    info:    'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    error:   'bg-red-50  border-red-200  text-red-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
  };
  const icons = {
    info:    <Info className="w-4 h-4 flex-shrink-0" />,
    success: <CheckCircle2 className="w-4 h-4 flex-shrink-0" />,
    error:   <AlertCircle className="w-4 h-4 flex-shrink-0" />,
    warning: <AlertCircle className="w-4 h-4 flex-shrink-0" />,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={`flex items-start gap-2 px-4 py-3 rounded-lg border text-sm font-medium ${styles[type]}`}
    >
      {icons[type]}
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="ml-2 opacity-60 hover:opacity-100">
          <X className="w-4 h-4" />
        </button>
      )}
    </motion.div>
  );
}

// ─── Loading Spinner ──────────────────────────────────────────────────────────
export function Spinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className={`${sizes[size]} border-2 border-current border-t-transparent rounded-full animate-spin ${className}`} />
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────────
export function Badge({ label, color = 'gray' }) {
  const colors = {
    gray:   'bg-gray-100 text-gray-700',
    blue:   'bg-blue-100 text-blue-700',
    green:  'bg-emerald-100 text-emerald-700',
    amber:  'bg-amber-100 text-amber-800',
    red:    'bg-red-100 text-red-700',
    purple: 'bg-purple-100 text-purple-700',
    navy:   'bg-[#1a2e4a]/10 text-[#1a2e4a]',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colors[color]}`}>
      {label}
    </span>
  );
}

// ─── Status Badge helpers ─────────────────────────────────────────────────────
export function DocStatusBadge({ status }) {
  const map = {
    UPLOADED:   { color: 'blue',  label: 'Uploaded' },
    PROCESSING: { color: 'amber', label: 'Processing' },
    PROCESSED:  { color: 'green', label: 'Processed' },
    FAILED:     { color: 'red',   label: 'Failed' },
  };
  const cfg = map[status] || { color: 'gray', label: status };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function QuestionStatusBadge({ status }) {
  const map = {
    PENDING_REVIEW: { color: 'amber',  label: 'Pending Review' },
    APPROVED:       { color: 'green',  label: 'Approved' },
    REJECTED:       { color: 'red',    label: 'Rejected' },
  };
  const cfg = map[status] || { color: 'gray', label: status };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function ProficiencyBadge({ level }) {
  const map = {
    BEGINNER:   { color: 'red',    label: 'Beginner' },
    DEVELOPING: { color: 'amber',  label: 'Developing' },
    PROFICIENT: { color: 'blue',   label: 'Proficient' },
    ADVANCED:   { color: 'green',  label: 'Advanced' },
  };
  const cfg = map[level] || { color: 'gray', label: level };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function GapLevelBadge({ level }) {
  const map = {
    HIGH:   { color: 'red',   label: 'HIGH Gap' },
    MEDIUM: { color: 'amber', label: 'MEDIUM Gap' },
    LOW:    { color: 'blue',  label: 'LOW Gap' },
  };
  const cfg = map[level] || { color: 'gray', label: level };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function RecommendationStatusBadge({ status }) {
  const map = {
    RECOMMENDED: { color: 'blue',  label: 'Recommended' },
    STARTED:     { color: 'amber', label: 'Started' },
    COMPLETED:   { color: 'green', label: 'Completed' },
    DISMISSED:   { color: 'gray',  label: 'Dismissed' },
  };
  const cfg = map[status] || { color: 'gray', label: status };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function DifficultyBadge({ difficulty }) {
  const map = {
    EASY:   { color: 'green', label: 'Easy' },
    MEDIUM: { color: 'amber', label: 'Medium' },
    HARD:   { color: 'red',   label: 'Hard' },
  };
  const cfg = map[difficulty] || { color: 'gray', label: difficulty };
  return <Badge label={cfg.label} color={cfg.color} />;
}

// ─── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 ${className}`}>
      {children}
    </div>
  );
}

// ─── Section Header ──────────────────────────────────────────────────────────
export function SectionHeader({ icon: Icon, title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-[#1a2e4a] flex items-center gap-3">
        {Icon && <Icon className="w-7 h-7 text-[#c97d2e]" />}
        {title}
      </h1>
      {subtitle && <p className="text-gray-500 mt-1 text-sm">{subtitle}</p>}
    </div>
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center text-gray-400">
      {Icon && <Icon className="w-16 h-16 mb-4 opacity-20" />}
      <p className="text-lg font-semibold text-gray-500">{title}</p>
      {description && <p className="text-sm mt-1">{description}</p>}
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 z-10"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-[#1a2e4a]">{title}</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          {children}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

// ─── Button ──────────────────────────────────────────────────────────────────
export function Button({ children, variant = 'primary', size = 'md', loading, ...props }) {
  const variants = {
    primary:  'bg-[#c97d2e] hover:bg-[#b56e25] text-white shadow-md shadow-[#c97d2e]/20',
    secondary:'bg-[#1a2e4a] hover:bg-[#243d5e] text-white shadow-md shadow-[#1a2e4a]/20',
    outline:  'border border-[#1a2e4a] text-[#1a2e4a] hover:bg-[#1a2e4a]/5',
    danger:   'bg-red-600 hover:bg-red-700 text-white shadow-md shadow-red-600/20',
    ghost:    'text-gray-600 hover:bg-gray-100',
    success:  'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20',
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };
  return (
    <button
      {...props}
      disabled={loading || props.disabled}
      className={`
        inline-flex items-center justify-center gap-2 font-medium rounded-xl
        transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${props.className || ''}
      `}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}

// ─── Form Input ──────────────────────────────────────────────────────────────
export function Input({ label, error, id, ...props }) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input
        id={id}
        {...props}
        className={`
          w-full px-4 py-2.5 rounded-xl border bg-white text-sm text-gray-900
          placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#c97d2e]/40
          transition-colors
          ${error ? 'border-red-400' : 'border-gray-200 hover:border-gray-300'}
          ${props.className || ''}
        `}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Select({ label, error, id, children, ...props }) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <select
        id={id}
        {...props}
        className={`
          w-full px-4 py-2.5 rounded-xl border bg-white text-sm text-gray-900
          focus:outline-none focus:ring-2 focus:ring-[#c97d2e]/40 transition-colors
          ${error ? 'border-red-400' : 'border-gray-200 hover:border-gray-300'}
          ${props.className || ''}
        `}
      >
        {children}
      </select>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
