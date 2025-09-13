#!/usr/bin/env python3
"""
Test XOAUTH2 string format
"""

import base64

def create_xoauth2_string(email, access_token):
    """Test XOAUTH2 string creation"""
    # Method 1: Current implementation
    auth_string1 = f'user={email}\x01auth=Bearer {access_token}\x01\x01'
    b64_1 = base64.b64encode(auth_string1.encode()).decode()
    
    # Method 2: Using byte literals
    auth_string2 = b'user=' + email.encode() + b'\x01auth=Bearer ' + access_token.encode() + b'\x01\x01'
    b64_2 = base64.b64encode(auth_string2).decode()
    
    # Method 3: Manual construction
    parts = [
        'user=' + email,
        'auth=Bearer ' + access_token,
        '',
        ''
    ]
    auth_string3 = '\x01'.join(parts)
    b64_3 = base64.b64encode(auth_string3.encode()).decode()
    
    print(f"Method 1 raw: {repr(auth_string1)}")
    print(f"Method 1 b64: {b64_1[:50]}...")
    print(f"Method 1 decoded: {repr(base64.b64decode(b64_1).decode())}")
    print()
    
    print(f"Method 2 raw: {repr(auth_string2)}")
    print(f"Method 2 b64: {b64_2[:50]}...")
    print(f"Method 2 decoded: {repr(base64.b64decode(b64_2).decode())}")
    print()
    
    print(f"Method 3 raw: {repr(auth_string3)}")
    print(f"Method 3 b64: {b64_3[:50]}...")
    print(f"Method 3 decoded: {repr(base64.b64decode(b64_3).decode())}")
    print()
    
    return b64_2  # Return the byte-based version

if __name__ == "__main__":
    test_email = "test@gmail.com"
    test_token = "ya29.test_token_123"
    
    create_xoauth2_string(test_email, test_token)