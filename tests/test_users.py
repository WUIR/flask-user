"""Users API tests — profile & admin CRUD."""


class TestGetProfile:
    def test_get_me_success(self, client, auth_header):
        resp = client.get("/api/v1/users/me", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["username"] == "testuser"
        assert "password_hash" not in data["data"]

    def test_get_me_no_auth(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_get_me_bad_token(self, client):
        resp = client.get("/api/v1/users/me", headers={
            "Authorization": "Bearer this.is.invalid",
        })
        # JWT extension returns 422 for malformed tokens
        assert resp.status_code in (401, 422)


class TestUpdateProfile:
    def test_update_nickname(self, client, auth_header):
        resp = client.put("/api/v1/users/me", json={
            "nickname": "NewNick",
        }, headers=auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["nickname"] == "NewNick"

    def test_update_all_fields(self, client, auth_header):
        resp = client.put("/api/v1/users/me", json={
            "nickname": "FullUpdate",
            "phone": "13800138000",
        }, headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["nickname"] == "FullUpdate"
        assert data["phone"] == "13800138000"

    def test_update_no_auth(self, client):
        resp = client.put("/api/v1/users/me", json={"nickname": "X"})
        assert resp.status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, auth_header):
        resp = client.put("/api/v1/users/me/password", json={
            "old_password": "Test1234",
            "new_password": "NewPass567",
        }, headers=auth_header)
        assert resp.status_code == 200

        # Login with new password
        resp = client.post("/api/v1/auth/login", json={
            "login": "testuser",
            "password": "NewPass567",
        })
        assert resp.status_code == 200

    def test_change_password_wrong_old(self, client, auth_header):
        resp = client.put("/api/v1/users/me/password", json={
            "old_password": "wrongpass",
            "new_password": "NewPass789",
        }, headers=auth_header)
        assert resp.status_code == 400
        assert "旧密码不正确" in resp.get_json()["message"]

    def test_change_password_weak_new(self, client, auth_header):
        resp = client.put("/api/v1/users/me/password", json={
            "old_password": "Test1234",
            "new_password": "12345678",
        }, headers=auth_header)
        assert resp.status_code == 422

    def test_change_password_no_auth(self, client):
        resp = client.put("/api/v1/users/me/password", json={
            "old_password": "x", "new_password": "y",
        })
        assert resp.status_code == 401


class TestDeleteAccount:
    def test_delete_no_auth(self, client):
        resp = client.delete("/api/v1/users/me")
        assert resp.status_code == 401

    def test_delete_success(self, client, app):
        """Register a disposable user, then delete."""
        resp = client.post("/api/v1/auth/register", json={
            "username": "goner",
            "email": "goner@example.com",
            "password": "Goner1234",
        })
        token = resp.get_json()["data"]["access_token"]

        resp = client.delete("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200

        # Verify user is gone
        resp = client.post("/api/v1/auth/login", json={
            "login": "goner",
            "password": "Goner1234",
        })
        assert resp.status_code == 401


# ── Admin Tests ────────────────────────────────────────────────

class TestAdminListUsers:
    def test_list_success(self, client, admin_auth_header):
        resp = client.get("/api/v1/users", headers=admin_auth_header)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_list_pagination(self, client, admin_auth_header):
        resp = client.get("/api/v1/users?page=1&per_page=5",
                          headers=admin_auth_header)
        assert resp.status_code == 200

    def test_list_search(self, client, admin_auth_header):
        resp = client.get("/api/v1/users?search=admin",
                          headers=admin_auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] >= 1

    def test_list_search_no_results(self, client, admin_auth_header):
        resp = client.get("/api/v1/users?search=zzz_nonexistent",
                          headers=admin_auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 0

    def test_non_admin_forbidden(self, client, auth_header):
        resp = client.get("/api/v1/users", headers=auth_header)
        assert resp.status_code == 403


class TestAdminGetUser:
    def test_get_user_success(self, client, admin_auth_header):
        resp = client.get("/api/v1/users/1", headers=admin_auth_header)
        assert resp.status_code == 200

    def test_get_user_not_found(self, client, admin_auth_header):
        resp = client.get("/api/v1/users/9999", headers=admin_auth_header)
        assert resp.status_code == 404


class TestAdminUpdateUser:
    def test_update_role(self, client, admin_auth_header):
        resp = client.put("/api/v1/users/1", json={
            "role": "admin",
        }, headers=admin_auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["role"] == "admin"

    def test_update_deactivate(self, client, admin_auth_header):
        resp = client.put("/api/v1/users/1", json={
            "is_active": False,
        }, headers=admin_auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_active"] is False

    def test_update_not_found(self, client, admin_auth_header):
        resp = client.put("/api/v1/users/9999", json={"role": "admin"},
                          headers=admin_auth_header)
        assert resp.status_code == 404


class TestAdminDeleteUser:
    def test_delete_success(self, client, app, admin_auth_header):
        """Register a temp user and delete via admin."""
        resp = client.post("/api/v1/auth/register", json={
            "username": "tempadmin",
            "email": "temp@example.com",
            "password": "Temp1234",
        })
        temp_id = resp.get_json()["data"]["user"]["id"]

        resp = client.delete(f"/api/v1/users/{temp_id}",
                             headers=admin_auth_header)
        assert resp.status_code == 200

    def test_delete_not_found(self, client, admin_auth_header):
        resp = client.delete("/api/v1/users/9999",
                             headers=admin_auth_header)
        assert resp.status_code == 404
