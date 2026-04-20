'use client';

import { useState, useEffect } from 'react';
import { Brain, Cpu, Zap, Database, RefreshCw, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

const ROLES = [
  { id: 'architect', name: 'Architect', icon: '🏗️', desc: 'Strategic Logic' },
  { id: 'build', name: 'Builder', icon: '👷', desc: 'Coding Expert' },
];

export default function ModelManager() {
  const [activeRole, setActiveRole] = useState('build');
  const [mapping, setMapping] = useState<Record<string, string>>({
    architect: 'mistral-nemo:12b',
    build: 'qwen2.5-coder:7b',
  });
  const [loading, setLoading] = useState<string | null>(null);
  const [vram, setVram] = useState({ used: 0, total: 0, percentage: 0 });
  const [onlineNodes, setOnlineNodes] = useState(0);
  const [nodes, setNodes] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1. Fetch Fleet Stats & Global Models
        const statsRes = await fetch('http://localhost:8001/api/nodes/models');
        const statsData = await statsRes.json();
        if (statsData.success) {
          if (statsData.fleet) {
            setOnlineNodes(statsData.fleet.online_nodes);
            setVram({
              used: statsData.fleet.used_vram_gb || 0,
              total: statsData.fleet.total_vram_gb || 0,
              percentage: statsData.fleet.vram_percentage || 0
            });
          }
        }

        // 2. Fetch Full Node List for Role Mapping
        const nodesRes = await fetch('http://localhost:8001/api/nodes');
        const nodesData = await nodesRes.json();
        if (Array.isArray(nodesData)) {
          setNodes(nodesData);
        }
      } catch (e) {
        console.error("Failed to fetch model manager data", e);
      }
    };

    fetchData();
    const iv = setInterval(fetchData, 5000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const r = await fetch('http://localhost:8001/bridge/status');
        const data = await r.json();
        if (data.success) {
          setActiveRole(data.active_role);
        }
      } catch (e) {
        console.error("Bridge status fail", e);
      }
    };
    fetchStatus();
    const iv = setInterval(fetchStatus, 3000);
    return () => clearInterval(iv);
  }, []);

  const switchModel = async (role: string, modelName: string) => {
    setLoading(role);
    try {
      const res = await fetch('http://localhost:8001/bridge/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, target_model: modelName })
      });
      const data = await res.json();
      if (data.success) {
        setMapping(prev => ({ ...prev, [role]: modelName }));
        setActiveRole(role);
      }
    } catch (e) {
      console.error("Model switch failed", e);
    } finally {
      setLoading(null);
    }
  };

  const isDeactivated = onlineNodes === 0;

  // Helper to find worker for a role
  const getWorkerForRole = (roleId: string) => {
    return nodes.find(n => n.assigned_roles?.includes(roleId) && n.status === 'online');
  };

  return (
    <div className={`glass-panel rounded-xl p-5 border border-purple-500/20 relative overflow-hidden transition-all duration-700 ${isDeactivated ? 'grayscale-[0.8] opacity-60' : ''}`}>
      {/* Arka Plan Efekti */}
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-500/10 blur-3xl rounded-full pointer-events-none" />
      
      {/* Deactivated Overlay */}
      {isDeactivated && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px]">
           <motion.div 
             animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }}
             transition={{ duration: 3, repeat: Infinity }}
             className="flex flex-col items-center gap-3"
           >
              <div className="p-3 rounded-full bg-purple-500/10 border border-purple-500/20">
                <Brain className="w-8 h-8 text-purple-400 opacity-50" />
              </div>
              <span className="text-[10px] font-black uppercase tracking-[0.3em] text-purple-400/80 drop-shadow-sm">Awaiting Neural Link...</span>
              <p className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Connect a worker to activate Cognitive Core</p>
           </motion.div>
        </div>
      )}

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-gray-400 flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-400" /> Cognitive Core
        </h2>
        <div className="flex items-center gap-1.5">
           <span className={`w-2 h-2 rounded-full ${isDeactivated ? 'bg-gray-600' : 'bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]'}`} />
           <span className="text-[8px] font-bold text-gray-500 uppercase tracking-widest">{onlineNodes} NODE{onlineNodes !== 1 ? 'S' : ''} ACTIVE</span>
        </div>
      </div>

      {/* VRAM Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-end mb-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Fleet Capacity</span>
          <span className="text-xs font-mono font-bold text-purple-400">
            {vram.total > 0 ? `${vram.used.toFixed(1)} / ${vram.total.toFixed(1)} GB` : '0.0 / 0.0 GB'}
          </span>
        </div>
        <div className="h-2.5 w-full bg-black/50 rounded-full overflow-hidden border border-white/5 shadow-inner">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${vram.percentage}%` }}
            className={`h-full ${vram.percentage > 85 ? 'bg-red-500' : 'bg-gradient-to-r from-purple-600 to-cyan-400'} shadow-[0_0_10px_rgba(168,85,247,0.5)] relative transition-all duration-1000`}
          >
            <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.2)_50%,transparent_75%)] bg-[length:1rem_1rem] animate-stripes" />
          </motion.div>
        </div>
      </div>

      {/* Model Seçiciler */}
      <div className="grid grid-cols-2 gap-3">
        {ROLES.map((role) => {
          const isActive = activeRole === role.id;
          const isLoading = loading === role.id;
          const assignedWorker = getWorkerForRole(role.id);
          const workerModels = assignedWorker?.capabilities?.ollama?.models || [];
          
          return (
            <div 
              key={role.id}
              className={`rounded-lg p-3 transition-all border ${
                isActive 
                  ? 'bg-cyan-900/10 border-cyan-500/30' 
                  : 'bg-black/30 border-white/5 hover:border-cyan-500/30'
              } relative overflow-hidden`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-[9px] font-bold uppercase tracking-widest flex items-center gap-1 ${isActive ? 'text-emerald-400' : 'text-cyan-400'}`}>
                  {isActive && <Zap className="w-3 h-3" />} {role.name}
                </span>
              </div>
              
              <div className="mb-2 flex items-center gap-1.5 opacity-60">
                 <Cpu className="w-2.5 h-2.5 text-gray-500" />
                 <span className="text-[8px] font-bold uppercase truncate max-w-full">
                    {assignedWorker ? assignedWorker.desktop_name : 'Unassigned'}
                 </span>
              </div>
              
              <div className="relative">
                <select 
                  value={mapping[role.id]}
                  onChange={(e) => switchModel(role.id, e.target.value)}
                  disabled={isLoading || isDeactivated || !assignedWorker}
                  className="w-full bg-transparent text-[10px] text-white outline-none cursor-pointer appearance-none relative z-10 font-bold"
                >
                  {workerModels.length > 0 ? (
                    workerModels.map((m: string) => (
                      <option key={m} value={m} className="bg-gray-900">{m}</option>
                    ))
                  ) : (
                    <option disabled className="bg-gray-900">
                        {assignedWorker ? 'No models on worker' : 'No worker for role'}
                    </option>
                  )}
                </select>
                {isLoading && (
                  <div className="absolute right-0 top-0">
                    <RefreshCw className="w-3 h-3 text-cyan-400 animate-spin" />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="mt-4 p-3 rounded-lg bg-black/20 border border-white/5 flex items-center gap-3">
         <div className="p-2 rounded-full bg-purple-500/10 border border-purple-500/20">
            <Activity className="w-3 h-3 text-purple-400 animate-pulse" />
         </div>
         <p className="text-[10px] text-gray-500 leading-tight italic">
           {isDeactivated 
             ? 'Cognitive Core offline. Connect worker for dynamic model swap.' 
             : 'Nexus Core: Modeller atanan worker bilgisayarlarından çekiliyor.'}
         </p>
      </div>
    </div>
  );
}
