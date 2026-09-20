# Deploy IDX Stock Analyzer ke CloudBaik VPS

## Prasyarat
- VPS CloudBaik (Ubuntu 22.04) - 1 vCPU, 2GB RAM
- SSH access ke VPS (IP + password/key)
- Akun GitHub
- (Opsional) Domain

---

## Langkah 1: Setup VPS

### SSH ke VPS
```bash
ssh root@IP_VPS_ANDA
```

### Update System
```bash
apt update && apt upgrade -y
```

### Install Dependencies
```bash
apt install -y python3.11 python3.11-venv python3-pip nginx git ufw
```

### Setup Firewall
```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

---

## Langkah 2: Clone Project

### Buat Directory
```bash
mkdir -p /opt/idx-stock-analyzer
cd /opt/idx-stock-analyzer
```

### Clone dari GitHub
```bash
git clone https://github.com/USERNAME/idx-stock-analyzer.git .
```

---

## Langkah 3: Setup Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Langkah 4: Setup Environment Variables

```bash
cp .env.example .env
nano .env
```

Isi file `.env` dengan API keys yang diperlukan (atau biarkan kosong jika tidak ada).

---

## Langkah 5: Setup Systemd Service

### Copy Service File
```bash
cp deploy/systemd/stock-analyzer.service /etc/systemd/system/
```

### Edit Path (sesuaikan jika perlu)
```bash
nano /etc/systemd/system/stock-analyzer.service
```

Pastikan `WorkingDirectory` dan `ExecStart` sesuai:
```
WorkingDirectory=/opt/idx-stock-analyzer
ExecStart=/opt/idx-stock-analyzer/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
```

### Start Service
```bash
systemctl daemon-reload
systemctl enable stock-analyzer
systemctl start stock-analyzer
systemctl status stock-analyzer
```

---

## Langkah 6: Setup Nginx

### Copy Config
```bash
cp deploy/nginx/stock-analyzer.conf /etc/nginx/sites-available/stock-analyzer
```

### Aktifkan Config
```bash
ln -sf /etc/nginx/sites-available/stock-analyzer /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
```

### Test & Restart Nginx
```bash
nginx -t
systemctl restart nginx
```

---

## Langkah 7: Test Deploy

Buka browser dan akses:
```
http://IP_VPS_ANDA
```

Harusnya muncul halaman IDX Stock Analyzer.

---

## Cek Log

### App Log
```bash
journalctl -u stock-analyzer -f
```

### Nginx Log
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## Update Aplikasi

```bash
cd /opt/idx-stock-analyzer
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart stock-analyzer
```

---

## Troubleshooting

### App Tidak Jalan
```bash
systemctl status stock-analyzer
journalctl -u stock-analyzer -n 50
```

### Port 8000 Sudah Terpakai
```bash
lsof -i :8000
kill PID_YANG_MENGAMBIL_PORT
systemctl restart stock-analyzer
```

### Permission Error
```bash
chown -R www-data:www-data /opt/idx-stock-analyzer
chmod -R 755 /opt/idx-stock-analyzer
```

---

## Struktur Deployment

```
CloudBaik VPS (Ubuntu 22.04)
├── nginx (port 80) ──────┐
│                         ├──→ Python FastAPI (port 8000)
│                         │         │
│                         │         ├──→ stock_analyzer.db (SQLite)
│                         │         ├──→ backend/
│                         │         └──→ frontend/
└─────────────────────────┘
```

---

## Estimasi Biaya

| Item | Biaya |
|------|-------|
| CloudBaik VPS (1 vCPU, 2GB) | ~Rp 50.000/bulan |
| Domain (.com) | ~Rp 150.000/tahun |
| **Total** | **~Rp 55.000/bulan** |
