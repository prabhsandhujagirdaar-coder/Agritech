"""
AgriChain AI — Non-destructive Inspector for Dataset B (7.7 GB)
Reads zip index and metadata files in memory without extracting images to disk.
"""
import zipfile
import os
import sys
from collections import Counter, defaultdict
import io

DATASET_B_PATH = r"C:\Users\PrabSandhu\Downloads\Guava (Psidium guajava) fruit digital and thermal Images.zip"

def inspect_dataset_b():
    print("=" * 60)
    print("INSPECTING DATASET B:")
    print(f"Path: {DATASET_B_PATH}")
    size_gb = os.path.getsize(DATASET_B_PATH) / (1024 ** 3)
    print(f"File Size: {size_gb:.3f} GB ({os.path.getsize(DATASET_B_PATH):,} bytes)")
    
    with zipfile.ZipFile(DATASET_B_PATH, 'r') as z:
        infolist = z.infolist()
        print(f"Total entries in archive: {len(infolist)}")
        
        files = [info for info in infolist if not info.is_dir()]
        dirs = [info for info in infolist if info.is_dir()]
        print(f"File entries: {len(files)}, Directory entries: {len(dirs)}")
        
        # Extensions
        exts = Counter(os.path.splitext(f.filename)[1].lower() for f in files)
        print(f"\nFile extensions breakdown:\n{dict(exts)}")
        
        # Check for nested zips or archives
        nested_archives = [f.filename for f in files if os.path.splitext(f.filename)[1].lower() in ['.zip', '.tar', '.gz', '.7z', '.rar']]
        if nested_archives:
            print(f"\n[ALERT] Found nested archives in Dataset B ({len(nested_archives)}):")
            for na in nested_archives[:10]:
                print(f"  - {na}")
        else:
            print("\nNo nested archives found in Dataset B.")
            
        # Check non-image metadata, doc, annotation files
        doc_exts = ['.txt', '.csv', '.xlsx', '.xls', '.json', '.xml', '.pdf', '.docx', '.doc', '.md', '.tsv', '.mat', '.seq', '.raw', '.csv']
        doc_files = [f for f in files if os.path.splitext(f.filename)[1].lower() in doc_exts or 'readme' in f.filename.lower() or 'license' in f.filename.lower()]
        print(f"\nDocumentation & Metadata files found ({len(doc_files)}):")
        for df in doc_files:
            print(f"  - {df.filename} ({df.file_size:,} bytes)")
            # If text/csv/json/md, print preview
            ext = os.path.splitext(df.filename)[1].lower()
            if ext in ['.txt', '.csv', '.json', '.md', ''] and df.file_size < 100000:
                try:
                    content = z.read(df.filename).decode('utf-8', errors='ignore')
                    print(f"    Preview:\n{content[:600]}\n    --- [End preview] ---")
                except Exception as e:
                    print(f"    Could not read text: {e}")
                    
        # Examine directory tree and path hierarchy
        print("\nAnalyzing Directory Tree Structure...")
        folder_counts = defaultdict(int)
        for f in files:
            norm_path = f.filename.replace('\\', '/')
            parts = norm_path.split('/')
            if len(parts) > 1:
                # Group by top 2 or 3 directory levels
                level_key = '/'.join(parts[:-1])
                folder_counts[level_key] += 1
            else:
                folder_counts["[root]"] += 1
                
        print(f"Total distinct subdirectories containing files: {len(folder_counts)}")
        print("Sample subdirectories and file counts (up to 30):")
        for k, cnt in sorted(folder_counts.items(), key=lambda x: x[0])[:30]:
            print(f"  - '{k}': {cnt} files")
            
        # Categorize Digital vs Thermal
        digital_files = [f for f in files if 'digital' in f.filename.lower() or 'rgb' in f.filename.lower()]
        thermal_files = [f for f in files if 'thermal' in f.filename.lower() or 'flir' in f.filename.lower() or 'ir' in f.filename.lower()]
        print(f"\nModality Counts:")
        print(f"  - Matching 'digital' or 'rgb': {len(digital_files)} files")
        print(f"  - Matching 'thermal' or 'flir' or 'ir': {len(thermal_files)} files")
        
        # Sample filenames from each modality
        if digital_files:
            print("  Sample digital filenames:")
            for df in digital_files[:5]:
                print(f"    {df.filename}")
        if thermal_files:
            print("  Sample thermal filenames:")
            for tf in thermal_files[:5]:
                print(f"    {tf.filename}")

if __name__ == "__main__":
    inspect_dataset_b()
