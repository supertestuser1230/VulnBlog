/**
 * Безопасное копирование ссылки в буфер обмена
 */
function copyLink() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        showNotification('Ссылка скопирована в буфер обмена!', 'success');
    }).catch(() => {
        // Fallback для старых браузеров
        try {
            const textArea = document.createElement('textarea');
            textArea.value = url;
            textArea.style.position = 'fixed'; // Предотвращение прокрутки
            textArea.style.opacity = '0'; // Скрытие элемента
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('Ссылка скопирована!', 'success');
        } catch (err) {
            showNotification('Ошибка копирования ссылки!', 'danger');
        }
    });
}

/**
 * Отображение уведомлений с защитой от XSS
 */
function showNotification(message, type = 'info') {
    // Экранирование сообщения для предотвращения XSS
    const safeMessage = DOMPurify.sanitize(message);
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${safeMessage}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Закрыть"></button>
    `;

    document.body.appendChild(alertDiv);

    // Автоматическое удаление через 3 секунды
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300); // Удаление после завершения анимации
        }
    }, 3000);
}

/**
 * Подтверждение удаления с использованием модального окна вместо confirm
 */
function confirmDelete(message = 'Вы уверены, что хотите удалить это?') {
    // Для продакшена рекомендуется использовать модальное окно Bootstrap
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
    // Автоматическая высота текстовых полей
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = `${Math.min(this.scrollHeight, 500)}px`; // Ограничение максимальной высоты
        });
    });

    // Анимация карточек
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });

    // Активные ссылки в навигации
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Инициализация всплывающих подсказок
    const buttons = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (buttons.length > 0 && typeof bootstrap !== 'undefined') {
        buttons.forEach(button => {
            new bootstrap.Tooltip(button);
        });
    }

    // Плавная прокрутка для якорей
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
                // Экранирование данных для предотвращения XSS
                preview.innerHTML = `<img src="${DOMPurify.sanitize(e.target.result)}" class="img-fluid uploaded-file" alt="Предварительный просмотр">`;
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

        if (query.length < 2 || query.length > 100) return;

        // Экранирование для предотвращения XSS
        const safeQuery = encodeURIComponent(DOMPurify.sanitize(query));
        searchTimeout = setTimeout(() => {
            fetch(`/search?q=${safeQuery}`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || '' // Получение CSRF-токена
                }
            })
                .then(response => {
                    if (!response.ok) throw new Error('Ошибка сети');
                    console.log('Поиск выполнен для:', query);
                })
                .catch(error => {
                    console.error('Ошибка поиска:', error);
                    showNotification('Ошибка при выполнении поиска.', 'danger');
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
            this.value = this.value.substring(0, maxLength); // Ограничение ввода
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
                showNotification('CSRF-токен отсутствует!', 'danger');
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
                if (!response.ok) throw new Error('Ошибка сети');
                return response.json();
            })
            .then(data => {
                showNotification(data.message || 'Форма отправлена успешно!', 'success');

                // Безопасная проверка redirect
                if (typeof data.redirect === 'string' && data.redirect.startsWith('/')) {
                    window.location.href = data.redirect;
                } else if (data.redirect) {
                    console.warn('Недопустимый redirect URL:', data.redirect);
                }
            })
            .catch(error => {
                showNotification('Ошибка при отправке формы!', 'danger');
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

    fetch('/admin/stats', {
        method: 'GET',
        headers: {
            'X-CSRF-Token': csrfToken
        }
    })
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сети');
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
            console.error('Ошибка получения статистики:', error);
            showNotification('Ошибка обновления статистики.', 'danger');
        });
}

if (window.location.pathname === '/admin') {
    refreshAdminStats(); // Начальная загрузка
    setInterval(refreshAdminStats, 30000);
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