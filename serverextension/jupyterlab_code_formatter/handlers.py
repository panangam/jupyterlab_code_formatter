import json
import pkg_resources

from notebook.notebookapp import NotebookWebApplication
from notebook.utils import url_path_join
from notebook.base.handlers import APIHandler

from jupyterlab_code_formatter.formatters import SERVER_FORMATTERS


def setup_handlers(web_app: NotebookWebApplication) -> None:
    host_pattern = ".*$"
    web_app.add_handlers(
        host_pattern,
        [
            (
                url_path_join(
                    web_app.settings["base_url"],
                    "/jupyterlab_code_formatter/formatters",
                ),
                FormattersAPIHandler,
            )
        ],
    )

    web_app.add_handlers(
        host_pattern,
        [
            (
                url_path_join(
                    web_app.settings["base_url"], "/jupyterlab_code_formatter/format"
                ),
                FormatAPIHandler,
            )
        ],
    )


def check_plugin_version(handler: APIHandler):
    server_extension_version = pkg_resources.get_distribution(
        "jupyterlab_code_formatter"
    ).version
    lab_extension_version = handler.request.headers.get("Plugin-Version")
    version_matches = server_extension_version == lab_extension_version
    if not version_matches:
        handler.set_status(
            422,
            f"Mismatched versions of server extension ({server_extension_version}) "
            f"and lab extension ({lab_extension_version}). "
            f"Please ensure they are the same.",
        )
        handler.finish()
    return version_matches


class FormattersAPIHandler(APIHandler):
    def get(self) -> None:
        """Show what formatters are installed and avaliable."""
        if check_plugin_version(self):
            self.finish(
                json.dumps(
                    {
                        "formatters": {
                            name: {
                                "enabled": formatter.importable,
                                "label": formatter.label,
                            }
                            for name, formatter in SERVER_FORMATTERS.items()
                        }
                    }
                )
            )


class FormatAPIHandler(APIHandler):
    def post(self) -> None:
        if check_plugin_version(self):
            data = json.loads(self.request.body.decode("utf-8"))
            formatter_instance = SERVER_FORMATTERS.get(data["formatter"])

            if formatter_instance is None or not formatter_instance.importable:
                self.set_status(404, "Formatter not found!")
                self.finish()
            else:
                options = data["options"] or {}
                formatted_code = []
                for code in data["code"]:
                    try:
                        formatted_code.append(
                            {"code": formatter_instance.format_code(code, **options)}
                        )
                    except Exception as e:
                        formatted_code.append({"error": str(e)})
                self.finish(json.dumps({"code": formatted_code}))