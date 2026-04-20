'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Cpu, MemoryStick, Play, MonitorSmartphone, XCircle, Trash2 } from 'lucide-react';

export type WorkerNodeData = {
    workerId: string;
    label: string;
    cpu: string;
    ram: string;
    gpu: string;
    activeRole: string | null;
    unavailableRoles: string[];
    last_seen: number;
    executionStatus?: 'pending' | 'running' | 'completed' | 'failed';
    onRoleSelect: (nodeId: string, role: string) => void;
    onDelete: (nodeId: string) => void;
};

const ROLE_COLORS: Record<string, string> = {
    'Builder': '#f59e0b',
    'Executor': '#3b82f6',
    'Orchestrator': '#8b5cf6',
    'Architect': '#10b981',
};

function WorkerNode({ id, data, selected }: NodeProps & { data: WorkerNodeData }) {
    const now = new Date().getTime();
    const isOnline = now - data.last_seen < 30000;
    const roles = ['Builder', 'Executor', 'Orchestrator', 'Architect'];

    return (
        <div
            className={`
                relative w-72 rounded-xl overflow-visible
                bg-[#0a0a0f] border transition-all duration-300
                ${selected
                    ? 'border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.5),0_0_40px_rgba(59,130,246,0.2)]'
                    : 'border-white/10 shadow-[0_0_15px_rgba(0,0,0,0.8)]'}
            `}
        >
            {/* Glow overlay */}
            {selected && (
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 rounded-xl pointer-events-none" />
            )}

            {/* Header */}
            <div 
                className="px-4 py-3 border-b border-white/10 flex items-center justify-between"
                style={{
                    background: data.activeRole 
                        ? `linear-gradient(to right, ${ROLE_COLORS[data.activeRole]}44, ${ROLE_COLORS[data.activeRole]}22)`
                        : 'linear-gradient(to right, rgba(255,255,255,0.05), rgba(255,255,255,0.02))'
                }}
            >
                <div className="flex items-center gap-1.5 min-w-0">
                    <MonitorSmartphone 
                        className={`w-4 h-4 flex-shrink-0 ${data.executionStatus === 'running' ? 'animate-pulse' : ''}`} 
                        style={{ color: data.activeRole ? ROLE_COLORS[data.activeRole] : '#6b7280' }} 
                    />
                    <div className="flex flex-col truncate">
                        <span className="font-bold text-sm tracking-wide text-white truncate">{data.label}</span>
                        {data.activeRole && (
                            <div className="flex items-center gap-1.5">
                                <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: ROLE_COLORS[data.activeRole] }}>{data.activeRole}</span>
                                {data.executionStatus && (
                                    <span className={`text-[8px] px-1 rounded font-black uppercase tracking-tighter ${
                                        data.executionStatus === 'running' ? 'bg-blue-500 text-white animate-pulse' :
                                        data.executionStatus === 'completed' ? 'bg-emerald-500 text-white' :
                                        data.executionStatus === 'failed' ? 'bg-red-500 text-white' : 'bg-white/10 text-white/40'
                                    }`}>
                                        {data.executionStatus}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-black border ${isOnline ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-red-500/10 text-red-500 border-red-500/30'}`}>
                        {isOnline ? 'ONLINE' : 'OFFLINE'}
                    </div>
                    <button 
                        onClick={(e) => { e.stopPropagation(); data.onDelete(id); }}
                        className="p-1 hover:bg-white/10 rounded transition-colors text-white/40 hover:text-red-400"
                    >
                        <XCircle className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Body */}
            <div className={`px-4 py-3 space-y-2.5 transition-all ${!data.activeRole ? 'pb-2' : ''}`}>
                <div className="space-y-1.5 list-none">
                    <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
                        <Cpu className="w-3.5 h-3.5 text-blue-400/50" />
                        <span className="truncate">{data.cpu}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
                        <MemoryStick className="w-3.5 h-3.5 text-emerald-400/50" />
                        <span className="truncate">{data.ram}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
                        <Play className="w-3.5 h-3.5 text-orange-400/50" />
                        <span className="truncate">{data.gpu}</span>
                    </div>
                </div>

                {!data.activeRole ? (
                    <div className="pt-2 border-t border-white/5">
                        <h4 className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-2 px-1">Assign Role</h4>
                        <div className="grid grid-cols-2 gap-1.5">
                            {roles.map(role => {
                                const isUnavailable = data.unavailableRoles.includes(role);
                                return (
                                    <button
                                        key={role}
                                        disabled={isUnavailable}
                                        onClick={() => data.onRoleSelect(id, role)}
                                        className={`
                                            px-2 py-2 rounded-lg text-[10px] font-bold transition-all border
                                            ${isUnavailable 
                                                ? 'bg-red-500/5 border-red-500/10 text-red-500/10 cursor-not-allowed line-through'
                                                : 'bg-white/5 border-white/5 text-gray-400 hover:bg-white/10 hover:border-white/20 hover:text-white'
                                            }
                                        `}
                                        style={!isUnavailable ? {
                                            boxShadow: `inset 0 0 10px ${ROLE_COLORS[role]}11`
                                        } : {}}
                                    >
                                        {role}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <div className="flex justify-end pt-1">
                        <button 
                            onClick={() => data.onRoleSelect(id, '')}
                            className="text-[9px] font-bold text-gray-600 hover:text-red-400 transition-colors uppercase tracking-widest flex items-center gap-1"
                        >
                            <Trash2 className="w-2.5 h-2.5" />
                            Change Role
                        </button>
                    </div>
                )}
            </div>

            {/* Handles */}
            <Handle
                type="target"
                position={Position.Left}
                className="!w-3 !h-3 !bg-blue-500 !border-2 !border-blue-300 !-left-1.5"
            />
            <Handle
                type="source"
                position={Position.Right}
                className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300 !-right-1.5"
            />
        </div>
    );
}

export default memo(WorkerNode);
