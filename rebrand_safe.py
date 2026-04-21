import os
import re

targets = {
    '피지수': 'Physis',
    'Piji-soo': 'Physis',
    'piji-soo': 'physis'
}

files = [
    'brain.md', 'README.md', 'implementation-roadmap.md', 
    'CONSTITUTION.md', 'architecture-overview.md', 'brain-layer-reference.md',
    'cost-optimization-guide.md', 'judgment.md', 'technical-guidelines.md',
    'mcp_server.py', 'run.py', 'requirements.txt'
]

def rebrand(filepath):
    if not os.path.exists(filepath):
        return
    
    content = None
    applied_enc = None
    for enc in ['utf-8', 'cp949', 'euc-kr', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
                applied_enc = enc
                break
        except Exception:
            continue
            
    if content is None:
        print(f"Could not read {filepath}")
        return
        
    pattern = '|'.join(re.escape(k) for k in targets.keys())
    new_content = re.sub(pattern, lambda m: targets[m.group(0)], content)
    
    if new_content != content:
        with open(filepath, 'w', encoding=applied_enc) as f:
            f.write(new_content)
        print(f"Rebranded {filepath} ({applied_enc})")
    else:
        print(f"No changes in {filepath}")

if __name__ == "__main__":
    for f in files:
        rebrand(f)
