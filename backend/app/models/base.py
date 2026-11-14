from sqlalchemy import event, text


def _auto_set_tenant_id(mapper, connection, target):
    """Automatically populate tenant_id on insert from request context or default tenant."""
    if getattr(target, 'tenant_id', None) is None:
        from ..tenant_context import get_current_tenant_id
        tid = get_current_tenant_id()
        if tid is not None:
            target.tenant_id = tid
        else:
            try:
                res = connection.execute(text("SELECT id FROM restaurantconfig LIMIT 1")).fetchone()
                if res and res[0] is not None:
                    target.tenant_id = int(res[0])
                else:
                    connection.execute(
                        text("INSERT INTO restaurantconfig (name, slug, pos_enabled, is_active) "
                             "VALUES ('Default Restaurant', 'default', 0, 1)")
                    )
                    res2 = connection.execute(text("SELECT id FROM restaurantconfig WHERE slug = 'default'")).fetchone()
                    if res2 and res2[0] is not None:
                        target.tenant_id = int(res2[0])
            except Exception:
                pass


def register_tenant_listener(*models) -> None:
    """Register the automatic tenant_id before_insert listener for the given SQLModel classes."""
    for model in models:
        event.listen(model, 'before_insert', _auto_set_tenant_id)
