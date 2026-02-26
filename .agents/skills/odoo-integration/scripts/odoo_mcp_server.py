import json
import sys

from odoo_client import from_env


def main() -> None:
    client = from_env()
    for raw in sys.stdin:
        request = json.loads(raw)
        method = request.get("method")

        if method == "odoo_list_partners":
            result = client.list_partners()
            response = {"id": request.get("id"), "result": result}
        else:
            response = {
                "id": request.get("id"),
                "error": {"message": f"Unsupported method: {method}"},
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
