import sqlite3
conn=sqlite3.connect('学习进度词库.db')
print([row[0] for row in conn.cursor().execute("SELECT word FROM words WHERE word IN ('of', 'is', 'the', 'a')")])
