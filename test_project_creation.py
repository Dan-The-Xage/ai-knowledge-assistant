import requests

# Login first
login = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'superadmin@dsn.ai', 'password': 'admin123'})
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Create a project with members
import time
project_data = {
    'name': f'Test Project with Members {int(time.time())}',
    'description': 'Testing member addition during project creation',
    'member_ids': [2, 3]  # Add admin and user to the project
}

create_response = requests.post('http://localhost:8000/api/v1/projects', json=project_data, headers=headers)
print(f'Project creation: {create_response.status_code}')
if create_response.ok:
    project = create_response.json()
    print(f'Created project: {project.get("name")} (ID: {project.get("id")})')
    print(f'Members: {project.get("member_count")}')
else:
    print(f'Error: {create_response.text}')
