/**
 * Antigravity Autopilot Browser Driver v1.0
 * Run this in your browser console (F12 > Console) on the worker machine.
 * It connects to the local bridge (port 9888) and clicks buttons on your behalf.
 */

(function() {
    const BRIDGE_URL = "http://localhost:9888/status";
    const CLEAR_URL = "http://localhost:9888/clear";
    let isProcessing = false;

    console.log("%c[Neural Forge] Autopilot Driver Active 🛫", "color: #06b6d4; font-weight: bold; font-size: 14px;");

    async function pollBridge() {
        if (isProcessing) return;
        try {
            const resp = await fetch(BRIDGE_URL);
            const data = await resp.json();

            if (data.action === "click_accept") {
                await handleAction("Accept", "click_accept");
            } else if (data.action === "click_run") {
                await handleAction("Run", "click_run");
            } else if (data.action === "click_all") {
                // If the user wants a full sequence (Accept + Run)
                const buttons = ["Accept", "Run", "Deploy"];
                for (const b of buttons) {
                    await attemptClick(b);
                }
                await clearAction();
            }
        } catch (e) {
            // Bridge might be down, ignore
        }
    }

    async function handleAction(buttonText, actionName) {
        console.log(`[Autopilot] Instruction received: ${actionName}`);
        const clicked = await attemptClick(buttonText);
        if (clicked) {
            console.log(`[Autopilot] Success! Clicked: ${buttonText}`);
            await clearAction();
        }
    }

    async function attemptClick(text) {
        // Find buttons containing the text
        const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
        const target = buttons.find(b => b.innerText.includes(text) || b.textContent.includes(text));
        
        if (target) {
            target.click();
            return true;
        }
        return false;
    }

    async function clearAction() {
        try {
            await fetch(CLEAR_URL, { method: "POST" });
        } catch (e) {}
    }

    // High-frequency polling for responsiveness
    setInterval(pollBridge, 500);

})();
