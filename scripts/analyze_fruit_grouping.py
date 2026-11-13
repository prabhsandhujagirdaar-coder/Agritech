"""
AgriChain AI — Fruit Instance Grouping Analysis
Evaluates connected components based on perceptual hash (dHash) and filename proximity
to test whether reliable fruit-level clusters can be formed.
"""
import os
import json
from collections import defaultdict, Counter
from PIL import Image

def dhash(image, hash_size=8):
    image = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = list(image.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** (index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
    return "".join(hex_string)

def hamming_distance(h1, h2):
    b1 = bytes.fromhex(h1)
    b2 = bytes.fromhex(h2)
    return sum(bin(x ^ y).count("1") for x, y in zip(b1, b2))

def analyze_clusters():
    base_dir = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\guava_classification"
    manifest_dir = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\manifests"
    
    all_records = []
    for split in ['train', 'val', 'test']:
        with open(os.path.join(manifest_dir, f"{split}.json")) as f:
            all_records.extend(json.load(f))
            
    print(f"Total images: {len(all_records)}")
    
    # Compute dHash for all
    print("Computing dHash for all 2,309 images...")
    hashes = {}
    for r in all_records:
        with Image.open(r["abs_path"]) as im:
            hashes[r["rel_path"]] = dhash(im)
            
    # Group by (variety, class)
    strata = defaultdict(list)
    for r in all_records:
        strata[(r["variety"], r["class_name"])].append(r)
        
    print("\nClustering within each (variety, class) using dHash distance <= 2...")
    total_clusters = 0
    cluster_size_dist = Counter()
    
    for (variety, class_name), records in sorted(strata.items()):
        # Build adjacency list
        n = len(records)
        adj = defaultdict(list)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = records[i]["rel_path"]
                r2 = records[j]["rel_path"]
                dist = hamming_distance(hashes[r1], hashes[r2])
                if dist <= 2:
                    adj[i].append(j)
                    adj[j].append(i)
                    
        # Connected components (BFS)
        visited = set()
        components = []
        for i in range(n):
            if i not in visited:
                comp = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)
                
        total_clusters += len(components)
        sizes = [len(c) for c in components]
        for s in sizes:
            cluster_size_dist[s] += 1
            
        print(f"  {variety} | {class_name} ({n} images): {len(components)} clusters. Sizes: min={min(sizes)}, max={max(sizes)}, median={sorted(sizes)[len(sizes)//2]}")
        
    print(f"\nTotal clusters across all 9 strata: {total_clusters}")
    print(f"Cluster size distribution (size: count of clusters):")
    for s, count in sorted(cluster_size_dist.items()):
        print(f"  Size {s}: {count} clusters ({s * count} images)")

if __name__ == "__main__":
    analyze_clusters()
