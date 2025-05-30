#!/usr/bin/env python3
import cgi
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
    try:
        return pymysql.connect(
            host='158.160.163.114',
            user='u68593',
            password='9258357',
            database='web_db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print(f"DB Error: {str(e)}", file=sys.stderr)
        return None

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
    messages = {
        'last_name': "Фамилия должна содержать только буквы кириллицы",
        'first_name': "Имя должно содержать только буквы кириллицы",
        'patronymic': "Отчество должно содержать только буквы кириллицы",
        'phone': "Некорректный формат телефона",
        'email': "Некорректный email",
        'birthdate': "Дата должна быть в формате ГГГГ-ММ-ДД",
        'bio': "Биография должна содержать минимум 10 символов"
    }
    
    for field, pattern in patterns.items():
        if field in data and not re.match(pattern, str(data[field])):
            errors[field] = messages.get(field, "Некорректное значение")
    
    if 'gender' not in data or data['gender'] not in ['male', 'female']:
        errors['gender'] = "Выберите пол"
    
    if 'languages' not in data or not data['languages']:
        errors['languages'] = "Выберите хотя бы один язык"
    
    if 'contract' not in data or not data['contract']:
        errors['contract'] = "Необходимо подтвердить контракт"
    
    return errors

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_credentials():
    return {
        'username': secrets.token_hex(8),
        'password': secrets.token_hex(8)
    }

def insert_user_data(connection, data, credentials=None):
    cursor = connection.cursor()
    try:
        if credentials and 'username' in credentials:
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
                credentials['username']
            ))
            user_id = credentials['username']
        else:
            creds = generate_credentials()
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
            user_id = creds['username']

        cursor.execute("DELETE FROM application_languages WHERE application_id IN (SELECT id FROM applications WHERE username=%s)", (user_id,))
        
        lang_map = {'Pascal':1, 'C':2, 'C++':3, 'JavaScript':4, 'PHP':5,
                   'Python':6, 'Java':7, 'Haskel':8, 'Clojure':9,
                   'Prolog':10, 'Scala':11, 'Go':12}
        
        for lang in data.get('languages', []):
            if lang in lang_map:
                cursor.execute("""
                    INSERT INTO application_languages (application_id, language_id)
                    SELECT id, %s FROM applications WHERE username=%s
                """, (lang_map[lang], user_id))
        
        connection.commit()
        return creds if not credentials else {'username': user_id}
        
    except Exception as e:
        connection.rollback()
        print(f"DB Error: {str(e)}", file=sys.stderr)
        return None
    finally:
        cursor.close()

def verify_user(connection, username, password):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT password_hash FROM applications WHERE username=%s
            """, (username,))
            result = cursor.fetchone()
            return result and result['password_hash'] == hash_password(password)
    except Exception as e:
        print(f"Auth Error: {str(e)}", file=sys.stderr)
        return False

def get_user_data(connection, username):
    try:
        with connection.cursor() as cursor:
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
        except json.JSONDecodeError as e:
            print(f"JSON Error: {str(e)}", file=sys.stderr)
            return None
    elif 'application/xml' in content_type:
        try:
            root = ElementTree.fromstring(data)
            return {
                child.tag: child.text if child.tag != 'languages' 
                else [lang.text for lang in child]
                for child in root
            }
        except Exception as e:
            print(f"XML Error: {str(e)}", file=sys.stderr)
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
            if verify_user(conn, username, password):
                return username
            return None
        finally:
            conn.close()
    except Exception as e:
        print(f"Auth Error: {str(e)}", file=sys.stderr)
        return None

def main():
    sys.stderr = sys.stdout
    print("Content-Type: application/json; charset=utf-8\n")
    
    method = os.environ.get('REQUEST_METHOD', 'GET')
    path_info = os.environ.get('PATH_INFO', '')
    
    try:
        if method == 'POST' and path_info == '/api/submit':
            data = parse_input()
            if not data:
                print(json.dumps({'error': 'Invalid input'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            errors = validate_form(data)
            if errors:
                print(json.dumps({'errors': errors}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            conn = create_connection()
            if not conn:
                print(json.dumps({'error': 'DB connection failed'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            try:
                username = check_auth()
                result = insert_user_data(conn, data, {'username': username} if username else None)
                
                if not result:
                    print(json.dumps({'error': 'Operation failed'}, ensure_ascii=False, cls=DateTimeEncoder))
                    return
                    
                response = {
                    'message': 'Data updated successfully' if username else 'User created successfully',
                    'profile_url': f'/api/profile/{username or result["username"]}'
                }
                if not username:
                    response.update({
                        'username': result['username'],
                        'password': result['password']
                    })
                
                print(json.dumps(response, ensure_ascii=False, indent=2, cls=DateTimeEncoder))
                
            finally:
                conn.close()
                
        elif method == 'GET' and path_info.startswith('/api/profile/'):
            username = check_auth()
            if not username:
                print(json.dumps({'error': 'Authentication required'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            requested_user = path_info.split('/')[-1]
            if requested_user != username:
                print(json.dumps({'error': 'Access denied'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            conn = create_connection()
            if not conn:
                print(json.dumps({'error': 'DB connection failed'}, ensure_ascii=False, cls=DateTimeEncoder))
                return
                
            try:
                user_data = get_user_data(conn, username)
                if not user_data:
                    print(json.dumps({'error': 'User not found'}, ensure_ascii=False, cls=DateTimeEncoder))
                    return
                    
                print(json.dumps(user_data, ensure_ascii=False, indent=2, cls=DateTimeEncoder))
            finally:
                conn.close()
        else:
            print(json.dumps({'error': 'Not found'}, ensure_ascii=False, cls=DateTimeEncoder))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False, cls=DateTimeEncoder))

if __name__ == "__main__":
    main()
