'use client';

import React from 'react';
import { CheckCircle2, CircleDashed, Loader2, Zap, AlertCircle, Layout, Code, ShieldCheck, Microscope, Play } from 'lucide-react';

export type NodeStatus = 'pending' | 'running' | 'success' | 'repairing' | 'failed';

export interface PipelineNode {
    id: string;
    label: string;
    status: NodeStatus;
}

const getIcon = (label: string, size = 24) => {
    const l = label.toLowerCase();
    if (l.includes('architect')) return <Layout size={size} />;
    if (l.includes('build')) return <Code size={size} />;
    if (l.includes('review') || l.includes('gatekeeper')) return <ShieldCheck size={size} />;
    if (l.includes('test') || l.includes('red team')) return <Microscope size={size} />;
    if (l.includes('execute')) return <Play size={size} />;
    return <CircleDashed size={size} />;
};

export default function FocusPipelineGraph({ nodes }: { nodes: PipelineNode[] }) {
    return (
        <div className="relative w-full max-w-6xl mx-auto py-12 h-48 flex items-center justify-between px-10">
            {/* SVG Background Layer for Connections */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'drop-shadow(0 0 8px rgba(34,211,238,0.2))' }}>
                {nodes.slice(0, -1).map((node, i) => {
                    const isSuccess = node.status === 'success';
                    const isRunning = node.status === 'running' || node.status === 'repairing';
                    
                    // Simple linear path between nodes based on 100% width distribution
                    const startX = `${(i / (nodes.length - 1)) * 100}%`;
                    const endX = `${((i + 1) / (nodes.length - 1)) * 100}%`;
                    
                    return (
                        <g key={`link-${i}`}>
                            {/* Base line */}
                            <line 
                                x1={startX} y1="50%" x2={endX} y2="50%" 
                                stroke="rgba(255,255,255,0.05)" strokeWidth="2" 
                            />
                            {/* Active/Success Path */}
                            {(isSuccess || isRunning) && (
                                <line 
                                    className={isRunning ? "animate-pulse" : ""}
                                    x1={startX} y1="50%" x2={endX} y2="50%" 
                                    stroke={isSuccess ? "#10b981" : "#22d3ee"} 
                                    strokeWidth="2"
                                    strokeDasharray={isRunning ? "8,8" : "0"}
                                    style={{ 
                                        transition: 'all 1s ease-in-out',
                                        strokeOpacity: isSuccess ? 0.6 : 1
                                    }}
                                />
                            )}
                        </g>
                    );
                })}
            </svg>

            {nodes.map((node) => {
                const isRunning = node.status === 'running' || node.status === 'repairing';
                
                return (
                    <div key={node.id} className="relative z-10 flex flex-col items-center group">
                        {/* Node Halo */}
                        <div className={`
                            w-16 h-16 rounded-2xl flex items-center justify-center border transition-all duration-700 shadow-2xl relative
                            bg-[#0a0a0a] backdrop-blur-xl
                            ${node.status === 'pending' ? 'border-white/5 text-white/10' : ''}
                            ${node.status === 'success' ? 'border-emerald-500/50 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.2)]' : ''}
                            ${node.status === 'running' ? 'border-cyan-400 text-cyan-300 shadow-[0_0_30px_rgba(34,211,238,0.4)] scale-110' : ''}
                            ${node.status === 'repairing' ? 'border-amber-500 text-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.4)] scale-110' : ''}
                            ${node.status === 'failed' ? 'border-red-500 text-red-500 shadow-[0_0_30px_rgba(239,68,68,0.3)]' : ''}
                        `}>
                            {/* Inner Scanning Effect for Running */}
                            {isRunning && (
                                <>
                                    <div className={`absolute inset-0 rounded-2xl opacity-10 animate-pulse ${node.status === 'repairing' ? 'bg-amber-400' : 'bg-cyan-400'}`} />
                                    <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-400/50 blur-[1px] animate-[scan_2s_linear_infinite]" />
                                </>
                            )}

                            <div className="relative z-10 transition-transform duration-500 group-hover:scale-110">
                                {node.status === 'repairing' ? <Zap className="w-7 h-7 animate-bounce" /> : getIcon(node.label, 28)}
                            </div>
                        </div>
                        
                        {/* Label Badge */}
                        <div className={`mt-4 px-3 py-1 rounded-full text-[9px] font-black tracking-widest uppercase transition-all duration-500 border
                            ${node.status === 'pending' ? 'bg-transparent border-transparent text-white/20' : ''}
                            ${node.status === 'success' ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-500' : ''}
                            ${node.status === 'running' ? 'bg-cyan-400/10 border-cyan-400/30 text-cyan-400 animate-pulse' : ''}
                            ${node.status === 'repairing' ? 'bg-amber-500/10 border-amber-500/30 text-amber-500' : ''}
                            ${node.status === 'failed' ? 'bg-red-500/10 border-red-500/30 text-red-500' : ''}
                        `}>
                            {node.label}
                        </div>

                        {/* Status Tooltip/Sublabel */}
                        {isRunning && (
                            <div className="absolute -top-10 flex items-center gap-2 px-2 py-1 bg-black/80 border border-white/10 rounded-md whitespace-nowrap animate-in fade-in slide-in-from-bottom-2">
                                <span className={`w-1.5 h-1.5 rounded-full animate-ping ${node.status === 'repairing' ? 'bg-amber-500' : 'bg-cyan-400'}`} />
                                <span className="text-[8px] font-bold text-white/70 uppercase">In Progress...</span>
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    );
}

