# TraceX Security, Privacy & Compliance Architecture

---

## 1. Security Principles
- **Air-Gapped & Offline Execution**: Zero outbound internet network calls during operational inference. No telemetry, third-party analytics, or external API keys required.
- **Strict Input Sanitization**: Defenses against malicious payloads, recursive entity expansion in XML (XML Bomb/Billion Laughs), path traversal in filenames, and non-numeric amount injections.
- **Role-Based Local Authentication**: Local JWT tokens with BCrypt password hashing supporting `INVESTIGATOR` and `ADMIN` roles.
- **Immutable Audit Trail**: All dataset uploads, model trainings, alert status changes, and report exports are logged with timestamps, user identities, and action metadata.

---

## 2. Forensic & Ethical Safeguards
- **Observation vs Proof Separation**: Network IP observations reflect P2P relay node records on the wire. The system explicitly disclaims that IP observations constitute cryptographic proof of wallet ownership.
- **Investigative Lead Classification**: Alerts are categorized strictly as prioritized investigative leads for human analyst verification. The system never claims to "prove criminal guilt".
