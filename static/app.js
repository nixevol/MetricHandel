let currentTable = '';
let currentPage = 1;
let totalPages = 1;
let searchField = '';
let searchValue = '';
let allTables = [];

// 选中文件集合（用于批量删除）
let selectedFiles = new Set();

// 自定义弹窗函数
function showAlert(message, title = '提示') {
    return new Promise((resolve) => {
        const modal = document.getElementById('customModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalMessage = document.getElementById('modalMessage');
        const modalConfirm = document.getElementById('modalConfirm');
        const modalCancel = document.getElementById('modalCancel');
        
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalCancel.classList.add('hidden');
        
        modal.classList.remove('hidden');
        
        const handleConfirm = () => {
            modal.classList.add('hidden');
            modalConfirm.removeEventListener('click', handleConfirm);
            document.removeEventListener('keydown', handleEsc);
            resolve(true);
        };
        
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                modal.classList.add('hidden');
                modalConfirm.removeEventListener('click', handleConfirm);
                document.removeEventListener('keydown', handleEsc);
                resolve(true);
            }
        };

        modalConfirm.addEventListener('click', handleConfirm);
        document.addEventListener('keydown', handleEsc);
    });
}

// 更新批量删除按钮状态
function updateDeleteSelectedButton() {
    const btn = document.getElementById('deleteSelectedBtn');
    if (!btn) return;
    const hasSelection = selectedFiles.size > 0;
    btn.disabled = !hasSelection;
}

// 全选/取消全选
function toggleSelectAllFiles(source) {
    const checkboxes = document.querySelectorAll('.file-select-checkbox');
    selectedFiles.clear();
    checkboxes.forEach(cb => {
        cb.checked = source.checked;
        if (source.checked) {
            selectedFiles.add(cb.getAttribute('data-filename'));
        }
    });
    updateDeleteSelectedButton();
}

// 批量删除选中文件
async function deleteSelectedFiles() {
    const btn = document.getElementById('deleteSelectedBtn');
    // 如果按钮是禁用状态，直接返回
    if (btn && btn.disabled) {
        return;
    }
    
    if (selectedFiles.size === 0) {
        return;
    }

    const confirmed = await showConfirm(`确定要删除选中的 ${selectedFiles.size} 个文件吗？`, '确认删除');
    if (!confirmed) return;

    let successCount = 0;
    let failMessages = [];

    for (const filename of selectedFiles) {
        try {
            const response = await axios.delete(`/api/files/${filename}`);
            if (response.status === 200) {
                successCount += 1;
            } else {
                failMessages.push(`${filename}: 删除失败 (${response.status})`);
            }
        } catch (error) {
            failMessages.push(`${filename}: ${error.message}`);
        }
    }

    await loadFiles();

    let message = '';
    if (successCount > 0) {
        message += `成功删除 ${successCount} 个文件。`;
    }
    if (failMessages.length > 0) {
        message += '\n以下文件删除失败:\n' + failMessages.join('\n');
    }

    if (message) {
        await showAlert(message.trim(), '删除结果');
    }
}

function showConfirm(message, title = '确认') {
    return new Promise((resolve) => {
        const modal = document.getElementById('customModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalMessage = document.getElementById('modalMessage');
        const modalConfirm = document.getElementById('modalConfirm');
        const modalCancel = document.getElementById('modalCancel');
        
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalCancel.classList.remove('hidden');
        
        modal.classList.remove('hidden');
        
        const handleConfirm = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(true);
        };
        
        const handleCancel = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            modalConfirm.removeEventListener('click', handleConfirm);
            modalCancel.removeEventListener('click', handleCancel);
            document.removeEventListener('keydown', handleEsc);
        };
        
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                modal.classList.add('hidden');
                cleanup();
                resolve(false);
            }
        };
        
        modalConfirm.addEventListener('click', handleConfirm);
        modalCancel.addEventListener('click', handleCancel);
        document.addEventListener('keydown', handleEsc);
    });
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadTables();
    loadModels();
    loadFiles();
    
    // 搜索框回车事件
    document.getElementById('searchValue').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchData();
        }
    });
    
    // 跳转页面回车事件（延迟绑定，因为元素可能还不存在）
    document.addEventListener('keypress', function(e) {
        if (e.target.id === 'jumpToPage' && e.key === 'Enter') {
            jumpToPage();
        }
    });
    
    // 页面离开时清理轮询
    window.addEventListener('beforeunload', function() {
        stopTaskPolling();
    });
    
    // 文件上传拖拽功能
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectedFilesInfo = document.getElementById('selectedFilesInfo');
    const uploadBtn = document.getElementById('uploadBtn');
    
    // 点击拖拽区域打开文件选择
    dropZone.addEventListener('click', function() {
        fileInput.click();
    });
    
    // 文件选择后更新UI
    fileInput.addEventListener('change', function() {
        updateFileSelection();
    });
    
    // 阻止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 拖拽时高亮显示
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, function() {
            dropZone.classList.add('border-blue-500', 'bg-blue-50');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, function() {
            dropZone.classList.remove('border-blue-500', 'bg-blue-50');
        }, false);
    });
    
    // 处理文件拖放
    dropZone.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        fileInput.files = dt.files;
        updateFileSelection();
    }, false);
    
    // 绑定删除选中文件按钮事件
    const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', deleteSelectedFiles);
    }
    
    // 注意：指标监控按钮使用 onclick 绑定，不需要在这里重复绑定
});

// 加载所有表
async function loadTables() {
    try {
        const response = await axios.get('/api/tables');
        allTables = response.data.tables;
        updateTableTabs();
    } catch (error) {
        console.error('加载表列表失败:', error);
        allTables = [];
    }
}

// 更新表标签页
function updateTableTabs() {
    const tableTabs = document.getElementById('tableTabs');
    tableTabs.innerHTML = '';
    
    if (allTables.length === 0) {
        return;
    }
    
    allTables.forEach((table, index) => {
        const button = document.createElement('button');
        button.className = index === 0 && !currentTable ? 
            'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600' :
            'px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent hover:border-gray-300';
        button.textContent = table;
        button.onclick = () => selectTable(table);
        tableTabs.appendChild(button);
    });
    
    // 如果没有选中表，默认选中第一个
    if (!currentTable && allTables.length > 0) {
        selectTable(allTables[0]);
    }
}

// 加载表列名
async function loadTableColumns() {
    try {
        const response = await axios.get(`/api/tables/${currentTable}/columns`);
        const searchField = document.getElementById('searchField');
        searchField.innerHTML = '<option value="">选择字段...</option>';
        
        response.data.columns.forEach(column => {
            const option = document.createElement('option');
            option.value = column;
            option.textContent = column;
            searchField.appendChild(option);
        });
    } catch (error) {
        await showAlert('加载列信息失败: ' + error.message, '错误');
    }
}

// 加载表数据
async function loadTableData(page = 1) {
    try {
        const params = {
            page: page,
            page_size: 50
        };
        
        if (searchField && searchValue) {
            params.search_field = searchField;
            params.search_value = searchValue;
        }
        
        const response = await axios.get(`/api/tables/${currentTable}/data`, { params });
        const data = response.data;
        
        currentPage = data.current_page;
        totalPages = data.total_pages;
        
        renderTable(data);
        renderPagination(data);
        
    } catch (error) {
        await showAlert('加载数据失败: ' + error.message, '错误');
    }
}

// 渲染表格
function renderTable(data) {
    const header = document.getElementById('tableHeader');
    const body = document.getElementById('tableBody');
    
    // 渲染表头
    header.innerHTML = '';
    const headerRow = document.createElement('tr');
    data.columns.forEach(column => {
        const th = document.createElement('th');
        th.className = 'px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-300';
        th.style.backgroundColor = '#f9fafb';
        th.style.position = 'sticky';
        th.style.top = '0';
        th.style.zIndex = '20';
        th.style.minWidth = '100px';
        th.style.whiteSpace = 'nowrap';
        th.textContent = column;
        headerRow.appendChild(th);
    });
    header.appendChild(headerRow);
    
    // 渲染数据
    body.innerHTML = '';
    data.data.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-200 hover:bg-gray-50';
        
        data.columns.forEach(column => {
            const td = document.createElement('td');
            td.className = 'px-3 py-2 text-sm text-gray-900';
            td.style.minWidth = '100px';
            td.style.maxWidth = '250px';
            td.style.overflow = 'hidden';
            td.style.textOverflow = 'ellipsis';
            td.style.whiteSpace = 'nowrap';
            td.title = row[column] || ''; // 添加tooltip显示完整内容
            td.textContent = row[column] || '';
            tr.appendChild(td);
        });
        
        body.appendChild(tr);
    });
}

// 渲染分页
function renderPagination(data) {
    const pageInfo = document.getElementById('pageInfo');
    const recordCount = document.getElementById('recordCount');
    const pageNumbers = document.getElementById('pageNumbers');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const jumpInput = document.getElementById('jumpToPage');
    
    // 更新页面信息
    pageInfo.textContent = `第 ${data.current_page} 页，共 ${data.total_pages} 页`;
    recordCount.textContent = `共 ${data.total_count} 条记录`;
    
    // 更新跳转输入框的最大值
    if (jumpInput) {
        jumpInput.max = data.total_pages;
        jumpInput.placeholder = `1-${data.total_pages}`;
    }
    
    // 更新按钮状态
    prevBtn.disabled = data.current_page <= 1;
    nextBtn.disabled = data.current_page >= data.total_pages;
    
    // 渲染页码
    pageNumbers.innerHTML = '';
    const startPage = Math.max(1, data.current_page - 2);
    const endPage = Math.min(data.total_pages, data.current_page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === data.current_page 
            ? 'px-3 py-1 bg-blue-500 text-white rounded border border-blue-500'
            : 'px-3 py-1 bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50';
        pageBtn.onclick = () => loadTableData(i);
        pageNumbers.appendChild(pageBtn);
    }
}


// 选择表
function selectTable(tableName, targetElement) {
    currentTable = tableName;
    loadTableColumns();
    loadTableData();
    
    // 更新标签页选中状态
    document.querySelectorAll('#tableTabs button').forEach(btn => {
        btn.className = 'px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent hover:border-gray-300';
    });
    
    // 如果提供了目标元素，使用它；否则通过文本内容查找按钮
    let targetBtn = targetElement;
    if (!targetBtn) {
        const buttons = document.querySelectorAll('#tableTabs button');
        buttons.forEach(btn => {
            if (btn.textContent === tableName) {
                targetBtn = btn;
            }
        });
    }
    
    if (targetBtn) {
        targetBtn.className = 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600';
    }
    
    // 显示数据表格和操作按钮
    document.getElementById('noDataMessage').classList.add('hidden');
    document.getElementById('dataTable').classList.remove('hidden');
    document.getElementById('downloadBtn').style.display = 'flex';
    document.getElementById('clearTableBtn').style.display = 'inline-flex';
}

// 刷新数据库
async function refreshDatabase() {
    const refreshBtn = document.getElementById('refreshDatabaseBtn');
    const originalContent = refreshBtn.innerHTML;
    
    // 保存当前选中的表名
    const previousTable = currentTable;
    
    try {
        // 显示加载状态
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>刷新中...';
        
        // 重新加载表列表
        await loadTables();
        
        // 更新UI状态
        if (allTables.length === 0) {
            currentTable = '';
            document.getElementById('noDataMessage').classList.remove('hidden');
            document.getElementById('dataTable').classList.add('hidden');
            const downloadBtn = document.getElementById('downloadBtn');
            const clearBtn = document.getElementById('clearTableBtn');
            if (downloadBtn) downloadBtn.style.display = 'none';
            if (clearBtn) clearBtn.style.display = 'none';
        } else {
            document.getElementById('noDataMessage').classList.add('hidden');
            updateTableTabs();
            
            // 如果之前有选中的表且该表仍然存在，重新选中并加载数据
            if (previousTable && allTables.includes(previousTable)) {
                currentTable = previousTable;
                await loadTableColumns();
                await loadTableData(1);
                // 更新标签页选中状态
                document.querySelectorAll('#tableTabs button').forEach(btn => {
                    if (btn.textContent === previousTable) {
                        btn.className = 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600';
                    } else {
                        btn.className = 'px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent hover:border-gray-300';
                    }
                });
                // 显示数据表格和操作按钮
                document.getElementById('dataTable').classList.remove('hidden');
                document.getElementById('downloadBtn').style.display = 'flex';
                document.getElementById('clearTableBtn').style.display = 'inline-flex';
            } else if (!currentTable && allTables.length > 0) {
                // 如果没有选中表，选中第一个表
                selectTable(allTables[0]);
            }
        }
        
    } catch (error) {
        console.error('刷新数据库失败:', error);
        await showAlert('刷新数据库失败: ' + error.message, '错误');
    } finally {
        // 恢复按钮状态
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = originalContent;
    }
}

// 显示数据库管理面板
function showDatabasePanel() {
    hideAllPanels();
    updateNavigation('nav-database');
    document.getElementById('databasePanel').classList.remove('hidden');
    document.getElementById('searchContainer').classList.remove('hidden');
    document.getElementById('pageTitle').textContent = '数据库管理';
    document.getElementById('pageSubtitle').textContent = '查看和管理数据表';
    
    // 每次切换到数据库管理页面时自动刷新
    refreshDatabase();
}

// 显示合并数据面板
function showScriptsPanel() {
    hideAllPanels();
    updateNavigation('nav-scripts');
    document.getElementById('scriptsPanel').classList.remove('hidden');
    document.getElementById('searchContainer').classList.add('hidden');
    document.getElementById('pageTitle').textContent = '合并数据';
    document.getElementById('pageSubtitle').textContent = '批量处理数据文件';
    loadModels();
}

// 显示文件管理面板
function showFilesPanel() {
    hideAllPanels();
    updateNavigation('nav-files');
    document.getElementById('filesPanel').classList.remove('hidden');
    document.getElementById('searchContainer').classList.add('hidden');
    document.getElementById('pageTitle').textContent = '文件管理';
    document.getElementById('pageSubtitle').textContent = '管理数据文件';
    loadFiles();
}

// 更新导航选中状态
function updateNavigation(activeId) {
    // 移除所有按钮的active类
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    // 给当前按钮添加active类
    const activeBtn = document.getElementById(activeId);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    // 如果点击的是子菜单项，也激活父菜单
    if (activeId === 'nav-high-load-cell') {
        const parentBtn = document.getElementById('nav-burst-monitor');
        if (parentBtn) {
            parentBtn.classList.add('active');
        }
        // 确保子菜单展开
        const submenu = document.getElementById('burst-monitor-submenu');
        const arrow = document.getElementById('burst-monitor-arrow');
        if (submenu && submenu.classList.contains('hidden')) {
            submenu.classList.remove('hidden');
            if (arrow) arrow.style.transform = 'rotate(180deg)';
        }
    }
}

// 隐藏所有面板
function hideAllPanels() {
    document.getElementById('welcomePanel').classList.add('hidden');
    document.getElementById('databasePanel').classList.add('hidden');
    document.getElementById('scriptsPanel').classList.add('hidden');
    document.getElementById('filesPanel').classList.add('hidden');
    const highLoadPanel = document.getElementById('highLoadCellPanel');
    if (highLoadPanel) {
        highLoadPanel.classList.add('hidden');
    }
}

// 切换指标监控菜单展开/收起
function toggleBurstMonitorMenu() {
    const submenu = document.getElementById('burst-monitor-submenu');
    const arrow = document.getElementById('burst-monitor-arrow');
    
    if (!submenu || !arrow) {
        console.error('无法找到子菜单元素');
        return false;
    }
    
    // 直接使用 toggle 方法切换 hidden 类
    submenu.classList.toggle('hidden');
    
    // 更新箭头旋转
    if (submenu.classList.contains('hidden')) {
        arrow.style.transform = 'rotate(0deg)';
    } else {
        arrow.style.transform = 'rotate(180deg)';
    }
    
    return false; // 阻止事件冒泡
}

// 高负荷小区监控相关功能已移至 static/high-load-cell.js

// 搜索数据
function searchData() {
    searchField = document.getElementById('searchField').value;
    searchValue = document.getElementById('searchValue').value;
    loadTableData(1);
}

// 清空搜索
function clearSearch() {
    document.getElementById('searchField').value = '';
    document.getElementById('searchValue').value = '';
    searchField = '';
    searchValue = '';
    loadTableData(1);
}

// 清空表数据
async function clearTableData() {
    const confirmed = await showConfirm(`确定要清空表 "${currentTable}" 的所有数据吗？此操作不可恢复！`, '确认清空');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await axios.delete(`/api/tables/${currentTable}/data`);
        await showAlert(response.data.message, '操作成功');
        loadTableData(1);
    } catch (error) {
        await showAlert('清空数据失败: ' + error.message, '错误');
    }
}

// 加载模型列表
async function loadModels() {
    try {
        const response = await axios.get('/api/models');
        const modelsList = document.getElementById('modelsList');
        modelsList.innerHTML = '';
        
        response.data.models.forEach(model => {
            const div = document.createElement('div');
            div.className = 'flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50';
            div.innerHTML = `
                <input type="checkbox" id="model_${model.name}" value="${model.path}" 
                       class="mr-4 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                <div class="flex-1">
                    <label for="model_${model.name}" class="block text-sm font-medium text-gray-900 cursor-pointer">
                        ${model.name}
                    </label>
                    <p class="text-xs text-gray-500 mt-1">文件: ${model.file_pattern}</p>
                    <p class="text-xs text-gray-500">目标表: ${model.table}</p>
                </div>
            `;
            modelsList.appendChild(div);
        });
    } catch (error) {
        console.error('加载模型列表失败:', error);
    }
}

// 全选模型
function selectAllModels() {
    document.querySelectorAll('#modelsList input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = true;
    });
}

// 清空模型选择
function clearModelSelection() {
    document.querySelectorAll('#modelsList input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });
}

// 当前执行任务ID
let currentTaskId = null;
let taskPollingInterval = null;

// 执行选中的模型
async function executeSelectedModels() {
    const selectedCheckboxes = document.querySelectorAll('#modelsList input[type="checkbox"]:checked');
    const modelPaths = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    if (modelPaths.length === 0) {
        await showAlert('请选择要执行的模型');
        return;
    }
    
    // 如果已有任务在执行，提示用户
    if (currentTaskId) {
        await showAlert('已有任务在执行中，请等待完成');
        return;
    }
    
    try {
        // 显示加载状态
        showExecutionLoading();
        
        // 启动异步任务
        const response = await axios.post('/api/models/execute', modelPaths);
        currentTaskId = response.data.task_id;
        
        // 开始轮询任务状态
        startTaskPolling();
        
    } catch (error) {
        hideExecutionLoading();
        await showAlert('启动任务失败: ' + error.message, '错误');
    }
}

// 显示执行加载状态
function showExecutionLoading() {
    const executeBtn = document.querySelector('button[onclick="executeSelectedModels()"]');
    executeBtn.disabled = true;
    executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>执行中...';
    
    const resultDiv = document.getElementById('executionResult');
    const contentDiv = document.getElementById('resultContent');
    
    contentDiv.innerHTML = `
        <div class="flex items-center space-x-3">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <div>
                <p class="font-medium">任务执行中...</p>
                <p id="taskProgress" class="text-sm text-gray-600">正在初始化...</p>
                <p id="taskElapsed" class="text-xs text-gray-500">已用时: 0秒</p>
            </div>
        </div>
    `;
    resultDiv.classList.remove('hidden');
}

// 隐藏执行加载状态
function hideExecutionLoading() {
    const executeBtn = document.querySelector('button[onclick="executeSelectedModels()"]');
    executeBtn.disabled = false;
    executeBtn.innerHTML = '<i class="fas fa-play mr-1"></i>执行选中';
}

// 开始轮询任务状态
function startTaskPolling() {
    taskPollingInterval = setInterval(async () => {
        try {
            const response = await axios.get(`/api/models/execute/${currentTaskId}`);
            const status = response.data;
            
            updateTaskProgress(status);
            
            // 任务完成或失败时停止轮询
            if (status.status === 'completed' || status.status === 'failed') {
                stopTaskPolling();
                handleTaskCompletion(status);
            }
            
        } catch (error) {
            console.error('获取任务状态失败:', error);
            stopTaskPolling();
            hideExecutionLoading();
            await showAlert('获取任务状态失败', '错误');
        }
    }, 1000); // 每秒轮询一次
}

// 停止轮询任务状态
function stopTaskPolling() {
    if (taskPollingInterval) {
        clearInterval(taskPollingInterval);
        taskPollingInterval = null;
    }
    currentTaskId = null;
}

// 更新任务进度显示
function updateTaskProgress(status) {
    const progressEl = document.getElementById('taskProgress');
    const elapsedEl = document.getElementById('taskElapsed');
    
    if (progressEl) {
        const progressText = `${status.current} (${status.progress}/${status.total})`;
        progressEl.textContent = progressText;
    }
    
    if (elapsedEl && status.elapsed_time) {
        const elapsed = Math.round(status.elapsed_time);
        elapsedEl.textContent = `已用时: ${elapsed}秒`;
    }
}

// 跳转到指定页
async function jumpToPage() {
    const jumpInput = document.getElementById('jumpToPage');
    const targetPage = parseInt(jumpInput.value);
    
    if (!targetPage || targetPage < 1 || targetPage > totalPages) {
        await showAlert(`请输入有效的页码 (1-${totalPages})`);
        return;
    }
    
    loadTableData(targetPage);
    jumpInput.value = '';
}

// 切换下载菜单显示
function toggleDownloadMenu() {
    const downloadBtn = document.getElementById('downloadBtn');
    const menu = document.getElementById('downloadMenu');
    
    // 如果按钮被禁用或正在下载，不显示菜单
    if (downloadBtn.disabled || isDownloading) {
        return;
    }
    
    menu.classList.toggle('hidden');
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', function closeMenu(e) {
        if (!e.target.closest('#downloadBtn') && !e.target.closest('#downloadMenu')) {
            menu.classList.add('hidden');
            document.removeEventListener('click', closeMenu);
        }
    });
}

// 下载状态标志
let isDownloading = false;

// 下载表数据
async function downloadTableData(format) {
    if (!currentTable) {
        await showAlert('请先选择一个数据表');
        return;
    }
    
    // 如果正在下载，阻止新的下载
    if (isDownloading) {
        await showAlert('正在下载中，请等待当前下载完成');
        return;
    }
    
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadMenu = document.getElementById('downloadMenu');
    const originalContent = downloadBtn.innerHTML;
    
    try {
        // 设置下载状态
        isDownloading = true;
        
        // 显示加载状态并禁用所有下载选项
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i>下载${format.toUpperCase()}中...`;
        
        // 禁用下载菜单中的所有按钮
        const menuButtons = downloadMenu.querySelectorAll('button');
        menuButtons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        });
        
        // 关闭下载菜单
        downloadMenu.classList.add('hidden');
        
        // 构建下载URL
        let url = `/api/tables/${currentTable}/download?format=${format}`;
        
        // 如果有搜索条件，添加到URL
        if (searchField && searchValue) {
            url += `&search_field=${encodeURIComponent(searchField)}&search_value=${encodeURIComponent(searchValue)}`;
        }
        
        // 使用fetch检查下载状态
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`下载失败: ${response.status} ${response.statusText}`);
        }
        
        // 创建blob并下载
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = downloadUrl;
        
        // 从响应头获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${currentTable}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format}`;
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename\*?=['"]?([^'";]+)['"]?/);
            if (filenameMatch) {
                filename = decodeURIComponent(filenameMatch[1]);
            }
        }
        
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理blob URL
        window.URL.revokeObjectURL(downloadUrl);
        
    } catch (error) {
        await showAlert('下载失败: ' + error.message, '下载失败');
    } finally {
        // 恢复所有状态
        isDownloading = false;
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = originalContent;
        
        // 恢复下载菜单中的按钮
        const menuButtons = downloadMenu.querySelectorAll('button');
        menuButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        });
    }
}

// 处理任务完成
function handleTaskCompletion(status) {
    hideExecutionLoading();
    
    const contentDiv = document.getElementById('resultContent');
    
    if (status.status === 'completed') {
        let resultHtml = '<div class="space-y-2">';
        resultHtml += '<div class="flex items-center space-x-2 text-green-600 mb-3">';
        resultHtml += '<i class="fas fa-check-circle"></i>';
        resultHtml += '<span class="font-medium">执行完成</span>';
        resultHtml += `<span class="text-sm text-gray-500">(用时: ${Math.round(status.elapsed_time)}秒)</span>`;
        resultHtml += '</div>';
        
        resultHtml += '<h5 class="font-medium mb-2">执行结果:</h5>';
        for (const [path, count] of Object.entries(status.results)) {
            const fileName = path.split(/[/\\]/).pop();
            resultHtml += `<p class="text-sm"><span class="font-medium">${fileName}:</span> 导入 ${count} 条数据</p>`;
        }
        resultHtml += '</div>';
        
        contentDiv.innerHTML = resultHtml;
        
        // 刷新表列表
        loadTables();
        
        // 如果当前在数据库管理面板，刷新显示
        if (!document.getElementById('databasePanel').classList.contains('hidden')) {
            setTimeout(() => {
                updateTableTabs();
            }, 500);
        }
        
    } else if (status.status === 'failed') {
        contentDiv.innerHTML = `
            <div class="flex items-center space-x-2 text-red-600 mb-3">
                <i class="fas fa-exclamation-circle"></i>
                <span class="font-medium">执行失败</span>
            </div>
            <p class="text-sm text-gray-600">错误信息: ${status.error}</p>
        `;
    }
}

// 加载文件列表
async function loadFiles() {
    try {
        const response = await axios.get('/api/files');
        const filesList = document.getElementById('filesList');
        filesList.innerHTML = '';
        
        if (response.data.files.length === 0) {
            filesList.innerHTML = '<p class="text-gray-500 text-center py-4">暂无文件</p>';
            selectedFiles.clear();
            updateDeleteSelectedButton();
            const selectAll = document.getElementById('selectAllFiles');
            if (selectAll) selectAll.checked = false;
            return;
        }

        selectedFiles.clear();
        const selectAll = document.getElementById('selectAllFiles');
        if (selectAll) selectAll.checked = false;
        updateDeleteSelectedButton();
        
        response.data.files.forEach(file => {
            const div = document.createElement('div');
            div.className = 'flex items-center justify-between p-3 border border-gray-200 rounded-lg';
            
            const sizeStr = formatFileSize(file.size);
            const dateStr = new Date(file.modified * 1000).toLocaleString();
            
            div.innerHTML = `
                <div class="flex items-center">
                    <input type="checkbox" class="mr-3 file-select-checkbox" data-filename="${file.name}">
                    <i class="fas fa-file mr-3 text-gray-400"></i>
                    <div>
                        <p class="text-sm font-medium text-gray-900">${file.name}</p>
                        <p class="text-xs text-gray-500">${sizeStr} • ${dateStr}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="downloadFile('${file.name}')" 
                            class="text-blue-600 hover:text-blue-800 text-sm">
                        <i class="fas fa-download"></i>
                    </button>
                    <button onclick="deleteFile('${file.name}')" 
                            class="text-red-600 hover:text-red-800 text-sm">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            const checkbox = div.querySelector('.file-select-checkbox');
            checkbox.addEventListener('change', (e) => {
                const name = e.target.getAttribute('data-filename');
                if (e.target.checked) {
                    selectedFiles.add(name);
                } else {
                    selectedFiles.delete(name);
                }
                updateDeleteSelectedButton();
            });

            filesList.appendChild(div);
        });
    } catch (error) {
        console.error('加载文件列表失败:', error);
    }
}

// 上传文件（支持多文件）
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const files = Array.from(fileInput.files || []);
    
    if (!files.length) {
        await showAlert('请选择文件');
        return;
    }
    
    const allowedTypes = ['.xlsx', '.xls', '.csv'];
    const uploadBtn = document.getElementById('uploadBtn');
    const originalContent = uploadBtn.innerHTML;
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>上传中...';
        
        let successCount = 0;
        let failMessages = [];
        
        for (const file of files) {
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            if (!allowedTypes.includes(fileExtension)) {
                failMessages.push(`${file.name}: 不支持的文件类型`);
                continue;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/files/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.detail || '上传失败');
                }
                successCount += 1;
            } catch (e) {
                failMessages.push(`${file.name}: ${e.message}`);
            }
        }
        
        // 刷新列表和重置UI
        loadFiles();
        fileInput.value = '';
        updateFileSelection();
        
        let message = '';
        if (successCount > 0) {
            message += `成功上传 ${successCount} 个文件。`;
        }
        if (failMessages.length > 0) {
            message += '\n以下文件上传失败:\n' + failMessages.join('\n');
        }
        
        if (message) {
            await showAlert(message.trim(), successCount > 0 ? '上传结果' : '上传失败');
        }
        
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalContent;
    }
}

// 下载文件
function downloadFile(filename) {
    const link = document.createElement('a');
    link.href = `/api/files/${filename}/download`;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 删除文件
async function deleteFile(filename) {
    const confirmed = await showConfirm(`确定要删除文件 "${filename}" 吗？`, '确认删除');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await axios.delete(`/api/files/${filename}`);
        await showAlert(response.data.message, '操作成功');
        loadFiles();
    } catch (error) {
        await showAlert('删除失败: ' + error.message, '错误');
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 更新文件选择信息
function updateFileSelection() {
    const fileInput = document.getElementById('fileInput');
    const selectedFilesInfo = document.getElementById('selectedFilesInfo');
    const uploadBtn = document.getElementById('uploadBtn');
    const files = Array.from(fileInput.files || []);
    
    if (files.length === 0) {
        selectedFilesInfo.textContent = '未选择文件';
        uploadBtn.disabled = true;
    } else if (files.length === 1) {
        const totalSize = files[0].size;
        selectedFilesInfo.textContent = `已选择 1 个文件 (${formatFileSize(totalSize)})`;
        uploadBtn.disabled = false;
    } else {
        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        selectedFilesInfo.textContent = `已选择 ${files.length} 个文件 (${formatFileSize(totalSize)})`;
        uploadBtn.disabled = false;
    }
}
