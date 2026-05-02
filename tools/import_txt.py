import os
from db_manager import DBManager

def run_import():
    db = DBManager()
    db.initialize()
    
    words_to_insert = []
    file_path = 'cet4_words.txt'
    
    try:
        # 读取 txt 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                # 这个仓库的 txt 是用 Tab 键 (\t) 分隔单词和释义的
                parts = line.split('\t')
                if len(parts) >= 2:
                    word = parts[0].strip()
                    definition = parts[1].strip()
                else:
                    word = parts[0].strip()
                    definition = "暂无释义"
                
                words_to_insert.append({
                    "word": word,
                    "phonetic": "",  # txt 版没有音标，留空即可
                    "definition": definition
                })
        
        # 批量插入数据库
        inserted = db.upsert_words(words_to_insert)
        print(f"✅ 太棒了！成功从 TXT 导入了 {inserted} 个四级词汇到数据库！")
        
    except FileNotFoundError:
        print(f"❌ 找不到 {file_path} 文件，请确认你下载的文件名拼写正确并放在了当前目录下。")
    except Exception as e:
        print(f"❌ 导入时发生错误：{e}")

if __name__ == "__main__":
    run_import()