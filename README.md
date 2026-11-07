# CivicResolve AI - Dubai AI Agents Championship
## Societal AI Agent: Consumer Problem-Resolution Assistant

> **"Your Problem. Your Rights. Your Resolution."**

CivicResolve AI is located in the [`civicresolve-ai/`](./civicresolve-ai/) directory.

### Quick Start
1. **Cloud Deployment (Vercel)**:
   - Connect this repository to [Vercel](https://vercel.com/) or run:
     ```bash
     npx vercel
     ```
   - See [Vercel Deployment Guide](./civicresolve-ai/docs/vercel_deployment.md).

2. **Launch Web Interface Locally**:
   ```bash
   cd civicresolve-ai
   streamlit run app.py
   ```
3. **Launch FastAPI Backend Locally**:
   ```bash
   cd civicresolve-ai
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Run Automated Test Suite**:
   ```bash
   python -m pytest civicresolve-ai/tests -v
   ```
5. **Run 100-Case Evaluation Benchmark**:
   ```bash
   python civicresolve-ai/tests/evaluate_benchmark.py
   ```

### Official External Workflow Links
- **File a New Complaint**: [AskDubai Civic Form](https://askdubai.app.n8n.cloud/form/civicresolve)
- **Check or Update Existing Case**: [AskDubai Update Form](https://askdubai.app.n8n.cloud/form/civicresolve-update)

For full technical specifications, architecture diagrams, and benchmark evaluations, see [civicresolve-ai/README.md](./civicresolve-ai/README.md).
