/**
 * Global Loading Overlay System
 * Handles all loading states across the application
 */

// Global loader object
const GlobalLoader = {
    overlay: null,
    
    // Initialize the loader
    init() {
        // Create loader overlay if it doesn't exist
        if (!document.getElementById('globalLoaderOverlay')) {
            const loaderHTML = `
                <div id="globalLoaderOverlay" class="global-loader-overlay">
                    <div class="loader-container">
                        <div class="loader-spinner"></div>
                        <div class="loader-text" id="loaderText">Loading...</div>
                        <div class="loader-subtext" id="loaderSubtext">Please wait</div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', loaderHTML);
        }
        
        this.overlay = document.getElementById('globalLoaderOverlay');
        this.setupEventListeners();
    },
    
    // Show loader with custom message
    show(message = 'Loading...', subtext = 'Please wait') {
        if (!this.overlay) this.init();
        
        document.getElementById('loaderText').textContent = message;
        document.getElementById('loaderSubtext').textContent = subtext;
        this.overlay.classList.add('active');
    },
    
    // Hide loader
    hide() {
        if (this.overlay) {
            this.overlay.classList.remove('active');
        }
    },
    
    // Setup automatic event listeners
    setupEventListeners() {
        // Show loader on page navigation
        window.addEventListener('beforeunload', () => {
            this.show('Loading page...', 'Please wait');
        });
        
        // Hide loader when page loads
        window.addEventListener('load', () => {
            this.hide();
        });
        
        // Handle all form submissions
        document.addEventListener('submit', (e) => {
            const form = e.target;
            
            // Skip if form has data-no-loader attribute
            if (form.hasAttribute('data-no-loader')) return;
            
            // Get custom messages from form attributes
            const message = form.getAttribute('data-loader-message') || 'Submitting...';
            const subtext = form.getAttribute('data-loader-subtext') || 'Please wait while we process your request';
            
            this.show(message, subtext);
            
            // Add loading state to submit button
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('btn-loading');
                submitBtn.disabled = true;
            }
        });
        
        // Handle all anchor tag clicks (navigation)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            
            if (link && !link.hasAttribute('data-no-loader')) {
                const href = link.getAttribute('href');
                
                // Only show loader for internal navigation (not for #, javascript:, or external links)
                if (href && 
                    !href.startsWith('#') && 
                    !href.startsWith('javascript:') && 
                    !href.startsWith('mailto:') && 
                    !href.startsWith('tel:') &&
                    !link.hasAttribute('download') &&
                    !link.target === '_blank') {
                    
                    const message = link.getAttribute('data-loader-message') || 'Loading page...';
                    this.show(message, 'Please wait');
                }
            }
        });
        
        // Handle AJAX requests (if using fetch)
        this.interceptFetch();
        
        // Handle AJAX requests (if using XMLHttpRequest)
        this.interceptXHR();
    },
    
    // Intercept fetch requests
    interceptFetch() {
        const originalFetch = window.fetch;
        const self = this;
        
        window.fetch = function(...args) {
            // Check if request should show loader
            const url = typeof args[0] === 'string' ? args[0] : args[0].url;
            const options = args[1] || {};
            
            // Skip loader for specific endpoints
            const skipLoader = options.skipLoader || 
                               url.includes('/socket.io') || 
                               url.includes('/static/');
            
            if (!skipLoader) {
                const message = options.loaderMessage || 'Loading data...';
                const subtext = options.loaderSubtext || 'Please wait';
                self.show(message, subtext);
            }
            
            return originalFetch.apply(this, args)
                .then(response => {
                    if (!skipLoader) {
                        self.hide();
                    }
                    return response;
                })
                .catch(error => {
                    if (!skipLoader) {
                        self.hide();
                    }
                    throw error;
                });
        };
    },
    
    // Intercept XMLHttpRequest
    interceptXHR() {
        const self = this;
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(...args) {
            this._url = args[1];
            return originalOpen.apply(this, args);
        };
        
        XMLHttpRequest.prototype.send = function(...args) {
            const xhr = this;
            
            // Skip loader for specific endpoints
            const skipLoader = xhr._url.includes('/socket.io') || 
                              xhr._url.includes('/static/');
            
            if (!skipLoader) {
                self.show('Loading data...', 'Please wait');
                
                xhr.addEventListener('loadend', () => {
                    self.hide();
                });
            }
            
            return originalSend.apply(this, args);
        };
    }
};

// Initialize loader when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        GlobalLoader.init();
    });
} else {
    GlobalLoader.init();
}

// Expose to global scope
window.GlobalLoader = GlobalLoader;
