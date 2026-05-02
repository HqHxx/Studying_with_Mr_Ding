import json
import re

def update_main():
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update load_api_config
    old_load_pattern = r'def load_api_config\(\) -> dict:\n\s+"""[^\n]+"""\n\s+if not API_CONFIG_PATH.exists\(\):\n\s+return \{\}\n\s+try:\n\s+return json\.loads\(API_CONFIG_PATH\.read_text\(encoding="utf-8"\)\)\n\s+except \(OSError, json\.JSONDecodeError\):\n\s+return \{\}'
    
    new_load = '''def load_api_config() -> dict:
    """读取多配置 API 文件。"""
    if not API_CONFIG_PATH.exists():
        return {"profiles": {}, "last_used": ""}
    try:
        data = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        if "profiles" not in data:
            data = {"profiles": {"默认配置": data}, "last_used": "默认配置"}
            API_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}, "last_used": ""}'''
        
    content = re.sub(old_load_pattern, new_load, content)

    # 2. Remove old save_api_config because we will handle it in the class methods directly
    old_save_pattern = r'def save_api_config\(.*?\) -> None:\n(?:.|\n)*?except OSError:\n\s+pass\n'
    content = re.sub(old_save_pattern, '', content)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_main()