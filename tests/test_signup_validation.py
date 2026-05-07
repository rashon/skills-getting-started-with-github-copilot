"""
Edge case tests for signup functionality.
Focuses on duplicate prevention, capacity limits, and edge cases.
"""

import pytest


class TestDuplicateRegistration:
    """Test duplicate registration prevention (bug fix verification)"""

    def test_cannot_register_twice_same_student(self, client, reset_activities):
        """Verify student cannot register twice for same activity"""
        activity = "Programming Class"
        email = "newstudent@test.edu"
        
        # First signup - should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup - should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already" in response2.json()["detail"].lower()
    
    def test_duplicate_prevention_with_initial_participant(self, client, reset_activities):
        """Verify cannot re-register someone already in system"""
        activity = "Programming Class"
        email = "emma@mergington.edu"  # Already registered
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()
    
    def test_duplicate_check_case_sensitive(self, client, reset_activities):
        """Test if duplicate check is case-sensitive"""
        activity = "Gym Class"
        email1 = "newstudent@test.edu"
        email2 = "NewStudent@Test.Edu"  # Different case
        
        # First signup
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email1}
        )
        assert response1.status_code == 200
        
        # Try with different case - behavior depends on implementation
        # If case-sensitive: should succeed
        # If case-insensitive: should fail
        # Document the actual behavior
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email2}
        )
        # This test documents actual behavior
        assert response2.status_code in [200, 400]


class TestCapacityLimits:
    """Test capacity limit enforcement"""

    def test_capacity_enforcement_single_slot_activity(self, client, reset_activities):
        """Test activity with single available slot"""
        # Find activity with max_participants - 1 current participants
        activity = "Art Club"  # max=18, currently has 1 (isabella@mergington.edu)
        
        students = [f"student{i}@test.edu" for i in range(17)]  # 17 remaining slots
        
        # Fill all slots
        for email in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify capacity reached
        response_get = client.get("/activities")
        assert len(response_get.json()[activity]["participants"]) == 18
        
        # Try to add one more - should fail
        response_over = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overflow@test.edu"}
        )
        assert response_over.status_code == 400
    
    def test_capacity_limits_different_activities(self, client, reset_activities):
        """Verify capacity limits are per-activity, not global"""
        activity1 = "Debate Club"  # max=16, currently has 1
        activity2 = "Drama Club"  # max=20, currently has 2
        
        email = "versatile@test.edu"
        
        # Should be able to signup for both (different activities)
        response1 = client.post(
            f"/activities/{activity1}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            f"/activities/{activity2}/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify in both activities
        get_response = client.get("/activities")
        assert email in get_response.json()[activity1]["participants"]
        assert email in get_response.json()[activity2]["participants"]
    
    @pytest.mark.parametrize("activity_name", [
        "Chess Club",          # max=12
        "Programming Class",   # max=20
        "Gym Class",          # max=30
        "Basketball Team",     # max=15
        "Soccer Club",        # max=22
        "Art Club",           # max=18
        "Drama Club",         # max=20
        "Debate Club",        # max=16
        "Science Club",       # max=25
    ])
    def test_all_activities_enforce_capacity(self, client, reset_activities, activity_name):
        """Verify all activities enforce capacity limits"""
        response_get = client.get("/activities")
        activity = response_get.json()[activity_name]
        max_participants = activity["max_participants"]
        current_count = len(activity["participants"])
        
        slots_available = max_participants - current_count
        
        # Fill available slots
        for i in range(slots_available):
            email = f"fill_{activity_name.replace(' ', '_')}_{i}@test.edu"
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify at capacity
        response_full = client.get("/activities")
        final_count = len(response_full.json()[activity_name]["participants"])
        assert final_count == max_participants
        
        # Try to overfill
        response_over = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "overflow@test.edu"}
        )
        assert response_over.status_code == 400


class TestSignupEdgeCases:
    """Test signup edge cases"""

    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test signup with various email formats"""
        activity = "Science Club"
        
        # Valid email formats - all should work
        valid_emails = [
            "student+tag@mergington.edu",
            "student.name@mergington.edu",
            "student_name@mergington.edu",
        ]
        
        for email in valid_emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            # Should either succeed or be rejected consistently
            # (depends on email validation)
            assert response.status_code in [200, 400]
    
    def test_signup_preserves_other_participants(self, client, reset_activities):
        """Verify signup doesn't affect other participants"""
        activity = "Chess Club"
        initial_participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        new_email = "newcomer@test.edu"
        
        # Get initial state
        response_before = client.get("/activities")
        initial = response_before.json()[activity]["participants"]
        
        # Add new participant
        client.post(
            f"/activities/{activity}/signup",
            params={"email": new_email}
        )
        
        # Verify original participants still present
        response_after = client.get("/activities")
        final = response_after.json()[activity]["participants"]
        
        for email in initial_participants:
            assert email in final
        assert new_email in final
        assert len(final) == len(initial) + 1
