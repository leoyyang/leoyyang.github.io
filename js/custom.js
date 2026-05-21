/**
 * 自定义JavaScript功能
 * 实现滚动触发动画和按钮交互效果
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ===============================================
    // 滚动触发动画
    // ===============================================
    
    function initScrollAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    // 为了性能，一旦动画触发就停止观察
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // 观察所有需要动画的元素
        const animateElements = document.querySelectorAll(
            '.pub-list-item, .card, .home-section, .article-container, .featurette'
        );
        
        animateElements.forEach(el => {
            el.classList.add('animate-on-scroll');
            observer.observe(el);
        });
    }

    // ===============================================
    // 按钮涟漪效果
    // ===============================================
    
    function addRippleEffect() {
        const buttons = document.querySelectorAll('.btn-outline-primary, .btn-primary');
        
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                // 移除现有的涟漪
                const existingRipple = this.querySelector('.ripple');
                if (existingRipple) {
                    existingRipple.remove();
                }
                
                // 创建新的涟漪效果
                const ripple = document.createElement('span');
                ripple.classList.add('ripple');
                
                // 计算涟漪位置
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                
                this.appendChild(ripple);
                
                // 清理涟漪元素
                setTimeout(() => {
                    if (ripple.parentNode) {
                        ripple.remove();
                    }
                }, 600);
            });
        });
    }

    // ===============================================
    // 按钮颜色增强
    // ===============================================
    
    function enhanceButtonColors() {
        const buttons = document.querySelectorAll('.btn-links .btn');
        
        buttons.forEach(button => {
            const href = button.getAttribute('href') || '';
            const text = button.textContent.toLowerCase();
            
            // 根据链接或文本内容添加特定的数据属性
            if (href.includes('arxiv') || text.includes('arxiv')) {
                button.setAttribute('data-arxiv', 'true');
            } else if (href.includes('ssrn') || text.includes('ssrn')) {
                button.setAttribute('data-ssrn', 'true');
            } else if (href.includes('scholar.google') || text.includes('scholar')) {
                button.setAttribute('data-scholar', 'true');
            } else if (href.includes('github') || text.includes('github')) {
                button.setAttribute('data-github', 'true');
            } else if (href.includes('dataverse') || text.includes('dataverse')) {
                button.setAttribute('data-dataverse', 'true');
            } else if (href.includes('repec') || text.includes('repec')) {
                button.setAttribute('data-repec', 'true');
            } else if (href.includes('doi.org') || text.includes('doi')) {
                button.setAttribute('data-doi', 'true');
            }
        });
    }

    // ===============================================
    // 平滑滚动增强
    // ===============================================
    
    function enhanceSmoothScroll() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    
                    // 计算目标位置，考虑固定导航栏
                    const headerHeight = document.querySelector('.navbar')?.offsetHeight || 0;
                    const targetPosition = target.offsetTop - headerHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    // ===============================================
    // 图片懒加载优化
    // ===============================================
    
    function optimizeImageLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        } else {
            // 降级处理
            images.forEach(img => {
                img.src = img.dataset.src;
            });
        }
    }

    // ===============================================
    // 主题切换动画
    // ===============================================
    
    function enhanceThemeToggle() {
        const themeToggle = document.querySelector('.js-set-theme-light, .js-set-theme-dark, .js-set-theme-auto');
        
        if (themeToggle) {
            // 监听主题变化
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        // 添加主题切换动画
                        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
                        
                        setTimeout(() => {
                            document.body.style.transition = '';
                        }, 300);
                    }
                });
            });
            
            observer.observe(document.body, {
                attributes: true,
                attributeFilter: ['class']
            });
        }
    }

    // ===============================================
    // 性能优化
    // ===============================================
    
    function optimizePerformance() {
        // 防抖函数
        function debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
        
        // 优化滚动事件
        let ticking = false;
        function updateScrollPosition() {
            // 可以在这里添加滚动相关的优化
            ticking = false;
        }
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateScrollPosition);
                ticking = true;
            }
        });
        
        // 优化窗口大小调整
        window.addEventListener('resize', debounce(() => {
            // 重新计算动画元素
            initScrollAnimations();
        }, 250));
    }

    // ===============================================
    // 辅助功能增强
    // ===============================================
    
    function enhanceAccessibility() {
        // 为动画元素添加 prefers-reduced-motion 支持
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (prefersReducedMotion.matches) {
            // 禁用动画
            const style = document.createElement('style');
            style.textContent = `
                *, *::before, *::after {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
            `;
            document.head.appendChild(style);
        }
        
        // 键盘导航支持
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    // ===============================================
    // 错误处理
    // ===============================================
    
    function setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.warn('JavaScript error in custom.js:', e.error);
        });
        
        // 捕获Promise错误
        window.addEventListener('unhandledrejection', (e) => {
            console.warn('Unhandled promise rejection in custom.js:', e.reason);
        });
    }

    // ===============================================
    // 初始化所有功能
    // ===============================================
    
    function initializeCustomFeatures() {
        try {
            setupErrorHandling();
            initScrollAnimations();
            addRippleEffect();
            enhanceButtonColors();
            enhanceSmoothScroll();
            optimizeImageLoading();
            enhanceThemeToggle();
            optimizePerformance();
            enhanceAccessibility();
            
            console.log('Custom features initialized successfully');
        } catch (error) {
            console.error('Error initializing custom features:', error);
        }
    }

    // 启动初始化
    initializeCustomFeatures();
    
    // 为动态加载的内容重新初始化
    const contentObserver = new MutationObserver((mutations) => {
        let shouldReinit = false;
        
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE && 
                        (node.classList.contains('pub-list-item') || 
                         node.classList.contains('card') ||
                         node.querySelector('.btn-links'))) {
                        shouldReinit = true;
                    }
                });
            }
        });
        
        if (shouldReinit) {
            // 延迟重新初始化以避免性能问题
            setTimeout(() => {
                enhanceButtonColors();
                addRippleEffect();
            }, 100);
        }
    });
    
    contentObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// ===============================================
// 全局工具函数
// ===============================================

window.customUtils = {
    // 添加加载指示器
    showLoadingIndicator: function(element) {
        const indicator = document.createElement('div');
        indicator.className = 'loading-indicator';
        indicator.style.margin = '20px auto';
        element.appendChild(indicator);
        return indicator;
    },
    
    // 移除加载指示器
    hideLoadingIndicator: function(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.remove();
        }
    },
    
    // 创建通知
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#f44336' : '#4caf50'};
            color: white;
            border-radius: 4px;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}; 