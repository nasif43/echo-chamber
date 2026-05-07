import os
import re

CLEAN_DIR = 'corpus/clean'

def fix_local_files_aggressively():
    print("Initiating Thermonuclear Scrub Protocol...")
    files = [f for f in os.listdir(CLEAN_DIR) if f.endswith('.txt')]
    
    fixed_count = 0
    
    for filename in files:
        filepath = os.path.join(CLEAN_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_length = len(content)
        text = content
        
        # --- 1. START STRIP ---
        # \s+ allows it to match even if "PROJECT GUTENBERG" is split across a line break
        start_pattern = r'\*\*\*\s*START OF.*?PROJECT\s+GUTENBERG.*?\*\*\*'
        start_match = re.search(start_pattern, text, re.IGNORECASE | re.DOTALL)
        if start_match:
            text = text[start_match.end():]
            
        # --- 2. END STRIP (THE GUILLOTINE) ---
        # Finds the earliest occurrence of any known Gutenberg footer signature
        end_patterns = [
            r'\*\*\*\s*END OF.*?PROJECT\s+GUTENBERG', 
            r'End of the Project Gutenberg',
            r'End of Project Gutenberg',
            r'\*\*\*\s*END:.*?PROJECT\s+GUTENBERG',
            # If they forgot the marker completely, catch the actual legal text
            r'Section 1\.\s+General Terms of Use',
            r'1\.F\.1\.\s+Project Gutenberg volunteers'
            r'Audio formats available:',
            r'the Work may be freely reproduced, distributed',
            r'including by methods that have not yet been invented or conceived'
        ]
        
        for pattern in end_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Slices off everything from the match to the end of the file
                text = text[:match.start()]
                break # Stop looking once we've successfully chopped it

        text = text.strip()
        
        # Overwrite only if we actually amputated a significant chunk of boilerplate
        if original_length - len(text) > 100:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            fixed_count += 1
            print(f"Amputated hidden boilerplate from: {filename}")
            
    print("-" * 50)
    print(f"Scrub complete! Fixed {fixed_count} out of {len(files)} files.")

if __name__ == "__main__":
    fix_local_files_aggressively()