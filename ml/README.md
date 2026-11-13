# AgriChain AI — Machine Learning Subsystem

This subsystem houses the computer vision and transit analytics pipelines for **AgriChain AI**, supporting the *Kinnow Quality Classification Using Convolutional Neural Networks* academic project.

---

## 1. Directory Layout

- **`data/`**: Local storage for raw citrus/Kinnow imagery and leak-free split directories (`train/`, `val/`, `test/`). Excluded from Git tracking.
- **`notebooks/`**: Jupyter notebooks for exploratory data analysis (EDA), class imbalance visualization, and sample inspection.
- **`src/`**: Modular ML source code:
  - Dataset abstractions and image augmentations.
  - Baseline CNN and ResNet18 transfer learning models.
  - Reproducible training loops with checkpointing.
  - Comprehensive evaluation suites (per-class Precision, Recall, F1, Accuracy, and Confusion Matrices).
  - Standalone inference engine compatible with FastAPI.
- **`experiments/`**: Metric summaries, loss curves, confusion matrices, and hyperparameter logs for each experiment. Excluded from Git tracking.
- **`artifacts/`**: Serialized model checkpoints (`.pth`) and ONNX exports. Excluded from Git tracking.

---

## 2. Experimental Principles & Standards

1. **Genuine Kinnow / Citrus Imagery**: No masquerading or relabeling of unrelated fruit datasets.
2. **Leak-Free Splits**: Image splitting will ensure near-duplicate frames or augmentations do not bridge across train, validation, and test subsets.
3. **Rigorous Comparison**: A custom simple CNN baseline will be benchmarked directly against a ResNet18 transfer learning architecture.
4. **Reproducibility**: Explicit random seeding (Python, NumPy, PyTorch) across all splits and training scripts.
5. **Hardware Acceleration**: Benchmarked on NVIDIA RTX 4050 Laptop GPU via PyTorch CUDA.
