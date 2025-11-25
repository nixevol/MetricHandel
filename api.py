from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional, List
from database import DatabaseManager
from data_processor import process_config, process_multiple_configs, DataProcessor
import uvicorn
import os
import glob
from pathlib import Path
import json
import asyncio
import threading
import time
import uuid
import pandas as pd
import io

app = FastAPI(title="MetricHandel API", version="1.0.0")
db = DatabaseManager()

# 任务状态存储
task_status = {}

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """返回主页"""
    return FileResponse("static/index.html")

@app.get("/api/tables")
async def get_tables():
    """获取所有表名"""
    try:
        tables = db.get_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables/{table_name}/columns")
async def get_table_columns(table_name: str):
    """获取表的列名"""
    try:
        columns = db.get_table_columns(table_name)
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search_field: Optional[str] = None,
    search_value: Optional[str] = None
):
    """获取表数据（分页）"""
    try:
        result = db.get_table_data(table_name, page, page_size, search_field, search_value)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tables/{table_name}/data")
async def clear_table_data(table_name: str):
    """清空表数据"""
    try:
        affected_rows = db.clear_table(table_name)
        return {"message": f"已清空表 {table_name}", "affected_rows": affected_rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables/{table_name}/count")
async def get_table_count(table_name: str):
    """获取表记录数"""
    try:
        count = db.get_table_count(table_name)
        return {"table": table_name, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def get_models():
    """获取所有模型配置文件"""
    try:
        models_dir = Path("./Models")
        if not models_dir.exists():
            return {"models": []}
        
        models = []
        for json_file in models_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            models.append({
                "name": json_file.stem,
                "path": str(json_file),
                "file_pattern": config.get("File", {}).get("Path", ""),
                "table": config.get("Export", {}).get("Table", "")
            })
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def execute_models_task(task_id: str, model_paths: List[str]):
    """后台执行模型配置的任务"""
    try:
        task_status[task_id] = {
            "status": "running",
            "progress": 0,
            "total": len(model_paths),
            "current": "",
            "results": {},
            "error": None,
            "start_time": time.time()
        }
        
        results = {}
        for i, model_path in enumerate(model_paths):
            task_status[task_id]["current"] = f"正在处理: {Path(model_path).name}"
            task_status[task_id]["progress"] = i
            
            # 处理单个配置文件
            result = process_config(model_path)
            results[model_path] = result
            
            task_status[task_id]["results"] = results
        
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["progress"] = len(model_paths)
        task_status[task_id]["current"] = "执行完成"
        task_status[task_id]["end_time"] = time.time()
        
    except Exception as e:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["end_time"] = time.time()

@app.post("/api/models/execute")
async def execute_models(model_paths: List[str]):
    """异步执行选中的模型配置"""
    try:
        task_id = str(uuid.uuid4())
        
        # 在后台线程中执行任务
        thread = threading.Thread(target=execute_models_task, args=(task_id, model_paths))
        thread.daemon = True
        thread.start()
        
        return {"task_id": task_id, "message": "任务已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/execute/{task_id}")
async def get_task_status(task_id: str):
    """获取任务执行状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    status = task_status[task_id].copy()
    
    # 计算执行时间
    if "start_time" in status:
        if status["status"] == "running":
            status["elapsed_time"] = time.time() - status["start_time"]
        elif "end_time" in status:
            status["elapsed_time"] = status["end_time"] - status["start_time"]
    
    return status

@app.get("/api/tables/{table_name}/download")
async def download_table_data(
    table_name: str,
    format: str = Query(..., pattern="^(csv|xlsx)$"),
    search_field: Optional[str] = None,
    search_value: Optional[str] = None
):
    """下载表数据为CSV或Excel格式"""
    try:
        # 获取所有数据（不分页）
        result = db.get_table_data(table_name, page=1, page_size=999999, 
                                 search_field=search_field, search_value=search_value)
        
        if not result['data']:
            raise HTTPException(status_code=404, detail="没有数据可下载")
        
        # 转换为DataFrame
        df = pd.DataFrame(result['data'])
        
        # 生成文件名
        import re
        from urllib.parse import quote
        
        # 创建时间戳
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            # 生成CSV
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')  # 使用utf-8-sig支持中文
            output.seek(0)
            
            # 使用URL编码处理中文文件名
            filename_encoded = quote(f"{table_name}_{timestamp}.csv".encode('utf-8'))
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
                }
            )
        
        elif format == 'xlsx':
            # 生成Excel
            output = io.BytesIO()
            # Excel sheet名称处理（移除特殊字符，限制长度）
            safe_sheet_name = re.sub(r'[^\w\u4e00-\u9fff\-_\.]', '_', table_name)[:31]
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            output.seek(0)
            
            # 使用URL编码处理中文文件名
            filename_encoded = quote(f"{table_name}_{timestamp}.xlsx".encode('utf-8'))
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
async def get_data_files():
    """获取Data目录下的文件列表"""
    try:
        data_dir = Path("./Data")
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            return {"files": []}
        
        files = []
        for file_path in data_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件到Data目录"""
    try:
        data_dir = Path("./Data")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查文件类型
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。仅支持: {', '.join(allowed_extensions)}"
            )
        
        # 读取文件内容（不限制大小，由操作系统和磁盘空间决定）
        content = await file.read()
        
        # 处理文件名冲突
        file_path = data_dir / file.filename
        counter = 1
        original_stem = file_path.stem
        
        while file_path.exists():
            file_path = data_dir / f"{original_stem}_{counter}{file_extension}"
            counter += 1
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "message": f"文件 {file_path.name} 上传成功",
            "filename": file_path.name,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{filename}/download")
async def download_file(filename: str):
    """下载Data目录中的文件"""
    try:
        file_path = Path("./Data") / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(file_path, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """删除Data目录中的文件"""
    try:
        file_path = Path("./Data") / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        file_path.unlink()
        return {"message": f"文件 {filename} 删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
