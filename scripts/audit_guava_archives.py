"""
AgriChain AI — Non-destructive Guava Dataset Archive Inspector
Inspects Dataset A (including nested archive) and Dataset B.
"""
import zipfile
import os
import sys
import json
from collections import Counter, defaultdict
from PIL import Image
import io

DATASET_A_PATH = r"C:\Users\PrabSandhu\Downloads\Guava Fruit  Dataset for Classification.zip"
DATASET_B_PATH = r"C:\Users\PrabSandhu\Downloads\Guava (Psidium guajava) fruit digital and thermal Images.zip"

def inspect_dataset_a_nested():
    print("=" * 60)
    print("INSPECTING DATASET A (OUTER & NESTED ARCHIVE):")
    
    with zipfile.ZipFile(DATASET_A_PATH, 'r') as outer_z:
        nested_name = outer_z.namelist()[0]
        print(f"Outer archive contains: {nested_name}")
        nested_bytes = outer_z.read(nested_name)
        print(f"Nested archive raw size: {len(nested_bytes) / (1024*1024):.2f} MB")
        
        with zipfile.ZipFile(io.BytesIO(nested_bytes), 'r') as inner_z:
            infolist = inner_z.infolist()
            print(f"Total entries in nested archive: {len(infolist)}")
            
            files = [info for info in infolist if not info.is_dir()]
            dirs = [info for info in infolist if info.is_dir()]
            print(f"Nested File entries: {len(files)}, Directory entries: {len(dirs)}")
            
            # File extensions
            exts = Counter(os.path.splitext(f.filename)[1].lower() for f in files)
            print(f"File extensions: {dict(exts)}")
            
            # Check for non-image files
            doc_files = [f.filename for f in files if os.path.splitext(f.filename)[1].lower() not in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp']]
            print(f"Non-image files found: {doc_files}")
            for df in doc_files[:10]:
                print(f"  Content of {df}:")
                try:
                    content = inner_z.read(df).decode('utf-8', errors='ignore')[:500]
                    print(f"    {content}")
                except Exception as e:
                    print(f"    Could not read as text: {e}")
            
            # Class folders / paths
            # Let's inspect directory paths
            class_counts = defaultdict(int)
            path_examples = defaultdict(list)
            for f in files:
                parts = f.filename.replace('\\', '/').split('/')
                # Filter out empty parts
                parts = [p for p in parts if p]
                if len(parts) > 1:
                    class_name = parts[-2]
                    class_counts[class_name] += 1
                    if len(path_examples[class_name]) < 3:
                        path_examples[class_name].append(f.filename)
                else:
                    class_counts["[root]"] += 1
            
            print(f"\nClass/Folder counts ({len(class_counts)} classes):")
            for c, cnt in sorted(class_counts.items()):
                print(f"  - '{c}': {cnt} images (e.g. {path_examples[c][:1]})")
                
            # Sample dimensions, color mode, formats across classes
            image_files = [f for f in files if os.path.splitext(f.filename)[1].lower() in ['.jpg', '.jpeg', '.png', '.bmp']]
            print(f"\nTotal image files in nested archive: {len(image_files)}")
            
            # Check image properties per class
            class_samples = defaultdict(list)
            for f in image_files:
                parts = f.filename.replace('\\', '/').split('/')
                parts = [p for p in parts if p]
                cname = parts[-2] if len(parts) > 1 else "[root]"
                if len(class_samples[cname]) < 5:
                    class_samples[cname].append(f)
                    
            print("\nSampling image dimensions and modes across classes:")
            for cname, smp_list in sorted(class_samples.items()):
                dim_set = set()
                mode_set = set()
                fmt_set = set()
                for info in smp_list:
                    try:
                        b = inner_z.read(info.filename)
                        with Image.open(io.BytesIO(b)) as im:
                            dim_set.add(im.size)
                            mode_set.add(im.mode)
                            fmt_set.add(im.format)
                    except Exception as e:
                        dim_set.add(f"ERR: {e}")
                print(f"  Class '{cname}': formats={fmt_set}, modes={mode_set}, sampled_dims={dim_set}")
                
            # Integrity check of nested archive
            print("\nRunning CRC integrity test on nested archive...")
            bad = inner_z.testzip()
            if bad is None:
                print("[NESTED INTEGRITY PASS] All nested files in Dataset A passed CRC check!")
            else:
                print(f"[NESTED INTEGRITY FAIL] Corrupt file: {bad}")

if __name__ == "__main__":
    inspect_dataset_a_nested()
