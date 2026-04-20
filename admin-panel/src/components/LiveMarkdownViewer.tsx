'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText } from 'lucide-react';

export default function LiveMarkdownViewer({ content, title = "AGENTS.md" }: { content: string, title?: string }) {
    return (
        <div className="flex flex-col h-full bg-black/40 backdrop-blur-md border border-white/5 rounded-2xl overflow-hidden shadow-2xl transition-all duration-500 hover:border-white/10">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/5">
                <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-white/50">{title}</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
                    <span className="text-[8px] font-bold text-purple-500 uppercase tracking-wider">Syncing</span>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-white/10">
                <div className="prose prose-invert prose-sm max-w-none 
                    prose-pre:bg-black/60 prose-pre:border prose-pre:border-white/10 prose-pre:shadow-inner
                    prose-headings:text-white/90 prose-headings:font-semibold tracking-wide
                    prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
                    prose-strong:text-emerald-400 prose-code:text-amber-200 prose-code:bg-amber-500/10 prose-code:px-1 prose-code:rounded">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {content || "*Awaiting quantum data stream...*"}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
