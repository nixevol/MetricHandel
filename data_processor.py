import json
import glob
import sqlite3
from pathlib import Path
import pandas as pd
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


# noinspection PyMethodMayBeStatic
class DataProcessor:
    def __init__(self, config_path, db_path):
        """
        初始化数据处理器
        
        Args:
            config_path: JSON配置文件路径
            db_path: 数据库文件路径（从config.ini读取）
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.db_path = db_path  # 从config.ini读取，不再从JSON配置读取
        self.table_name = self.config['Export']['Table']
        self.config_path = config_path
    
    def validate(self):
        """
        验证配置文件的有效性
        
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        try:
            # 检查必要的配置项
            if 'Table' not in self.config:
                return False, "配置文件中缺少 'Table' 配置项"
            
            if 'FieldRow' not in self.config['Table']:
                return False, "配置文件中缺少 'Table.FieldRow' 配置项"
            
            if 'StartRow' not in self.config['Table']:
                return False, "配置文件中缺少 'Table.StartRow' 配置项"
            
            field_row = self.config['Table']['FieldRow']
            start_row = self.config['Table']['StartRow']
            
            # 检查FieldRow和StartRow是否相等
            if field_row == start_row:
                return False, f"FieldRow ({field_row}) 和 StartRow ({start_row}) 不能相等，这会导致无法正确读取数据"
            
            # 检查StartRow必须大于FieldRow
            if start_row <= field_row:
                return False, f"StartRow ({start_row}) 必须大于 FieldRow ({field_row})"
            
            # 检查必要的配置项
            if 'File' not in self.config:
                return False, "配置文件中缺少 'File' 配置项"
            
            if 'Path' not in self.config['File']:
                return False, "配置文件中缺少 'File.Path' 配置项"
            
            if 'Export' not in self.config:
                return False, "配置文件中缺少 'Export' 配置项"
            
            if 'Table' not in self.config['Export']:
                return False, "配置文件中缺少 'Export.Table' 配置项"
            
            if 'Columns' not in self.config:
                return False, "配置文件中缺少 'Columns' 配置项"
            
            if not isinstance(self.config['Columns'], list) or len(self.config['Columns']) == 0:
                return False, "配置文件中 'Columns' 必须是非空数组"
            
            return True, ""
            
        except Exception as e:
            return False, f"验证配置文件时出错: {str(e)}"
        
    def process(self):
        """处理所有匹配的文件并导入数据库"""
        files = self._get_files()
        all_data = []
        processed_files = []  # 记录已处理的文件
        
        for file in files:
            data = self._read_file(file)
            if data is not None and not data.empty:
                all_data.append(data)
                processed_files.append(file)  # 记录成功处理的文件
        
        if all_data:
            merged_data = pd.concat(all_data, ignore_index=True)
            self._save_to_db(merged_data)
            
            # 如果配置了删除文件，在处理完数据后删除
            delete_after_process = self.config.get('File', {}).get('DeleteAfterProcess', False)
            if delete_after_process:
                self._delete_files(processed_files)
            
            return len(merged_data)
        return 0
    
    def _get_files(self):
        """根据通配符获取文件列表"""
        path_pattern = self.config['File']['Path']
        return glob.glob(path_pattern)
    
    def _read_file(self, file_path):
        """读取文件数据"""
        try:
            suffix = Path(file_path).suffix.lower()
            
            if suffix in ['.xlsx', '.xls']:
                return self._read_excel(file_path)
            elif suffix == '.csv':
                return self._read_csv(file_path)
            return None
        except Exception as e:
            # 文件读取失败，记录错误但不中断整个流程
            print(f"警告: 读取文件失败 {file_path}: {e}")
            return None
    
    def _read_excel(self, file_path):
        """读取Excel文件"""
        sheet_name = self.config['File'].get('SheetName', 0)
        field_row = self.config['Table']['FieldRow'] - 1
        start_row = self.config['Table']['StartRow'] - 1
        
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=field_row)
        # 当使用header=field_row时，DataFrame的索引0对应原始文件的field_row+1行
        # 如果StartRow=field_row+1，那么数据从DataFrame的索引0开始
        # 如果StartRow>field_row+1，那么数据从DataFrame的索引(start_row-field_row)开始
        df = df.iloc[start_row - field_row:]
        
        return self._map_columns(df)
    
    def _read_csv(self, file_path):
        """读取CSV文件"""
        field_row = self.config['Table']['FieldRow'] - 1
        start_row = self.config['Table']['StartRow'] - 1
        
        df = pd.read_csv(file_path, header=field_row)
        # 当使用header=field_row时，DataFrame的索引0对应原始文件的field_row+1行
        # 如果StartRow=field_row+1，那么数据从DataFrame的索引0开始
        # 如果StartRow>field_row+1，那么数据从DataFrame的索引(start_row-field_row)开始
        df = df.iloc[start_row - field_row:]
        
        return self._map_columns(df)
    
    def _map_columns(self, df):
        """映射字段并应用默认值"""
        mapped_data = {}
        
        for col_config in self.config['Columns']:
            field = col_config['Field']
            target = col_config['Target']
            default = col_config['DefaultValue']
            
            if field in df.columns:
                mapped_data[target] = df[field]
            else:
                mapped_data[target] = default
        
        return pd.DataFrame(mapped_data)
    
    def _save_to_db(self, df):
        """保存数据到SQLite数据库"""
        db_path = Path(self.db_path)
        db_dir = db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用上下文管理器管理数据库连接
        with sqlite3.connect(str(db_path)) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False)
            
            # 如果有"开始时间"字段，创建索引
            if '开始时间' in df.columns:
                index_name = f'idx_{self.table_name}_开始时间'
                try:
                    cursor = conn.cursor()
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {self.table_name} (开始时间)')
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
    
    def _delete_files(self, file_paths):
        """删除已处理的文件"""
        for file_path in file_paths:
            try:
                file_obj = Path(file_path)
                if file_obj.exists():
                    file_obj.unlink()
            except Exception as e:
                # 删除失败不影响主流程，只记录错误
                print(f"警告: 删除文件失败 {file_path}: {e}")


def validate_config(config_path, db_path):
    """
    验证单个配置文件
    
    Args:
        config_path: JSON配置文件路径
        db_path: 数据库文件路径（从config.ini读取，用于验证）
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    try:
        processor = DataProcessor(config_path, db_path)
        return processor.validate()
    except Exception as e:
        return False, f"验证配置文件失败: {str(e)}"


def process_config(config_path, db_path):
    """
    处理单个配置文件
    
    Args:
        config_path: JSON配置文件路径
        db_path: 数据库文件路径（从config.ini读取）
    """
    processor = DataProcessor(config_path, db_path)
    return processor.process()


def process_multiple_configs(config_paths, db_path):
    """
    处理多个配置文件
    
    Args:
        config_paths: JSON配置文件路径列表
        db_path: 数据库文件路径（从config.ini读取）
    """
    results = {}
    for config_path in config_paths:
        count = process_config(config_path, db_path)
        results[config_path] = count
    return results
