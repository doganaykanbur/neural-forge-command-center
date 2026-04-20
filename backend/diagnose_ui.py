import uiautomation as auto
import time

def diagnose_ui():
    print("Searching for Antigravity window...")
    # Antigravity is Electron-based, its main window class is usually Chrome_WidgetWin_1
    win = auto.WindowControl(searchDepth=1, ClassName='Chrome_WidgetWin_1')
    
    if not win.Exists(0):
        print("[FAIL] Antigravity window not found.")
        return

    print(f"[SUCCESS] Window found: {win.Name}")
    win.SetActive()
    
    print("\nScanning for buttons (this may take a moment)...")
    # We look for buttons that likely belong to the side panel or terminal
    buttons = win.ButtonControl(searchDepth=15) # Deep search for sidepanel buttons
    
    found_any = False
    for btn in win.ButtonControl().GetChildren():
        name = btn.Name
        auto_id = btn.AutomationId
        if name or auto_id:
            print(f"[*] Button: Name='{name}', ID='{auto_id}'")
            found_any = True
            
    if not found_any:
        print("[!] No direct buttons found. Scanning all controls for 'Accept' or 'Run'...")
        # Fallback recursive search
        for control in win.GetChildren():
            if "Accept" in control.Name or "Run" in control.Name or "Allow" in control.Name:
                print(f"[FOUND] {control.ControlTypeName}: Name='{control.Name}', ID='{control.AutomationId}'")

if __name__ == "__main__":
    diagnose_ui()
