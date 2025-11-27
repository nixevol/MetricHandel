import sqlite3
from typing import List, Dict, Any, Optional
import math


class DatabaseManager:
    def __init__(self, db_path: str = "./DB/Data.db"):
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
                      search_field: Optional[str] = None, search_value: Optional[str] = None,
                      filters: Optional[Dict[str, str]] = None, 
                      sort_field: Optional[str] = None, sort_order: Optional[str] = None) -> Dict[str, Any]:
        """分页获取表数据，支持多字段筛选和排序"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        # 兼容旧的单字段查询方式
        if search_field and search_value:
            where_conditions.append(f"[{search_field}] LIKE ?")
            params.append(f"%{search_value}%")
        
        # 支持多字段筛选（filters是字典，key为字段名，value是{rule: 'contains', value: 'xxx'}）
        if filters:
            for field, filter_obj in filters.items():
                if isinstance(filter_obj, dict):
                    rule = filter_obj.get('rule', 'contains')
                    value = filter_obj.get('value', '')
                else:
                    # 兼容旧格式（直接是字符串值）
                    rule = 'contains'
                    value = filter_obj
                
                if value and str(value).strip():
                    value_str = str(value).strip()
                    if rule == 'contains':
                        where_conditions.append(f"[{field}] LIKE ?")
                        params.append(f"%{value_str}%")
                    elif rule == 'equals':
                        where_conditions.append(f"[{field}] = ?")
                        params.append(value_str)
                    elif rule == 'starts':
                        where_conditions.append(f"[{field}] LIKE ?")
                        params.append(f"{value_str}%")
                    elif rule == 'ends':
                        where_conditions.append(f"[{field}] LIKE ?")
                        params.append(f"%{value_str}")
                    elif rule == 'greater':
                        # 尝试转换为数字进行比较
                        try:
                            num_value = float(value_str)
                            where_conditions.append(f"CAST([{field}] AS REAL) > ?")
                            params.append(num_value)
                        except ValueError:
                            # 如果不是数字，按字符串比较
                            where_conditions.append(f"[{field}] > ?")
                            params.append(value_str)
                    elif rule == 'greater_equal':
                        # 尝试转换为数字进行比较
                        try:
                            num_value = float(value_str)
                            where_conditions.append(f"CAST([{field}] AS REAL) >= ?")
                            params.append(num_value)
                        except ValueError:
                            # 如果不是数字，按字符串比较
                            where_conditions.append(f"[{field}] >= ?")
                            params.append(value_str)
                    elif rule == 'less':
                        # 尝试转换为数字进行比较
                        try:
                            num_value = float(value_str)
                            where_conditions.append(f"CAST([{field}] AS REAL) < ?")
                            params.append(num_value)
                        except ValueError:
                            # 如果不是数字，按字符串比较
                            where_conditions.append(f"[{field}] < ?")
                            params.append(value_str)
                    elif rule == 'less_equal':
                        # 尝试转换为数字进行比较
                        try:
                            num_value = float(value_str)
                            where_conditions.append(f"CAST([{field}] AS REAL) <= ?")
                            params.append(num_value)
                        except ValueError:
                            # 如果不是数字，按字符串比较
                            where_conditions.append(f"[{field}] <= ?")
                            params.append(value_str)
        
        where_clause = ""
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
        
        # 构建排序
        order_clause = ""
        if sort_field:
            order_by = f"[{sort_field}]"
            if sort_order and sort_order.upper() == "DESC":
                order_by += " DESC"
            else:
                order_by += " ASC"
            order_clause = f" ORDER BY {order_by}"
        
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) FROM [{table_name}]{where_clause}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = math.ceil(total_count / page_size)
        
        # 获取数据
        data_sql = f"SELECT * FROM [{table_name}]{where_clause}{order_clause} LIMIT ? OFFSET ?"
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
    
    def execute_sql_file(self, sql_file_path: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行SQL文件，支持参数替换"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 读取SQL文件
            sql = ""
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # 替换参数
            if params:
                for key, value in params.items():
                    sql = sql.replace(f'{{{{{key}}}}}', str(value))
            
            # 执行查询
            cursor.execute(sql)
            
            # 检查是否有结果
            if cursor.description is None:
                return []
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            return data
        except Exception as e:
            raise Exception(f"SQL执行错误: {str(e)}")
        finally:
            if conn:
                conn.close()