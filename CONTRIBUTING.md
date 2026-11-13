# Contributing to AgriChain AI

Thank you for your interest in contributing to **AgriChain AI — Predictive Cold-Chain Agritech Exchange**!

This guide outlines our development standards, branch management, and testing workflows to maintain code quality, scientific rigor, and data integrity.

---

## 1. Branch Strategy

We adhere to a clean, structured Git branching model:

- `main`: The stable production branch. Every commit must pass all regression suites and model integrity checks.
- `develop`: Ongoing integration branch for new features and cross-module enhancements.
- `feature/<name>`: Dedicated feature branches (e.g., `feature/kinnow-model-v2`, `feature/telemetry-alert-ui`).
- `fix/<name>`: Targeted bug fixes and corrections (e.g., `fix/route-interpolation-clamp`).
- `mobile/flutter`: Dedicated branch for mobile application features and Android integration.

---

## 2. Development Guidelines

### Codebase Integrity & Coding Standards
- **Python (Backend & ML)**: Follow PEP 8 guidelines. Type hints are encouraged across FastAPI routers, Pydantic schemas, and services.
- **JavaScript / React (Next.js)**: Maintain strict ESLint compliance (`npm --prefix apps/web run lint`).
- **Documentation**: Preserve comments and docstrings. Document new APIs and services in relevant `/docs` files.

### Frozen Checkpoints Policy
> [!CRITICAL]
> The five core ML model checkpoints in `ml/artifacts/` (`best_guava_resnet18.pth`, `best_banana_resnet18.pth`, `best_fruit_identifier_mobilenet_v3_large.pth`, `best_fruit_identifier_resnet18.pth`, `best_apple_yolov8n.pt`) are **cryptographically locked**.
> Never retrain, overwrite, or modify frozen model weights without an approved architectural phase proposal, new version tag, and updated cryptographic audit record.

---

## 3. Pull Request Workflow

1. Fork or branch from `develop` (or `main` if `develop` is absent).
2. Create your feature branch: `git checkout -b feature/your-feature-name`.
3. Implement your changes following project conventions.
4. Run all local regression tests:
   ```bash
   # Python backend unit & inventory tests
   $env:PYTHONPATH="backend"
   .\.venv\Scripts\python.exe backend/tests/test_inventory.py
   .\.venv\Scripts\python.exe scripts/verify_shipment_routing.py
   .\.venv\Scripts\python.exe scripts/verify_simulation_route_integrity.py

   # Frontend unit tests & linter
   npm --prefix apps/web test
   npm --prefix apps/web run lint
   ```
5. Ensure zero secret keys, credentials, or private keys are committed (`python scripts/audit_security.py`).
6. Submit a Pull Request targeting `main` or `develop` with a clear explanation of modifications.

---

## 4. Reporting Issues

When filing an issue, please include:
- Operating System and environment details (Python version, CUDA version, Node.js version).
- Reproduction steps and error logs.
- Observed vs expected behavior.
- Relevant corridor or shipment IDs if reporting simulation/routing defects.
