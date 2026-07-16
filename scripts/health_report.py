import subprocess
import os
import sqlite3
import json

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception:
        return "N/A"

def get_service_status(service_name):
    out = run_cmd(f"systemctl is-active {service_name}")
    if out == "active":
        return "🟢 running"
    return "🔴 stopped/failed"

def main():
    print("FUNPAY HUB STATUS\n")
    print(f"Core:\n{get_service_status('funpayhub-core')}\n")
    print(f"Bot:\n{get_service_status('funpayhub')}\n")
    
    # Memory
    free_out = run_cmd("free -m | grep Mem")
    parts = free_out.split()
    total_mem = parts[1] if len(parts) > 1 else "?"
    used_mem = parts[2] if len(parts) > 2 else "?"
    print(f"Memory:\n{used_mem}MB / {total_mem}MB\n")
    
    # Disk
    df_out = run_cmd("df -h / | awk 'NR==2 {print $5}'")
    print(f"Disk:\n{df_out}\n")
    
    # Database Size
    db_path = "/opt/funpayhub/source/funpayhub.db"
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) / 1024
        print(f"Database:\nOK ({size_kb:.1f} KB)\n")
    else:
        print("Database:\nNot Found\n")
        
    # Directories sizes
    data_size = run_cmd("du -sh /opt/funpayhub/source/data 2>/dev/null | cut -f1") or "0"
    logs_size = run_cmd("du -sh /opt/funpayhub/source/logs 2>/dev/null | cut -f1") or "0"
    db_dir_size = run_cmd("du -sh /opt/funpayhub/source/backups 2>/dev/null | cut -f1") or "0"
    
    print("Sizes:")
    print(f"  data/: {data_size}")
    print(f"  logs/: {logs_size}")
    print(f"  backups/: {db_dir_size}\n")
    
    print("Последние ошибки (journalctl):")
    errs = run_cmd("journalctl -p err -n 10 --no-pager")
    print(errs if errs and errs != "N/A" else "Ошибок нет.")

if __name__ == "__main__":
    main()
