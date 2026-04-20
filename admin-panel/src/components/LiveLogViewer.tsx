'use client';

import { useState, useEffect, useRef } from 'react';
import { db } from '@/lib/firebaseClient';
import { ref, onValue, off, query, limitToLast } from 'firebase/database';
import { Terminal, ScrollText, ChevronRight } from 'lucide-react';

interface LogEntry {
    msg: string;
    timestamp: number;
}

export default function LiveLogViewer({ executionId, nodeId }: { executionId: string; nodeId: string }) {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!executionId || !nodeId) return;

        const logRef = query(ref(db, `executions/${executionId}/logs/${nodeId}`), limitToLast(50));
        
        const listener = onValue(logRef, (snapshot) => {
            if (snapshot.exists()) {
                const data = snapshot.val();
                const logArray = Object.values(data) as LogEntry[];
                setLogs(logArray.sort((a, b) => a.timestamp - b.timestamp));
            }
        });

        return () => off(logRef, 'value', listener);
    }, [executionId, nodeId]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="flex flex-col h-full bg-black/40 backdrop-blur-md border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/5">
                <div className="flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5 text-blue-400" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-white/50">Live Matrix Stream</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[8px] font-bold text-emerald-500 uppercase">Input Active</span>
                </div>
            </div>

            {/* Logs Area */}
            <div 
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-1.5 scrollbar-thin scrollbar-thumb-white/10"
            >
                {logs.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full opacity-20 py-8">
                        <ScrollText className="w-8 h-8 mb-2" />
                        <span className="text-[9px] font-bold uppercase tracking-wider">Waiting for telemetry...</span>
                    </div>
                )}
                
                {logs.map((log, idx) => (
                    <div key={idx} className="flex gap-3 group animate-in fade-in slide-in-from-left-2 duration-300">
                        <span className="text-white/20 select-none shrink-0">{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                        <ChevronRight className="w-3 h-3 text-blue-500/50 mt-0.5 shrink-0" />
                        <span className="text-gray-300 break-all group-hover:text-white transition-colors">{log.msg}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
