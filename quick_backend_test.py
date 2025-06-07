import requests
import json
import time
import uuid

# Get the backend URL from environment variable
BACKEND_URL = "https://4c7b5b9a-d875-452d-b60c-6238c7db2a45.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

def test_api_root():
    """Test the API root endpoint"""
    print("\n🔍 Testing API root endpoint...")
    response = requests.get(f"{API_URL}/")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API root endpoint test passed. Response: {data}")
        return True
    else:
        print(f"❌ API root endpoint test failed. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_create_user():
    """Test creating a new user"""
    print("\n🔍 Testing user creation...")
    
    # Generate unique test user data
    timestamp = int(time.time())
    test_user = {
        "name": f"Test User {timestamp}",
        "email": f"test{timestamp}@example.com",
        "education_level": "bachelors",
        "work_experience": "mid_level",
        "current_role": "Software Developer",
        "target_role": "Senior Software Engineer",
        "industry": "technology",
        "skills": ["Python", "JavaScript", "React"],
        "timeline_months": 12,
        "availability_hours_per_week": 10
    }
    
    response = requests.post(f"{API_URL}/users", json=test_user)
    if response.status_code == 200:
        data = response.json()
        user_id = data["id"]
        print(f"✅ User creation test passed. User ID: {user_id}")
        return user_id
    else:
        print(f"❌ User creation test failed. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_get_user(user_id):
    """Test retrieving a user by ID"""
    print(f"\n🔍 Testing get user with ID: {user_id}...")
    response = requests.get(f"{API_URL}/users/{user_id}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Get user test passed. User name: {data['name']}")
        return True
    else:
        print(f"❌ Get user test failed. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_leaderboard():
    """Test retrieving the leaderboard"""
    print("\n🔍 Testing leaderboard retrieval...")
    response = requests.get(f"{API_URL}/leaderboard")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Leaderboard test passed. Found {len(data)} entries")
        return True
    else:
        print(f"❌ Leaderboard test failed. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def run_quick_tests():
    """Run quick tests for basic API functionality"""
    print("🚀 Starting CareerPath AI API Quick Tests")
    
    # Test API root
    api_root_success = test_api_root()
    
    # Test user creation and retrieval
    user_id = test_create_user()
    user_retrieval_success = False
    if user_id:
        user_retrieval_success = test_get_user(user_id)
    
    # Test leaderboard
    leaderboard_success = test_leaderboard()
    
    # Print summary
    print("\n📊 Test Summary:")
    print(f"API Root: {'✅ Passed' if api_root_success else '❌ Failed'}")
    print(f"User Creation: {'✅ Passed' if user_id else '❌ Failed'}")
    print(f"User Retrieval: {'✅ Passed' if user_retrieval_success else '❌ Failed'}")
    print(f"Leaderboard: {'✅ Passed' if leaderboard_success else '❌ Failed'}")
    
    all_passed = api_root_success and user_id and user_retrieval_success and leaderboard_success
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}")
    
    return all_passed

if __name__ == "__main__":
    run_quick_tests()