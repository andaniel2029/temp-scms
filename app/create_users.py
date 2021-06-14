# Ensure there's at least one user.
from app import user_manager
from app.models import User, db, Role

try:
    if not User.query.filter(User.username == 'tim').first():
        user1 = User(username='tim', email='tim@ginn.ca', is_enabled=True,
                     password=user_manager.hash_password('MKC2018'), phone='123456789', company='My Company',
                     confirmed_at="2018-01-01 00:00:00")
        user1.roles.append(Role(name='superadmin'))
        db.session.add(user1)
        db.session.commit()
    if not User.query.filter(User.username == 'demo').first():
        user1 = User(username='demo', email='demo@example.com', is_enabled=True,
                     password=user_manager.hash_password('demo'), phone='123456789', company='Acme Ltd',
                     confirmed_at="2018-01-01 00:00:00")
        db.session.add(user1)
        db.session.commit()
    if not User.query.filter(User.username == 'warehousedemo').first():
        user1 = User(username='warehousedemo', email='warehouse@example.com', is_enabled=True,
                     password=user_manager.hash_password('warehousedemo'), phone='123456789',
                     company='Demo Warehouse Ltd', confirmed_at="2018-01-01 00:00:00")
        user1.roles.append(Role(name='warehouse'))
        db.session.add(user1)
        db.session.commit()
    if not User.query.filter(User.username == 'admindemo').first():
        user1 = User(username='admindemo', email='admin@example.com', is_enabled=True,
                     password=user_manager.hash_password('admindemo'), phone='123456789', company='PriorityBiz',
                     confirmed_at="2018-01-01 00:00:00")
        user1.roles.append(Role.query.get(1))
        db.session.add(user1)
        db.session.commit()
except:
    db.session.rollback()  # This happens if DB has not been created with db.create_all()
