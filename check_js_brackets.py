import sys
import re

def check_brackets(code):
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    lines = code.split('\n')
    
    for line_no, line in enumerate(lines, 1):
        # Ignore comments
        if line.strip().startswith('//'): continue
        
        for char_no, char in enumerate(line, 1):
            if char in '({[':
                stack.append((char, line_no, char_no))
            elif char in ')}]':
                if not stack:
                    print(f"Error: Unmatched '{char}' at line {line_no}, col {char_no}")
                    return False
                top_char, top_line, top_col = stack.pop()
                if pairs[char] != top_char:
                    print(f"Error: Mismatched '{char}' at line {line_no}, col {char_no}. Expected '{pairs[char]}' to match opening '{top_char}' at line {top_line}, col {top_col}")
                    return False
    
    if stack:
        for char, line_no, char_no in stack:
            print(f"Error: Unclosed '{char}' starting at line {line_no}, col {char_no}")
        return False
        
    print("Bracket matching OK")
    return True

with open('temp_script.js', 'r', encoding='utf-8') as f:
    js = f.read()
    check_brackets(js)
