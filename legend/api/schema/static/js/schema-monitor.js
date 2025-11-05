/**
 * Schema注册监控系统 - 通用JavaScript功能
 */

// 通用工具函数
const schemaMonitor = {
    // API基础URL
    apiBaseUrl: '/schema-monitor',

    // 存储全局状态
    state: {
        pulsar_admin_url: localStorage.getItem('pulsar_admin_url') || '',
        lastHealthCheck: null,
        registryInfo: null,
        metrics: null,
        history: null
    },

    // 格式化日期时间
    formatDateTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    // 格式化时间
    formatTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    // 格式化JSON
    formatJson(json) {
        try {
            if (typeof json === 'string') {
                json = JSON.parse(json);
            }
            return JSON.stringify(json, null, 2);
        } catch (e) {
            return json || '';
        }
    },

    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('复制成功!', 'success');
            return true;
        } catch (err) {
            console.error('无法复制到剪贴板', err);
            this.showToast('复制失败: ' + err.message, 'error');
            return false;
        }
    },

    // 显示Toast通知
    showToast(message, type = 'info', duration = 3000) {
        // 如果存在旧的toast，先移除
        const existingToast = document.querySelector('#toast-notification');
        if (existingToast) {
            document.body.removeChild(existingToast);
        }

        // 创建新的toast
        const toast = document.createElement('div');
        toast.id = 'toast-notification';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.padding = '10px 15px';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '250px';
        toast.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';
        toast.style.transition = 'all 0.3s ease';

        // 设置类型样式
        let icon = '';
        switch (type) {
            case 'success':
                toast.style.backgroundColor = '#10b981';
                toast.style.color = 'white';
                icon = '<i class="fas fa-check-circle mr-2"></i>';
                break;
            case 'error':
                toast.style.backgroundColor = '#ef4444';
                toast.style.color = 'white';
                icon = '<i class="fas fa-exclamation-circle mr-2"></i>';
                break;
            case 'warning':
                toast.style.backgroundColor = '#f59e0b';
                toast.style.color = 'white';
                icon = '<i class="fas fa-exclamation-triangle mr-2"></i>';
                break;
            default:
                toast.style.backgroundColor = '#6366f1';
                toast.style.color = 'white';
                icon = '<i class="fas fa-info-circle mr-2"></i>';
        }

        toast.innerHTML = `<div class="flex items-center">${icon}<span>${message}</span></div>`;
        document.body.appendChild(toast);

        // 显示toast
        setTimeout(() => {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        }, 50);

        // 自动隐藏
        setTimeout(() => {
            toast.style.transform = 'translateY(20px)';
            toast.style.opacity = '0';

            // 移除元素
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, duration);
    },

    // 显示加载状态
    showLoader(element, size = 'normal') {
        const loader = `<div class="loading-indicator ${size === 'large' ? 'large' : ''}"></div>`;
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = loader;
        }
        return loader;
    },

    // 隐藏加载状态
    hideLoader(element, content = '') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = content;
        }
    },

    // 显示错误状态
    showError(element, message = '加载失败') {
        const errorHtml = `<div class="text-error"><i class="fas fa-exclamation-circle mr-2"></i>${message}</div>`;
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = errorHtml;
        }
        return errorHtml;
    },

    // API请求包装器
    async fetchAPI(endpoint, options = {}) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        try {
            const response = await fetch(url, options);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP错误: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API请求失败 (${url}):`, error);
            throw error;
        }
    },

    // 获取健康状态
    async getHealth(pulsar_admin_url = null) {
        const queryParams = new URLSearchParams();
        if (pulsar_admin_url) {
            queryParams.set('pulsar_admin_url', pulsar_admin_url);
        }

        const url = `/health${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
        const data = await this.fetchAPI(url);
        this.state.lastHealthCheck = data;
        return data;
    },

    // 获取注册表信息
    async getRegistry() {
        const data = await this.fetchAPI('/registry');
        this.state.registryInfo = data;
        return data;
    },

    // 获取指标数据
    async getMetrics(days = 7) {
        const data = await this.fetchAPI(`/metrics?days=${days}`);
        this.state.metrics = data;
        return data;
    },

    // 获取历史记录
    async getHistory(limit = 10) {
        const data = await this.fetchAPI(`/history?limit=${limit}`);
        this.state.history = data;
        return data;
    },

    // 获取Schema详情
    async getSchemaInfo(schemaName) {
        return await this.fetchAPI(`/schema/${schemaName}`);
    },

    // 获取Schema历史
    async getSchemaHistory(schemaName) {
        return await this.fetchAPI(`/schema/${schemaName}/history`);
    },

    // 验证Schema数据
    async validateSchema(schemaName, data) {
        return await this.fetchAPI(`/schema/${schemaName}/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ data })
        });
    },

    // 检查Schema兼容性
    async checkCompatibility(schemaName, schema) {
        return await this.fetchAPI(`/schema/${schemaName}/compatibility`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ schema })
        });
    },

    // 存储设置
    saveSettings(settings) {
        for (const [key, value] of Object.entries(settings)) {
            localStorage.setItem(key, value);
            this.state[key] = value;
        }
    },

    // 初始化
    init() {
        // 从LocalStorage加载设置
        this.state.pulsar_admin_url = localStorage.getItem('pulsar_admin_url') || '';

        // 添加全局事件监听
        document.addEventListener('click', (e) => {
            // 复制按钮处理
            if (e.target.closest('.copy-btn')) {
                const btn = e.target.closest('.copy-btn');
                const textToCopy = btn.getAttribute('data-copy');
                if (textToCopy) {
                    this.copyToClipboard(textToCopy);
                }
            }
        });
    }
};

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', () => {
    schemaMonitor.init();
});

// 导出
window.schemaMonitor = schemaMonitor; 