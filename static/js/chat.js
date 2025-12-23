// ===================== 字段映射 =====================
const FIELD_LABEL_MAP = {
    // 学生表字段
    sno: '学号',
    sname: '学生姓名',
    sex: '性别',
    age: '年龄',
    native: '籍贯',
    semester: '学期',
    home: '家庭住址',
    telephone: '电话',
    entime: '入学时间',
    'classno_id': '班级ID',

    // 班级表字段
    classno: '班级编号',
    classname: '班级名称',
    'dno_id': '系部ID',

    // 系部表字段
    dno: '系部编号',
    dname: '系部名称',
    // 注意：telephone 在多个表里出现，这里保持原逻辑不变
    // 'telephone': '电话',

    // 课程表字段
    cno: '课程编号',
    cname: '课程名称',
    lecture: '学时',
    credit: '学分',
    type: '课程类型',

    // 成绩表字段
    grade: '成绩',
    id: '记录ID',

    // 跨表查询字段
    'classno__classname': '班级名称',
    'classno__classno': '班级编号',
    'cno__cname': '课程名称',
    'cno__cno': '课程编号',

    // 聚合字段
    total: '总计',
    total_credit: '课程总学分',
    avg: '平均值',
    count: '数量'
};

// ===================== 工具函数 =====================

// 转义 HTML
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// 安全处理值
function makeSafe(value) {
    if (value === null || value === undefined) return '';
    if (value instanceof Date) return value.toLocaleString();
    if (typeof value === 'object') return JSON.stringify(value);
    return value;
}

// 递归生成表格
function buildTableHTML(data) {
    if (!data || !Array.isArray(data) || data.length === 0) {
        return '<div class="text-muted">无数据</div>';
    }

    const keys = Object.keys(data[0]);
    let html = `<div class="table-responsive"><table class="table table-bordered table-sm mb-2"><thead><tr>`;

    keys.forEach(k => {
        const label = FIELD_LABEL_MAP[k] || k.replace(/_/g, ' ');
        html += `<th>${escapeHtml(label)}</th>`;
    });

    html += `</tr></thead><tbody>`;

    data.forEach(row => {
        html += '<tr>';
        keys.forEach(k => {
            const value = makeSafe(row[k]);
            html += `<td>${escapeHtml(value)}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
}

// 从文本中提取 JSON 数组（支持 ```json ... ``` 或直接 [...]）
function extractJSONArray(content) {
    if (!content) return null;

    // 1) 优先匹配 ```json ... ```
    const fenced = content.match(/```json([\s\S]*?)```/i);
    if (fenced && fenced[1]) {
        const candidate = fenced[1].trim();
        if (candidate.startsWith('[') && candidate.endsWith(']')) return candidate;
    }

    // 2) 退回匹配第一个 [...]（原逻辑）
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    return jsonMatch ? jsonMatch[0] : null;
}

// 格式化 AI 结果
function formatAIResult(content) {
    try {
        const jsonText = extractJSONArray(content);
        if (!jsonText) return content;

        const data = JSON.parse(jsonText);
        let html = '';

        data.forEach((step) => {
            html += `<div class="ai-step mb-4">`;

            // 步骤标题（保持你原来写死“查询成功”的展示）
            html += `<div class="ai-step-header mb-2"><span class="badge bg-primary me-2">查询成功</span></div>`;

            // 多表处理
            if (step.type === 'multi' && Array.isArray(step.data)) {
                step.data.forEach(tbl => {
                    if (tbl.title && Array.isArray(tbl.data)) {
                        html += `<h5 class="mt-2 mb-2">${escapeHtml(tbl.title)}</h5>`;
                        html += buildTableHTML(tbl.data);
                    }
                });
            }
            // 单表或普通对象数组
            else if (step.data && Array.isArray(step.data) && typeof step.data[0] === 'object') {
                html += buildTableHTML(step.data);
            }
            // 聚合/对象
            else if (step.data && typeof step.data === 'object') {
                const keys = Object.keys(step.data);
                if (keys.length === 1) {
                    const key = keys[0];
                    html += `<div class="ai-aggregate-result mb-2"><strong>${escapeHtml(key)}:</strong> <span class="badge bg-warning">${escapeHtml(step.data[key])}</span></div>`;
                } else {
                    html += buildTableHTML([step.data]);
                }
            }

            // 错误信息
            if (step.error) {
                html += `<div class="ai-error-result mb-2 text-danger"><i class="bi bi-x-circle-fill me-1"></i>${escapeHtml(step.error)}</div>`;
            }

            html += `</div>`; // ai-step
        });

        return html;
    } catch (e) {
        console.error('格式化AI结果出错:', e);
        return content;
    }
}

// 应用 AI 格式化
function applyAIFormatting() {
    const containers = document.querySelectorAll('.ai-result-container');
    containers.forEach(c => {
        // 关键：用 textContent，避免 innerHTML 里已有 <p><br> 被再次解析导致内容“固定/异常”
        const originalText = c.textContent || '';
        const formatted = formatAIResult(originalText);

        // 如果格式化后变成 HTML（有表格），才替换
        if (formatted !== originalText) {
            c.innerHTML = formatted;
        }
    });
}

// 滚动到底部
function scrollBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);
}

document.addEventListener('DOMContentLoaded', function () {
    applyAIFormatting();
    scrollBottom();

    // 清空聊天
    const clearChatBtn = document.getElementById('clearChat');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', function () {
            if (confirm('确定清空对话吗？')) window.location.href = '/chat/?clear=1';
        });
    }

    // 表单提交：保持你原逻辑（fetch -> reload）
    const chatForm = document.getElementById('chatForm');
    const sendBtn = document.getElementById('sendBtn');

    if (chatForm) {
        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();

            if (sendBtn) sendBtn.disabled = true;

            const formData = new FormData(chatForm);
            fetch(chatForm.action || window.location.href, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(res => res.text())
                .then(() => window.location.reload())
                .catch(err => {
                    console.error(err);
                    alert('提交失败');
                    if (sendBtn) sendBtn.disabled = false;
                });
        });
    }

    // Enter 发送（保持你原逻辑：Enter 直接 submit；不做 shift+enter 多行）
    const messageInput = document.getElementById('messageInput');
    if (messageInput && chatForm) {
        messageInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.requestSubmit();
            }
        });
    }
});
// 打开示例弹窗
const showExamplesBtn = document.getElementById('showExamples');
if (showExamplesBtn) {
    showExamplesBtn.addEventListener('click', () => {
        const modalEl = document.getElementById('examplesModal');
        if (!modalEl) return;
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    });
}

// 点击示例问题 -> 填入输入框
document.querySelectorAll('.example-question').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const question = e.currentTarget.dataset.question || '';
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = question;
            messageInput.focus();
        }
        // 关闭 modal
        const modalEl = document.getElementById('examplesModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
    });
});

// 导出对话
const exportChatBtn = document.getElementById('exportChat');
if (exportChatBtn) {
    exportChatBtn.addEventListener('click', () => exportChat());
}

// 导出函数：从 DOM 中提取消息文本
function exportChat() {
    const messageNodes = document.querySelectorAll('#chatMessages .message');
    if (!messageNodes || messageNodes.length === 0) {
        alert('暂无对话可导出');
        return;
    }

    let text = '学生信息管理系统 - AI 对话记录\n';
    text += '导出时间: ' + new Date().toLocaleString('zh-CN') + '\n';
    text += '='.repeat(50) + '\n\n';

    messageNodes.forEach(node => {
        // 根据是否有 text-end 判断用户/AI（保持与你模板一致）
        const isUser = node.classList.contains('text-end');
        const role = isUser ? '用户' : 'AI助手';

        // 取卡片里的纯文本（表格也会被转成文本导出）
        const body = node.querySelector('.card-body');
        const content = body ? body.textContent.trim() : '';

        if (!content) return;
        text += `【${role}】\n${content}\n\n`;
        text += '-'.repeat(50) + '\n\n';
    });

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `AI对话记录_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
}
