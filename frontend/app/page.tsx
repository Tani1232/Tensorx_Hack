'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { ShieldCheck, User, Briefcase, ArrowRight, Lock, Mail } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import InterviewScreen from '@/components/InterviewScreen';
import EmployeeDashboard from '@/components/EmployeeDashboard';
import { AnimatePresence, motion } from 'framer-motion';

type Role = 'customer' | 'employee' | null;

function AuthContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // Initialize role from URL if present
  const urlRole = searchParams.get('role') as Role;
  const [role, setRole] = useState<Role>(urlRole);
  const [isLogin, setIsLogin] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Persist authentication across tabs for the same role
  useEffect(() => {
    const authKey = `auth_${role}`;
    const storedAuth = localStorage.getItem(authKey);
    if (storedAuth === 'true') {
      setIsAuthenticated(true);
    }
  }, [role]);

  // Sync role state with URL
  useEffect(() => {
    if (urlRole && urlRole !== role) {
      setRole(urlRole);
    }
  }, [urlRole]);

  const updateRole = (newRole: Role) => {
    setRole(newRole);
    if (newRole) {
      router.push(`/?role=${newRole}`);
    } else {
      router.push('/');
    }
  };

  const handleAuth = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) {
      setIsAuthenticated(true);
      localStorage.setItem(`auth_${role}`, 'true');
    }
  };

  if (isAuthenticated) {
    if (role === 'employee') {
      return <EmployeeDashboard />;
    }
    return <InterviewScreen />;
  }

  return (
    <div className="min-h-screen bg-[#080A0E] text-[#F1F5F9] flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center mb-4 shadow-2xl shadow-blue-500/10">
            <ShieldCheck size={32} className="text-blue-500" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">LoanAI</h1>
          <p className="text-slate-500 mt-2">Next-gen AI Credit Assessment</p>
        </div>

        {!role ? (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-xl font-semibold text-center mb-6">Continue as</h2>
            <button
              onClick={() => updateRole('customer')}
              className="w-full p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/50 hover:bg-blue-500/5 transition-all group flex items-center gap-4 text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                <User className="text-blue-500" size={24} />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg text-white">Loan Applicant</h3>
                <p className="text-sm text-slate-500">Apply for a loan and complete AI interview</p>
              </div>
              <ArrowRight className="text-slate-700 group-hover:text-blue-500 transition-colors" size={20} />
            </button>

            <button
              onClick={() => updateRole('employee')}
              className="w-full p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all group flex items-center gap-4 text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <Briefcase className="text-emerald-500" size={24} />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg text-white">Bank Employee</h3>
                <p className="text-sm text-slate-500">Review applications and risk assessments</p>
              </div>
              <ArrowRight className="text-slate-700 group-hover:text-emerald-500 transition-colors" size={20} />
            </button>
          </div>
        ) : (
          <div className="bg-slate-900/40 border border-slate-800 p-8 rounded-3xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-300">
            <button 
              onClick={() => updateRole(null)}
              className="text-slate-500 hover:text-white text-sm mb-6 flex items-center gap-1 transition-colors"
            >
              ← Back to roles
            </button>
            
            <h2 className="text-2xl font-bold mb-2">
              {isLogin ? 'Welcome back' : 'Create account'}
            </h2>
            <p className="text-slate-500 mb-8 text-sm">
              {role === 'employee' ? 'Employee Access Portal' : 'Customer Loan Portal'}
            </p>

            <form onSubmit={handleAuth} className="space-y-5">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400 ml-1">Email address</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:border-blue-500 transition-colors text-white placeholder:text-slate-700"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400 ml-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:border-blue-500 transition-colors text-white placeholder:text-slate-700"
                  />
                </div>
              </div>

              <button
                type="submit"
                className={`w-full py-4 rounded-xl font-semibold text-white transition-all shadow-lg ${
                  role === 'employee' 
                    ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/20' 
                    : 'bg-blue-600 hover:bg-blue-500 shadow-blue-900/20'
                }`}
              >
                {isLogin ? 'Sign In' : 'Sign Up'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button 
                onClick={() => setIsLogin(!isLogin)}
                className="text-sm text-slate-500 hover:text-white transition-colors"
              >
                {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#080A0E] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    }>
      <AuthContent />
    </Suspense>
  );
}
