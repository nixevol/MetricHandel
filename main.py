# noinspection PyUnresolvedReferences,PyBroadException
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List
from contextlib import asynccontextmanager
from database import DatabaseManager
from data_processor import process_config, validate_config
from config_manager import ConfigManager
from resource_extractor import extract_resources
from updater import Updater
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
import sys

# 程序版本号和更新配置（内置，不在 config.ini 中）
APP_VERSION = "1.0.0"  # 当前程序版本号
GITEE_REPO = "guaotiantangmy/MetricHandel"  # Gitee 仓库地址（用于检查更新）
APP_NAME = "MetricHandel"  # 软件名称

# 设置控制台窗口标题

# noinspection PyBroadException,PyUnresolvedReferences
def set_console_title(title: str):
    """设置控制台窗口标题"""
    try:
        if sys.platform == 'win32':
            import ctypes
            # 使用 Windows API 设置控制台标题
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleTitleW(title)
    except Exception:
        pass  # 静默失败，不影响程序运行

# 设置窗口标题为软件名称 + 版本号
set_console_title(f"{APP_NAME} {APP_VERSION}")

# 初始化配置管理器
config = ConfigManager()

# 确保所有目录存在
config.ensure_directories()

# 启动时检查更新（必须在提取资源之前）
if getattr(sys, 'frozen', False) and GITEE_REPO:
    print("正在启动程序...")
    # noinspection PyBroadException
    try:
        updater = Updater(GITEE_REPO, APP_VERSION)
        
        # 首先检查注册表中的版本号
        need_update, registry_version = updater.check_version_control()
        
        if need_update:
            # 注册表中的版本号大于当前版本，说明之前检测到更新
            # 必须更新成功才能运行，无论网络是否可用
            print(f"\n检测到需要更新: {registry_version}（当前版本: {APP_VERSION}）")
            print("程序必须更新后才能使用")
            
            # 无论本地是否有更新文件，都重新下载以确保文件完整
            if updater.check_network():
                has_update, release_info = updater.check_update(timeout=10)
                if has_update and release_info:
                    # 删除本地可能存在的旧更新文件（如果存在），避免使用不完整的文件
                    new_exe_name = f"MetricHandel_{registry_version}.exe"
                    old_update_file = updater.base_path / new_exe_name
                    if old_update_file.exists():
                        # noinspection PyBroadException
                        try:
                            old_update_file.unlink()
                        except Exception:
                            pass
                    
                    # 下载更新（注册表中已有版本号，不需要再次写入）
                    update_file = updater.download_update(release_info)
                    if update_file:
                        if updater.launch_new_version_and_exit(update_file):
                            time.sleep(1)
                            sys.exit(0)
                        else:
                            print("启动新版本失败！")
                            print("程序无法运行，请手动更新")
                            print("\n按任意键退出...")
                            try:
                                import msvcrt
                                msvcrt.getch()
                            except (ImportError, AttributeError):
                                try:
                                    input()
                                except (EOFError, KeyboardInterrupt):
                                    pass
                            except (EOFError, KeyboardInterrupt):
                                pass
                            sys.exit(1)
                    else:
                        print("下载失败！")
                        print("程序无法运行，请检查网络连接后重试")
                        print("\n按任意键退出...")
                        try:
                            import msvcrt
                            msvcrt.getch()
                        except (ImportError, AttributeError):
                            try:
                                input()
                            except (EOFError, KeyboardInterrupt):
                                pass
                        except (EOFError, KeyboardInterrupt):
                            pass
                        sys.exit(1)
                else:
                    print(f"需要更新到版本: {registry_version}")
                    print("\n按任意键退出...")
                    try:
                        import msvcrt
                        msvcrt.getch()
                    except (ImportError, AttributeError):
                        try:
                            input()
                        except (EOFError, KeyboardInterrupt):
                            pass
                    except (EOFError, KeyboardInterrupt):
                        pass
                    sys.exit(1)
            else:
                print(f"需要更新到版本: {registry_version}")
                print("\n按任意键退出...")
                try:
                    import msvcrt
                    msvcrt.getch()
                except (ImportError, AttributeError):
                    try:
                        input()
                    except (EOFError, KeyboardInterrupt):
                        pass
                except (EOFError, KeyboardInterrupt):
                    pass
                sys.exit(1)
        
        # 注册表版本号 <= 当前版本，可以正常使用，但需要检查是否有新版本
        # 检查网络连接
        if updater.check_network():
            # 检查更新（15秒超时）
            has_update, release_info = updater.check_update(timeout=10)
            
            if has_update and release_info:
                new_version = release_info['version']
                print(f"\n检测到新版本: {new_version}")
                
                # 检测到新版本后，立即将版本号写入注册表
                updater.set_registry_version(new_version)
                print("开始下载更新...")
                
                # 下载更新
                update_file = updater.download_update(release_info)
                
                if update_file:
                    print(f"\n更新下载完成，正在启动新版本...")
                    # 启动新版本并退出
                    if updater.launch_new_version_and_exit(update_file):
                        print("新版本已启动，程序即将退出...")
                        time.sleep(1)
                        sys.exit(0)
                    else:
                        print("启动新版本失败！")
                        print("程序无法运行，请手动更新")
                        print("\n按任意键退出...")
                        try:
                            import msvcrt
                            msvcrt.getch()
                        except (ImportError, AttributeError):
                            try:
                                input()
                            except (EOFError, KeyboardInterrupt):
                                pass
                        except (EOFError, KeyboardInterrupt):
                            pass
                        sys.exit(1)
                else:
                    print("下载失败！")
                    print("程序无法运行，请检查网络连接后重试")
                    print("\n按任意键退出...")
                    try:
                        import msvcrt
                        msvcrt.getch()
                    except (ImportError, AttributeError):
                        try:
                            input()
                        except (EOFError, KeyboardInterrupt):
                            pass
                    except (EOFError, KeyboardInterrupt):
                        pass
                    sys.exit(1)
    except Exception as e:
        pass

# 如果是打包后的exe，提取资源文件
if getattr(sys, 'frozen', False):
    extract_resources(config.get_models_path(), config.get_scripts_path())

# 获取配置的路径
# 静态文件路径：打包后在临时目录，开发环境在项目目录
if getattr(sys, 'frozen', False):
    # 打包后，static目录在临时解压目录中
    # noinspection PyUnresolvedReferences,PyProtectedMember
    STATIC_PATH = Path(sys._MEIPASS) / "static"
else:
    # 开发环境
    STATIC_PATH = Path(__file__).parent / "static"
MODELS_PATH = config.get_models_path()
SCRIPTS_PATH = config.get_scripts_path()
DATA_PATH = config.get_data_path()
DB_PATH = config.get_db_file_path()
SERVER_PORT = config.get_port()
LOG_LEVEL = config.get_log_level()

# 任务状态存储
task_status = {}

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    def open_browser():
        # 等待服务器完全启动
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{SERVER_PORT}")
    
    # 在后台线程中打开浏览器，避免阻塞启动
    print(f"程序已运行，前端界面请在浏览器中打开：http://127.0.0.1:{SERVER_PORT}")
    thread = threading.Thread(target=open_browser)
    thread.daemon = True
    thread.start()
    
    yield  # 应用运行期间
    
    # 关闭时执行（如果需要清理资源，可以在这里添加）

app = FastAPI(title="MetricHandel API", version="1.0.0", lifespan=lifespan)
db = DatabaseManager(db_path=str(DB_PATH))

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
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

@app.get("/")
async def read_root():
    """返回主页"""
    index_path = STATIC_PATH / "index.html"
    return FileResponse(str(index_path))

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
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.get("/api/tables/{table_name}/columns")
async def get_table_columns(table_name: str):
    """获取表的列名"""
    try:
        columns = db.get_table_columns(table_name)
        return {"columns": columns}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

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
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.delete("/api/tables/{table_name}/data")
async def clear_table_data(table_name: str):
    """清空表数据"""
    try:
        affected_rows = db.clear_table(table_name)
        return {"message": f"已清空表 {table_name}", "affected_rows": affected_rows}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.get("/api/tables/{table_name}/count")
async def get_table_count(table_name: str):
    """获取表记录数"""
    try:
        count = db.get_table_count(table_name)
        return {"table": table_name, "count": count}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.get("/api/models")
async def get_models():
    """获取所有模型配置文件"""
    try:
        models_dir = MODELS_PATH
        if not models_dir.exists():
            return {"models": []}
        
        models = []
        for json_file in models_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                model_config = json.load(f)  # 使用model_config避免与全局config冲突
            models.append({
                "name": json_file.stem,
                "path": str(json_file),
                "file_pattern": model_config.get("File", {}).get("Path", ""),
                "table": model_config.get("Export", {}).get("Table", "")
            })
        return {"models": models}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

def execute_models_task(task_id: str, model_paths: List[str], db_path: str):
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
            
            # 处理单个配置文件，传入数据库路径
            result = process_config(model_path, db_path)
            results[model_path] = result
            
            task_status[task_id]["results"] = results
        
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["progress"] = len(model_paths)
        task_status[task_id]["current"] = "执行完成"
        task_status[task_id]["end_time"] = time.time()
        
    except Exception as err:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(err)
        task_status[task_id]["end_time"] = time.time()

@app.post("/api/models/execute")
async def execute_models(model_paths: List[str]):
    """异步执行选中的模型配置"""
    try:
        # 先验证所有配置文件
        validation_errors = []
        for model_path in model_paths:
            is_valid, error_message = validate_config(model_path, str(DB_PATH))
            if not is_valid:
                validation_errors.append({
                    "config": Path(model_path).name,
                    "error": error_message
                })
        
        # 如果有验证错误，直接返回错误信息，不执行任务
        if validation_errors:
            error_details = "\n".join([f"{err['config']}: {err['error']}" for err in validation_errors])
            raise HTTPException(
                status_code=400,
                detail=f"配置文件验证失败，请修复以下问题后再执行：\n{error_details}"
            )
        
        # 所有验证通过，启动任务
        task_id = str(uuid.uuid4())
        
        # 在后台线程中执行任务，传入数据库路径
        thread = threading.Thread(target=execute_models_task, args=(task_id, model_paths, str(DB_PATH)))
        thread.daemon = True
        thread.start()
        
        return {"task_id": task_id, "message": "任务已启动"}
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

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
            
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.get("/api/files")
async def get_data_files():
    """获取Data目录下的文件列表"""
    try:
        data_dir = DATA_PATH
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
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件到Data目录"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        data_dir = DATA_PATH
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查文件类型
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。仅支持: {', '.join(allowed_extensions)}"
            )
        
        # 防止路径遍历攻击：只使用文件名，移除路径部分
        safe_filename = Path(file.filename).name
        
        # 移除路径遍历字符（../ 和 ..\）
        # 注意：这里不删除中文字符，因为用户可能需要上传中文文件名的文件
        # 由于我们已经使用了 Path().name 和 resolve() 检查，所以只需要移除明显的危险字符即可
        if '..' in safe_filename or '/' in safe_filename or '\\' in safe_filename:
            # 如果包含路径分隔符，只保留文件名部分（再次确保）
            safe_filename = Path(safe_filename).name
        
        if not safe_filename or safe_filename.strip() == '':
            raise HTTPException(status_code=400, detail="文件名无效")
        
        # 读取文件内容（不限制大小，由操作系统和磁盘空间决定）
        content = await file.read()
        
        # 处理文件名冲突
        file_path = data_dir / safe_filename
        counter = 1
        original_stem = file_path.stem
        
        while file_path.exists():
            file_path = data_dir / f"{original_stem}_{counter}{file_extension}"
            counter += 1
        
        # 确保最终路径在DATA_PATH目录内（双重检查）
        file_path_resolved = file_path.resolve()
        data_path_resolved = data_dir.resolve()
        if not str(file_path_resolved).startswith(str(data_path_resolved)):
            raise HTTPException(status_code=403, detail="禁止访问该文件路径")
        
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
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


# noinspection DuplicatedCode
@app.get("/api/files/{filename}/download")
async def download_file(filename: str):
    """下载Data目录中的文件"""
    try:
        # 防止路径遍历攻击：确保文件路径在DATA_PATH目录内
        file_path = (DATA_PATH / filename).resolve()
        data_path_resolved = DATA_PATH.resolve()
        
        # 检查文件路径是否在DATA_PATH目录内
        if not str(file_path).startswith(str(data_path_resolved)):
            raise HTTPException(status_code=403, detail="禁止访问该文件路径")
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(file_path, filename=filename)
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


# noinspection DuplicatedCode
@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """删除Data目录中的文件"""
    try:
        # 防止路径遍历攻击：确保文件路径在DATA_PATH目录内
        file_path = (DATA_PATH / filename).resolve()
        data_path_resolved = DATA_PATH.resolve()
        
        # 检查文件路径是否在DATA_PATH目录内
        if not str(file_path).startswith(str(data_path_resolved)):
            raise HTTPException(status_code=403, detail="禁止访问该文件路径")
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_path.unlink()
        return {"message": f"文件 {filename} 删除成功"}
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.get("/api/query/overload")
async def query_overload(start_time: str = Query(..., description="开始时间"), 
                        end_time: str = Query(..., description="结束时间")):
    """执行突发高负荷小区查询"""
    try:
        sql_file = SCRIPTS_PATH / "OverLoad.sql"
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
                "burst": 0,
                "total_important": 0,
                "burst_important": 0
            },
            "5G": {
                "total": 0,
                "burst": 0,
                "total_important": 0,
                "burst_important": 0
            }
        }
        
        # 用于去重的CGI集合
        cgi_4g_total = set()
        cgi_4g_burst = set()
        cgi_5g_total = set()
        cgi_5g_burst = set()
        
        # 重要区域CGI集合
        cgi_4g_total_important = set()
        cgi_4g_burst_important = set()
        cgi_5g_total_important = set()
        cgi_5g_burst_important = set()
        
        for row in data:
            cgi = row.get("CGI", "")
            system = row.get("制式", "")
            is_burst = row.get("是否突发高负荷", "") == "是"
            important_area = row.get("重要区域", "")
            is_important = important_area and str(important_area).strip() != ""
            
            if system == "4G":
                cgi_4g_total.add(cgi)
                if is_important:
                    cgi_4g_total_important.add(cgi)
                if is_burst:
                    cgi_4g_burst.add(cgi)
                    if is_important:
                        cgi_4g_burst_important.add(cgi)
            elif system == "5G":
                cgi_5g_total.add(cgi)
                if is_important:
                    cgi_5g_total_important.add(cgi)
                if is_burst:
                    cgi_5g_burst.add(cgi)
                    if is_important:
                        cgi_5g_burst_important.add(cgi)
        
        stats["4G"]["total"] = len(cgi_4g_total)
        stats["4G"]["burst"] = len(cgi_4g_burst)
        stats["4G"]["total_important"] = len(cgi_4g_total_important)
        stats["4G"]["burst_important"] = len(cgi_4g_burst_important)
        stats["5G"]["total"] = len(cgi_5g_total)
        stats["5G"]["burst"] = len(cgi_5g_burst)
        stats["5G"]["total_important"] = len(cgi_5g_total_important)
        stats["5G"]["burst_important"] = len(cgi_5g_burst_important)
        
        return {
            "data": data,
            "stats": stats,
            "total_count": len(data)
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


# noinspection PyTypeChecker
@app.get("/api/query/overload/download")
async def download_overload_data(
    start_time: str = Query(..., description="开始时间"),
    end_time: str = Query(..., description="结束时间"),
    table_format: str = Query(..., alias="format", pattern="^(csv|xlsx)$")
):
    """下载突发高负荷小区数据为CSV或Excel格式"""
    try:
        sql_file = SCRIPTS_PATH / "OverLoad.sql"
        if not sql_file.exists():
            raise HTTPException(status_code=404, detail="SQL文件不存在")
        
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        
        # 执行SQL查询
        try:
            data = db.execute_sql_file(str(sql_file), params)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"SQL执行失败: {str(err)}")
        
        if not data:
            raise HTTPException(status_code=404, detail="没有数据可下载")
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"数据转换失败: {str(err)}")
        
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
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"CSV生成失败: {str(err)}")
        
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
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Excel生成失败: {str(err)}")
            
    except HTTPException:
        raise
    except Exception as err:
        import traceback
        error_detail = f"{str(err)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level=LOG_LEVEL)
