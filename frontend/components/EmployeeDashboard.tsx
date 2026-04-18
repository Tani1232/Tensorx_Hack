'use client';

import React, { useState } from 'react';
import { 
  Users, 
  Search, 
  Filter, 
  ArrowUpRight, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  ChevronRight,
  MoreVertical,
  LogOut,
  RefreshCw
} from 'lucide-react';



const STATUS_CONFIG = {
  APPROVED: { label: 'Approved', color: '#10B981', bg: 'rgba(16,185,129,0.1)', icon: CheckCircle2 },
  REVIEW: { label: 'In Review', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', icon: Clock },
  DECLINED: { label: 'Declined', color: '#EF4444', bg: 'rgba(239,68,68,0.1)', icon: AlertCircle },
};

export default function EmployeeDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [customers, setCustomers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchApplications = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/applications');
      if (response.ok) {
        const data = await response.json();
        const transformed = data.map((app: any) => ({
          id: app.application_id,
          name: app.input?.interview_meta?.full_name || 'Anonymous Applicant',
          email: app.input?.interview_meta?.email || 'No email provided',
          score: app.output?.risk_score || 0,
          status: app.output?.decision || 'REVIEW',
          date: new Date(app.timestamp).toLocaleDateString(),
          income: app.input?.customer_profile?.monthly_income ? `₹${app.input.customer_profile.monthly_income.toLocaleString()}` : '—',
          loan: app.input?.loan_request?.amount ? `₹${app.input.loan_request.amount.toLocaleString()}` : '—',
        }));
        setCustomers(transformed);
      }
    } catch (error) {
      console.error('Failed to fetch applications:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const filteredCustomers = customers.filter(c => 
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    c.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSignOut = () => {
    localStorage.removeItem('auth_employee');
    window.location.href = '/';
  };

  return (
    <div className="min-h-screen bg-[#080A0E] text-[#F1F5F9] font-sans">
      {/* Sidebar */}
      <div className="fixed left-0 top-0 bottom-0 w-64 border-r border-slate-800 bg-[#0A0D12] hidden lg:flex flex-col">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
            <TrendingUp size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">Employee Hub</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 mt-4">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-600/10 text-emerald-500 border border-emerald-500/20">
            <Users size={20} />
            <span className="font-medium">Applications</span>
          </div>
          {/* Add more nav items as needed */}
        </nav>

        <div className="p-4 border-t border-slate-800">
          <button 
            onClick={handleSignOut}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-slate-500 hover:text-white hover:bg-slate-900 transition-all w-full"
          >
            <LogOut size={20} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="lg:ml-64 p-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
          <div>
            <h1 className="text-3xl font-bold text-white">Application Review</h1>
            <p className="text-slate-500 mt-1">Manage and assess customer loan risk profiles</p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                placeholder="Search customers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl py-2.5 pl-11 pr-4 w-64 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>
            <button 
              onClick={fetchApplications}
              className={`p-2.5 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition-all`}
              title="Refresh applications"
            >
              <RefreshCw size={20} className={isLoading ? 'animate-spin' : ''} />
            </button>
            <button className="p-2.5 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition-all">
              <Filter size={20} />
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm">
            <p className="text-slate-500 text-sm font-medium">Total Applications</p>
            <div className="flex items-end gap-3 mt-2">
              <span className="text-3xl font-bold text-white">{customers.length}</span>
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm">
            <p className="text-slate-500 text-sm font-medium">Avg Risk Score</p>
            <div className="flex items-end gap-3 mt-2">
              <span className="text-3xl font-bold text-white">
                {customers.length > 0 
                  ? Math.round(customers.reduce((acc, c) => acc + c.score, 0) / customers.length)
                  : 0}
              </span>
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm">
            <p className="text-slate-500 text-sm font-medium">Pending Review</p>
            <div className="flex items-end gap-3 mt-2">
              <span className="text-3xl font-bold text-white">
                {customers.filter(c => c.status === 'REVIEW').length}
              </span>
            </div>
          </div>
        </div>

        {/* Customer Table */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
          {isLoading ? (
            <div className="py-20 text-center">
              <div className="animate-spin inline-block w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-4" />
              <p className="text-slate-500">Loading applications...</p>
            </div>
          ) : (
            <>
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/50">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Customer</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Risk Score</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Financials</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredCustomers.map((customer) => {
                    const config = STATUS_CONFIG[customer.status as keyof typeof STATUS_CONFIG];
                    const StatusIcon = config.icon;
                    
                    return (
                      <tr key={customer.id} className="hover:bg-slate-800/30 transition-colors group">
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-400 group-hover:bg-emerald-600/20 group-hover:text-emerald-500 transition-all">
                              {customer.name.charAt(0)}
                            </div>
                            <div>
                              <p className="font-semibold text-white">{customer.name}</p>
                              <p className="text-xs text-slate-500 mt-0.5">{customer.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-5 text-center">
                          <div className="inline-flex flex-col items-center">
                            <span className={`text-lg font-mono font-bold ${
                              customer.score > 700 ? 'text-emerald-500' : 
                              customer.score > 500 ? 'text-amber-500' : 'text-rose-500'
                            }`}>
                              {customer.score}
                            </span>
                            <div className="w-16 h-1 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${
                                  customer.score > 700 ? 'bg-emerald-500' : 
                                  customer.score > 500 ? 'bg-amber-500' : 'bg-rose-500'
                                }`}
                                style={{ width: `${customer.score / 10}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <div className="space-y-1">
                            <p className="text-xs text-slate-400">Income: <span className="text-slate-200 font-medium">{customer.income}</span></p>
                            <p className="text-xs text-slate-400">Loan: <span className="text-slate-200 font-medium">{customer.loan}</span></p>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-slate-800" style={{ background: config.bg, color: config.color }}>
                            <StatusIcon size={14} />
                            <span className="text-xs font-bold uppercase tracking-wide">{config.label}</span>
                          </div>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <button className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 transition-all">
                            <ChevronRight size={20} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              
              {filteredCustomers.length === 0 && (
                <div className="py-20 text-center">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-slate-800/50 text-slate-600 mb-4">
                    <Search size={24} />
                  </div>
                  <p className="text-slate-500">No applications found matching "{searchTerm}"</p>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
