import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(hashed_password, plain_password):
    """
    Verify a plain password against hashed password
    Args:
        hashed_password: bytes or string (from database)
        plain_password: string (user input)
    """
    try:
        # If hashed_password is string (from database), encode it
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        
        # Encode plain password if it's string
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
            
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False