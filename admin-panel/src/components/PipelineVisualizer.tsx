import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, XCircle, Clock, Loader2, RefreshCw, 
  Cpu, Brain, Search, Terminal, Activity, ShieldCheck, 
  Rocket, Compass, Network, Server, FileSearch,
  ChevronDown, ChevronUp, History, Info
} from 'lucide-react';

interface TaskData {
  task_id: string;
  title: string;
  task_type: string;
  status: string;
  assigned_to_name: string | null;
  retry_count: number;
  created_at: string;
  duration_ms?: number;
}

interface PipelineVisualizerProps {
  tasks: TaskData[];
}

const STAGES = [
  { type: 'architect', label: 'System Architecture', icon: Network, est: '15s' },
  { type: 'build', label: 'Code Synthesis', icon: Cpu, est: '45s' },
  { type: 'test', label: 'Validation', icon: Activity, est: '30s' },
  { type: 'review', label: 'Quality Audit', icon: Search, est: '20s' },
  { type: 'execute', label: 'Deployment', icon: Server, est: '10s' },
];

export default function PipelineVisualizer({ tasks }: PipelineVisualizerProps) {
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  // Find the most recent task for each stage.
  const pipelineTasks = STAGES.map((stage) => {
    return tasks.find((t) => t.task_type === stage.type);
  });

  if (!pipelineTasks.some(t => t)) return null;

  const formatDuration = (ms?: number) => {
    if (!ms) return '0s';
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="glass-panel rounded-2xl p-6 mb-6 overflow-hidden relative border border-white/5 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
      {/* Dynamic Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/[0.03] via-transparent to-purple-500/[0.03] pointer-events-none" />
      
      {/* Header with DAG Meta */}
      <div className="flex items-center justify-between mb-10">
        <div className="space-y-1">
          <h2 className="text-[10px] font-black uppercase tracking-[0.4em] text-cyan-400 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
            Neural Forge Production DAG
          </h2>
          <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest ml-4">Logical Flow & Synthesis Pipeline</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-[8px] font-black text-gray-400 uppercase tracking-tighter">Status: Synchronized</span>
          </div>
          <div className="text-[9px] font-mono text-gray-500 opacity-50">V2.4 DAG-NODE-V1</div>
        </div>
      </div>

      <div className="relative flex items-start justify-between px-2 min-h-[160px]">
        {/* SVG Connectors Layer */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" style={{ overflow: 'visible' }}>
          <defs>
            <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(255,255,255,0.0)" />
              <stop offset="50%" stopColor="rgba(255,255,255,0.3)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.0)" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            {/* White Arrowhead Marker (Thin) */}
            <marker id="arrowhead-white" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.3)" />
            </marker>
          </defs>
          
          {STAGES.map((_, i) => {
            if (i === STAGES.length - 1) return null;
            const startX = `${(i * 20) + 12}%`;
            const endX = `${((i + 1) * 20) + 8}%`;
            
            // Draw a thin white animated path between nodes (0.3 opacity)
            return (
              <g key={`path-${i}`}>
                <path
                  d={`M ${startX} 48 L ${endX} 48`}
                  stroke="rgba(255,255,255,0.15)"
                  strokeWidth="0.5"
                  fill="none"
                  markerEnd="url(#arrowhead-white)"
                />
                <motion.path
                  d={`M ${startX} 48 L ${endX} 48`}
                  stroke="url(#flowGradient)"
                  strokeWidth="1"
                  fill="none"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear", delay: i * 0.5 }}
                  markerEnd="url(#arrowhead-white)"
                />
              </g>
            );
          })}
        </svg>

        {STAGES.map((stage, i) => {
          const task = pipelineTasks[i];
          const isActive = expandedStage === stage.type;
          const Icon = stage.icon;
          
          let stateConfig = {
            border: 'border-white/5',
            bg: 'bg-white/5',
            text: 'text-white/20',
            glow: '',
            StatusIcon: Clock,
            colorClass: 'text-gray-500',
            animation: '',
            status: 'Standby'
          };

          if (task) {
            if (task.status === 'completed') {
              stateConfig = {
                border: 'border-emerald-500/40',
                bg: 'bg-emerald-500/10',
                text: 'text-emerald-400',
                glow: 'shadow-[0_0_20px_rgba(16,185,129,0.2)]',
                StatusIcon: CheckCircle2,
                colorClass: 'text-emerald-500',
                animation: '',
                status: 'Verified'
              };
            } else if (task.status === 'failed') {
              stateConfig = {
                border: 'border-red-500/40',
                bg: 'bg-red-500/10',
                text: 'text-red-400',
                glow: 'shadow-[0_0_20px_rgba(239,68,68,0.2)]',
                StatusIcon: XCircle,
                colorClass: 'text-red-500',
                animation: '',
                status: 'Aborted'
              };
            } else if (task.status === 'running') {
              stateConfig = {
                border: 'border-amber-400 shadow-[0_0_30px_rgba(251,191,36,0.6)]', // GOLD BORDER & INTENSE GLOW
                bg: 'bg-amber-500/20',
                text: 'text-amber-400',
                glow: 'ring-4 ring-amber-500/20',
                StatusIcon: Loader2,
                colorClass: 'text-amber-400',
                animation: 'animate-spin',
                status: 'Processing'
              };
            } else {
              stateConfig = {
                border: 'border-amber-500/30',
                bg: 'bg-amber-500/5',
                text: 'text-amber-400/80',
                glow: '',
                StatusIcon: Clock,
                colorClass: 'text-amber-500/80',
                animation: 'animate-pulse',
                status: 'Queued'
              };
            }
          }

          return (
            <div 
              key={stage.type} 
              className={`relative z-10 flex flex-col items-center w-1/5 transition-all duration-500 ${isActive ? 'scale-110' : ''}`}
            >
              {/* NODE CARD */}
              <div className="relative group/node">
                <motion.div
                  whileHover={{ y: -5 }}
                  title={stage.label}
                  onClick={() => setExpandedStage(isActive ? null : stage.type)}
                  className={`
                    cursor-pointer w-14 h-14 md:w-16 md:h-16 rounded-2xl flex items-center justify-center 
                    border-2 backdrop-blur-2xl transition-all duration-700 
                    ${stateConfig.border} ${stateConfig.bg} ${stateConfig.glow}
                  `}
                >
                  <Icon className={`w-6 h-6 md:w-7 md:h-7 ${stateConfig.text}`} />
                  
                  {/* Duration Tooltip Badge */}
                  {task && (
                     <div className="absolute -top-3 px-2 py-0.5 bg-black/60 border border-white/10 rounded-md text-[8px] font-mono text-gray-400 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                       {formatDuration(task.duration_ms)} / {stage.est}
                     </div>
                  )}
                </motion.div>

                {/* CSS Tooltip (Koyu arka plan, beyaz metin, 12px) */}
                <div className="absolute -top-12 left-1/2 -translate-x-1/2 pointer-events-none opacity-0 group-hover/node:opacity-100 transition-opacity z-[60] whitespace-nowrap">
                  <div className="bg-slate-900 text-white text-[12px] font-bold px-3 py-1.5 rounded-lg border border-white/10 shadow-2xl">
                    {stage.label}
                  </div>
                  <div className="w-2 h-2 bg-slate-900 border-r border-b border-white/10 rotate-45 mx-auto -mt-1" />
                </div>
              </div>

              {/* LABEL & STATUS */}
              <div className="mt-5 text-center px-1 group/label">
                <p 
                  title={stage.label}
                  className="text-[9px] md:text-[10px] font-black text-white/80 tracking-widest uppercase mb-2 h-6 md:h-7 flex items-center justify-center cursor-help"
                >
                  {stage.label.length > 10 ? stage.label.substring(0, 10) + '…' : stage.label}
                </p>
                <div className={`
                  flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg border 
                  ${stateConfig.bg} ${stateConfig.border} transition-colors
                `}>
                  <stateConfig.StatusIcon className={`w-2.5 h-2.5 ${stateConfig.colorClass} ${stateConfig.animation}`} />
                  <span className={`text-[8px] md:text-[9px] font-black tracking-tighter uppercase ${stateConfig.colorClass}`}>
                    {stateConfig.status}
                  </span>
                </div>
              </div>

              {/* EXPANDABLE DETAILS */}
              <AnimatePresence>
                {isActive && task && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: 10, height: 0 }}
                    className="absolute top-full mt-4 w-48 p-3 rounded-xl bg-[#0f172a]/90 backdrop-blur-xl border border-white/10 shadow-2xl z-50 pointer-events-none"
                  >
                    <div className="space-y-2">
                       <div className="flex justify-between items-center text-[9px] border-b border-white/5 pb-1">
                         <span className="text-gray-500 uppercase font-black tracking-widest">Metadata</span>
                         <span className="text-cyan-400 font-mono">#{task.task_id.slice(0, 6)}</span>
                       </div>
                       <div className="space-y-1">
                         <div className="flex items-center gap-2 text-[10px] text-gray-300">
                           <History className="w-3 h-3 text-purple-400" />
                           <span>Time: {formatDuration(task.duration_ms)}</span>
                         </div>
                         <div className="flex items-center gap-2 text-[10px] text-gray-300">
                           <Cpu className="w-3 h-3 text-blue-400" />
                           <span className="truncate">{task.assigned_to_name || 'Unassigned'}</span>
                         </div>
                         <div className="flex items-center gap-2 text-[10px] text-gray-300">
                           <Info className="w-3 h-3 text-amber-400" />
                           <span>Retry Count: {task.retry_count}</span>
                         </div>
                       </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* DIRECTIONAL INDICATOR (Mobile only mostly) */}
              {i < STAGES.length - 1 && (
                <div className="absolute right-[-10%] top-1/2 -translate-y-1/2 md:hidden">
                  <ChevronDown className="w-4 h-4 text-white/10" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* LEGEND BRIDGING (Semantic Colors) */}
      <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-center gap-8">
        <LegendItem color="bg-emerald-500" label="Succeeded" />
        <LegendItem color="bg-cyan-400" label="Active Flow" />
        <LegendItem color="bg-amber-400" label="Waiting" />
        <LegendItem color="bg-red-500" label="Failed" />
        <LegendItem color="bg-white/10" label="Inactive" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-1.5 h-1.5 rounded-full ${color}`} />
      <span className="text-[8px] font-black text-gray-600 uppercase tracking-widest">{label}</span>
    </div>
  );
}
