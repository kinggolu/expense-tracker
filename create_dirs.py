import os

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')
    print("Templates directory created successfully.")
else:
    print("Templates directory already exists.") 