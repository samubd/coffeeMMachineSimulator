# Security Guide: Removing Sensitive Data from Code

## What Was Changed

The original code contained hardcoded credentials:
```python
self.auth_data = {
    'username': 'samuele.vecchi',
    'password': '12.T1rzan.21',
    'grant_type': 'password',
    'client_id': 'riseberg-web'
}
```

This has been replaced with secure environment variable loading.

## Current Implementation (Recommended)

### Option 1: Environment Variables with .env file (IMPLEMENTED)

**Files created/modified:**
- `.env` - Contains your credentials and configuration (DO NOT COMMIT TO GIT)
- `.gitignore` - Ensures .env and .toml files are not committed
- `astarte_api_client.py` - Modified to use environment variables for all sensitive data

**How it works:**
1. Credentials are stored in `.env` file
2. `python-dotenv` loads them as environment variables
3. Code reads from environment variables with validation
4. `.gitignore` prevents accidental commits

**Usage:**
```python
# The code now automatically loads from .env file
client = AstarteAPIClient()  # Will use environment variables
```

## Alternative Approaches

### Option 2: Pure Environment Variables (No .env file)

If you prefer not to use a .env file, you can set environment variables directly:

**Windows:**
```cmd
set ASTARTE_USERNAME=samuele.vecchi
set ASTARTE_PASSWORD=12.T1rzan.21
set ASTARTE_CLIENT_ID=riseberg-web
set ASTARTE_GRANT_TYPE=password
python your_script.py
```

**Linux/Mac:**
```bash
export ASTARTE_USERNAME=samuele.vecchi
export ASTARTE_PASSWORD=12.T1rzan.21
export ASTARTE_CLIENT_ID=riseberg-web
export ASTARTE_GRANT_TYPE=password
python your_script.py
```

### Option 3: Configuration File Approach

Add credentials to your existing `config.toml`:

```toml
# Add to config.toml
[auth]
username = "samuele.vecchi"
password = "12.T1rzan.21"
client_id = "riseberg-web"
grant_type = "password"
```

Then modify the code to read from TOML:
```python
import toml

# In __init__:
config = toml.load('config.toml')
self.auth_data = config['auth']
```

### Option 4: No Dependencies Approach

If you want to avoid the `python-dotenv` dependency, here's a version that only uses built-in Python:

```python
import os

class AstarteAPIClient:
    def __init__(self):
        # ... other initialization ...
        
        # Load from environment variables (no .env file support)
        self.auth_data = {
            'username': os.environ.get('ASTARTE_USERNAME'),
            'password': os.environ.get('ASTARTE_PASSWORD'),
            'grant_type': os.environ.get('ASTARTE_GRANT_TYPE', 'password'),
            'client_id': os.environ.get('ASTARTE_CLIENT_ID')
        }
        
        # Validate required variables
        required_vars = ['username', 'password', 'client_id']
        missing_vars = [var for var in required_vars if not self.auth_data[var]]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
```

## Security Best Practices

1. **Never commit credentials to version control**
   - Always use `.gitignore` to exclude credential files
   - Use environment variables or external configuration

2. **Use different credentials for different environments**
   - Development, staging, and production should have separate credentials
   - Consider using different .env files (.env.dev, .env.prod)

3. **Rotate credentials regularly**
   - Change passwords periodically
   - Use strong, unique passwords

4. **Limit credential access**
   - Only give credentials to team members who need them
   - Use role-based access control when possible

5. **Consider using secrets management systems**
   - For production: AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
   - For development: Environment variables are usually sufficient

## Testing Your Setup

To verify everything works:

1. Make sure `.env` file exists with your credentials
2. Run your application - it should work without hardcoded credentials
3. Try removing one variable from `.env` - you should get a clear error message

## Troubleshooting

**Error: "Missing required environment variables"**
- Check that your `.env` file exists and contains all required variables
- Ensure there are no typos in variable names
- Make sure `.env` file is in the same directory as your Python script

**Error: "Import 'dotenv' could not be resolved"**
- Install python-dotenv: `pip install python-dotenv`
- Or use Option 4 (no dependencies approach)

**Credentials not loading**
- Verify `.env` file format (no quotes around values unless needed)
- Check file encoding (should be UTF-8)
- Ensure no extra spaces around variable names or values
