'use client';

import React, { useState, useEffect } from 'react';
import FocusPipelineGraph, { PipelineNode } from '@/components/FocusPipelineGraph';
import LiveLogViewer from '@/components/LiveLogViewer';
import LiveMarkdownViewer from '@/components/LiveMarkdownViewer';
import { Network } from 'lucide-react';

const mockAgentsMd = `
# AGENTS.md
> 🟢 **STATUS**: Architect Initialized. Building Matrix Layout...

## Project Overview
This is a secure, quantum-encrypted REST API for the Neural Forge Matrix environment.
All connections must be isolated and scanned for structural vulnerabilities.

## Build & Test Commands
- Dev: \`npm run dev\`
- Test: \`pytest --cov=src\`

## Code Standards
- Strict Zero-Trust policy
- Hardcoded secrets will result in immediate pipeline destruction.
- \`pydantic\` strictly required for data validation.

> 🛑 **Attention Downstream Nodes**: 
> Failure to comply with tests triggers an automatic 
> Amber Repair Sequence. Do not hallucinate.
`;

export default function LiveTaskPage() {
    // Mock simulation state
    const [nodes, setNodes] = useState<PipelineNode[]>([
        { id: '1', label: 'Architect', status: 'success' },
        { id: '2', label: 'Builder', status: 'running' },
        { id: '3', label: 'Gatekeeper', status: 'pending' },
        { id: '4', label: 'Red Team', status: 'pending' },
        { id: '5', label: 'Execute', status: 'pending' },
    ]);

    const [executionId, setExecutionId] = useState('demo-exec-123');
    const [activeNodeId, setActiveNodeId] = useState('demo-node-id');
    const [markdownContent, setMarkdownContent] = useState('');

    useEffect(() => {
        // Typing effect for the AGENTS.md blueprint to simulate agent thinking
        let i = 0;
        const interval = setInterval(() => {
            setMarkdownContent(mockAgentsMd.substring(0, i));
            i += 3;
            if (i > mockAgentsMd.length) clearInterval(interval);
        }, 15);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        // Simulate pipeline progression & error handling
        const timer1 = setTimeout(() => {
            setNodes(prev => [
                prev[0],
                { ...prev[1], status: 'repairing' }, // Self healing simulation
                prev[2], prev[3], prev[4]
            ]);
        }, 6000);

        const timer2 = setTimeout(() => {
            setNodes(prev => [
                prev[0],
                { ...prev[1], status: 'success' },
                { ...prev[2], status: 'running' },
                prev[3], prev[4]
            ]);
            setActiveNodeId('gatekeeper-node'); // Switch logs
        }, 12000);

        return () => { clearTimeout(timer1); clearTimeout(timer2); };
    }, []);

    return (
        <div className="min-h-screen bg-[#050505] text-white flex flex-col overflow-hidden font-sans selection:bg-cyan-500/30">
            {/* Ambient Background Glow */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-emerald-900/20 blur-[150px] rounded-full" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan-900/30 blur-[150px] rounded-full" />
                <div className="absolute top-[40%] left-[40%] w-[20%] h-[20%] bg-purple-900/20 blur-[120px] rounded-full" />
                {/* CSS Noise Overlay */}
                <div className="absolute inset-0 opacity-[0.03] mix-blend-overlay" style={{backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")'}}></div>
            </div>

            <div className="relative z-10 flex-1 flex flex-col p-4 md:p-6 lg:p-8 gap-6 h-screen">
                
                {/* Header / Pipeline Module */}
                <div className="w-full bg-black/50 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 shadow-2xl relative overflow-hidden group transition-all duration-500 hover:border-white/20">
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                    
                    <div className="flex items-center gap-4 mb-2">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-emerald-500/10 flex items-center justify-center border border-cyan-500/30 shadow-[0_0_15px_rgba(34,211,238,0.2)]">
                            <Network className="w-6 h-6 text-cyan-400" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold tracking-tight text-white/90 drop-shadow-sm">Live Focus View</h1>
                            <p className="text-[10px] text-white/40 tracking-[0.3em] uppercase font-black mt-1">
                                Cipher Pipeline // <span className="text-cyan-400 animate-pulse">UUID-{executionId.split('-')[0]}</span>
                            </p>
                        </div>
                    </div>

                    <FocusPipelineGraph nodes={nodes} />
                </div>

                {/* Workspace Modules (Terminal & Markdown) */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
                    {/* Left: Live Terminal (LiveLogViewer) */}
                    <div className="h-full flex flex-col min-h-0">
                        <LiveLogViewer executionId={executionId} nodeId={activeNodeId} />
                    </div>

                    {/* Right: Live Markdown */}
                    <div className="h-full flex flex-col min-h-0 relative group">
                        {/* Glow effect for Markdown panel */}
                        <div className="absolute -inset-1 bg-gradient-to-b from-purple-500/20 to-transparent blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                        <div className="relative h-full">
                            <LiveMarkdownViewer content={markdownContent} title="Architect Blueprint (AGENTS.md)" />
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
