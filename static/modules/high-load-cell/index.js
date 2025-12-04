// 高负荷小区监控相关功能
// noinspection ExceptionCaughtLocallyJS

// 显示高负荷小区监控面板
function showHighLoadCellPanel() {
    hideAllPanels();
    updateNavigation('nav-high-load-cell');
    const panel = document.getElementById('highLoadCellPanel');
    if (panel) {
        panel.classList.remove('hidden');
    }
    document.getElementById('searchContainer').classList.add('hidden');
    document.getElementById('pageTitle').textContent = '突发高负荷小区监控';
    document.getElementById('pageSubtitle').textContent = '监控突发高负荷小区清单';
    
    // 初始化时间范围（默认最近1小时，整点对齐）
    const now = new Date();
    // 结束时间：当前整点（例如1:15 -> 1:00）
    const endTime = new Date(now);
    endTime.setMinutes(0);
    endTime.setSeconds(0);
    endTime.setMilliseconds(0);
    
    // 开始时间：结束时间往前1小时（例如1:00 -> 12:00）
    const startTime = new Date(endTime);
    startTime.setHours(startTime.getHours() - 1);
    
    const startTimeInput = document.getElementById('overloadStartTime');
    const endTimeInput = document.getElementById('overloadEndTime');
    
    if (startTimeInput && endTimeInput) {
        startTimeInput.value = formatDateTimeLocal(startTime);
        endTimeInput.value = formatDateTimeLocal(endTime);
    }
}

// 格式化日期时间为datetime-local格式
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// 查询突发高负荷数据
async function queryOverloadData() {
    const startTimeInput = document.getElementById('overloadStartTime');
    const endTimeInput = document.getElementById('overloadEndTime');
    
    if (!startTimeInput || !endTimeInput) {
        await showAlert('页面元素未加载完成，请稍后再试', '错误');
        return;
    }
    
    const startTime = startTimeInput.value;
    const endTime = endTimeInput.value;
    
    if (!startTime || !endTime) {
        await showAlert('请选择开始时间和结束时间', '提示');
        return;
    }
    
    if (new Date(startTime) > new Date(endTime)) {
        await showAlert('开始时间不能晚于结束时间', '错误');
        return;
    }
    
    // 转换时间格式为SQL需要的格式
    const startTimeFormatted = startTime.replace('T', ' ') + ':00';
    const endTimeFormatted = endTime.replace('T', ' ') + ':00';
    
    const loadingDiv = document.getElementById('overloadLoading');
    const noDataDiv = document.getElementById('overloadNoData');
    const dataTableDiv = document.getElementById('overloadDataTable');
    
    try {
        // 显示加载状态
        loadingDiv.classList.remove('hidden');
        noDataDiv.classList.add('hidden');
        dataTableDiv.classList.add('hidden');
        
        const response = await axios.get('/api/query/overload', {
            params: {
                start_time: startTimeFormatted,
                end_time: endTimeFormatted
            }
        });
        
        const result = response.data;
        
        // 更新统计信息
        document.getElementById('stat-4g-total').textContent = result.stats['4G'].total;
        document.getElementById('stat-4g-burst').textContent = result.stats['4G'].burst;
        document.getElementById('stat-5g-total').textContent = result.stats['5G'].total;
        document.getElementById('stat-5g-burst').textContent = result.stats['5G'].burst;
        
        // 更新重要区域统计
        document.getElementById('stat-4g-total-important').textContent = result.stats['4G'].total_important || 0;
        document.getElementById('stat-4g-burst-important').textContent = result.stats['4G'].burst_important || 0;
        document.getElementById('stat-5g-total-important').textContent = result.stats['5G'].total_important || 0;
        document.getElementById('stat-5g-burst-important').textContent = result.stats['5G'].burst_important || 0;
        
        // 更新总记录数
        document.getElementById('overloadTotalCount').textContent = result.total_count;
        
        if (result.data.length === 0) {
            loadingDiv.classList.add('hidden');
            noDataDiv.classList.remove('hidden');
        } else {
            loadingDiv.classList.add('hidden');
            dataTableDiv.classList.remove('hidden');
            renderOverloadTable(result.data);
        }
        
    } catch (error) {
        loadingDiv.classList.add('hidden');
        await showAlert('查询失败: ' + error.message, '错误');
    }
}

// 渲染突发高负荷数据表格
function renderOverloadTable(data) {
    const header = document.getElementById('overloadTableHeader');
    const body = document.getElementById('overloadTableBody');
    
    if (data.length === 0) {
        return;
    }
    
    // 获取列名
    const columns = Object.keys(data[0]);
    
    // 渲染表头
    header.innerHTML = '';
    const headerRow = document.createElement('tr');
    columns.forEach(column => {
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
    data.forEach((row) => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-200 hover:bg-gray-50';
        
        // 根据是否突发高负荷设置行背景色
        if (row['是否突发高负荷'] === '是') {
            tr.classList.add('bg-red-50');
        }
        
        columns.forEach(column => {
            const td = document.createElement('td');
            td.className = 'px-3 py-2 text-sm text-gray-900';
            td.style.minWidth = '100px';
            td.style.maxWidth = '250px';
            td.style.overflow = 'hidden';
            td.style.textOverflow = 'ellipsis';
            td.style.whiteSpace = 'nowrap';
            
            let cellValue = row[column] || '';
            
            // 格式化数值显示
            if (column === '上行利用率' || column === '下行利用率') {
                if (typeof cellValue === 'number' || (typeof cellValue === 'string' && !isNaN(cellValue))) {
                    cellValue = (parseFloat(cellValue) * 100).toFixed(2) + '%';
                }
            }
            
            td.title = cellValue;
            td.textContent = cellValue;
            tr.appendChild(td);
        });
        
        body.appendChild(tr);
    });
}

// 重置时间范围
function resetOverloadTimeRange() {
    // 重置为最近1小时，整点对齐
    const now = new Date();
    // 结束时间：当前整点（例如1:15 -> 1:00）
    const endTime = new Date(now);
    endTime.setMinutes(0);
    endTime.setSeconds(0);
    endTime.setMilliseconds(0);
    
    // 开始时间：结束时间往前1小时（例如1:00 -> 12:00）
    const startTime = new Date(endTime);
    startTime.setHours(startTime.getHours() - 1);
    
    const startTimeInput = document.getElementById('overloadStartTime');
    const endTimeInput = document.getElementById('overloadEndTime');
    
    if (startTimeInput && endTimeInput) {
        startTimeInput.value = formatDateTimeLocal(startTime);
        endTimeInput.value = formatDateTimeLocal(endTime);
    }
}

// 导出突发高负荷数据
async function exportOverloadData(format) {
    const startTimeInput = document.getElementById('overloadStartTime');
    const endTimeInput = document.getElementById('overloadEndTime');
    
    if (!startTimeInput || !endTimeInput || !startTimeInput.value || !endTimeInput.value) {
        await showAlert('请先查询数据', '提示');
        return;
    }
    
    const startTime = startTimeInput.value.replace('T', ' ') + ':00';
    const endTime = endTimeInput.value.replace('T', ' ') + ':00';
    
    try {
        // 构建下载URL
        const url = `/api/query/overload/download?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}&format=${format}`;
        
        // 使用fetch下载文件
        const response = await fetch(url);
        
        if (!response.ok) {
            // 尝试获取详细的错误信息
            let errorMessage = `下载失败: ${response.status} ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMessage = `下载失败: ${errorData.detail}`;
                }
            } catch (e) {
                // 如果无法解析JSON，使用默认错误信息
                const errorText = await response.text();
                if (errorText) {
                    errorMessage = `下载失败: ${errorText.substring(0, 200)}`;
                }
            }
            throw new Error(errorMessage);
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `突发高负荷小区_${startTime.replace(/[: ]/g, '-')}_${endTime.replace(/[: ]/g, '-')}.${format}`;
        
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
            if (utf8Match) {
                filename = decodeURIComponent(utf8Match[1]);
            }
        }
        
        // 创建blob并下载
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理blob URL
        window.URL.revokeObjectURL(downloadUrl);
        
    } catch (error) {
        await showAlert('导出失败: ' + error.message, '错误');
    }
}

// 注意：CSV和Excel导出功能已移至后端API，通过exportOverloadData函数统一处理

