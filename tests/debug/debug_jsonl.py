"""
Debug JSONL format issue
"""

import json
import tempfile

def debug_jsonl():
    print("Debugging JSONL format...")
    
    # Create test data
    test_entries = [
        {"email_id": "test_001", "decision": "keep"},
        {"email_id": "test_002", "decision": "delete"}
    ]
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.jsonl', delete=False) as f:
        print(f"Writing to: {f.name}")
        
        for i, entry in enumerate(test_entries):
            json_line = json.dumps(entry) + '\n'
            print(f"Writing line {i}: {repr(json_line)}")
            f.write(json_line)
        
        f.flush()
        f.seek(0)
        
        print("\nReading back:")
        content = f.read()
        print(f"Raw content: {repr(content)}")
        
        f.seek(0)
        lines = f.readlines()
        print(f"Lines: {lines}")
        
        for i, line in enumerate(lines):
            print(f"Line {i}: {repr(line)}")
            if line.strip():
                try:
                    parsed = json.loads(line.strip())
                    print(f"Parsed: {parsed}")
                except Exception as e:
                    print(f"Parse error: {e}")

if __name__ == "__main__":
    debug_jsonl()