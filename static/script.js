/**
 * Безопасное копирование ссылки в буфер обмена
 */
function copyLink() {
    const url = window.location.href;
    if (!navigator.clipboard) {
        showNotification('Копирование в буфер обмена не поддерживается в вашем браузере!', 'danger');
        return;
    }
    navigator.clipboard.writeText(url).then(() => {
        showNotification('Ссылка скопирована в буфер обмена!', 'success');
    }).catch(() => {
        showNotification('Ошибка копирования ссылки!', 'danger');
    });
}

/**
 * Отображение уведомлений с защитой от XSS
 */
function showNotification(message, type = 'info') {
    const safeMessage = DOMPurify.sanitize(message);
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

    const messageNode = document.createTextNode(safeMessage);
    alertDiv.appendChild(messageNode);

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Закрыть');
    alertDiv.appendChild(closeButton);

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }
    }, 3000);
}

/**
 * Подтверждение удаления с использованием модального окна
 */
function confirmDelete(message = 'Вы уверены, что хотите удалить это?') {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Подтверждение</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body">
                        ${DOMPurify.sanitize(message)}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-danger confirm-btn">Удалить</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        modal.querySelector('.confirm-btn').addEventListener('click', () => {
            bootstrapModal.hide();
            modal.remove();
            resolve(true);
        });

        modal.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                bootstrapModal.hide();
                modal.remove();
                resolve(false);
            });
        });
    });
}

/**
 * Инициализация событий при загрузке DOM
 */
document.addEventListener('DOMContentLoaded', () => {
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = `${Math.min(this.scrollHeight, 500)}px`;
        });
    });

    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });

    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    const buttons = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (buttons.length > 0 && typeof bootstrap !== 'undefined') {
        buttons.forEach(button => {
            new bootstrap.TooltipREQUI

            button => new bootstrap.Tooltip(button));
        });
    }

    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

/**
 * Предпросмотр изображения с проверкой
 */
function previewImage(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const maxSize = 5 * 1024 * 1024; // 5MB
        const allowedTypes = ['image/png', 'image/jpeg', 'image/gif'];

        if (!allowedTypes.includes(file.type)) {
            showNotification('Недопустимый формат изображения!', 'danger');
            return;
        }
        if (file.size > maxSize) {
            showNotification('Изображение слишком большое! Максимум 5 МБ.', 'danger');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('image-preview');
            if (preview) {
                preview.innerHTML = '';
                const img = document.createElement('img');
                img.src = DOMPurify.sanitize(e.target.result);
                img.className = 'img-fluid uploaded-file';
                img.alt = 'Предварительный просмотр';
                preview.appendChild(img);
            }
        };
        reader.onerror = () => {
            showNotification('Ошибка чтения изображения!', 'danger');
        };
        reader.readAsDataURL(file);
    }
}

/**
 * Инициализация предпросмотра изображения
 */
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('image');
    if (fileInput) {
        const previewDiv = document.createElement('div');
        previewDiv.id = 'image-preview';
        previewDiv.className = 'mt-3';
        fileInput.parentNode.appendChild(previewDiv);

        fileInput.addEventListener('change', () => {
            previewImage(fileInput);
        });
    }
});

/**
 * Автодополнение поиска с CSRF-защитой
 */
function setupSearchAutocomplete() {
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2 || query.length > 100) {
            showNotification('Запрос должен быть от 2 до 100 символов!', 'warning');
            return;
        }

        const safeQuery = encodeURIComponent(DOMPurify.sanitize(query));
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (!csrfToken) {
            showNotification('CSRF-токен отсутствует!', 'danger');
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/search?q=${safeQuery}`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': csrfToken
                }
            })
                .then(response => {
                    if (!response.ok) throw new Error(`Ошибка сети: ${response.status}`);
                    console.log('Поиск выполнен для:', query);
                })
                .catch(error => {
                    console.error('Ошибка поиска:', error);
                    showNotification(`Ошибка при выполнении поиска: ${error.message}`, 'danger');
                });
        }, 300);
    });
}

document.addEventListener('DOMContentLoaded', setupSearchAutocomplete);

/**
 * Счетчик символов для комментариев
 */
function setupCharacterCounter() {
    const commentTextarea = document.querySelector('textarea[name="content"]');
    if (!commentTextarea) return;

    const maxLength = 500;
    const counter = document.createElement('div');
    counter.className = 'text-muted small mt-1';
    counter.textContent = '0 символов';
    commentTextarea.parentNode.appendChild(counter);

    commentTextarea.addEventListener('input', function() {
        const count = this.value.length;
        counter.textContent = `${count} символов`;

        if (count > maxLength) {
            counter.classList.add('text-danger');
            this.value = this.value.substring(0, maxLength);
            showNotification(`Максимальная длина комментария ${maxLength} символов!`, 'danger');
        } else {
            counter.classList.remove('text-danger');
        }
    });
}

document.addEventListener('DOMContentLoaded', setupCharacterCounter);

/**
 * Отправка форм через AJAX с CSRF-защитой
 */
function setupAjaxForms() {
    const forms = document.querySelectorAll('form[data-ajax="true"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

            if (!csrfToken) {
                showNotification('CSRF-токен отсутствует! Пожалуйста, обновите страницу.', 'danger');
                console.error('CSRF-токен не найден');
                return;
            }

            fetch(this.action, {
                method: this.method,
                body: formData,
                headers: {
                    'X-CSRF-Token': csrfToken
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Ошибка сети: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                showNotification(data.message || 'Форма отправлена успешно!', 'success');
                if (typeof data.redirect === 'string' && data.redirect.match(/^\/[a-zA-Z0-9\/_-]*$/)) {
                    window.location.href = data.redirect;
                } else if (data.redirect) {
                    console.warn('Недопустимый redirect URL:', data.redirect);
                }
            })
            .catch(error => {
                showNotification(`Ошибка при отправке формы: ${error.message}`, 'danger');
                console.error('Ошибка отправки формы:', error);
            });
        });
    });
}

document.addEventListener('DOMContentLoaded', setupAjaxForms);

/**
 * Обновление статистики администратора
 */
function refreshAdminStats() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!csrfToken) {
        console.error('CSRF-токен отсутствует');
        return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch('/admin/stats', {
        method: 'GET',
        headers: {
            'X-CSRF-Token': csrfToken
        },
        signal: controller.signal
    })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error(`Ошибка сети: ${response.status}`);
            return response.json();
        })
        .then(data => {
            const usersCount = document.querySelector('.users-count');
            const postsCount = document.querySelector('.posts-count');
            const commentsCount = document.querySelector('.comments-count');
            if (usersCount) usersCount.textContent = data.users || 0;
            if (postsCount) postsCount.textContent = data.posts || 0;
            if (commentsCount) commentsCount.textContent = data.comments || 0;
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                console.warn('Запрос статистики прерван по таймауту');
            } else {
                console.error('Ошибка получения статистики:', error);
                showNotification(`Ошибка обновления статистики: ${error.message}`, 'danger');
            }
        });
}

if (window.location.pathname === '/admin') {
    refreshAdminStats();
    setInterval(refreshAdminStats, 60000);
}

/**
 * Экспорт данных с проверкой прав
 */
function exportData(type) {
    if (!['users', 'posts', 'comments'].includes(type)) {
        showNotification('Недопустимый тип данных для экспорта!', 'danger');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!csrfToken) {
        showNotification('CSRF-токен отсутствует!', 'danger');
        return;
    }

    fetch(`/admin/export?type=${encodeURIComponent(type)}`, {
        method: 'GET',
        headers: {
            'X-CSRF-Token': csrfToken
        }
    })
        .then(response => {
            if (!response.ok) throw new Error('Ошибка доступа');
            window.location.href = `/admin/export?type=${encodeURIComponent(type)}`;
        })
        .catch(error => {
            showNotification('Ошибка экспорта данных: недостаточно прав или ошибка сервера.', 'danger');
            console.error('Ошибка экспорта:', error);
        });
}
