import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import math


class DatabaseManager:
    def __init__(self, db_path: str = "./DB/4G.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    
    def get_table_data(self, table_name: str, page: int = 1, page_size: int = 50, 
                      search_field: Optional[str] = None, search_value: Optional[str] = None) -> Dict[str, Any]:
        """分页获取表数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        where_clause = ""
        params = []
        if search_field and search_value:
            where_clause = f" WHERE [{search_field}] LIKE ?"
            params.append(f"%{search_value}%")
        
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) FROM [{table_name}]{where_clause}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = math.ceil(total_count / page_size)
        
        # 获取数据
        data_sql = f"SELECT * FROM [{table_name}]{where_clause} LIMIT ? OFFSET ?"
        cursor.execute(data_sql, params + [page_size, offset])
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return {
            "data": data,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "columns": columns
        }
    
    def clear_table(self, table_name: str) -> int:
        """清空表数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM [{table_name}]")
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return affected_rows
    
    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]
        conn.close()
        return count
