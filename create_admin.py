from django.contrib.auth.models import User

# Get or create admin user
user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'is_superuser': True,
        'is_staff': True,
        'is_active': True
    }
)

# Set password
user.set_password('admin123')
user.save()

if created:
    print('Created new admin user with password: admin123')
else:
    print('Updated existing admin user password to: admin123')

print(f'Admin user status:')
print(f'  Username: {user.username}')
print(f'  Is superuser: {user.is_superuser}')
print(f'  Is staff: {user.is_staff}')
print(f'  Is active: {user.is_active}')