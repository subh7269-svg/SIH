# LeadForge Model Evaluation & Validation Benchmark

---

## 1. Evaluation Methodology

Because real Bitcoin forensic data often lacks perfect ground-truth labels, LeadForge evaluates detectors against controlled synthetic benchmark scenarios modeled on empirical laundering and peeling patterns:
1. **Normal Activity (Baseline ~80%)**: Regular consumer wallets, single IP, low velocity.
2. **Rapid Multi-Hop Peeling Chains (Anomalous)**: Automated rapid transfers (< 3 min intervals), small peels, shifting IP relays across multiple countries.
3. **High-Fanout Structuring / Layering (Anomalous)**: Single source wallet fragmenting funds across 20+ transient output addresses in a short burst.
4. **Multi-IP Network Dispersal (Anomalous)**: Single entity observed broadcasting transactions across 8+ distinct foreign IP addresses and ASNs in under an hour.

---

## 2. Evaluation Metrics

- **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$
- **Recall (Detection Rate)**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$
- **F1 Score**: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$
- **ROC-AUC & PR-AUC**: Area under ROC and Precision-Recall curves.
- **False Positive Rate**: $\frac{\text{FP}}{\text{FP} + \text{TN}}$

All metrics are computed in real time during model training and displayed transparently in the ML Model Studio.
