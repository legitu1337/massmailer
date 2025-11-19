# Bulk SMTP Sender

A multi-threaded, SMTP-rotating bulk email sender designed for educational and authorized testing purposes.

---

## Features

### **Multi-Threaded Sending**

Utilizes `ThreadPoolExecutor` for concurrent email delivery, massively improving throughput during bulk operations.

### **SMTP Rotation**

Automatically cycles through multiple SMTP servers to load-balance traffic and avoid single-account rate limits.

### **DNS Blacklist Checker**

Checks SMTP server IPs against major DNSBL services (Spamhaus, Spamcop, Sorbs) during startup to protect sender reputation.

### **Smart Connection Handling**

Automatically selects connection type based on port:

* **465** → Implicit SSL
* **587 / 25** → STARTTLS

### **Usage Tracking**

Tracks per-account daily sending usage in `smtp_usage.json` and skips accounts that have reached their daily limit.

---

## Usage

1. **Edit `configs.json`**

   * Add your SMTP server list
   * Set daily limits for each account
   * Configure preferred timeouts

2. **Run the application:**

```bash
python main.py
```

3. **Provide your data:**

   * Sender email address
   * Email recipient list
   * HTML template / letter

Logs are displayed in the console and written to a persistent UTF-8 encoded log file.

---

## ⚠️ Disclaimer

This tool is intended **strictly for educational purposes and authorized testing**. The developer assumes **no responsibility** for misuse.

* Do **NOT** use this tool for spam or harassment.
* Ensure you have **permission** from recipients or service providers before sending bulk emails.
* Violating SMTP provider Terms of Service **may result in account suspension**.
