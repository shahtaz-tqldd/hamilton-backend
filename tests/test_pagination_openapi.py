from app.main import app


def query_parameters(path: str) -> dict[str, dict]:
    operation = app.openapi()["paths"][path]["get"]
    return {
        parameter["name"]: parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "query"
    }


def test_resource_lists_use_page_based_pagination() -> None:
    for path in ("/api/v1/snippets", "/api/v1/env-variables", "/api/v1/files"):
        parameters = query_parameters(path)

        assert "page" in parameters
        assert parameters["page"]["schema"]["default"] == 1
        assert "page_size" in parameters
        assert parameters["page_size"]["schema"]["default"] == 50
        assert "limit" not in parameters
        assert "offset" not in parameters


def test_folder_list_defaults_to_twenty_per_page() -> None:
    parameters = query_parameters("/api/v1/folders")

    assert parameters["page"]["schema"]["default"] == 1
    assert parameters["page_size"]["schema"]["default"] == 20


def test_folder_response_includes_total_items() -> None:
    folder_schema = app.openapi()["components"]["schemas"]["FolderResponse"]

    assert "total_items" in folder_schema["properties"]
