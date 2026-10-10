import re

with open('backend/app/routers/sysadmin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken function signature
broken_signature = '''def update_restaurant_status(
    restaurant_id: int,
    payload: SysAdminRestaurantStatusUpdate,
    SysAdminRestaurantUpdate,
    SysAdminUserResponse,
    SysAdminPasswordReset,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):'''

fixed_signature = '''def update_restaurant_status(
    restaurant_id: int,
    payload: SysAdminRestaurantStatusUpdate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):'''

content = content.replace(broken_signature, fixed_signature)

with open('backend/app/routers/sysadmin.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed!')
