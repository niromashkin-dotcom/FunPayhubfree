import os
import ast
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_cluster(file_path):
    parts = Path(file_path).parts
    if 'runtime' in parts:
        if 'messages' in parts: return 'CCE'
        if 'database' in parts: return 'Database'
        if 'ai_team' in parts or 'automation' in parts: return 'AI'
        if 'order_flow.py' in parts or 'order_tracker.py' in parts: return 'Order Engine'
        return 'Core Runtime'
    if 'plugins' in parts: return 'Plugins'
    if 'web' in parts: return 'Web API'
    if 'bot' in parts: return 'Bot'
    if 'FunPayAPI' in parts: return 'FunPayAPI'
    if 'security' in parts: return 'Security'
    return 'Other'

def analyze_file(file_path, root_dir):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
    except Exception as e:
        logging.error(f"Error parsing {file_path}: {e}")
        return None

    rel_path = os.path.relpath(file_path, root_dir).replace('\\', '/')
    module_name = rel_path.replace('.py', '').replace('/', '.')
    
    analysis = {
        'module': module_name,
        'cluster': get_cluster(rel_path),
        'file_path': rel_path,
        'classes': [],
        'functions': [],
        'imports': [],
        'depends_on': []
    }

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            analysis['classes'].append({
                'name': node.name,
                'methods': methods
            })
        elif isinstance(node, ast.FunctionDef):
            analysis['functions'].append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                analysis['imports'].append(alias.name)
                root_module = alias.name.split('.')[0]
                if root_module in ['runtime', 'plugins', 'web', 'bot', 'FunPayAPI', 'security', 'Utils']:
                    analysis['depends_on'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                analysis['imports'].append(node.module)
                root_module = node.module.split('.')[0]
                if root_module in ['runtime', 'plugins', 'web', 'bot', 'FunPayAPI', 'security', 'Utils']:
                    analysis['depends_on'].append(node.module)

    analysis['depends_on'] = list(set(analysis['depends_on']))
    return analysis

def build_map(root_dir):
    map_data = []
    scan_dirs = ['runtime', 'plugins', 'web', 'bot', 'FunPayAPI', 'security', 'Utils', '.']
    
    for dir_name in scan_dirs:
        dir_path = os.path.join(root_dir, dir_name)
        if not os.path.exists(dir_path):
            continue
            
        if dir_name == '.':
            # Only top-level root files like funpayhub_main.py, hub_bootstrap.py
            for file in os.listdir(dir_path):
                if file.endswith('.py') and os.path.isfile(os.path.join(dir_path, file)):
                    res = analyze_file(os.path.join(dir_path, file), root_dir)
                    if res: map_data.append(res)
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py'):
                    res = analyze_file(os.path.join(root, file), root_dir)
                    if res:
                        map_data.append(res)
                        
    return map_data

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging.info(f"Analyzing project in {root_dir}")
    
    project_map = build_map(root_dir)
    
    # Calculate used_by
    for module in project_map:
        module['used_by'] = []
        for other_module in project_map:
            if module['module'] == other_module['module']: continue
            for dep in other_module['depends_on']:
                if dep == module['module'] or module['module'].startswith(dep + '.'):
                    module['used_by'].append(other_module['module'])
                    
        module['used_by'] = list(set(module['used_by']))
    
    out_dir = os.path.join(root_dir, 'docs', 'generated')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'project_map.json')
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(project_map, f, indent=2, ensure_ascii=False)
        
    # Also save as a JS file for the local HTML site to bypass CORS on file://
    docs_site_dir = os.path.join(root_dir, 'docs-site')
    os.makedirs(docs_site_dir, exist_ok=True)
    js_out_file = os.path.join(docs_site_dir, 'project_map.js')
    with open(js_out_file, 'w', encoding='utf-8') as f:
        f.write("window.projectMapData = ")
        json.dump(project_map, f, indent=2, ensure_ascii=False)
        f.write(";")
        
    logging.info(f"Project map generated at {out_file} with {len(project_map)} modules.")

if __name__ == '__main__':
    main()
