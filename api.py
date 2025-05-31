#!/usr/bin/env python3
import os
import json
import sys
import base64
import pymysql
import secrets
import hashlib
import re
from datetime import date, datetime
from xml.etree import ElementTree

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)

def create_connection():
    return pymysql.connect(
        host='158.160.152.200',
        user='u68593',
        password='9258357',
        database='web_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def validate_form(data):
    errors = {}
    patterns = {
        'last_name': r'^[А-Яа-яЁё]+$',
        'first_name': r'^[А-Яа-яЁё]+$',
        'patronymic': r'^[А-Яа-яЁё]*$',
        'phone': r'^\+?\d{10,15}$',
        'email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        'birthdate': r'^\d{4}-\d{2}-\d{2}$',
        'bio': r'^.{10,}$'
    }
    for field, pattern in patterns.items():
        if field in data and not re.match(pattern, str(data[field])):
            errors[field] = f"Некорректное значение поля {field}"
    if 'gender' not in data or data['gender'] not in ['male', 'female']:
        errors['gender'] = "Выберите пол (male/female)"
    if 'languages' not in data or not data['languages']:
        errors['languages'] = "Выберите хотя бы один язык"
    if 'contract' not in data or not data['contract']:
        errors['contract'] = "Необходимо подтвердить контракт"
    return errors if errors else None

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_credentials():
    return {
        'username': secrets.token_hex(8),
        'password': secrets.token_hex(8)
    }

def parse_input():
    content_type = os.environ.get('CONTENT_TYPE', '')
    try:
        content_length = int(os.environ.get('CONTENT_LENGTH', 0))
    except:
        content_length = 0
    data = sys.stdin.read(content_length)
    if not data:
        return None
    if 'application/json' in content_type:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    elif 'application/xml' in content_type:
        try:
            root = ElementTree.fromstring(data)
            return {
                child.tag: child.text if child.tag != 'languages' 
                else [lang.text for lang in child]
                for child in root
            }
        except:
            return None
    return None

def check_auth():
    auth_header = os.environ.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Basic '):
        return None
    try:
        auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = auth_decoded.split(':', 1)
        conn = create_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT password_hash FROM applications WHERE username=%s
                """, (username,))
                result = cursor.fetchone()
                if result and result['password_hash'] == hash_password(password):
                    return username
                return None
        finally:
            conn.close()
    except:
        return None

def create_user(data):
    conn = create_connection()
    if not conn:
        return None
    try:
        creds = generate_credentials()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO applications (
                    last_name, first_name, patronymic,
                    phone, email, birthdate,
                    gender, bio, contract,
                    username, password_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['last_name'], data['first_name'], data['patronymic'],
                data['phone'], data['email'], data['birthdate'],
                data['gender'], data['bio'], data['contract'],
                creds['username'], hash_password(creds['password'])
            ))
            lang_map = {'Pascal':1, 'C':2, 'C++':3, 'JavaScript':4, 'PHP':5,
                      'Python':6, 'Java':7, 'Haskel':8, 'Clojure':9,
                      'Prolog':10, 'Scala':11, 'Go':12}
            for lang in data.get('languages', []):
                if lang in lang_map:
                    cursor.execute("""
                        INSERT INTO application_languages (application_id, language_id)
                        SELECT id, %s FROM applications WHERE username=%s
                    """, (lang_map[lang], creds['username']))
            conn.commit()
            return creds
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {str(e)}", file=sys.stderr)
        return None
    finally:
        conn.close()

def update_user(username, data):
    conn = create_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE applications SET
                    last_name=%s, first_name=%s, patronymic=%s,
                    phone=%s, email=%s, birthdate=%s,
                    gender=%s, bio=%s, contract=%s
                WHERE username=%s
            """, (
                data['last_name'], data['first_name'], data['patronymic'],
                data['phone'], data['email'], data['birthdate'],
                data['gender'], data['bio'], data['contract'],
                username
            ))
            cursor.execute("DELETE FROM application_languages WHERE application_id IN (SELECT id FROM applications WHERE username=%s)", (username,))
            lang_map = {'Pascal':1, 'C':2, 'C++':3, 'JavaScript':4, 'PHP':5,
                       'Python':6, 'Java':7, 'Haskel':8, 'Clojure':9,
                       'Prolog':10, 'Scala':11, 'Go':12}
            for lang in data.get('languages', []):
                if lang in lang_map:
                    cursor.execute("""
                        INSERT INTO application_languages (application_id, language_id)
                        SELECT id, %s FROM applications WHERE username=%s
                    """, (lang_map[lang], username))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {str(e)}", file=sys.stderr)
        return None
    finally:
        conn.close()

def get_user(username):
    conn = create_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.*, GROUP_CONCAT(pl.name) as languages
                FROM applications a
                LEFT JOIN application_languages al ON a.id = al.application_id
                LEFT JOIN programming_languages pl ON al.language_id = pl.id
                WHERE a.username=%s
                GROUP BY a.id
            """, (username,))
            result = cursor.fetchone()
            if not result:
                return None
            return {
                'last_name': result['last_name'],
                'first_name': result['first_name'],
                'patronymic': result['patronymic'],
                'phone': result['phone'],
                'email': result['email'],
                'birthdate': result['birthdate'].isoformat() if result['birthdate'] else None,
                'gender': result['gender'],
                'languages': [lang for lang in result['languages'].split(',') if lang] if result['languages'] else [],
                'bio': result['bio'],
                'contract': bool(result['contract'])
            }
    except Exception as e:
        print(f"DB Error: {str(e)}", file=sys.stderr)
        return None
    finally:
        conn.close()

def handle_request():
    sys.stderr = sys.stdout
    method = os.environ.get('REQUEST_METHOD', 'GET')
    path = os.environ.get('PATH_INFO', '')

    # Устанавливаем заголовки ответа
    print("Content-Type: application/json; charset=utf-8\n")

    try:
        # Создание пользователя
        if method == 'POST' and path == '/users':
            data = parse_input()
            if not data:
                print(json.dumps({'error': 'Invalid input data'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            errors = validate_form(data)
            if errors:
                print(json.dumps({'errors': errors}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            result = create_user(data)
            if not result:
                print(json.dumps({'error': 'Failed to create user'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            response = {
                'message': 'User created successfully',
                'username': result['username'],
                'password': result['password'],
                'profile_url': f'/users/{result["username"]}'
            }
            print(json.dumps(response, ensure_ascii=False, indent=2, cls=DateTimeEncoder))

        # Обновление пользователя
        elif method == 'PUT' and path.startswith('/users/'):
            username = path.split('/')[-1]
            auth_user = check_auth()
            if not auth_user or auth_user != username:
                print("Status: 401 Unauthorized")
                print()
                print(json.dumps({'error': 'Unauthorized'}, ensure_ascii=False, cls=DateTimeEncoder))
                return

            data = parse_input()
            if not data:
                print(json.dumps({'error': 'Invalid input data'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            errors = validate_form(data)
            if errors:
                print(json.dumps({'errors': errors}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            if not update_user(username, data):
                print(json.dumps({'error': 'Failed to update user'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            print(json.dumps({
                'message': 'User updated successfully',
                'profile_url': f'/users/{username}'
            }, ensure_ascii=False, indent=2, cls=DateTimeEncoder))

        # Получение профиля
        elif method == 'GET' and path.startswith('/users/'):
            username = path.split('/')[-1]
            auth_user = check_auth()
            if not auth_user or auth_user != username:
                print("Status: 401 Unauthorized")
                print()
                print(json.dumps({'error': 'Unauthorized'}, ensure_ascii=False, cls=DateTimeEncoder))
                return

            user_data = get_user(username)
            if not user_data:
                print(json.dumps({'error': 'User not found'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
            print(json.dumps(user_data, ensure_ascii=False, indent=2, cls=DateTimeEncoder))

        else:
            print(json.dumps({'error': 'Not found'}, ensure_ascii=False, cls=DateTimeEncoder))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False, cls=DateTimeEncoder))

if __name__ == "__main__":
    handle_request()
