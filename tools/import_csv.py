import csv
from db_manager import DBManager

def run_import():
    db = DBManager()
    db.initialize()
    
    words_to_insert = []
    try:
        with open('cet4_words.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                words_to_insert.append({
                    "word": row['word'],
                    "phonetic": row['phonetic'],
                    "definition": row['definition']
                })
        
        inserted = db.upsert_words(words_to_insert)
        print(f"✅ 成功从 CSV 导入了 {inserted} 个生词到 SQLite 数据库！")
    except FileNotFoundError:
        print("❌ 找不到 cet4_words.csv 文件，请检查拼写。")

if __name__ == "__main__":
    run_import()