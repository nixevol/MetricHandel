from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List
from contextlib import asynccontextmanager
from database import DatabaseManager
from data_processor import process_config
from pathlib import Path
from urllib.parse import quote
import json
import re
import threading
import time
import uuid
import pandas as pd
import io
import uvicorn
import webbrowser

# 任务状态存储
task_status = {}

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    def open_browser():
        # 等待服务器完全启动
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")
    
    # 在后台线程中打开浏览器，避免阻塞启动
    print("程序已运行，前端界面请在浏览器中打开：http://127.0.0.1:8000")
    thread = threading.Thread(target=open_browser)
    thread.daemon = True
    thread.start()
    
    yield  # 应用运行期间
    
    # 关闭时执行（如果需要清理资源，可以在这里添加）

app = FastAPI(title="MetricHandel API", version="1.0.0", lifespan=lifespan)
db = DatabaseManager()

# 中间件：为静态文件添加禁用缓存响应头（开发环境）
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # 如果是静态文件请求，添加禁用缓存头
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """返回主页"""
    return FileResponse("static/index.html")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config():
    """Chrome DevTools配置（可选）"""
    return {"status": "ok"}

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
    search_value: Optional[str] = None,
    filters: Optional[str] = Query(None, description="JSON格式的多字段筛选条件"),
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = Query(None, pattern="^(asc|desc|ASC|DESC)$")
):
    """获取表数据（分页），支持多字段筛选和排序"""
    try:
        # 解析filters JSON字符串
        filters_dict = None
        if filters:
            try:
                filters_dict = json.loads(filters)
            except json.JSONDecodeError:
                filters_dict = None
        
        result = db.get_table_data(
            table_name, page, page_size, 
            search_field, search_value,
            filters_dict, sort_field, sort_order
        )
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


# noinspection PyTypeChecker
@app.get("/api/tables/{table_name}/download")
async def download_table_data(
    table_name: str,
    table_format: str = Query(..., pattern="^(csv|xlsx)$"),
    search_field: Optional[str] = None,
    search_value: Optional[str] = None,
    filters: Optional[str] = Query(None, description="JSON格式的多字段筛选条件"),
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = Query(None, pattern="^(asc|desc|ASC|DESC)$")
):
    """下载表数据为CSV或Excel格式，支持多字段筛选和排序"""
    try:
        # 解析filters JSON字符串
        filters_dict = None
        if filters:
            try:
                filters_dict = json.loads(filters)
            except json.JSONDecodeError:
                filters_dict = None
        
        # 获取所有数据（不分页）
        result = db.get_table_data(
            table_name, page=1, page_size=999999, 
            search_field=search_field, search_value=search_value,
            filters=filters_dict, sort_field=sort_field, sort_order=sort_order
        )
        
        if not result['data']:
            raise HTTPException(status_code=404, detail="没有数据可下载")
        
        # 转换为DataFrame
        df = pd.DataFrame(result['data'])
        
        # 生成文件名
        # 创建时间戳
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        if table_format == 'csv':
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
        
        elif table_format == 'xlsx':
            # 生成Excel
            output = io.BytesIO()
            # Excel sheet名称处理（移除特殊字符，限制长度）
            # noinspection RegExpRedundantEscape
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

@app.get("/api/query/overload")
async def query_overload(start_time: str = Query(..., description="开始时间"), 
                        end_time: str = Query(..., description="结束时间")):
    """执行突发高负荷小区查询"""
    try:
        sql_file = Path("./Scripts/OverLoad.sql")
        if not sql_file.exists():
            raise HTTPException(status_code=404, detail="SQL文件不存在")
        
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        data = db.execute_sql_file(str(sql_file), params)
        
        # 统计信息
        stats = {
            "4G": {
                "total": 0,
                "burst": 0
            },
            "5G": {
                "total": 0,
                "burst": 0
            }
        }
        
        # 用于去重的CGI集合
        cgi_4g_total = set()
        cgi_4g_burst = set()
        cgi_5g_total = set()
        cgi_5g_burst = set()
        
        for row in data:
            cgi = row.get("CGI", "")
            system = row.get("制式", "")
            is_burst = row.get("是否突发高负荷", "") == "是"
            
            if system == "4G":
                cgi_4g_total.add(cgi)
                if is_burst:
                    cgi_4g_burst.add(cgi)
            elif system == "5G":
                cgi_5g_total.add(cgi)
                if is_burst:
                    cgi_5g_burst.add(cgi)
        
        stats["4G"]["total"] = len(cgi_4g_total)
        stats["4G"]["burst"] = len(cgi_4g_burst)
        stats["5G"]["total"] = len(cgi_5g_total)
        stats["5G"]["burst"] = len(cgi_5g_burst)
        
        return {
            "data": data,
            "stats": stats,
            "total_count": len(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# noinspection PyTypeChecker
@app.get("/api/query/overload/download")
async def download_overload_data(
    start_time: str = Query(..., description="开始时间"),
    end_time: str = Query(..., description="结束时间"),
    table_format: str = Query(..., alias="format", pattern="^(csv|xlsx)$")
):
    """下载突发高负荷小区数据为CSV或Excel格式"""
    try:
        sql_file = Path("./Scripts/OverLoad.sql")
        if not sql_file.exists():
            raise HTTPException(status_code=404, detail="SQL文件不存在")
        
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        # 执行SQL查询
        try:
            data = db.execute_sql_file(str(sql_file), params)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL执行失败: {str(e)}")
        
        if not data:
            raise HTTPException(status_code=404, detail="没有数据可下载")
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"数据转换失败: {str(e)}")
        
        # 生成文件名
        safe_start = start_time.replace(':', '-').replace(' ', '_')
        safe_end = end_time.replace(':', '-').replace(' ', '_')
        
        if table_format == 'csv':
            # 生成CSV
            try:
                output = io.StringIO()
                df.to_csv(output, index=False, encoding='utf-8-sig')
                output.seek(0)
                
                # 生成文件名
                filename = f"突发高负荷小区_{safe_start}_{safe_end}.csv"
                filename_encoded = quote(filename.encode('utf-8'))
                
                return StreamingResponse(
                    io.BytesIO(output.getvalue().encode('utf-8-sig')),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"CSV生成失败: {str(e)}")
        
        elif table_format == 'xlsx':
            # 生成Excel
            try:
                output = io.BytesIO()
                safe_sheet_name = "突发高负荷小区"[:31]
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                output.seek(0)
                
                # 生成文件名
                filename = f"突发高负荷小区_{safe_start}_{safe_end}.xlsx"
                filename_encoded = quote(filename.encode('utf-8'))
                
                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Excel生成失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
