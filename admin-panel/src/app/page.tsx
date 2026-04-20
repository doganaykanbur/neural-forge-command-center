'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cpu, MemoryStick, MonitorSmartphone, Activity, Layers,
  Brain, Terminal, Zap, Send, ChevronRight, ChevronUp,
  CheckCircle2, XCircle, Clock, Loader2, AlertTriangle,
  Play, Gauge, Sparkles, RefreshCw, Shield, ShieldOff,
  Settings, X, Trash2, PlayCircle, ShieldAlert, Info
} from 'lucide-react';

import PipelineVisualizer from '@/components/PipelineVisualizer';
import ModelManager from '@/components/ModelManager';

// ═══════════════════════════════════════════
// Types
// ═══════════════════════════════════════════

type NodeData = {
  node_id: string;
  desktop_name: string;
  mac_address: string;
  system_info: { cpu: string; ram: string; gpu: string };
  live_metrics: { cpu_percent: number; ram_percent: number; gpu_percent: number | null; current_task: string | null };
  assigned_roles: string[];
  registered_at: string;
  last_seen: string;
  status: string;
  autopilot_enabled: boolean;
  usage?: { total_tokens: number; token_limit: number };
};

type TaskData = {
  task_id: string;
  title: string;
  description: string;
  task_type: string;
  priority: number;
  status: string;
  assigned_to_name: string | null;
  created_at: string;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  logs: Array<{ timestamp: string; level: string; message: string }>;
  artifacts: Array<{ name: string; path: string }>;
  retry_count: number;
  parent_task_id: string | null;
  can_be_parallel: boolean;
  duration_ms: number;
};

type DashboardStats = {
  nodes_total: number;
  nodes_online: number;
  tasks_total: number;
  tasks_queued: number;
  tasks_running: number;
  tasks_completed: number;
  tasks_failed: number;
  queue_depth: number;
};

type UsageData = {
  global: {
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
    token_limit: number;
    models: Record<string, { prompt: number; completion: number; total: number }>;
  };
  nodes: Record<string, {
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
    token_limit: number;
    models: Record<string, { prompt: number; completion: number; total: number }>;
  }>;
};

// ═══════════════════════════════════════════
// API helpers
// ═══════════════════════════════════════════

const BACKEND_URL = 'http://localhost:8001';

const api = {
  get: async (path: string) => {
    const r = await fetch(`${BACKEND_URL}${path}`);
    return r.json();
  },
  post: async (path: string, body: unknown) => {
    const r = await fetch(`${BACKEND_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return r.json();
  },
  delete: async (path: string) => {
    const r = await fetch(`${BACKEND_URL}${path}`, { method: 'DELETE' });
    return r.json();
  },
};

// ═══════════════════════════════════════════
// Small components
// ═══════════════════════════════════════════

function ProgressBar({ value, color, label }: { value: number; color: string; label: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[8px] font-black tracking-widest uppercase">
        <span className="text-gray-500">{label}</span>
        <span style={{ color }} className="font-mono">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden border border-white/5">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          className="h-full"
          style={{ background: color, boxShadow: `0 0 10px ${color}44` }}
        />
      </div>
    </div>
  );
}

function MetricMini({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-2 rounded-xl bg-black/20 border border-white/5 space-y-1">
      <div className="text-[7px] font-black text-gray-600 uppercase tracking-widest">{label}</div>
      <div className="text-xs font-black font-mono" style={{ color }}>{Math.round(value)}%</div>
      <div className="h-0.5 w-full bg-white/5 rounded-full overflow-hidden">
        <div className="h-full" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-1.5 h-1.5 rounded-full bg-${color}`} />
      <span className="text-[8px] font-black text-gray-500 uppercase tracking-widest">{label}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const icons: Record<string, React.ReactNode> = {
    queued: <Clock className="w-3 h-3" />,
    assigned: <Loader2 className="w-3 h-3 animate-spin" />,
    running: <Loader2 className="w-3 h-3 animate-spin" />,
    completed: <CheckCircle2 className="w-3 h-3" />,
    failed: <XCircle className="w-3 h-3" />,
  };
  
  const colors: Record<string, string> = {
    queued: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    assigned: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
    running: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
    completed: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    failed: 'text-red-500 bg-red-500/10 border-red-500/20',
  };

  return (
    <span className={`${colors[status] || 'text-gray-500 bg-gray-500/10 border-gray-500/20'} inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-[9px] font-black uppercase tracking-wider`}>
      {icons[status] || <AlertTriangle className="w-3 h-3" />}
      {status}
    </span>
  );
}

// Component: Node Settings Modal
function NodeSettingsModal({ node, usage, onClose, onUpdateLimit }: { node: NodeData; usage: UsageData | null; onClose: () => void; onUpdateLimit: (limit: number) => void }) {
  const [limit, setLimit] = useState(node.usage?.token_limit || 1000000);
  const nodeStats = usage?.nodes?.[node.node_id] || { total_tokens: 0, token_limit: limit };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/80 backdrop-blur-md"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="glass-panel w-full max-w-lg p-8 rounded-3xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-6 right-6 p-2 hover:bg-white/5 rounded-xl transition-colors">
          <X className="w-5 h-5 text-gray-500" />
        </button>

        <div className="flex items-center gap-4 mb-8">
          <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
            <Settings className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-black tracking-tight">{node.desktop_name} Settings</h2>
            <p className="text-[10px] uppercase font-bold tracking-widest text-gray-500">Node ID: {node.node_id}</p>
          </div>
        </div>

        <div className="space-y-8">
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <label className="text-[10px] font-black uppercase tracking-widest text-gray-400">Token Quota Management</label>
              <div className="text-right">
                <div className="text-xl font-bold font-mono text-cyan-400">{(nodeStats.total_tokens).toLocaleString()}</div>
                <div className="text-[9px] font-bold text-gray-600 uppercase">Consumed</div>
              </div>
            </div>
            
            <div className="relative pt-4">
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value) || 0)}
                className="w-full bg-black/40 border border-white/5 rounded-2xl px-6 py-4 text-sm font-mono focus:border-cyan-500/50 outline-none transition-all"
                placeholder="Set max tokens..."
              />
              <p className="text-[9px] text-gray-600 mt-2 italic px-2">Set the maximum LLM tokens this worker can consume.</p>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-2xl bg-white/[0.02]">
             <div className="flex justify-between items-center mb-2 text-[9px] font-black tracking-widest uppercase text-gray-500">
               <span>Usage Intensity</span>
               <span>{Math.round((nodeStats.total_tokens / (nodeStats.token_limit || 1)) * 100)}%</span>
             </div>
             <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden border border-white/5">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${Math.min(100, (nodeStats.total_tokens / (nodeStats.token_limit || 1)) * 100)}%` }}
                 className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 shadow-[0_0_15px_rgba(6,182,212,0.5)]"
               />
             </div>
          </div>

          <div className="flex gap-3">
            <button
               onClick={() => onUpdateLimit(limit)}
               className="flex-1 py-4 bg-cyan-600 hover:bg-cyan-500 rounded-2xl text-xs font-black uppercase tracking-widest transition-all shadow-lg hover:shadow-cyan-500/20"
            >
              Update Quota
            </button>
            <button
               onClick={onClose}
               className="px-8 py-4 bg-white/5 hover:bg-white/10 rounded-2xl text-xs font-black uppercase tracking-widest transition-all border border-white/10"
            >
              Done
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function StatCard({ icon, value, label, accent }: { icon: React.ReactNode; value: number | string; label: string; accent: string }) {
  return (
    <div className="glass-panel rounded-xl p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${accent}15`, color: accent }}>
        {icon}
      </div>
      <div>
        <div className="text-2xl font-black tabular-nums" style={{ color: accent }}>{value}</div>
        <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest">{label}</div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════
// Main Dashboard
// ═══════════════════════════════════════════

export default function Dashboard() {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [orchInfo, setOrchInfo] = useState<{ provider: string; is_mock: boolean } | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [useDocker, setUseDocker] = useState<boolean>(true);
  const [decisions, setDecisions] = useState('');

  // New task form
  const [newTitle, setNewTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Drag and drop state
  const [dragHoverId, setDragHoverId] = useState<string | null>(null);

  // Pipeline form
  const [pipelineGoal, setPipelineGoal] = useState('');
  const [isPipelining, setIsPipelining] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<string | null>(null);

  // Active pipeline tracking (for the Live Tab)
  const [activePipelineId, setActivePipelineId] = useState<string | null>(null);

  // Per-node settings modal
  const [settingsNode, setSettingsNode] = useState<NodeData | null>(null);
  const [isOverride, setIsOverride] = useState(false);
  const [manualInput, setManualInput] = useState('');

  const [loadingRoleId, setLoadingRoleId] = useState<string | null>(null); // New state for UI feedback
  const [rightPanelView, setRightPanelView] = useState<'logs' | 'issues'>('logs');
  const [mockIssues] = useState([
    { id: 1, severity: 'CRITICAL', message: 'VRAM Exhaustion on Node-01', component: 'GPU_ALLOCATOR', icon: AlertTriangle },
    { id: 2, severity: 'WARNING', message: 'High Latency in Bridge Heartbeat', component: 'NEXUS_BRIDGE', icon: Activity },
    { id: 3, severity: 'INFO', message: 'Architect cache near capacity', component: 'RUNTIME_MANAGER', icon: Brain },
    { id: 4, severity: 'ERROR', message: 'Docker Daemon disconnect', component: 'CONTAINER_ENGINE', icon: ShieldOff },
    { id: 5, severity: 'WARNING', message: 'Task queue depth > 50', component: 'ORCHESTRATOR', icon: Layers },
    { id: 6, severity: 'INFO', message: 'Ollama endpoint responding slowly', component: 'LLM_PROVIDER', icon: Zap },
  ]);

  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close profile menu on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // --- Incremental Log State ---
  const [unifiedLogs, setUnifiedLogs] = useState<any[]>([]);
  const logOffsets = useRef<Record<string, number>>({});
  const activeTaskIds = useRef<Set<string>>(new Set());

  const logRef = useRef<HTMLDivElement>(null);

  // ── Polling ──
  const fetchAll = useCallback(async () => {
    // 1. Core Data (Nodes, Tasks, Dashboard)
    try {
      const nodesRes = await api.get('/api/nodes');
      setNodes(Array.isArray(nodesRes) ? nodesRes : []);
    } catch (e) {
      console.error('Nodes fetch failed:', e);
    }
    
    try {
      const tasksRes = await api.get('/api/tasks');
      setTasks(Array.isArray(tasksRes) ? tasksRes : []);
    } catch (e) {
      console.error('Tasks fetch failed:', e);
    }
    
    try {
      const statsRes = await api.get('/api/dashboard');
      setStats(statsRes);
    } catch (e) {
      console.error('Stats fetch failed:', e);
    }
    
    // 2. Orchestrator & Settings
    try {
      const orchRes = await api.get('/api/orchestrator/info');
      setOrchInfo(orchRes);
    } catch (e) {
      console.warn('OrchInfo fetch failed:', e);
    }
    
    try {
      const usageRes = await api.get('/api/orchestrator/usage');
      setUsage(usageRes || null);
    } catch (e) {
      console.warn('Usage fetch failed:', e);
    }
    
    try {
      const nexusRes = await api.get('/api/nexus/decisions');
      setDecisions(nexusRes?.decisions || '');
    } catch (e) {
      console.warn('Nexus fetch failed:', e);
    }
    
    // Update log offsets for new tasks
    tasks.forEach((task: any) => {
      if (!logOffsets.current[task.task_id]) {
        logOffsets.current[task.task_id] = 0;
      }
    });
    
    activeTaskIds.current = new Set(tasks.map((task: any) => task.task_id));
    
    try {
      const settingsRes = await api.get('/api/settings');
      if (settingsRes && typeof settingsRes.use_docker === 'boolean') {
        setUseDocker(settingsRes.use_docker);
      }
    } catch (e) {
      console.warn('Settings fetch failed:', e);
    }
  }, [tasks]);

  const fetchIncrementalLogs = useCallback(async () => {
    const runningTasks = tasks.filter(t => t.status === 'running' || t.status === 'assigned');
    
    for (const task of runningTasks) {
      const offset = logOffsets.current[task.task_id] || 0;
      try {
        const res = await api.get(`/api/tasks/${task.task_id}/logs?since=${offset}`);
        if (res.logs && res.logs.length > 0) {
          const newLogs = res.logs.map((l: any) => ({
            ...l,
            task: task.title,
            node: task.assigned_to_name,
            task_id: task.task_id
          }));
          
          setUnifiedLogs(prev => {
            // Avoid duplicates by timestamp + message
            const existingKeys = new Set(prev.map(p => p.timestamp + p.message));
            const filteredNew = newLogs.filter((l: any) => !existingKeys.has(l.timestamp + l.message));
            return [...prev, ...filteredNew].sort((a,b) => a.timestamp.localeCompare(b.timestamp)).slice(-200);
          });
          
          logOffsets.current[task.task_id] = offset + res.logs.length;
        }
      } catch (e) {
        console.error(`Failed to fetch logs for task ${task.task_id}`, e);
      }
    }
  }, [tasks]);

  useEffect(() => {
    let mounted = true;
    const runAll = async () => {
       if (mounted) await fetchAll();
    };
    const runLogs = async () => {
       if (mounted) await fetchIncrementalLogs();
    };
    
    runAll();
    runLogs();
    
    const mainIv = setInterval(runAll, 4000);
    const logIv = setInterval(runLogs, 2000);
    
    return () => { 
      mounted = false; 
      clearInterval(mainIv); 
      clearInterval(logIv);
    };
  }, [fetchAll, fetchIncrementalLogs]);

  // ── Actions ──
  const createTask = async () => {
    if (!newTitle.trim()) return;
    setIsCreating(true);
    await api.post('/api/tasks', { title: newTitle, task_type: 'pipeline', priority: 3 });
    setNewTitle('');
    setIsCreating(false);
    fetchAll();
  };

  const executePipeline = async () => {
    if (!pipelineGoal.trim()) return;
    setIsPipelining(true);
    setPipelineResult(null);
    try {
      const res = await api.post('/api/orchestrator/pipeline/execute', { goal: pipelineGoal });
      setPipelineResult(`${res.tasks_created} tasks queued`);
      // Store execution ID so the Live Pipeline tab can appear
      if (res.execution_id) {
        setActivePipelineId(res.execution_id);
      }
    } catch {
      setPipelineResult('Pipeline execution failed');
    }
    setPipelineGoal('');
    setIsPipelining(false);
    fetchAll();
  };

  const clearAllTasks = async () => {
     if (!confirm("Are you sure? This will stop and delete all current tasks.")) return;
     await api.delete('/api/tasks');
     fetchAll();
  };

  const assignRole = async (workerId: string, currentRoles: string[], newRole: string) => {
    const roleKey = `${workerId}-${newRole}`;
    setLoadingRoleId(roleKey);
    try {
      const updatedRoles = currentRoles.includes(newRole)
        ? currentRoles.filter(r => r !== newRole)
        : [...currentRoles, newRole];

      await api.post(`/api/nodes/${workerId}/roles`, { roles: updatedRoles });
      await fetchAll();
    } catch (e) {
      console.error("Role update failed", e);
    } finally {
      setLoadingRoleId(null);
    }
  };

  const toggleDocker = async () => {
    const newVal = !useDocker;
    setUseDocker(newVal);
    await api.post('/api/settings', { use_docker: newVal });
    fetchAll();
  };

  const toggleAutopilot = async (nodeId: string, current: boolean) => {
    await api.post(`/api/nodes/${nodeId}/autopilot`, { enabled: !current });
    fetchAll();
  };

  const ROLES = ['architect', 'review', 'build', 'test', 'execute', 'pipeline', 'system'];

  // Auto-scroll logs
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [unifiedLogs.length]);

  const onlineNodes = nodes.filter(n => n.status === 'online');

  // Check if any pipeline is actively running
  const hasRunningTasks = tasks.some(t => t.status === 'running' || t.status === 'assigned');

  return (
    <main className="min-h-screen p-6 lg:p-10 max-w-[1600px] mx-auto">

      {/* ════ HEADER ════ */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex justify-between items-start flex-wrap gap-4">
          <div>
            <h1 className="text-4xl lg:text-5xl font-black tracking-tighter">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500">
                NEURAL FORGE
              </span>
            </h1>
            <p className="text-gray-500 mt-1 flex items-center gap-2 text-sm">
              <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
              Command Center Active
              {orchInfo && (
                <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  <Brain className="w-3 h-3 inline mr-1" />
                  {orchInfo.provider}
                </span>
              )}
            </p>
          </div>

          {/* ═══ LIVE PIPELINE TAB & SETTINGS ═══ */}
          <div className="flex items-center gap-3">
            <button
              onClick={toggleDocker}
              className={`relative flex items-center gap-2 px-4 py-3 rounded-2xl border transition-all cursor-pointer group shadow-sm ${
                useDocker
                  ? 'bg-gradient-to-r from-emerald-600/20 to-green-600/20 border-emerald-500/30 hover:border-emerald-400/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                  : 'bg-gradient-to-r from-orange-600/20 to-red-600/20 border-orange-500/30 hover:border-orange-400/50'
              }`}
              title="Toggle Docker Isolation globally for all workers"
            >
              {useDocker ? (
                <Shield className="w-4 h-4 text-emerald-400" />
              ) : (
                <ShieldOff className="w-4 h-4 text-orange-400" />
              )}
              <span className={`text-[11px] font-black uppercase tracking-[0.1em] ${useDocker ? 'text-emerald-400' : 'text-orange-400'}`}>
                Docker: {useDocker ? 'ON' : 'OFF'}
              </span>
            </button>

            <AnimatePresence>
              {hasRunningTasks && (
                <motion.a
                  href="/live-task"
                  initial={{ opacity: 0, scale: 0.9, y: -10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9, y: -10 }}
                  className="relative flex items-center gap-3 px-6 py-3 rounded-2xl bg-gradient-to-r from-cyan-600/20 to-blue-600/20 border border-cyan-500/30 hover:border-cyan-400/50 transition-all cursor-pointer group shadow-[0_0_30px_rgba(34,211,238,0.15)] hover:shadow-[0_0_40px_rgba(34,211,238,0.25)]"
                >
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-cyan-500/5 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="relative flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                    <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 absolute" />
                    <span className="text-[11px] font-black uppercase tracking-[0.2em] text-cyan-400">
                      Live Pipeline
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 text-cyan-400/60 group-hover:translate-x-1 transition-transform" />
                  </div>
                </motion.a>
              )}
            </AnimatePresence>

            {/* AVATAR & DROPDOWN RELOCATION */}
            <div className="relative" ref={profileRef}>
              <button 
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="w-12 h-12 rounded-full bg-cyan-600 flex items-center justify-center text-white font-black shadow-lg hover:shadow-cyan-500/20 transition-all active:scale-95 cursor-pointer ring-2 ring-white/10"
              >
                N
              </button>
              
              <AnimatePresence>
                {showProfileMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-3 w-48 glass-panel rounded-2xl border border-white/10 shadow-2xl z-[100] overflow-hidden"
                  >
                    <div className="p-2 space-y-1">
                      <button className="w-full flex items-center gap-3 px-3 py-2 text-xs font-bold text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <Settings className="w-4 h-4" /> Settings
                      </button>
                      <button className="w-full flex items-center gap-3 px-3 py-2 text-xs font-bold text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <Shield className="w-4 h-4" /> About
                      </button>
                      <div className="h-px bg-white/5 mx-2 my-1" />
                      <button className="w-full flex items-center gap-3 px-3 py-2 text-xs font-bold text-red-400 hover:bg-red-500/10 rounded-xl transition-all" onClick={() => alert('Logout sequence initiated...')}>
                        <ShieldOff className="w-4 h-4" /> Logout
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mt-6">
            <StatCard icon={<MonitorSmartphone className="w-5 h-5" />} value={stats.nodes_online} label="Nodes Online" accent="#22c55e" />
            <StatCard icon={<Layers className="w-5 h-5" />} value={stats.queue_depth} label="Queue Depth" accent="#eab308" />
            <StatCard icon={<Loader2 className="w-5 h-5" />} value={stats.tasks_running} label="Running" accent="#a855f7" />
            <StatCard icon={<CheckCircle2 className="w-5 h-5" />} value={stats.tasks_completed} label="Completed" accent="#22c55e" />
            <StatCard icon={<XCircle className="w-5 h-5" />} value={stats.tasks_failed} label="Failed" accent="#ef4444" />
            <StatCard icon={<Gauge className="w-5 h-5" />} value={stats.tasks_total} label="Total Tasks" accent="#3b82f6" />
          </div>
        )}

      </motion.header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 text-white">

        {/* ════ LEFT: SECONDARY ZONE (NODE FLEET) ════ */}
        <section className="lg:col-span-3 space-y-6">
          <div className="flex justify-between items-end mb-2">
            <div className="space-y-1">
              <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-500 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" /> System Perimeter
              </h2>
              <p className="text-[9px] text-gray-600 font-bold uppercase tracking-widest ml-6">Active Node Strategy</p>
            </div>
            
            {/* ISSUE COUNTER BADGE */}
            <button 
              onClick={() => setRightPanelView(rightPanelView === 'issues' ? 'logs' : 'issues')}
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-all group cursor-pointer"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              <span className="text-[10px] font-black text-red-500">{mockIssues.length}</span>
            </button>
          </div>

          <div className="space-y-4">
            {nodes.map((node, i) => {
              // HEALTH SCORE CALCULATION
              const cpu = node.live_metrics.cpu_percent;
              const ram = node.live_metrics.ram_percent;
              const gpu = node.live_metrics.gpu_percent || 0;
              const healthScore = Math.max(0, Math.round(100 - (cpu * 0.4 + ram * 0.4 + gpu * 0.2)));
              
              let healthStatus = 'emerald';
              if (healthScore < 50 || cpu > 80 || ram > 85) healthStatus = 'amber';
              if (healthScore < 20 || gpu > 90) healthStatus = 'red';

              return (
                <motion.div
                  key={node.node_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`glass-panel rounded-2xl p-5 border-l-4 transition-all duration-500 ${
                    healthStatus === 'emerald' ? 'border-l-emerald-500/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.1)]' :
                    healthStatus === 'amber' ? 'border-l-amber-500/50 animate-pulse' :
                    'border-l-red-500 shadow-[0_0_30px_rgba(239,68,68,0.2)]'
                  }`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl bg-white/5 border border-white/5 ${healthStatus === 'red' ? 'text-red-400' : 'text-gray-400'}`}>
                        <MonitorSmartphone className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="font-black text-xs text-white/90 uppercase tracking-tighter">{node.desktop_name}</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${node.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                          <span className="text-[8px] font-black text-gray-500 uppercase">{node.status}</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* HEALTH GAUGE */}
                    <div className="text-right">
                      <div className={`text-lg font-black font-mono leading-none ${
                        healthStatus === 'emerald' ? 'text-emerald-400' : 
                        healthStatus === 'amber' ? 'text-amber-400' : 'text-red-400'
                      }`}>
                        {healthScore}%
                      </div>
                      <div className="text-[7px] font-bold text-gray-600 uppercase tracking-widest">Health</div>
                    </div>
                  </div>

                  {/* METRICS */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <MetricMini label="CPU" value={cpu} color={cpu > 80 ? '#f43f5e' : '#10b981'} />
                    <MetricMini label="RAM" value={ram} color={ram > 85 ? '#f43f5e' : '#3b82f6'} />
                    <MetricMini label="GPU" value={gpu} color={gpu > 90 ? '#f43f5e' : '#f59e0b'} />
                  </div>

                  {/* ROLES ACTIVE */}
                  <div className="flex flex-wrap gap-1">
                    {(node.assigned_roles || []).map(role => (
                      <span key={role} className="px-2 py-0.5 rounded bg-white/5 border border-white/5 text-[7px] font-black text-cyan-400/70 uppercase">
                        {role}
                      </span>
                    ))}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Add Worker Guide */}
          <div className="glass-panel rounded-xl p-4 border-dashed border-white/10 bg-black/20 mt-4">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
              <MonitorSmartphone className="w-3 h-3 text-emerald-400" />
              Infrastructure Scale
            </h3>
            <p className="text-[11px] text-gray-500 leading-relaxed mb-3">
              Run the node agent on any machine to expand the fleet capacity:
            </p>
            <div className="bg-black/80 border border-white/5 rounded p-2">
              <code className="text-emerald-400 text-[10px] font-mono break-all italic">
                python agent.py
              </code>
            </div>
          </div>
        </section>

        {/* ════ MIDDLE: TASKS & BRAIN ════ */}
        {/* ════ MIDDLE: PRIMARY ZONE (COGNITIVE CORE & DAG) ════ */}
        <section className="lg:col-span-6 space-y-8">
          
          {/* COGNITIVE CORE (PIPELINE GOAL) */}
          <div className="glass-panel rounded-3xl p-8 relative overflow-hidden border border-cyan-500/10 shadow-[0_0_80px_rgba(6,182,212,0.1)]">
            <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
              <Brain className="w-32 h-32 text-cyan-400" />
            </div>
            
            <div className="relative z-10 space-y-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
                  <Zap className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black tracking-tight text-white/90">Cognitive Core</h2>
                  <p className="text-[10px] uppercase font-bold tracking-[0.2em] text-gray-500">Autonomous Strategy Synthesis</p>
                </div>
              </div>

              <div className="relative group">
                <input
                  type="text"
                  value={pipelineGoal}
                  onChange={(e) => setPipelineGoal(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && executePipeline()}
                  placeholder="Describe your production goal (e.g. 'Build a secure auth API with tests')..."
                  className="w-full bg-black/40 border-2 border-white/5 rounded-2xl px-6 py-5 text-sm font-medium focus:border-cyan-500/50 outline-none transition-all placeholder:text-gray-600 pr-32"
                />
                <button
                  onClick={executePipeline}
                  disabled={isPipelining || !pipelineGoal.trim()}
                  className="absolute right-3 top-3 bottom-3 px-6 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:hover:bg-cyan-600 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center gap-2 group/btn shadow-xl shadow-cyan-900/20"
                >
                  {isPipelining ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Distill
                      <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* ACTIVE DAG */}
          <PipelineVisualizer tasks={tasks} />

          {/* TASK BOARD (ACTIVE OPERATIONS) */}
          <div className="glass-panel rounded-2xl p-6 border border-white/5 bg-black/40">
             <div className="flex justify-between items-center mb-6">
                <h3 className="text-xs font-black uppercase tracking-[0.3em] text-gray-200 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-400" /> Active Operations
                </h3>
                <button onClick={clearAllTasks} className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group">
                  <Trash2 className="w-4 h-4 text-gray-600 group-hover:text-red-500" />
                </button>
             </div>

             <div className="space-y-3">
               {tasks.length === 0 ? (
                 <div className="py-20 text-center space-y-3 opacity-20">
                   <Clock className="w-12 h-12 mx-auto" />
                   <p className="text-xs font-black uppercase tracking-widest">Awaiting Neural Stimulus</p>
                 </div>
               ) : (
                 [...tasks].reverse().slice(0, 10).map((task) => (
                   <div key={task.task_id} className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.08] transition-all group/row relative overflow-hidden">
                     <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${
                          task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                          task.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                          task.status === 'running' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-white/5 text-gray-500'
                        }`}>
                          {task.status === 'completed' ? <CheckCircle2 className="w-4 h-4" /> :
                           task.status === 'failed' ? <XCircle className="w-4 h-4" /> :
                           task.status === 'running' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white/90">{task.title}</div>
                          <div className="text-[9px] font-mono text-gray-600 uppercase tracking-tighter">
                            {task.task_id.slice(0, 8)} • {task.task_type}
                          </div>
                        </div>
                     </div>

                     <div className="flex items-center gap-3">
                        {/* TASK HOVER ACTIONS */}
                        <div className="flex items-center gap-2 opacity-0 group-hover/row:opacity-100 transition-opacity translate-x-4 group-hover/row:translate-x-0 transition-transform">
                          <button title="Detay" className="w-6 h-6 flex items-center justify-center rounded-lg bg-white/5 hover:bg-cyan-500/20 text-gray-500 hover:text-cyan-400 transition-all">
                            <Info className="w-3.5 h-3.5" />
                          </button>
                          <button title="Öncelik Artır" className="w-6 h-6 flex items-center justify-center rounded-lg bg-white/5 hover:bg-purple-500/20 text-gray-500 hover:text-purple-400 transition-all">
                            <ChevronUp className="w-3.5 h-3.5" />
                          </button>
                          <button title="İptal" className="w-6 h-6 flex items-center justify-center rounded-lg bg-white/5 hover:bg-red-500/20 text-gray-500 hover:text-red-500 transition-all" onClick={() => confirm('Cancel task?') && api.delete(`/api/tasks/${task.task_id}`)}>
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <div className="text-right min-w-[80px]">
                          <div className={`text-[10px] font-black uppercase tracking-widest ${
                             task.status === 'completed' ? 'text-emerald-500' :
                             task.status === 'failed' ? 'text-red-500' :
                             task.status === 'running' ? 'text-cyan-400' : 'text-gray-600'
                          }`}>
                            {task.status}
                          </div>
                          <div className="text-[8px] font-mono text-gray-600 mt-0.5">
                            {task.assigned_to_name || 'UNASSIGNED'}
                          </div>
                        </div>
                     </div>
                   </div>
                 ))
               )}
             </div>
          </div>
        </section>

          {/* ════ RIGHT: NEXUS & LOGS ════ */}
        {/* ════ RIGHT: TERTIARY ZONE (ACTIVITY LOG & INTEL) ════ */}
        <section className="lg:col-span-3 space-y-6">
          <div className="flex justify-between items-center">
            <div className="space-y-1">
              <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-500 flex items-center gap-2">
                {rightPanelView === 'logs' ? (
                  <><Terminal className="w-4 h-4 text-purple-400" /> Activity Log</>
                ) : (
                  <><ShieldAlert className="w-4 h-4 text-red-500" /> Issues Drawer</>
                )}
              </h2>
              <p className="text-[9px] text-gray-600 font-bold uppercase tracking-widest ml-6">
                {rightPanelView === 'logs' ? 'Incremental Execution Feed' : 'System Critical Violations'}
              </p>
            </div>
            <button 
              onClick={() => setRightPanelView(rightPanelView === 'logs' ? 'issues' : 'logs')}
              className="text-[8px] font-black uppercase tracking-widest text-gray-500 hover:text-white transition-colors"
            >
              [ Switch to {rightPanelView === 'logs' ? 'Issues' : 'Logs'} ]
            </button>
          </div>

          <div className="glass-panel rounded-2xl flex flex-col h-[700px] border border-white/5 bg-black/40 overflow-hidden shadow-2xl text-white">
            <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
              <span className="text-[8px] font-black text-gray-500 uppercase tracking-[0.2em]">
                {rightPanelView === 'logs' ? 'Latest Stimuli' : 'Registry of Anomalies'}
              </span>
              <div className={`w-2 h-2 rounded-full ${rightPanelView === 'logs' ? 'bg-cyan-400' : 'bg-red-500'} animate-pulse`} />
            </div>
            
            <div 
              ref={logRef}
              className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs custom-scrollbar"
            >
              {rightPanelView === 'logs' ? (
                unifiedLogs.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center space-y-3 opacity-20 animate-pulse">
                    <Terminal className="w-12 h-12" />
                    <p className="text-[10px] font-black uppercase tracking-[0.2em]">Waiting for first execution…</p>
                  </div>
                ) : (
                  unifiedLogs.map((log, i) => (
                    <motion.div
                      key={`${log.timestamp}-${i}`}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="group"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`mt-1.5 w-1 h-1 rounded-full flex-shrink-0 ${
                          log.level === 'error' ? 'bg-red-500' : 
                          log.level === 'warn' ? 'bg-amber-500' : 'bg-cyan-500/40'
                        }`} />
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[8px] text-gray-600 font-black tracking-tighter uppercase">
                              {log.timestamp.slice(11, 19)} | {log.task_id?.slice(0, 8) || 'SYSTEM'} | {log.node || 'CORE'}
                            </span>
                          </div>
                          <p className={`text-[10px] leading-relaxed break-words ${
                             log.level === 'error' ? 'text-red-400' : 
                             log.level === 'warn' ? 'text-amber-300' : 'text-gray-300'
                          }`}>
                            {log.message}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )
              ) : (
                <div className="space-y-3">
                  {mockIssues.map((issue, idx) => (
                    <motion.div
                      key={issue.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`p-3 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-all group`}
                    >
                       <div className="flex justify-between items-start mb-2">
                         <div className={`text-[8px] font-black px-1.5 py-0.5 rounded border ${
                           issue.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-500 border-red-500/30' :
                           issue.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-500 border-amber-500/30' :
                           issue.severity === 'ERROR' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                           'bg-blue-500/20 text-blue-400 border-blue-500/30'
                         }`}>
                           {issue.severity}
                         </div>
                         <span className="text-[8px] font-mono text-gray-600 uppercase tracking-tighter">{issue.component}</span>
                       </div>
                       <p className="text-[11px] font-bold text-gray-300 leading-tight">{issue.message}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          {/* LEGEND TABLE */}
          <div className="glass-panel rounded-xl p-4 border border-white/5 opacity-50 hover:opacity-100 transition-all cursor-help">
            <h4 className="text-[8px] font-black text-gray-500 uppercase tracking-widest mb-3">Semantic Color Legend</h4>
            <div className="grid grid-cols-2 gap-y-2">
              <LegendRow color="emerald-500" label="Success / Online" />
              <LegendRow color="amber-500" label="Warning / Standby" />
              <LegendRow color="red-500" label="Error / Critical" />
              <LegendRow color="cyan-400" label="Info / Running" />
            </div>
          </div>
        </section>
      </div>

      <AnimatePresence>
        {settingsNode && (
          <NodeSettingsModal 
            node={settingsNode}
            usage={usage}
            onClose={() => setSettingsNode(null)}
            onUpdateLimit={async (limit) => {
              await api.post('/api/orchestrator/usage/limit', { node_id: settingsNode.node_id, limit });
              setSettingsNode(null);
              fetchAll();
            }}
          />
        )}
      </AnimatePresence>
    </main>
  );
}
