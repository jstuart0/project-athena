# Home Assistant Configuration for Athena Lite
# Generated on Mon Nov  3 10:24:09 EST 2025

HOME_ASSISTANT_URL = 'https://192.168.10.168:8123'
HOME_ASSISTANT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhNzcyNTZkMDc0NGU0MjdkYWMzZTc1YzM5OWYzOTQ2YSIsImlhdCI6MTc2MjE0Njg5MSwiZXhwIjoyMDc3NTA2ODkxfQ.PPRVmvA3nTP1JBN1JBN1JwOYfcxq8QZuR_V9II4AFhTcQjQ'

# Test connectivity
import requests
def test_ha_connection():
    headers = {'Authorization': f'Bearer {HOME_ASSISTANT_TOKEN}'}
    try:
        response = requests.get(f'{HOME_ASSISTANT_URL}/api/', headers=headers, verify=False)
        return response.status_code == 200
    except Exception as e:
        return False
