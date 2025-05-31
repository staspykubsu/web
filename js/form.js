function setupRegistrationForm() {
    const form = document.getElementById('registration-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Отправка...';

        try {
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
                return;
            }

            const response = await fetch('api.py/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(formObject)
            });

            const data = await response.json();

            if (!response.ok) {
                if (data.errors) {
                    displayErrors(data.errors);
                } else {
                    throw new Error(data.error || 'Неизвестная ошибка');
                }
                return;
            }

            localStorage.setItem('username', data.username);
            localStorage.setItem('password', data.password);

            showCredentials(data.username, data.password);

            showSuccessMessage('Регистрация прошла успешно!');

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Произошла ошибка: ' + error.message);
            form.submit();
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
        }
    });
}

function validateForm(data) {
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

document.addEventListener('DOMContentLoaded', function() {
    setupRegistrationForm();
});
