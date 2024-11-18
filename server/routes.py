import os

from flask import (
  request,
  jsonify,
  send_file,
  send_from_directory,
  Flask,
)

def routes(app: Flask):

  @app.route("/static/<file_name>")
  def get_static_file(file_name: str):
    root_path = os.path.join(__file__, "..", "..", "browser.lib")
    root_path = os.path.abspath(root_path)
    dir_path = os.path.join(root_path, "dist")
    dir_path = os.path.abspath(dir_path)
    file_path = os.path.join(dir_path, file_name)
    file_path = os.path.abspath(file_path)

    if os.path.exists(file_path):
      return send_from_directory(dir_path, file_name)

    dir_path = os.path.join(root_path, "static")
    dir_path = os.path.abspath(dir_path)

    return send_from_directory(dir_path, file_name)

  @app.errorhandler(404)
  def page_not_found(e):
    mimetypes = request.accept_mimetypes
    if mimetypes.accept_json and not mimetypes.accept_html:
      return jsonify({ "error": "Not found" }), 404

    path = os.path.join(__file__, "..", "..", "browser.lib", "index.html")
    path = os.path.abspath(path)
    return send_file(path, mimetype="text/html")

  @app.errorhandler(500)
  def internal_server_error(e):
    return jsonify({
      "error": "Internal server error",
      "description": str(e),
    }), 500
