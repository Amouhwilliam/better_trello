"""
Functional tests for /tasks endpoints.
All requests go through the full HTTP stack: routing → dependency injection
→ application service → domain → SQLite.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def future(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_task(client: TestClient, title: str = "My Task", days: int = 7, **kwargs) -> dict:
    payload = {"title": title, "deadline": future(days), **kwargs}
    r = client.post("/tasks", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def create_project(client: TestClient, title: str = "Project", days: int = 30) -> dict:
    r = client.post("/projects", json={"title": title, "deadline": future(days)})
    assert r.status_code == 201, r.text
    return r.json()


def create_user(client: TestClient, email: str = "worker@example.com") -> dict:
    r = client.post("/users", json={"fullname": "Worker", "email": email, "password": "pass1234"})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# POST /tasks
# ---------------------------------------------------------------------------

class TestCreateTask:
    def test_returns_201(self, client: TestClient):
        r = client.post("/tasks", json={"title": "T", "deadline": future()})
        assert r.status_code == 201

    def test_response_shape(self, client: TestClient):
        r = client.post("/tasks", json={"title": "T", "deadline": future(), "description": "d"})
        body = r.json()
        assert "id" in body
        assert body["title"] == "T"
        assert body["description"] == "d"
        assert body["completed"] is False
        assert body["project_id"] is None

    def test_missing_title_returns_422(self, client: TestClient):
        r = client.post("/tasks", json={"deadline": future()})
        assert r.status_code == 422

    def test_missing_deadline_returns_422(self, client: TestClient):
        r = client.post("/tasks", json={"title": "T"})
        assert r.status_code == 422

    def test_empty_title_returns_422(self, client: TestClient):
        r = client.post("/tasks", json={"title": "", "deadline": future()})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------

class TestListTasks:
    def test_returns_200(self, client: TestClient):
        r = client.get("/tasks")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_includes_created_task(self, client: TestClient):
        t = create_task(client, title="ListMe")
        ids = [x["id"] for x in client.get("/tasks").json()]
        assert t["id"] in ids

    def test_filter_completed_true(self, client: TestClient):
        t = create_task(client, title="CompletedFilter")
        client.patch(f"/tasks/{t['id']}/complete")
        results = client.get("/tasks?completed=true").json()
        assert all(x["completed"] for x in results)
        assert any(x["id"] == t["id"] for x in results)

    def test_filter_completed_false(self, client: TestClient):
        create_task(client, title="OpenFilter")
        results = client.get("/tasks?completed=false").json()
        assert all(not x["completed"] for x in results)

    def test_filter_overdue(self, client: TestClient):
        r = client.post("/tasks", json={"title": "OverdueFilter", "deadline": past(2)})
        assert r.status_code == 201
        results = client.get("/tasks?overdue=true").json()
        assert all(not x["completed"] for x in results)
        assert any(x["id"] == r.json()["id"] for x in results)

    def test_filter_by_project_id(self, client: TestClient):
        project = create_project(client)
        t = create_task(client, title="ProjectFilter", days=10)
        client.post(f"/projects/{project['id']}/tasks/{t['id']}/link")
        results = client.get(f"/tasks?project_id={project['id']}").json()
        assert len(results) >= 1
        assert all(x["project_id"] == project["id"] for x in results)


# ---------------------------------------------------------------------------
# GET /tasks/{id}
# ---------------------------------------------------------------------------

class TestGetTask:
    def test_returns_task(self, client: TestClient):
        t = create_task(client, title="GetMe")
        r = client.get(f"/tasks/{t['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == t["id"]

    def test_returns_404_for_unknown_id(self, client: TestClient):
        r = client.get("/tasks/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_404_body_has_detail(self, client: TestClient):
        r = client.get("/tasks/00000000-0000-0000-0000-000000000001")
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# PUT /tasks/{id}
# ---------------------------------------------------------------------------

class TestUpdateTask:
    def test_updates_title(self, client: TestClient):
        t = create_task(client, title="OldTitle")
        r = client.put(f"/tasks/{t['id']}", json={"title": "NewTitle"})
        assert r.status_code == 200
        assert r.json()["title"] == "NewTitle"

    def test_updates_description(self, client: TestClient):
        t = create_task(client)
        r = client.put(f"/tasks/{t['id']}", json={"description": "Updated desc"})
        assert r.status_code == 200
        assert r.json()["description"] == "Updated desc"

    def test_updates_deadline(self, client: TestClient):
        t = create_task(client, days=10)
        new_dl = future(5)
        r = client.put(f"/tasks/{t['id']}", json={"deadline": new_dl})
        assert r.status_code == 200

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.put("/tasks/00000000-0000-0000-0000-000000000000", json={"title": "X"})
        assert r.status_code == 404

    def test_deadline_exceeding_project_returns_422(self, client: TestClient):
        project = create_project(client, days=5)
        t = create_task(client, days=3)
        client.post(f"/projects/{project['id']}/tasks/{t['id']}/link")
        r = client.put(f"/tasks/{t['id']}", json={"deadline": future(10)})
        assert r.status_code == 422
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# DELETE /tasks/{id}
# ---------------------------------------------------------------------------

class TestDeleteTask:
    def test_returns_204(self, client: TestClient):
        t = create_task(client)
        r = client.delete(f"/tasks/{t['id']}")
        assert r.status_code == 204

    def test_task_no_longer_retrievable(self, client: TestClient):
        t = create_task(client)
        client.delete(f"/tasks/{t['id']}")
        assert client.get(f"/tasks/{t['id']}").status_code == 404

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.delete("/tasks/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/complete
# ---------------------------------------------------------------------------

class TestCompleteTask:
    def test_returns_200(self, client: TestClient):
        t = create_task(client)
        r = client.patch(f"/tasks/{t['id']}/complete")
        assert r.status_code == 200

    def test_completed_flag_is_true(self, client: TestClient):
        t = create_task(client)
        r = client.patch(f"/tasks/{t['id']}/complete")
        assert r.json()["completed"] is True

    def test_persisted_after_complete(self, client: TestClient):
        t = create_task(client)
        client.patch(f"/tasks/{t['id']}/complete")
        assert client.get(f"/tasks/{t['id']}").json()["completed"] is True

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.patch("/tasks/00000000-0000-0000-0000-000000000000/complete")
        assert r.status_code == 404

    def test_idempotent(self, client: TestClient):
        t = create_task(client)
        client.patch(f"/tasks/{t['id']}/complete")
        r = client.patch(f"/tasks/{t['id']}/complete")
        assert r.status_code == 200
        assert r.json()["completed"] is True


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/reopen
# ---------------------------------------------------------------------------

class TestReopenTask:
    def test_returns_200(self, client: TestClient):
        t = create_task(client)
        client.patch(f"/tasks/{t['id']}/complete")
        r = client.patch(f"/tasks/{t['id']}/reopen")
        assert r.status_code == 200

    def test_completed_flag_is_false(self, client: TestClient):
        t = create_task(client)
        client.patch(f"/tasks/{t['id']}/complete")
        r = client.patch(f"/tasks/{t['id']}/reopen")
        assert r.json()["completed"] is False

    def test_reopening_task_reopens_completed_project(self, client: TestClient):
        project = create_project(client, days=20)
        t = create_task(client, days=10)
        client.post(f"/projects/{project['id']}/tasks/{t['id']}/link")
        client.patch(f"/tasks/{t['id']}/complete")
        client.patch(f"/projects/{project['id']}/complete")

        assert client.get(f"/projects/{project['id']}").json()["completed"] is True

        client.patch(f"/tasks/{t['id']}/reopen")
        assert client.get(f"/projects/{project['id']}").json()["completed"] is False

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.patch("/tasks/00000000-0000-0000-0000-000000000000/reopen")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/assign/{user_id}  &  PATCH /tasks/{id}/unassign
# ---------------------------------------------------------------------------

class TestAssignTask:
    def test_assign_sets_assignee_id(self, client: TestClient):
        user = create_user(client, email="assign_test1@x.com")
        t = create_task(client, title="Assignable")
        r = client.patch(f"/tasks/{t['id']}/assign/{user['id']}")
        assert r.status_code == 200
        assert r.json()["assignee_id"] == user["id"]

    def test_assign_is_persisted(self, client: TestClient):
        user = create_user(client, email="assign_test2@x.com")
        t = create_task(client, title="Persist assign")
        client.patch(f"/tasks/{t['id']}/assign/{user['id']}")
        assert client.get(f"/tasks/{t['id']}").json()["assignee_id"] == user["id"]

    def test_assign_unknown_user_returns_404(self, client: TestClient):
        t = create_task(client, title="No user assign")
        r = client.patch(f"/tasks/{t['id']}/assign/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_assign_unknown_task_returns_404(self, client: TestClient):
        user = create_user(client, email="assign_test3@x.com")
        r = client.patch(f"/tasks/00000000-0000-0000-0000-000000000000/assign/{user['id']}")
        assert r.status_code == 404

    def test_reassign_to_different_user(self, client: TestClient):
        u1 = create_user(client, email="assign_u1@x.com")
        u2 = create_user(client, email="assign_u2@x.com")
        t = create_task(client, title="Reassign")
        client.patch(f"/tasks/{t['id']}/assign/{u1['id']}")
        r = client.patch(f"/tasks/{t['id']}/assign/{u2['id']}")
        assert r.json()["assignee_id"] == u2["id"]

    def test_unassign_clears_assignee(self, client: TestClient):
        user = create_user(client, email="unassign_test@x.com")
        t = create_task(client, title="Unassignable")
        client.patch(f"/tasks/{t['id']}/assign/{user['id']}")
        r = client.patch(f"/tasks/{t['id']}/unassign")
        assert r.status_code == 200
        assert r.json()["assignee_id"] is None

    def test_unassign_is_persisted(self, client: TestClient):
        user = create_user(client, email="unassign_persist@x.com")
        t = create_task(client, title="Unassign persist")
        client.patch(f"/tasks/{t['id']}/assign/{user['id']}")
        client.patch(f"/tasks/{t['id']}/unassign")
        assert client.get(f"/tasks/{t['id']}").json()["assignee_id"] is None

    def test_unassign_idempotent(self, client: TestClient):
        t = create_task(client, title="Already unassigned")
        r = client.patch(f"/tasks/{t['id']}/unassign")
        assert r.status_code == 200
        assert r.json()["assignee_id"] is None

    def test_task_response_has_assignee_id_field(self, client: TestClient):
        t = create_task(client, title="Field check")
        assert "assignee_id" in t
