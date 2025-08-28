#!/usr/bin/env python3
"""
Fix SQLite Row object handling in the app.py file
The current code uses selected_prize.keys() which doesn't work properly with SQLite Row objects
"""

def fix_sqlite_row_handling():
    """Fix SQLite Row object handling in app.py"""
    
    with open('/home/tim/incentDev/app.py', 'r') as f:
        content = f.read()
    
    # Count occurrences before fix
    old_pattern = "selected_prize['dollar_value'] if 'dollar_value' in selected_prize.keys() else 0.0"
    count_before = content.count(old_pattern)
    
    print(f"Found {count_before} instances of problematic SQLite Row handling")
    
    # Replace with proper handling
    # For SQLite Row objects, we should use getattr or try/except
    new_pattern = "getattr(selected_prize, 'dollar_value', 0.0) or 0.0"
    
    fixed_content = content.replace(old_pattern, new_pattern)
    
    # Also fix any duplicated lines (common copy-paste error)
    lines = fixed_content.split('\n')
    cleaned_lines = []
    prev_line = None
    
    for line in lines:
        # Skip exact duplicates (same line appearing twice)
        if line != prev_line or not line.strip().startswith('dollar_value ='):
            cleaned_lines.append(line)
        else:
            print(f"Removed duplicate line: {line.strip()}")
        prev_line = line
    
    final_content = '\n'.join(cleaned_lines)
    
    # Write the fixed file
    with open('/home/tim/incentDev/app.py', 'w') as f:
        f.write(final_content)
    
    count_after = final_content.count(new_pattern)
    print(f"✅ Fixed {count_before} instances of SQLite Row handling")
    print(f"✅ Applied {count_after} proper fixes")

if __name__ == "__main__":
    print("🔧 FIXING SQLITE ROW HANDLING")
    print("=" * 40)
    fix_sqlite_row_handling()
    print("🏁 SQLite Row handling fixed!")