"""
Edge case tests for unregister functionality.
Focuses on idempotency, state transitions, and capacity freeing.
"""

import pytest


class TestUnregisterEdgeCases:
    """Test unregister edge cases"""

    def test_unregister_then_reregister_same_student(self, client, reset_activities):
        """Verify student can re-register after unregistering"""
        activity = "Science Club"
        email = "harper@mergington.edu"  # Currently registered
        
        # Unregister
        response1 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Verify unregistered
        response_check1 = client.get("/activities")
        assert email not in response_check1.json()[activity]["participants"]
        
        # Re-register
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify registered again
        response_check2 = client.get("/activities")
        assert email in response_check2.json()[activity]["participants"]
    
    def test_unregister_nonexistent_student_twice(self, client, reset_activities):
        """Verify unregister fails consistently for nonexistent student"""
        activity = "Chess Club"
        email = "doesnotexist@test.edu"
        
        # First unregister attempt
        response1 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response1.status_code == 400
        
        # Second unregister attempt - should fail same way
        response2 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response2.status_code == 400
    
    def test_unregister_preserves_other_participants(self, client, reset_activities):
        """Verify unregister only removes target participant"""
        activity = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        email_to_keep = "daniel@mergington.edu"
        
        # Unregister one participant
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email_to_remove}
        )
        assert response.status_code == 200
        
        # Verify correct participant removed
        response_check = client.get("/activities")
        participants = response_check.json()[activity]["participants"]
        
        assert email_to_remove not in participants
        assert email_to_keep in participants


class TestCapacityFreeing:
    """Test that unregistering frees capacity for new signups"""

    def test_unregister_creates_available_slot(self, client, reset_activities):
        """Verify unregister frees capacity for new signups"""
        activity = "Basketball Team"  # max=15, currently has 1
        original_participant = "alex@mergington.edu"
        
        # Fill to capacity
        for i in range(14):
            email = f"filler{i}@test.edu"
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify at capacity
        response_check1 = client.get("/activities")
        assert len(response_check1.json()[activity]["participants"]) == 15
        
        # Try to add one more - should fail
        response_over = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overflow1@test.edu"}
        )
        assert response_over.status_code == 400
        
        # Unregister someone
        response_unreg = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": original_participant}
        )
        assert response_unreg.status_code == 200
        
        # Verify capacity freed
        response_check2 = client.get("/activities")
        assert len(response_check2.json()[activity]["participants"]) == 14
        
        # Now should be able to add someone
        response_new = client.post(
            f"/activities/{activity}/signup",
            params={"email": "newfill@test.edu"}
        )
        assert response_new.status_code == 200
    
    def test_unregister_multiple_creates_space(self, client, reset_activities):
        """Verify multiple unregisters create multiple slots"""
        activity = "Debate Club"  # max=16, currently has 1
        new_participant = "newdebater@test.edu"
        
        # Fill activity
        for i in range(15):
            email = f"debater_{i}@test.edu"
            client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
        
        # At capacity
        response_check1 = client.get("/activities")
        assert len(response_check1.json()[activity]["participants"]) == 16
        
        # Cannot add more
        response_fail1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overflow1@test.edu"}
        )
        assert response_fail1.status_code == 400
        
        # Unregister two participants
        response_unreg1 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": "debater_0@test.edu"}
        )
        assert response_unreg1.status_code == 200
        
        response_unreg2 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": "debater_1@test.edu"}
        )
        assert response_unreg2.status_code == 200
        
        # Should have 2 slots now
        response_check2 = client.get("/activities")
        assert len(response_check2.json()[activity]["participants"]) == 14
        
        # Can add two more
        response_new1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": "newdebater1@test.edu"}
        )
        assert response_new1.status_code == 200
        
        response_new2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": "newdebater2@test.edu"}
        )
        assert response_new2.status_code == 200
        
        # Back at capacity
        response_check3 = client.get("/activities")
        assert len(response_check3.json()[activity]["participants"]) == 16


class TestUnregisterStateTransitions:
    """Test state transitions during unregister"""

    def test_unregister_decrements_count_correctly(self, client, reset_activities):
        """Verify participant count decrements by exactly 1"""
        activity = "Programming Class"
        email = "emma@mergington.edu"
        
        # Get initial state
        response1 = client.get("/activities")
        initial_count = len(response1.json()[activity]["participants"])
        
        # Unregister
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Get final state
        response2 = client.get("/activities")
        final_count = len(response2.json()[activity]["participants"])
        
        # Should decrement by exactly 1
        assert final_count == initial_count - 1
    
    @pytest.mark.parametrize("activity_name,target_email", [
        ("Chess Club", "michael@mergington.edu"),
        ("Programming Class", "emma@mergington.edu"),
        ("Gym Class", "john@mergington.edu"),
        ("Soccer Club", "liam@mergington.edu"),
        ("Drama Club", "mason@mergington.edu"),
    ])
    def test_unregister_from_multiple_activities(self, client, reset_activities, activity_name, target_email):
        """Test unregister from various activities"""
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": target_email}
        )
        
        assert response.status_code == 200
        
        # Verify removed
        response_check = client.get("/activities")
        assert target_email not in response_check.json()[activity_name]["participants"]
