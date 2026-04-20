import { Agent, ToolRegistry, ToolExecutor, registerBuiltInTools } from '@jackchen_me/open-multi-agent';
import axios from 'axios';
import si from 'systeminformation';
import os from 'os';
import { v4 as uuidv4 } from 'uuid';
import dotenv from 'dotenv';

dotenv.config();

/**
 * Neural Forge — Node.js System Worker
 * This worker integrates the 'open-multi-agent' library with the Neural Forge Backend.
 */

const SERVER_URL = process.env.NERVE_CENTER_URL || 'http://localhost:8000';
const POLL_INTERVAL = 5000;
const HEARTBEAT_INTERVAL = 10000;
const NODE_ID = `node-js-${uuidv4().split('-')[0]}`;

async function registerNode() {
    const cpu = await si.cpu();
    const mem = await si.mem();
    
    const payload = {
        desktop_name: os.hostname(),
        mac_address: os.networkInterfaces()['Ethernet']?.[0]?.mac || `node-${NODE_ID}`,
        system_info: {
            cpu: cpu.brand || 'Unknown CPU',
            ram: `${Math.round(mem.total / (1024 ** 3))} GB`,
            gpu: 'N/A (Node Worker)'
        },
        capabilities: {
            node_runtime: 'Node.js',
            agent_library: '@jackchen_me/open-multi-agent',
            tools: ['file_write', 'bash'],
            status: 'ready'
        }
    };

    try {
        console.log(`[*] Registering Node.js Worker at ${SERVER_URL}...`);
        await axios.post(`${SERVER_URL}/api/nodes/register`, payload);
        console.log(`[🚀] Node Registered: ${NODE_ID}`);
    } catch (e) {
        console.error(`[!] Registration failed: ${e.message}`);
    }
}

async function sendHeartbeat() {
    try {
        const load = await si.currentLoad();
        const mem = await si.mem();
        
        const payload = {
            cpu_percent: load.currentLoad,
            ram_percent: (mem.active / mem.total) * 100,
            status: 'online',
            current_task: null // Placeholder for Phase 2
        };

        await axios.post(`${SERVER_URL}/api/nodes/heartbeat/${os.hostname()}`, payload);
    } catch (e) {
        // Silently fail on heartbeat
    }
}

async function pollTask() {
    try {
        const payload = { node_id: os.hostname() };
        const resp = await axios.post(`${SERVER_URL}/api/tasks/poll`, payload);
        const data = resp.data;
        
        if (data.success && data.task) {
            console.log(`[📦] Task Received: ${data.task.title}`);
            await executeTask(data.task);
        }
    } catch (e) {
        // Silently fail on poll
    }
}

async function executeTask(task) {
    const registry = new ToolRegistry();
    registerBuiltInTools(registry);
    const executor = new ToolExecutor(registry);

    const agent = new Agent(
        { 
            name: 'system-worker-js', 
            model: process.env.OLLAMA_MODEL || 'mistral:latest',
            provider: 'openai',
            tools: ['file_write', 'bash'] 
        },
        registry,
        executor
    );

    try {
        console.log(`[*] [AGENT] Executing: ${task.description}`);
        
        // Use the agent to run the task
        const result = await agent.run(task.description);
        
        // Report completion
        await axios.post(`${SERVER_URL}/api/tasks/complete/${task.task_id}`, {
            status: 'completed',
            result: { 
                output: result.output,
                engine: 'node-js-agent'
            }
        });
        
        console.log(`[✅] Task Completed: ${task.task_id}`);
    } catch (e) {
        console.error(`[❌] Task Execution Error: ${e.message}`);
        await axios.post(`${SERVER_URL}/api/tasks/complete/${task.task_id}`, {
            status: 'failed',
            result: { error: e.message }
        });
    }
}

async function start() {
    console.log("-----------------------------------------");
    console.log("🚀 NEURAL FORGE | NODE.JS CORE WORKER");
    console.log("-----------------------------------------");
    
    // Check Ollama connectivity first
    try {
        await axios.get('http://localhost:11434/api/tags');
        console.log("[✔] Ollama is online.");
    } catch (e) {
        console.error("[!] WARN: Local Ollama appears to be offline.");
    }

    await registerNode();
    
    // Heartbeat every 10s
    setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
    
    // Polling every 5s
    setInterval(pollTask, POLL_INTERVAL);
    
    console.log(`\n[📡] Node.js Worker is polling for tasks from ${SERVER_URL}...`);
}

start();