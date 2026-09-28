import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, FileText, HelpCircle, ClipboardCheck,
  GraduationCap, Users, LogOut, ChevronLeft, ChevronRight,
  BookOpen, BarChart3, Menu, X,
} from 'lucide-react';

const NAV_BY_ROLE = {
  TRAINER: [
    { to: '/trainer',           icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/trainer/documents', icon: FileText,         label: 'Documents' },
    { to: '/trainer/questions', icon: HelpCircle,       label: 'Questions' },
  ],
  SME: [
    { to: '/sme',               icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/sme/review',        icon: ClipboardCheck,   label: 'Review Queue' },
  ],
  OFFICER: [
    { to: '/officer',                icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/officer/assessments',    icon: ClipboardCheck,   label: 'Assessments' },
    { to: '/officer/recommendations',icon: BookOpen,         label: 'Learning Path' },
  ],
  ADMIN: [
    { to: '/admin',          icon: LayoutDashboard, label: 'Overview' },
    { to: '/admin/users',    icon: Users,            label: 'Users' },
    { to: '/admin/documents',icon: FileText,         label: 'Documents' },
    { to: '/admin/assessments',icon: BarChart3,      label: 'Assessments' },
  ],
};

const ROLE_COLOR = {
  TRAINER: 'from-[#1a2e4a] to-[#243d5e]',
  SME:     'from-[#2e1a4a] to-[#3d2465]',
  OFFICER: 'from-[#1a3a2e] to-[#245040]',
  ADMIN:   'from-[#4a1a1a] to-[#5e2424]',
};

const ROLE_LABEL = {
  TRAINER: 'Trainer Console',
  SME:     'SME Review Portal',
  OFFICER: 'Officer Workspace',
  ADMIN:   'Admin Dashboard',
};

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const nav = NAV_BY_ROLE[user?.role] || [];
  const gradient = ROLE_COLOR[user?.role] || 'from-[#1a2e4a] to-[#243d5e]';
  const roleLabel = ROLE_LABEL[user?.role] || 'Dashboard';

  const SidebarContent = () => (
    <div className={`flex flex-col h-full bg-gradient-to-b ${gradient} text-white`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <div className="w-9 h-9 bg-[#c97d2e] rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div>
            <div className="text-sm font-bold leading-tight">StatKarmayogi</div>
            <div className="text-xs text-white/50">MoSPI · SIH26101</div>
          </div>
        )}
      </div>

      {/* Role badge */}
      {!collapsed && (
        <div className="mx-4 mt-4 px-3 py-2 bg-white/10 rounded-xl">
          <div className="text-xs text-white/60">Workspace</div>
          <div className="text-sm font-semibold">{roleLabel}</div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all
               ${isActive
                 ? 'bg-white/20 text-white shadow-inner'
                 : 'text-white/70 hover:bg-white/10 hover:text-white'
               }`
            }
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User + logout */}
      <div className="border-t border-white/10 p-4 space-y-3">
        {!collapsed && user && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#c97d2e] rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
              {user.name?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="overflow-hidden">
              <div className="text-sm font-medium truncate">{user.name}</div>
              <div className="text-xs text-white/50 truncate">{user.role}</div>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-sm text-white/70
                     hover:bg-white/10 hover:text-white transition-all"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && 'Sign Out'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-[#f4f6f9] overflow-hidden">
      {/* Desktop Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 72 : 256 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="hidden md:flex flex-col flex-shrink-0 relative shadow-xl"
      >
        <SidebarContent />
        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="absolute -right-3 top-16 w-6 h-6 bg-white border border-gray-200 rounded-full
                     flex items-center justify-center shadow-sm text-gray-500 hover:text-[#1a2e4a]
                     transition-colors z-10"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </motion.aside>

      {/* Mobile Sidebar */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-40 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed left-0 top-0 bottom-0 w-64 z-50 md:hidden shadow-2xl"
            >
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-200 px-4 md:px-6 h-16 flex items-center gap-4 flex-shrink-0 shadow-sm">
          <button
            className="md:hidden text-gray-500 hover:text-[#1a2e4a]"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          {user && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-[#1a2e4a] rounded-full flex items-center justify-center text-sm font-bold text-white">
                {user.name?.[0]?.toUpperCase() || '?'}
              </div>
              <div className="hidden sm:block text-right">
                <div className="text-sm font-semibold text-[#1a2e4a]">{user.name}</div>
                <div className="text-xs text-gray-400">{user.designation || user.role}</div>
              </div>
            </div>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
