import os

CLEAN_DIR = 'corpus/clean'

def purge_fake_books():
    print("Initiating Imposter Purge...")
    files = [f for f in os.listdir(CLEAN_DIR) if f.endswith('.txt')]
    
    deleted_count = 0
    
    for filename in files:
        filepath = os.path.join(CLEAN_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # If it's an audiobook index OR ridiculously short (less than ~1000 words)
        if "Audio formats available:" in content or len(content) < 5000:
            f.close() # Close before deleting
            os.remove(filepath)
            deleted_count += 1
            print(f"Incinerated fake book: {filename}")
            
    print("-" * 50)
    print(f"Purge complete! Burned {deleted_count} imposter files.")

if __name__ == "__main__":
    purge_fake_books()