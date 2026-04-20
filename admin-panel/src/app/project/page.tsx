'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    ReactFlow,
    Controls,
    Background,
    BackgroundVariant,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Cpu, MonitorSmartphone, Play, Trash2, Rocket, Loader2, X } from 'lucide-react';
import Link from 'next/link';
import WorkerNode, { WorkerNodeData } from '@/components/WorkerNode';
import LiveLogViewer from '@/components/LiveLogViewer';

const nodeTypes = { workerNode: WorkerNode };

const ROLE_COLORS: Record<string, string> = {
    'Builder': '#f59e0b',
    'Executor': '#3b82f6',
    'Orchestrator': '#8b5cf6',
    'Architect': '#10b981',
};

type WorkerData = {
    system_info: { cpu: string; ram: string; gpu: string };
    desktop_name: string;
    roles: string[];
    last_seen: number;
};

export default function ProjectPage() {
    const [workers, setWorkers] = useState<Record<string, WorkerData>>({});
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const [draggingWorkerId, setDraggingWorkerId] = useState<string | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [executionId, setExecutionId] = useState<string | null>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [executionData, setExecutionData] = useState<any>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [rfInstance, setRfInstance] = useState<any>(null);

    // Initial and polling fetch for workers
    useEffect(() => {
        const fetch_workers = async () => {
            try {
                const res = await fetch('/api/admin/workers');
                const data = await res.json();
                if (data.workers) setWorkers(data.workers);
            } catch (e) {
                console.error("Fetch workers error:", e);
            }
        };
        fetch_workers();
        const interval = setInterval(fetch_workers, 5000);
        return () => clearInterval(interval);
    }, []);

    // Polling for execution status if one is running
    useEffect(() => {
        if (!executionId) {
            setExecutionData(null);
            return;
        }

        const fetchStatus = async () => {
            try {
                const res = await fetch(`/api/admin/execution-status?id=${executionId}`);
                const data = await res.json();
                if (data.error) {
                    setExecutionId(null);
                    return;
                }
                setExecutionData(data);
            } catch {
                // ignore
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 2000);
        return () => clearInterval(interval);
    }, [executionId]);

    const onDeleteNode = useCallback((nodeId: string) => {
        setNodes(nds => nds.filter(n => n.id !== nodeId));
        setEdges(eds => eds.filter(e => e.source !== nodeId && e.target !== nodeId));
        if (selectedNodeId === nodeId) setSelectedNodeId(null);
    }, [setNodes, setEdges, selectedNodeId]);

    const handleRoleSelect = useCallback((nodeId: string, role: string) => {
        setNodes(nds => {
            const updatedNodes = nds.map(node => {
                if (node.id === nodeId) {
                    return { ...node, data: { ...node.data, activeRole: role || null } };
                }
                return node;
            });
            const targetWorkerId = (nds.find(n => n.id === nodeId)?.data as WorkerNodeData).workerId;
            return updatedNodes.map(node => {
                const nodeData = node.data as WorkerNodeData;
                if (nodeData.workerId === targetWorkerId) {
                    const others = updatedNodes.filter(n => (n.data as WorkerNodeData).workerId === targetWorkerId && n.id !== node.id);
                    const taken = others.map(n => (n.data as WorkerNodeData).activeRole).filter(Boolean) as string[];
                    return { ...node, data: { ...nodeData, unavailableRoles: taken } };
                }
                return node;
            });
        });
    }, [setNodes]);

    // Real-time synchronization
    useEffect(() => {
        setNodes(nds => nds.map(node => {
            const data = node.data as WorkerNodeData;
            const worker = workers[data.workerId];
            const nodeExecStatus = executionData?.nodes?.[node.id]?.status;

            if (!worker) return node;
            return {
                ...node,
                data: {
                    ...data,
                    last_seen: worker.last_seen,
                    cpu: worker.system_info?.cpu || data.cpu,
                    ram: worker.system_info?.ram || data.ram,
                    gpu: worker.system_info?.gpu || data.gpu,
                    executionStatus: nodeExecStatus || data.executionStatus,
                    onRoleSelect: handleRoleSelect,
                    onDelete: onDeleteNode
                }
            };
        }));
    }, [workers, executionData, setNodes, handleRoleSelect, onDeleteNode]);

    const onRunFactory = async () => {
        if (nodes.length === 0) return alert("Canvas is empty");
        const missingRoles = nodes.some(n => !(n.data as Record<string, unknown>).activeRole);
        if (missingRoles) return alert("Assign roles to all nodes before starting.");

        setIsRunning(true);
        try {
            const res = await fetch('/api/admin/run-blueprint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nodes, edges })
            });
            const data = await res.json();
            if (data.success) {
                setExecutionId(data.execution_id);
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch {
            alert("Failed to start execution");
        } finally {
            setIsRunning(false);
        }
    };

    const onConnect = useCallback((connection: Connection) => {
        setEdges(eds => addEdge({
            ...connection,
            type: 'smoothstep',
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
            style: { stroke: '#6366f1', strokeWidth: 2, filter: 'drop-shadow(0 0 6px #6366f1)' }
        }, eds));
    }, [setEdges]);

    const onDrop = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        const workerId = event.dataTransfer.getData('application/nf-worker-id');
        if (!workerId || !rfInstance || !reactFlowWrapper.current) return;

        const bounds = reactFlowWrapper.current.getBoundingClientRect();
        const position = rfInstance.screenToFlowPosition({
            x: event.clientX - bounds.left,
            y: event.clientY - bounds.top,
        });

        const worker = workers[workerId];
        if (!worker) return;

        const instanceId = `node-${workerId}-${Date.now()}`;
        const newNode: Node = {
            id: instanceId,
            type: 'workerNode',
            position,
            data: {
                workerId: workerId,
                label: worker.desktop_name,
                cpu: worker.system_info?.cpu || 'Unknown',
                ram: worker.system_info?.ram || 'Unknown',
                gpu: worker.system_info?.gpu || 'Unknown',
                activeRole: null,
                unavailableRoles: [],
                last_seen: worker.last_seen,
                onRoleSelect: handleRoleSelect,
                onDelete: onDeleteNode
            } as WorkerNodeData,
        };

        setNodes(nds => [...nds, newNode]);
    }, [rfInstance, workers, setNodes, handleRoleSelect, onDeleteNode]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const onNodeClick = (_: any, node: Node) => {
        setSelectedNodeId(node.id);
    };

    return (
        <div className="flex h-screen bg-[#06060c] overflow-hidden text-white">
            {/* Sidebar */}
            <motion.div
                initial={{ x: -300, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="w-72 flex-shrink-0 flex flex-col border-r border-white/5 bg-[#0a0a0f]/80 backdrop-blur-3xl z-10"
            >
                {/* Sidebar Header */}
                <div className="p-5 border-b border-white/5 space-y-4">
                    <Link href="/" className="group flex items-center gap-2 text-gray-500 hover:text-blue-400 font-bold transition-all text-[10px] uppercase tracking-widest">
                        <ArrowLeft className="w-3 h-3 group-hover:-translate-x-1 transition-transform" />
                        Dashboard
                    </Link>
                    <div>
                        <h2 className="text-xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-white/40">Blueprint</h2>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="h-[2px] w-8 bg-blue-600 rounded-full" />
                            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-[0.2em]">Pipeline Editor</p>
                        </div>
                    </div>
                </div>

                {/* Controls Area */}
                <div className="p-4 space-y-3 bg-white/[0.02] border-b border-white/5">
                    <button 
                        onClick={onRunFactory}
                        disabled={isRunning || nodes.length === 0}
                        className={`
                            w-full py-4 rounded-xl flex items-center justify-center gap-3 transition-all relative overflow-hidden group
                            ${isRunning 
                                ? 'bg-blue-600/50 cursor-not-allowed border-blue-500/50' 
                                : 'bg-gradient-to-br from-blue-600 to-indigo-700 hover:shadow-[0_0_30px_rgba(37,99,235,0.4)] border-blue-400/20 active:scale-95'
                            }
                            border font-black uppercase tracking-[0.15em] text-sm
                        `}
                    >
                        {isRunning ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5 group-hover:-translate-y-1 transition-transform" />}
                        <span>{isRunning ? 'Launching...' : 'Run Factory'}</span>
                        {!isRunning && <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />}
                    </button>
                    
                    <button onClick={() => { setNodes([]); setEdges([]); setSelectedNodeId(null); setExecutionId(null); }} className="w-full py-2.5 rounded-lg border border-white/5 text-gray-400 text-[10px] font-bold uppercase hover:bg-red-500/10 hover:text-red-400 transition-all flex items-center justify-center gap-2">
                        <Trash2 className="w-3 h-3" /> Clear Factory
                    </button>
                </div>

                {/* Worker List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {Object.entries(workers).map(([id, worker]) => {
                        const isOnline = Date.now() - worker.last_seen < 30000;
                        return (
                            <div key={id} draggable onDragStart={e => { e.dataTransfer.setData('application/nf-worker-id', id); setDraggingWorkerId(id); }} onDragEnd={() => setDraggingWorkerId(null)} className="p-4 rounded-2xl border border-white/5 bg-white/[0.03] hover:border-white/20 transition-all cursor-grab group">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2.5">
                                        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500 box-shadow-[0_0_10px_#10b981]' : 'bg-red-500'}`} />
                                        <span className="font-black text-xs uppercase tracking-wider">{worker.desktop_name}</span>
                                    </div>
                                    <MonitorSmartphone className="w-3 h-3 text-white/20" />
                                </div>
                                <div className="space-y-1.5 opacity-60 text-[9px] font-bold text-gray-400">
                                    <div className="flex items-center gap-2"><Cpu className="w-3 h-3 text-blue-500/60" /> {worker.system_info?.cpu}</div>
                                    <div className="flex items-center gap-2"><Play className="w-3 h-3 text-orange-500/60" /> {worker.system_info?.gpu}</div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </motion.div>

            {/* Canvas Area */}
            <div ref={reactFlowWrapper} className="flex-1 relative bg-[radial-gradient(circle_at_center,_#0a0a1f_0%,_#06060c_100%)]">
                {/* Status Bar */}
                <AnimatePresence>
                    {executionId && (
                        <motion.div initial={{ y: -50 }} animate={{ y: 0 }} exit={{ y: -50 }} className="absolute top-6 left-1/2 -translate-x-1/2 z-20 px-6 py-3 rounded-full bg-blue-600/90 backdrop-blur-xl border border-blue-400/30 flex items-center gap-4 shadow-2xl">
                            <Rocket className="w-4 h-4 text-white" />
                            <span className="text-xs font-black uppercase tracking-widest text-white">{executionData?.status || 'RUNNING'}</span>
                            <div className="w-[2px] h-3 bg-white/20" />
                            <span className="text-[10px] font-mono font-bold text-blue-100">{executionId}</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                <ReactFlow
                    nodes={nodes} edges={edges}
                    onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
                    onInit={setRfInstance} onDrop={onDrop} onDragOver={e => e.preventDefault()}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes} fitView proOptions={{ hideAttribution: true }}
                >
                    <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#ffffff05" />
                    <Controls className="!bg-black/90 !border-white/5 !rounded-2xl shadow-2xl" />
                </ReactFlow>

                {/* Live Log Overlay */}
                <AnimatePresence>
                    {selectedNodeId && (
                        <motion.div 
                            initial={{ x: 400 }} animate={{ x: 0 }} exit={{ x: 400 }}
                            className="absolute right-6 top-6 bottom-6 w-96 z-30 flex flex-col"
                        >
                            <div className="flex-1 flex flex-col relative">
                                <button 
                                    onClick={() => setSelectedNodeId(null)}
                                    className="absolute -left-3 top-10 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 flex items-center justify-center z-10 backdrop-blur-md"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                                <LiveLogViewer 
                                    executionId={executionId || 'Global'} 
                                    nodeId={selectedNodeId} 
                                />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
