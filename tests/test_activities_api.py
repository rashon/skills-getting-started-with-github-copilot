"""
Integration tests for the Activities API endpoints.
Tests GET /activities, POST /signup, and DELETE /unregister.
"""

import pytest


class TestGetActivities:
    """Test the GET /activities endpoint"""

    def test_get_activities_success(self, client, reset_activities):
        """Should return all activities with correct structure"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all activities are returned
        assert len(data) >= 3
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_has_correct_structure(self, client, reset_activities):
        """Should return activities with required fields"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        
        # Verify structure
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)
    
    def test_get_activities_has_initial_participants(self, client, reset_activities):
        """Should include initial participants in response"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have 2 participants initially
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupEndpoint:
    """Test the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client, reset_activities):
        """Should successfully sign up a new student"""
        activity = "Chess Club"
        email = "newstudent@mergington.edu"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Should add participant to activity"""
        activity = "Chess Club"
        email = "newstudent@mergington.edu"
        
        # Get initial count
        response1 = client.get("/activities")
        initial_count = len(response1.json()[activity]["participants"])
        
        # Sign up
        client.post(f"/activities/{activity}/signup", params={"email": email})
        
        # Verify participant was added
        response2 = client.get("/activities")
        final_count = len(response2.json()[activity]["participants"])
        
        assert final_count == initial_count + 1
        assert email in response2.json()[activity]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Should return 404 for nonexistent activity"""
        activity = "Nonexistent Club"
        email = "student@mergington.edu"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_duplicate_registration(self, client, reset_activities):
        """Should return 400 when student already signed up (bug fix test)"""
        activity = "Chess Club"
        email = "michael@mergington.edu"  # Already registered
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
    
    def test_signup_capacity_limit(self, client, reset_activities):
        """Should return 400 when activity is at max capacity"""
        activity = "Basketball Team"
        # Basketball Team has max_participants=15, currently has 1 (alex@mergington.edu)
        # Fill it up to capacity
        base_email = "student{0}@mergington.edu"
        
        for i in range(14):  # Add 14 more students to reach 15 total
            email = base_email.format(i)
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Try to add one more (should fail)
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overcapacity@mergington.edu"}
        )
        
        assert response.status_code == 400
        assert "capacity" in response.json()["detail"].lower() or "full" in response.json()["detail"].lower()


class TestUnregisterEndpoint:
    """Test the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client, reset_activities):
        """Should successfully unregister a participant"""
        activity = "Chess Club"
        email = "michael@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Should remove participant from activity"""
        activity = "Chess Club"
        email = "michael@mergington.edu"
        
        # Get initial count
        response1 = client.get("/activities")
        initial_count = len(response1.json()[activity]["participants"])
        
        # Unregister
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Verify participant was removed
        response2 = client.get("/activities")
        final_count = len(response2.json()[activity]["participants"])
        
        assert final_count == initial_count - 1
        assert email not in response2.json()[activity]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Should return 404 for nonexistent activity"""
        activity = "Nonexistent Club"
        email = "student@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Should return 400 when student is not registered"""
        activity = "Chess Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_frees_capacity(self, client, reset_activities):
        """Should free up capacity after unregister, allowing new signup"""
        activity = "Basketball Team"  # max_participants=15, currently has 1
        email_to_unregister = "alex@mergington.edu"
        email_to_signup = "newstudent@mergington.edu"
        
        # Unregister existing participant
        response1 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email_to_unregister}
        )
        assert response1.status_code == 200
        
        # Verify capacity is now available
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email_to_signup}
        )
        assert response2.status_code == 200
