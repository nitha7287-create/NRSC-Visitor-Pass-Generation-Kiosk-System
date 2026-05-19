from waitress import serve

from app import (
    app,
    init_visitor_db,
    init_staff_db,
    init_admin_db
)

init_visitor_db()
init_staff_db()
init_admin_db()

serve(
    app,
    host="0.0.0.0",
    port=5000
)