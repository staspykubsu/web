document.addEventListener('DOMContentLoaded', function() {
    setupForms();
    checkAuthStatus();
});

function utf8ToB64(str) {
    return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (match, p1) => String.fromCharCode('0x' + p1)));
}

function setupForms() {
    const registrationForm = document.getElementById('registration-form');
    const loginForm = document.getElementById('login-form');
    const logoutButton = document.getElementById('logout-button');

    if (registrationForm) {
        registrationForm.removeEventListener('submit', handleRegistrationSubmit);
        registrationForm.removeEventListener('submit', handleUpdateSubmit);
        registrationForm.addEventListener('submit', handleRegistrationSubmit);
    }

    if (loginForm) {
        loginForm.removeEventListener('submit', handleLoginSubmit);
        loginForm.addEventListener('submit', handleLoginSubmit);
    }

    if (logoutButton) {
        logoutButton.removeEventListener('click', handleLogout);
        logoutButton.addEventListener('click', handleLogout);
    }
}

function handleRegistrationSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Отправка...';

    const formData = new FormData(form);
    const formObject = {};

    formData.forEach((value, key) => {
        if (key === 'languages[]') {
            if (!formObject.languages) formObject.languages = [];
            formObject.languages.push(value);
        } else if (key === 'contract') {
            formObject[key] = true;
        } else {
            formObject[key] = value;
        }
    });

    const errors = validateForm(formObject);
    if (Object.keys(errors).length > 0) {
        displayErrors(errors);
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
    }

    fetch('api.py/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(formObject)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.error || 'Ошибка регистрации');
            });
        }
        return response.json();
    })
    .then(data => {
        showCredentials(data.username, data.password);
        showSuccessMessage('Регистрация прошла успешно!');
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Произошла ошибка: ' + error.message);
        form.submit();
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
    });
}

function handleLoginSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Вход...';

    const formData = new FormData(form);
    const username = formData.get('username');
    const password = formData.get('password');

    if (!username || !password) {
        alert('Заполните все поля');
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
    }

    const authHeader = 'Basic ' + utf8ToB64(`${username}:${password}`);
    fetch(`api.py/users/${encodeURIComponent(username)}`, {
        method: 'GET',
        headers: {
            'Authorization': authHeader,
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Ошибка авторизации');
            });
        }
        return response.json();
    })
    .then(userData => {
        localStorage.setItem('username', username);
        localStorage.setItem('password', password);
        showSuccessMessage('Вход выполнен успешно!');
        checkAuthStatus();
        hideCredentials();
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка авторизации: Неправильный логин или пароль.');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
    });
}

function handleLogout(e) {
    e.preventDefault();
    localStorage.removeItem('username');
    localStorage.removeItem('password');
    hideCredentials();
    showSuccessMessage('Вы вышли из системы');
    checkAuthStatus();
    
    // Очищаем поля формы авторизации
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.reset();
    }
    
    const registrationForm = document.getElementById('registration-form');
    if (registrationForm) {
        registrationForm.reset();
        const submitBtn = registrationForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.textContent = 'Сохранить';
        }
    }
}

function checkAuthStatus() {
    const username = localStorage.getItem('username');
    const password = localStorage.getItem('password');
    
    const loginSection = document.getElementById('login-section');
    const logoutButton = document.getElementById('logout-button-container');
    const registrationForm = document.getElementById('registration-form');
    const formTitle = document.getElementById('form-title');
    
    if (username && password) {
        if (loginSection) loginSection.style.display = 'none';
        if (logoutButton) logoutButton.style.display = 'block';
        if (formTitle) formTitle.textContent = 'Редактирование профиля';
        
        if (registrationForm) {
            registrationForm.removeEventListener('submit', handleRegistrationSubmit);
            registrationForm.addEventListener('submit', handleUpdateSubmit);
        }
        
        loadUserProfile(username, password);
    } else {
        if (loginSection) loginSection.style.display = 'block';
        if (logoutButton) logoutButton.style.display = 'none';
        if (formTitle) formTitle.textContent = 'Регистрация';
        
        if (registrationForm) {
            registrationForm.removeEventListener('submit', handleUpdateSubmit);
            registrationForm.addEventListener('submit', handleRegistrationSubmit);
        }
    }
}

function hideCredentials() {
    const credentialsSection = document.querySelector('.credentials');
    if (credentialsSection) {
        credentialsSection.innerHTML = '';
    }
}

function handleUpdateSubmit(e) {
    e.preventDefault();

    const username = localStorage.getItem('username');
    const password = localStorage.getItem('password');
    
    if (!username || !password) {
        alert('Требуется авторизация');
        return;
    }

    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Обновление...';

    const formData = new FormData(form);
    const formObject = {};

    formData.forEach((value, key) => {
        if (key === 'languages[]') {
            if (!formObject.languages) formObject.languages = [];
            formObject.languages.push(value);
        } else if (key === 'contract') {
            formObject[key] = true;
        } else {
            formObject[key] = value;
        }
    });

    const errors = validateForm(formObject);
    if (Object.keys(errors).length > 0) {
        displayErrors(errors);
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
    }

    const authHeader = 'Basic ' + utf8ToB64(`${username}:${password}`);

    fetch(`api.py/users/${username}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader,
            'Accept': 'application/json'
        },
        body: JSON.stringify(formObject)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.error || 'Ошибка обновления');
            });
        }
        return response.json();
    })
    .then(data => {
        showSuccessMessage('Данные успешно обновлены!');
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка обновления: ' + error.message);
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
    });
}

async function loadUserProfile(username, password) {
    try {
	const authHeader = 'Basic ' + utf8ToB64(`${username}:${password}`);
        
        const response = await fetch(`api.py/users/${username}`, {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки профиля');
        }

        const userData = await response.json();
        loadUserData(userData);
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
    }
}

function validateForm(data) {
    clearAllErrors();
    
    const errors = {};
    const patterns = {
        'last_name': /^[А-Яа-яЁё]+$/,
        'first_name': /^[А-Яа-яЁё]+$/,
        'patronymic': /^[А-Яа-яЁё]*$/,
        'phone': /^\+?\d{10,15}$/,
        'email': /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/,
        'birthdate': /^\d{4}-\d{2}-\d{2}$/,
        'bio': /^.{10,}$/
    };

    if (!data.last_name) errors.last_name = "Фамилия обязательна";
    if (!data.first_name) errors.first_name = "Имя обязательно";

    for (const field in patterns) {
        if (data[field] && !patterns[field].test(data[field])) {
            errors[field] = `Некорректное значение поля ${field}`;
        }
    }

    if (!data.gender) {
        errors.gender = "Выберите пол";
    }

    if (!data.languages || data.languages.length === 0) {
        errors.languages = "Выберите хотя бы один язык";
    }

    if (!data.contract) {
        errors.contract = "Необходимо подтвердить контракт";
    }

    return errors;
}

function clearAllErrors() {
    document.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
    });
    
    document.querySelectorAll('input, select, textarea').forEach(el => {
        el.classList.remove('error');
    });
}

function displayErrors(errors) {
    document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
    document.querySelectorAll('input, select, textarea').forEach(el => el.classList.remove('error'));

    for (const field in errors) {
        const errorElement = document.querySelector(`.error-message[data-for="${field}"]`);
        let inputElement = document.querySelector(`[name="${field}"]`);

        if (!inputElement && field === 'gender') {
            inputElement = document.querySelector(`input[name="gender"]:checked`) ||
                          document.querySelector(`input[name="gender"]`);
        }

        if (!inputElement && field === 'contract') {
            inputElement = document.getElementById('terms');
        }

        if (errorElement) {
            errorElement.textContent = errors[field];
        }

        if (inputElement) {
            inputElement.classList.add('error');
        }
    }
}

function showCredentials(username, password) {
    const credentialsSection = document.querySelector('.credentials');
    if (credentialsSection) {
        credentialsSection.innerHTML = `
            <h3>Ваши учетные данные (сохраните их):</h3>
            <p><strong>Логин:</strong> ${username}</p>
            <p><strong>Пароль:</strong> ${password}</p>
            <button onclick="copyCredentials()">Копировать</button>
        `;
    }
}

function copyCredentials() {
    const credentialsSection = document.querySelector('.credentials');
    if (!credentialsSection) return;

    const login = credentialsSection.querySelector('p:nth-child(2)').textContent.replace('Логин:', '').trim();
    const password = credentialsSection.querySelector('p:nth-child(3)').textContent.replace('Пароль:', '').trim();
    const text = `Логин: ${login}\nПароль: ${password}`;

    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.top = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999);

    try {
        document.execCommand('copy');
        alert("Данные скопированы!");
    } catch (err) {
        alert("Не удалось скопировать данные. Скопируйте вручную.");
        console.error("Ошибка при копировании:", err);
    }

    document.body.removeChild(textarea);
}

function showSuccessMessage(message) {
    alert(message);
}

function loadUserData(userData) {
    const registrationForm = document.getElementById('registration-form');
    if (!registrationForm) return;

    document.getElementById('last_name').value = userData.last_name || '';
    document.getElementById('first_name').value = userData.first_name || '';
    document.getElementById('patronymic').value = userData.patronymic || '';
    document.getElementById('phone').value = userData.phone || '';
    document.getElementById('email').value = userData.email || '';
    document.getElementById('birthdate').value = userData.birthdate || '';
    document.getElementById('bio').value = userData.bio || '';

    if (userData.gender) {
        document.querySelector(`input[name="gender"][value="${userData.gender}"]`).checked = true;
    }

    const languageSelect = document.getElementById('languages');
    if (languageSelect && userData.languages) {
        Array.from(languageSelect.options).forEach(option => {
            option.selected = userData.languages.includes(option.value);
        });
    }

    document.getElementById('terms').checked = userData.contract || false;

    const submitBtn = registrationForm.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.textContent = 'Обновить';
    }

    registrationForm.removeEventListener('submit', handleFormSubmit);
    registrationForm.addEventListener('submit', handleUpdateSubmit);
}
