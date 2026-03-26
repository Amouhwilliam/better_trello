"""
Functional tests for /projects endpoints.
All requests go through the full HTTP stack: routing → dependency injection
→ application service → domain → SQLite.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def future(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client: TestClient, title: str = "My Project", days: int = 30) -> dict:
    r = client.post("/projects", json={"title": title, "deadline": future(days)})
    assert r.status_code == 201, r.text
    return r.json()


def create_task(client: TestClient, title: str = "My Task", days: int = 10) -> dict:
    r = client.post("/tasks", json={"title": title, "deadline": future(days)})
    assert r.status_code == 201, r.text
    return r.json()


def link(client: TestClient, project_id: str, task_id: str) -> None:
    r = client.post(f"/projects/{project_id}/tasks/{task_id}/link")
    assert r.status_code == 200, r.text


def complete_task(client: TestClient, task_id: str) -> None:
    r = client.patch(f"/tasks/{task_id}/complete")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# POST /projects
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_returns_201(self, client: TestClient):
        r = client.post("/projects", json={"title": "P", "deadline": future()})
        assert r.status_code == 201

    def test_response_shape(self, client: TestClient):
        r = client.post("/projects", json={"title": "Launch", "deadline": future()})
        body = r.json()
        assert "id" in body
        assert body["title"] == "Launch"
        assert body["completed"] is False

    def test_missing_title_returns_422(self, client: TestClient):
        r = client.post("/projects", json={"deadline": future()})
        assert r.status_code == 422

    def test_missing_deadline_returns_422(self, client: TestClient):
        r = client.post("/projects", json={"title": "P"})
        assert r.status_code == 422

    def test_empty_title_returns_422(self, client: TestClient):
        r = client.post("/projects", json={"title": "", "deadline": future()})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_returns_200(self, client: TestClient):
        r = client.get("/projects")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert "has_more" in body

    def test_includes_created_project(self, client: TestClient):
        p = create_project(client, title="ListMe")
        ids = [x["id"] for x in client.get("/projects").json()["items"]]
        assert p["id"] in ids


# ---------------------------------------------------------------------------
# GET /projects — pagination
# ---------------------------------------------------------------------------

class TestListProjectsPaginated:
    def test_default_page_is_1(self, client: TestClient):
        r = client.get("/projects")
        assert r.json()["page"] == 1

    def test_default_page_size_is_10(self, client: TestClient):
        r = client.get("/projects")
        assert r.json()["page_size"] == 10

    def test_total_reflects_all_projects(self, client: TestClient):
        for i in range(3):
            create_project(client, title=f"PagTotal{i}")
        total = client.get("/projects").json()["total"]
        assert total >= 3

    def test_page_size_limits_items(self, client: TestClient):
        for i in range(5):
            create_project(client, title=f"PagSize{i}")
        items = client.get("/projects?page_size=2").json()["items"]
        assert len(items) <= 2

    def test_second_page_returns_next_items(self, client: TestClient):
        for i in range(4):
            create_project(client, title=f"PagPage{i}")
        page1 = client.get("/projects?page=1&page_size=2").json()["items"]
        page2 = client.get("/projects?page=2&page_size=2").json()["items"]
        ids1 = {x["id"] for x in page1}
        ids2 = {x["id"] for x in page2}
        assert ids1.isdisjoint(ids2)

    def test_has_more_true_when_more_pages_exist(self, client: TestClient):
        for i in range(3):
            create_project(client, title=f"HasMore{i}")
        body = client.get("/projects?page=1&page_size=1").json()
        assert body["has_more"] is True

    def test_has_more_false_on_last_page(self, client: TestClient):
        create_project(client, title="LastPage")
        total = client.get("/projects").json()["total"]
        body = client.get(f"/projects?page=1&page_size={total}").json()
        assert body["has_more"] is False

    def test_invalid_page_returns_422(self, client: TestClient):
        r = client.get("/projects?page=0")
        assert r.status_code == 422

    def test_invalid_page_size_returns_422(self, client: TestClient):
        r = client.get("/projects?page_size=0")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{id}
# ---------------------------------------------------------------------------

class TestGetProject:
    def test_returns_project(self, client: TestClient):
        p = create_project(client)
        r = client.get(f"/projects/{p['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == p["id"]

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.get("/projects/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_404_body_has_detail(self, client: TestClient):
        r = client.get("/projects/00000000-0000-0000-0000-000000000001")
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# PUT /projects/{id}
# ---------------------------------------------------------------------------

class TestUpdateProject:
    def test_updates_title(self, client: TestClient):
        p = create_project(client, title="Old")
        r = client.put(f"/projects/{p['id']}", json={"title": "New"})
        assert r.status_code == 200
        assert r.json()["title"] == "New"

    def test_updates_deadline(self, client: TestClient):
        p = create_project(client, days=60)
        new_dl = future(45)
        r = client.put(f"/projects/{p['id']}", json={"deadline": new_dl})
        assert r.status_code == 200

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.put("/projects/00000000-0000-0000-0000-000000000000", json={"title": "X"})
        assert r.status_code == 404

    def test_moving_deadline_earlier_clamps_task_deadlines(self, client: TestClient):
        p = create_project(client, days=60)
        t = create_task(client, days=40)
        link(client, p["id"], t["id"])

        client.put(f"/projects/{p['id']}", json={"deadline": future(20)})

        updated_task = client.get(f"/tasks/{t['id']}").json()
        task_dl = datetime.fromisoformat(updated_task["deadline"].replace("Z", "+00:00"))
        project_dl = datetime.now(timezone.utc) + timedelta(days=20)
        assert task_dl.date() == project_dl.date()

    def test_moving_deadline_later_does_not_affect_tasks(self, client: TestClient):
        p = create_project(client, days=30)
        t = create_task(client, days=10)
        link(client, p["id"], t["id"])
        original_deadline = client.get(f"/tasks/{t['id']}").json()["deadline"]

        client.put(f"/projects/{p['id']}", json={"deadline": future(60)})

        assert client.get(f"/tasks/{t['id']}").json()["deadline"] == original_deadline


# ---------------------------------------------------------------------------
# DELETE /projects/{id}
# ---------------------------------------------------------------------------

class TestDeleteProject:
    def test_returns_204(self, client: TestClient):
        p = create_project(client)
        r = client.delete(f"/projects/{p['id']}")
        assert r.status_code == 204

    def test_project_no_longer_retrievable(self, client: TestClient):
        p = create_project(client)
        client.delete(f"/projects/{p['id']}")
        assert client.get(f"/projects/{p['id']}").status_code == 404

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.delete("/projects/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /projects/{id}/complete
# ---------------------------------------------------------------------------

class TestCompleteProject:
    def test_completes_project_with_no_tasks(self, client: TestClient):
        p = create_project(client)
        r = client.patch(f"/projects/{p['id']}/complete")
        assert r.status_code == 200
        assert r.json()["completed"] is True

    def test_completes_when_all_tasks_done(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        link(client, p["id"], t["id"])
        complete_task(client, t["id"])

        r = client.patch(f"/projects/{p['id']}/complete")
        assert r.status_code == 200
        assert r.json()["completed"] is True

    def test_returns_422_when_open_tasks_exist(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        link(client, p["id"], t["id"])

        r = client.patch(f"/projects/{p['id']}/complete")
        assert r.status_code == 422
        assert "detail" in r.json()

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.patch("/projects/00000000-0000-0000-0000-000000000000/complete")
        assert r.status_code == 404

    def test_persisted_after_complete(self, client: TestClient):
        p = create_project(client)
        client.patch(f"/projects/{p['id']}/complete")
        assert client.get(f"/projects/{p['id']}").json()["completed"] is True


# ---------------------------------------------------------------------------
# GET /projects/{id}/tasks
# ---------------------------------------------------------------------------

class TestGetProjectTasks:
    def test_returns_empty_list_for_new_project(self, client: TestClient):
        p = create_project(client)
        r = client.get(f"/projects/{p['id']}/tasks")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_linked_tasks(self, client: TestClient):
        p = create_project(client, days=20)
        t1 = create_task(client, title="T1", days=10)
        t2 = create_task(client, title="T2", days=10)
        link(client, p["id"], t1["id"])
        link(client, p["id"], t2["id"])
        create_task(client, title="Unlinked")

        r = client.get(f"/projects/{p['id']}/tasks")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert t1["id"] in ids
        assert t2["id"] in ids
        assert len(ids) == 2

    def test_returns_404_for_unknown_project(self, client: TestClient):
        r = client.get("/projects/00000000-0000-0000-0000-000000000000/tasks")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/tasks/{task_id}/link
# ---------------------------------------------------------------------------

class TestLinkTask:
    def test_links_task_to_project(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        r = client.post(f"/projects/{p['id']}/tasks/{t['id']}/link")
        assert r.status_code == 200
        assert r.json()["project_id"] == p["id"]

    def test_task_appears_in_project_tasks(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        client.post(f"/projects/{p['id']}/tasks/{t['id']}/link")
        ids = [x["id"] for x in client.get(f"/projects/{p['id']}/tasks").json()]
        assert t["id"] in ids

    def test_returns_422_when_task_deadline_exceeds_project(self, client: TestClient):
        p = create_project(client, days=5)
        t = create_task(client, days=15)
        r = client.post(f"/projects/{p['id']}/tasks/{t['id']}/link")
        assert r.status_code == 422

    def test_returns_404_for_unknown_project(self, client: TestClient):
        t = create_task(client)
        r = client.post(f"/projects/00000000-0000-0000-0000-000000000000/tasks/{t['id']}/link")
        assert r.status_code == 404

    def test_returns_404_for_unknown_task(self, client: TestClient):
        p = create_project(client)
        r = client.post(f"/projects/{p['id']}/tasks/00000000-0000-0000-0000-000000000000/link")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/tasks/{task_id}/unlink
# ---------------------------------------------------------------------------

class TestUnlinkTask:
    def test_unlinks_task_from_project(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        link(client, p["id"], t["id"])

        r = client.delete(f"/projects/{p['id']}/tasks/{t['id']}/unlink")
        assert r.status_code == 200
        assert r.json()["project_id"] is None

    def test_task_no_longer_in_project_tasks(self, client: TestClient):
        p = create_project(client, days=20)
        t = create_task(client, days=10)
        link(client, p["id"], t["id"])
        client.delete(f"/projects/{p['id']}/tasks/{t['id']}/unlink")

        ids = [x["id"] for x in client.get(f"/projects/{p['id']}/tasks").json()]
        assert t["id"] not in ids

    def test_returns_404_for_unknown_task(self, client: TestClient):
        p = create_project(client)
        r = client.delete(
            f"/projects/{p['id']}/tasks/00000000-0000-0000-0000-000000000000/unlink"
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
