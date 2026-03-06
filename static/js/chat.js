function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function buildTableHTML(rows) {
    if (!Array.isArray(rows) || rows.length === 0) {
        return '<div class="text-muted">暂无结果</div>';
    }

    const columns = Object.keys(rows[0]);
    const header = columns.map(function (column) {
        return '<th>' + escapeHtml(column) + '</th>';
    }).join('');

    const body = rows.map(function (row) {
        const cells = columns.map(function (column) {
            const value = row[column] == null ? '' : String(row[column]);
            return '<td>' + escapeHtml(value) + '</td>';
        }).join('');
        return '<tr>' + cells + '</tr>';
    }).join('');

    return '<div class="table-responsive"><table class="table table-sm table-bordered align-middle mb-0"><thead><tr>' + header + '</tr></thead><tbody>' + body + '</tbody></table></div>';
}

function extractJSONArray(content) {
    const fenced = content.match(/```json([\s\S]*?)```/i);
    if (fenced && fenced[1]) {
        const candidate = fenced[1].trim();
        if (candidate.startsWith('[') && candidate.endsWith(']')) {
            return candidate;
        }
    }

    const jsonMatch = content.match(/\[[\s\S]*\]/);
    return jsonMatch ? jsonMatch[0] : null;
}

function formatAIResult(content) {
    try {
        const jsonText = extractJSONArray(content);
        if (!jsonText) {
            return content;
        }

        const data = JSON.parse(jsonText);
        let html = '';

        data.forEach(function (step) {
            html += '<div class="ai-step mb-4">';
            html += '<div class="ai-step-header mb-2"><span class="badge bg-primary me-2">查询成功</span></div>';

            if (step.type === 'multi' && Array.isArray(step.data)) {
                step.data.forEach(function (table) {
                    if (table.title && Array.isArray(table.data)) {
                        html += '<h5 class="mt-2 mb-2">' + escapeHtml(table.title) + '</h5>';
                        html += buildTableHTML(table.data);
                    }
                });
            } else if (step.data && Array.isArray(step.data) && typeof step.data[0] === 'object') {
                html += buildTableHTML(step.data);
            } else if (step.data && typeof step.data === 'object') {
                const keys = Object.keys(step.data);
                if (keys.length === 1) {
                    const key = keys[0];
                    html += '<div class="ai-aggregate-result mb-2"><strong>' + escapeHtml(key) + ':</strong> <span class="badge bg-warning">' + escapeHtml(step.data[key]) + '</span></div>';
                } else {
                    html += buildTableHTML([step.data]);
                }
            }

            if (step.error) {
                html += '<div class="ai-error-result mb-2 text-danger"><i class="bi bi-x-circle-fill me-1"></i>' + escapeHtml(step.error) + '</div>';
            }

            html += '</div>';
        });

        return html;
    } catch (error) {
        console.error('格式化 AI 结果出错:', error);
        return content;
    }
}

function applyAIFormatting(root) {
    const scope = root || document;
    scope.querySelectorAll('.ai-result-container').forEach(function (container) {
        const originalText = container.textContent || '';
        const formatted = formatAIResult(originalText);
        if (formatted !== originalText) {
            container.innerHTML = formatted;
        }
    });
}

function scrollBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        return;
    }
    window.setTimeout(function () {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);
}

function setChatStatus(message) {
    const status = document.getElementById('chatStatus');
    if (!status) {
        return;
    }
    status.textContent = message || '';
    status.classList.toggle('d-none', !message);
}

function renderChatMessages(html) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        return;
    }
    chatMessages.innerHTML = html;
    applyAIFormatting(chatMessages);
    scrollBottom();
}

document.addEventListener('DOMContentLoaded', function () {
    applyAIFormatting(document);
    scrollBottom();

    const chatForm = document.getElementById('chatForm');
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    if (chatForm) {
        chatForm.addEventListener('submit', function (event) {
            event.preventDefault();

            const message = messageInput ? messageInput.value.trim() : '';
            if (!message) {
                setChatStatus('请输入内容');
                if (messageInput) {
                    messageInput.focus();
                }
                return;
            }

            setChatStatus('');
            if (typeof showLoading === 'function') {
                showLoading();
            }
            if (sendBtn) {
                sendBtn.disabled = true;
            }

            const formData = new FormData(chatForm);
            fetch(chatForm.action || window.location.href, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (response) {
                    return response.json().then(function (payload) {
                        if (!response.ok) {
                            throw new Error(payload.error || '提交失败');
                        }
                        return payload;
                    });
                })
                .then(function (payload) {
                    renderChatMessages(payload.messages_html || '');
                    if (messageInput) {
                        messageInput.value = '';
                        messageInput.focus();
                    }
                })
                .catch(function (error) {
                    console.error(error);
                    setChatStatus(error.message || '提交失败');
                })
                .finally(function () {
                    if (typeof hideLoading === 'function') {
                        hideLoading();
                    }
                    if (sendBtn) {
                        sendBtn.disabled = false;
                    }
                });
        });
    }

    if (messageInput && chatForm) {
        messageInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                chatForm.requestSubmit();
            }
        });
    }

    const showExamples = document.getElementById('showExamples');
    const examplesModal = document.getElementById('examplesModal');
    if (showExamples && examplesModal) {
        showExamples.addEventListener('click', function () {
            bootstrap.Modal.getOrCreateInstance(examplesModal).show();
        });
    }

    document.querySelectorAll('.example-question').forEach(function (button) {
        button.addEventListener('click', function () {
            if (messageInput) {
                messageInput.value = button.dataset.question || '';
                messageInput.focus();
            }
            if (examplesModal) {
                bootstrap.Modal.getOrCreateInstance(examplesModal).hide();
            }
        });
    });

    const exportChatBtn = document.getElementById('exportChat');
    if (exportChatBtn) {
        exportChatBtn.addEventListener('click', exportChat);
    }
});

function exportChat() {
    const messageNodes = document.querySelectorAll('#chatMessages .message');
    if (!messageNodes.length) {
        alert('暂无对话可导出');
        return;
    }

    let text = '学生信息管理系统 - AI 对话记录\n';
    text += '导出时间: ' + new Date().toLocaleString('zh-CN') + '\n';
    text += '='.repeat(50) + '\n\n';

    messageNodes.forEach(function (node) {
        const isUser = node.classList.contains('text-end');
        const role = isUser ? '用户' : 'AI助手';
        const body = node.querySelector('.card-body');
        const content = body ? body.textContent.trim() : '';
        if (!content) {
            return;
        }
        text += '【' + role + '】\n' + content + '\n\n';
        text += '-'.repeat(50) + '\n\n';
    });

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'AI对话记录_' + new Date().toISOString().slice(0, 10) + '.txt';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
}
