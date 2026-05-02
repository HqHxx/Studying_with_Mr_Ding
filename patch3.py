import traceback

def patch():
    with open('../../main.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open('../../main.py', 'w', encoding='utf-8') as f:
        for line in lines:
            if '批量生成遇到致命错误:' in line:
                f.write('            import traceback\n')
                f.write('            task_safe_log(f"批量生成遇到致命错误: {traceback.format_exc()}")\n')
            else:
                f.write(line)

patch()