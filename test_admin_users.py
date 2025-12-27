import requests

# Login first
login = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'superadmin@dsn.ai', 'password': 'admin123'})
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Test admin users endpoint
users_response = requests.get('http://localhost:8000/api/v1/admin/users', headers=headers)
print(f'Admin users endpoint: {users_response.status_code}')
if users_response.ok:
    users = users_response.json()
    print(f'Found {len(users)} users')
    for user in users[:3]:  # Show first 3 users
        print(f'  ID: {user.get("id")}, Email: {user.get("email")}, Role: {user.get("role")}')
else:
    print(f'Error: {users_response.text}')
