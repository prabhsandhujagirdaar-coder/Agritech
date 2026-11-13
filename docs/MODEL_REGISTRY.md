# AgriChain AI — Machine Learning Model Registry

This document records the authoritative cryptographic audit, architecture, taxonomy, and inference characteristics for all trained and frozen model checkpoints in **AgriChain AI**.

---

## 1. Cryptographic Model Checkpoint Audit

All production weights are located in `ml/artifacts/` and tracked via Git LFS.

| Checkpoint Filename | Architecture | Size | Target Crop | SHA-256 Cryptographic Hash |
| :--- | :--- | :---: | :--- | :--- |
| **`best_guava_resnet18.pth`** | PyTorch ResNet-18 | 44.8 MB | Guava | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` |
| **`best_banana_resnet18.pth`** | PyTorch ResNet-18 | 128.8 MB | Banana | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` |
| **`best_fruit_identifier_mobilenet_v3_large.pth`** | MobileNetV3-Large | 17.0 MB | Multi-Fruit | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` |
| **`best_fruit_identifier_resnet18.pth`** | ResNet-18 | 128.8 MB | Multi-Fruit | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` |
| **`best_apple_yolov8n.pt`** | Ultralytics YOLOv8n | 6.5 MB | Apple | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` |
| **`latest_guava_resnet18_checkpoint.pth`** | PyTorch ResNet-18 | 128.8 MB | Guava (Epoch 15) | `4bbdb1f855d05ffda631bfa2863a3ca4ba022a106e2ceb1fa9f127a6f2359aa5` |

---

## 2. Model Architecture & Class Taxonomies

### 2.1 Guava Maturity Classifier (`best_guava_resnet18.pth`)
- **Backbone**: Modified ResNet-18 with 3-class linear head.
- **Taxonomy**:
  - `0: Green` (Unripe, hard texture, optimal for extended transit > 5 days)
  - `1: Mature Green` (Harvest-ready, firm, optimal cold-chain export 4°C – 8°C)
  - `2: Ripe` (Yellowing skin, soft, immediate local mandi dispatch)
- **Performance**: 97.4% test accuracy across Pakistani & Indian Guava benchmarks.

### 2.2 Banana Ripeness Classifier (`best_banana_resnet18.pth`)
- **Backbone**: PyTorch ResNet-18 with 4-class classification head.
- **Taxonomy**:
  - `0: Underripe` (Solid green peel, high starch)
  - `1: Barely Ripe` (Yellow-green transition)
  - `2: Ripe` (Solid yellow, prime commercial table quality)
  - `3: Overripe` (Brown flecks, rapid sugar conversion)
- **Performance**: 98.1% accuracy.

### 2.3 Fruit Identifier Service (`best_fruit_identifier_mobilenet_v3_large.pth`)
- **Backbone**: MobileNetV3-Large tuned for fast mobile/edge inference.
- **Taxonomy**:
  - `guava`, `banana`, `apple`, `kinnow`, `mango`, `foliage_background`
- **Role**: Automatically detects produce category before routing to crop-specific models, preventing out-of-distribution classification errors.

### 2.4 Apple Quality Detector (`best_apple_yolov8n.pt`)
- **Backbone**: YOLOv8 Nano object detector.
- **Role**: Detects apple fruit instances and surface defects/scab blemishes.

---

## 3. Checkpoint Placement & Verification

To verify that local checkpoints match the frozen baseline:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -c "
import hashlib
from pathlib import Path

baseline = {
    'best_guava_resnet18.pth': 'b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4',
    'best_banana_resnet18.pth': '3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae',
    'best_fruit_identifier_mobilenet_v3_large.pth': '273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356',
    'best_fruit_identifier_resnet18.pth': '07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967',
    'best_apple_yolov8n.pt': '02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2',
}

for name, expected in baseline.items():
    p = Path('ml/artifacts') / name
    if not p.exists():
        print(f'MISSING: {name}')
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    match = (h == expected)
    print(f'[{'PASS' if match else 'FAIL'}] {name} (size: {p.stat().st_size:,} bytes)')
"
```
