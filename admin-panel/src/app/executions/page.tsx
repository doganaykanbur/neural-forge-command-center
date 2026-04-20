'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, CheckCircle2, XCircle, Loader2, Calendar } from 'lucide-react';
import Link from 'next/link';

type Execution = {
    id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    start_time: number;
    end_time?: number;
    nodes: Record<string, unknown>;
};

export default function ExecutionsPage() {
    const [executions, setExecutions] = useState<Record<string, Execution>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchExecutions = async () => {
            try {
                // In Phase 2, we reuse our generic workers API or create a new one. 
                // Let's assume we have /api/admin/executions
                const res = await fetch('/api/admin/executions');
                const data = await res.json();
                if (data.executions) setExecutions(data.executions);
            } catch {
                // ignore
            } finally {
                setLoading(false);
            }
        };

        fetchExecutions();
        const interval = setInterval(fetchExecutions, 5000);
        return () => clearInterval(interval);
    }, []);

    const sortedExecutions = Object.entries(executions)
        .sort(([, a], [, b]) => b.start_time - a.start_time);

    return (
        <div className="min-h-screen bg-[#06060c] text-white p-8">
            <div className="max-w-6xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <Link href="/" className="group flex items-center gap-2 text-gray-500 hover:text-blue-400 font-bold transition-all text-[10px] uppercase tracking-widest mb-4">
                            <ArrowLeft className="w-3 h-3 group-hover:-translate-x-1 transition-transform" />
                            Dashboard
                        </Link>
                        <h1 className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-white/40">Execution Logs</h1>
                        <p className="text-gray-500 text-xs font-bold uppercase tracking-[0.2em]">Audit trail for Neural Forge Factory</p>
                    </div>
                </div>

                {/* List */}
                <div className="grid gap-4">
                    {loading && <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-blue-500" /></div>}
                    
                    {!loading && sortedExecutions.length === 0 && (
                        <div className="text-center py-20 border border-dashed border-white/5 rounded-3xl">
                            <Clock className="w-12 h-12 mx-auto mb-4 opacity-10" />
                            <p className="text-gray-600 font-black uppercase tracking-widest">No Executions Found</p>
                        </div>
                    )}

                    {sortedExecutions.map(([id, exec]) => (
                        <motion.div
                            key={id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="p-6 rounded-3xl border border-white/5 bg-[#0a0a0f]/80 backdrop-blur-xl group hover:border-white/10 transition-all"
                        >
                            <div className="flex items-center justify-between flex-wrap gap-4">
                                <div className="flex items-center gap-4">
                                    <div className={`p-3 rounded-2xl ${
                                        exec.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                                        exec.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                                        'bg-blue-500/10 text-blue-400'
                                    }`}>
                                        {exec.status === 'running' ? <Loader2 className="w-6 h-6 animate-spin" /> : 
                                         exec.status === 'completed' ? <CheckCircle2 className="w-6 h-6" /> : 
                                         exec.status === 'failed' ? <XCircle className="w-6 h-6" /> : <Clock className="w-6 h-6" />}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-bold text-gray-400 text-blue-300">#{id}</span>
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-black uppercase ${
                                                exec.status === 'completed' ? 'bg-emerald-500 text-black' :
                                                exec.status === 'failed' ? 'bg-red-500 text-white' :
                                                'bg-blue-500 text-white'
                                            }`}>
                                                {exec.status}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3 mt-1 text-gray-500 text-[10px] font-bold">
                                            <div className="flex items-center gap-1.5"><Calendar className="w-3 h-3"/> {new Date(exec.start_time).toLocaleString()}</div>
                                            {exec.end_time && (
                                                <div className="flex items-center gap-1.5"><Clock className="w-3 h-3"/> {Math.round((exec.end_time - exec.start_time)/1000)}s total</div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                                    {Object.values(exec.nodes).map((node: any, idx: number) => (
                                        <div 
                                            key={idx}
                                            title={`${node.role}: ${node.status}`}
                                            className={`w-2 h-2 rounded-full ${
                                                node.status === 'completed' ? 'bg-emerald-500' :
                                                node.status === 'running' ? 'bg-blue-500 animate-pulse' :
                                                node.status === 'failed' ? 'bg-red-500' : 'bg-white/10'
                                            }`}
                                        />
                                    ))}
                                </div>

                                <Link 
                                    href={`/project?execution=${id}`}
                                    className="px-6 py-2 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/10 text-[10px] font-black uppercase tracking-widest transition-all"
                                >
                                    View Details
                                </Link>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
