from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def static_client():
    # 静态页面不依赖数据库生命周期；业务 API 仍在其他测试中验证。
    return TestClient(create_app(Settings(mongo_database="frontend_static_test")))


def test_root_and_ui_routes_serve_browser_entrypoint():
    client = static_client()
    for path in ("/", "/ui", "/ui/"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "简问 · 在线问卷" in response.text
        assert 'src="/ui-assets/app.js"' in response.text


def test_javascript_and_stylesheet_are_served_as_static_assets():
    client = static_client()
    javascript = client.get("/ui-assets/app.js")
    stylesheet = client.get("/ui-assets/style.css")
    assert javascript.status_code == stylesheet.status_code == 200
    assert javascript.headers["content-type"].startswith(("text/javascript", "application/javascript"))
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert "/surveys/access/" in javascript.text
    assert ":root" in stylesheet.text


def test_api_contract_paths_remain_in_openapi_and_frontend_is_not_an_api():
    schema = static_client().get("/openapi.json").json()
    paths = schema["paths"]
    assert "/auth/login" in paths
    assert "/surveys" in paths
    assert "/surveys/access/{access_token}/progress" in paths
    assert "/surveys/{form_id}/statistics" in paths
    assert "/" not in paths and "/ui" not in paths
