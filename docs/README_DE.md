# 🇩🇪 Network File System (NFS) — Free Edition

> [🇪🇸 Español](README_ES.md) · [🇧🇷 Português](README_PT.md) · [🇬🇧 English](README_EN.md) · [🇯🇵 日本語](README_JA.md) · [🇷🇺 Русский](README_RU.md)

Ein kostenloses Open-Source-Plugin für aaPanel, das eine vollständige NFS-Verwaltung über eine grafische Oberfläche bietet: Exporte (Freigaben) erstellen, Remote-Verzeichnisse einbinden, den NFS-Server überwachen und Fehler beim Einbinden automatisch diagnostizieren.

```
Autor:   Jose Alexis Correa Valencia (jalexiscv)
Version: 1.0
Lizenz:  MIT — Freie Software
```

---

## Inhaltsverzeichnis

1. [Über das NFS-Protokoll](#1-über-das-nfs-protokoll)
2. [Plugin-Funktionen](#2-plugin-funktionen)
3. [Systemvoraussetzungen](#3-systemvoraussetzungen)
4. [Installation](#4-installation)
5. [Dateistruktur](#5-dateistruktur)
6. [Ports und Firewall](#6-ports-und-firewall)
7. [Konfigurationsdateien](#7-konfigurationsdateien)
8. [Auto-Mount beim Systemstart](#8-auto-mount-beim-systemstart)
9. [Fehlerdiagnose](#9-fehlerdiagnose)
10. [Wartungsskripte](#10-wartungsskripte)
11. [Backend-API](#11-backend-api)
12. [Mitwirken](#12-mitwirken)
13. [Support und Community](#13-support-und-community)
14. [Lizenz](#14-lizenz)
15. [Autor](#15-autor)
16. [Spenden](#16-spenden)

---

## 1. Über das NFS-Protokoll

**Network File System (NFS)** ist ein verteiltes Dateisystemprotokoll, das ursprünglich 1984 von Sun Microsystems entwickelt wurde. Es ermöglicht einem Betriebssystem, auf Dateien zuzugreifen, die auf einem anderen Computer im Netzwerk gespeichert sind – auf dieselbe Weise, wie es auf lokale Dateien zugreifen würde. Dadurch wird der physische Speicherort für Anwendungen transparent.

NFS arbeitet nach dem Client/Server-Modell: Der Server **exportiert** ein Verzeichnis und stellt es im Netzwerk zur Verfügung; der Client **bindet** es lokal ein, als wäre es ein eigenes Volume. Die Kommunikation erfolgt über Remote Procedure Calls (RPC) via TCP oder UDP.

### Protokollversionen

| Version | Jahr | Wichtigste Merkmale |
|---------|------|---------------------|
| NFSv2   | 1989 | Erste weit verbreitete Version; nur UDP; max. 2-GB-Dateien |
| NFSv3   | 1995 | TCP-Unterstützung; große Dateien (64-Bit-Offsets); asynchrone Schreibvorgänge |
| NFSv4   | 2003 | Stateful-Protokoll; starke Authentifizierung (Kerberos); einzelner Port (2049); ACL-Unterstützung |
| NFSv4.1 | 2010 | pNFS (paralleler Zugriff); resiliente Sitzungen; verbesserte Cluster-Unterstützung |

### Häufige Anwendungsfälle

- Gemeinsamer Speicher zwischen Anwendungsservern
- Zentrale Home-Verzeichnisse in Linux/Unix-Umgebungen
- Verteilte Backup-Infrastruktur
- Gemeinsamer Speicher für HPC-Cluster und Kubernetes
- Gemeinsame Nutzung statischer Assets (Bilder, Videos) zwischen Webservern

> **Sicherheit:** NFS verschlüsselt den Datenverkehr nicht (außer mit Kerberos + RPCSEC_GSS). Der Zugang sollte stets auf vertrauenswürdige Subnetze beschränkt und NFS-Ports niemals dem öffentlichen Internet ausgesetzt werden.

---

## 2. Plugin-Funktionen

Dieses kostenlose Open-Source-Plugin für aaPanel vereinfacht die Verwaltung des Network File System (NFS) über eine grafische Oberfläche. Es ermöglicht Administratoren, NFS-Exporte zu verwalten, Remote-Verzeichnisse einzubinden und die automatische Bereitstellung von Freigaben beim Systemstart zu konfigurieren. Eine intelligente Diagnose-Engine identifiziert Verbindungsfehler und schlägt gezielte Lösungen für Netzwerkprobleme vor. Benutzer können die Serverleistung in Echtzeit überwachen und detaillierte Aktivitätsprotokolle einsehen, um die Betriebssicherheit zu gewährleisten. Automatisierte Installationsskripte und mehrsprachige Unterstützung erleichtern den weltweiten Einsatz in Linux-Umgebungen.

- **Shares (NFS-Exporte):** Legt fest, welche lokalen Verzeichnisse für Remote-Clients zugänglich sind, mit IP-Zugriffskontrolle (CIDR), Lese-/Schreibmodus, Synchronisation und Squash-Richtlinie für Berechtigungen.
- **Mounts (Remote-Einbindungen):** Verbindet freigegebene Ressourcen anderer NFS-Server mit vollständigen Protokolloptionen: Version (NFSv3/NFSv4), Blockgröße (rsize/wsize), Timeouts, TCP/UDP, Hard/Soft-Mount.
- **Serverüberwachung:** Status von `nfs-server` und `rpcbind`, registrierte RPC-Dienste, Protokollstatistiken aus `/proc/net/rpc`, I/O-Metriken pro Einbindung via `nfsiostat`.
- **Auto-Mount beim Systemstart:** Bindet Ressourcen mit `auto_mount=1` automatisch über einen System-Init-Dienst ein.
- **Verbindungsverfolgung:** Überwacht aktive Einbindungen und verbundene Clients in Echtzeit; erkennt Zustandsänderungen außerhalb des Plugins.
- **Intelligente Fehlerdiagnose:** 7-stufige Überprüfungssequenz (Ping, IP-Erkennung, Portprüfung, Showmount, CIDR-Abgleich) mit genauer Ursache und konkreten Lösungsvorschlägen.
- **Aktivitätsprotokoll:** Thread-sicheres Protokoll aller Operationen mit Filtern nach Ereignistyp, Ergebnis und IP-Adresse.

---

## 3. Systemvoraussetzungen

| Komponente | Anforderung |
|---|---|
| Panel | aaPanel (BT Panel) installiert |
| Betriebssystem | Ubuntu/Debian 16.04+ · CentOS/RHEL/Rocky/Alma 7+ |
| Python | 3.6+ (im Panel-Environment enthalten) |
| Systempakete | `nfs-kernel-server` + `nfs-common` (Debian/Ubuntu) · `nfs-utils` (RHEL/CentOS) |

---

## 4. Installation

```bash
# 1. Plugin in das Panel-Verzeichnis kopieren
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. Installer ausführen
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

Das Installationsskript übernimmt automatisch:

- NFS-Paketinstallation
- Fixierung von mountd auf Port 20048
- Öffnen von Firewall-Ports in ufw (falls aktiv)
- Registrierung des Init-Dienstes unter `/etc/init.d/nfs_free`
- Aktivierung von `nfs-server` und `rpcbind` via systemd
- Neuladen des aaPanel

**Deinstallation:**

```bash
sudo bash /www/server/panel/plugin/nfs_free/install.sh uninstall
```

> System-NFS-Pakete und `/etc/exports` werden bei der Deinstallation **nicht verändert**.

**Manuelle Installation der Abhängigkeiten (falls der automatische Installer fehlschlägt):**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server nfs-common rpcbind

# RHEL/CentOS/Rocky/Alma
sudo yum install -y nfs-utils rpcbind
```

---

## 5. Dateistruktur

```
nfs_free/
├── info.json              # Plugin-Metadaten (Name, Version, Autor)
├── icon.png               # 512×512 RGBA-Symbol
├── index.html             # Frontend: CSS + HTML + JavaScript
├── nfs_free_main.py       # Backend: Klasse nfs_free_main (32 Methoden)
├── nfs_free_service       # Python-Wrapper für auto_mount() beim Boot
├── install.sh             # Installation und Deinstallation
├── init.sh                # /etc/init.d-Skript für Auto-Mount
├── upgrade.sh             # Aktualisiert NFS-Pakete und startet Dienste neu
├── repair.sh              # Konfiguriert mountd-Port neu und startet neu
└── config/
    ├── share.json             # Konfigurierte NFS-Exporte
    ├── mount.json             # Konfigurierte Remote-Einbindungen
    ├── connection_state.json  # Aktueller Verbindungsstatus
    └── activity.log.json      # Aktivitätsprotokoll (letzte 1000 Einträge)
```

---

## 6. Ports und Firewall

NFS erfordert folgende offene Ports auf dem **Server**:

| Port  | Dienst   | Protokoll | Beschreibung |
|-------|----------|-----------|--------------|
| 111   | rpcbind  | TCP/UDP   | Port-Mapper — erkennt RPC-Dienste |
| 2049  | nfs      | TCP       | Haupt-NFS-Protokoll |
| 20048 | mountd   | TCP/UDP   | Mount-Anfragen (fester Port) |
| 32874 | lockd    | TCP/UDP   | Dateisperrung |
| 32876 | statd    | TCP/UDP   | Zustandswiederherstellung |

Standardmäßig verwendet mountd einen von rpcbind zugewiesenen zufälligen Port. Das Plugin konfiguriert `/etc/nfs.conf` um es auf Port **20048** zu fixieren, wodurch vorhersehbare Firewall-Regeln zwischen Servern ermöglicht werden.

```bash
# Ports für ein bestimmtes Subnetz mit ufw öffnen
sudo ufw allow from 192.168.1.0/24 to any port 111
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 20048
```

---

## 7. Konfigurationsdateien

### share.json — NFS-Exporte

```json
[
  {
    "share_name": "backups",
    "path": "/www/backup",
    "rw_mode": "rw",
    "sync_mode": "async",
    "squash": "all_squash",
    "user": "nfsnobody",
    "limit_address": "192.168.1.0/24",
    "ps": "Tägliche Backups"
  }
]
```

### mount.json — Remote-Einbindungen

```json
[
  {
    "mount_name": "produktion",
    "server_address": "192.168.1.100",
    "nfs_path": "/data/app",
    "mount_path": "/mnt/nfs-prod",
    "proto": "tcp",
    "rw_mode": "rw",
    "hard": 1,
    "rsize": 1048576,
    "wsize": 1048576,
    "timeo": 600,
    "vers": 4,
    "auto_mount": 1
  }
]
```

---

## 8. Auto-Mount beim Systemstart

Der Dienst `/etc/init.d/nfs_free` bindet beim Systemstart automatisch alle Ressourcen mit `auto_mount=1` ein.

```
System startet
  → /etc/init.d/nfs_free start
    → nfs_free_service (Python)
      → nfs_free_main.auto_mount()
        → für jedes Mount mit auto_mount=1:
            prüfen ob bereits eingebunden (mountpoint -q)
            falls nicht: mount -t nfs -o ... ausführen
```

```bash
/etc/init.d/nfs_free start    # Starten
/etc/init.d/nfs_free stop     # Stoppen
/etc/init.d/nfs_free restart  # Neustarten
/etc/init.d/nfs_free status   # Status anzeigen
```

---

## 9. Fehlerdiagnose

Schlägt eine Einbindung fehl, führt das System automatisch eine 7-stufige Überprüfungssequenz durch:

| Stufe | Prüfung | Werkzeug |
|-------|---------|---------|
| 1     | Erreichbarkeit des Servers | `ping -c 1 -W 2` |
| 2     | Ausgehende IP des Clients | `ip route get` |
| 3     | Ports 111, 2049, 20048 | `/dev/tcp` |
| 4     | Export-Liste des Servers | `showmount -e` |
| 5     | Pfad in Exports vorhanden | Showmount-Ausgabe-Analyse |
| 6     | Client-IP in Zugriffsregeln | `ipaddress.ip_network()` CIDR |
| 7     | Hinweise aus Kernel-Fehlermeldung | Schlüsselwort-Analyse |

---

## 10. Wartungsskripte

```bash
# mountd-Port reparieren und Dienste neu starten
sudo bash /www/server/panel/plugin/nfs_free/repair.sh

# NFS-Systempakete aktualisieren
sudo bash /www/server/panel/plugin/nfs_free/upgrade.sh
```

---

## 11. Backend-API

Die Klasse `nfs_free_main` stellt 32 Methoden in 5 Kategorien bereit:

| Kategorie | Hauptmethoden |
|---|---|
| Shares | `get_share_list`, `create_share`, `modify_share`, `remove_share`, `show_ip_share_list` |
| Mounts | `get_mount_list`, `create_mount`, `modify_mount`, `remove_mount`, `to_mount`, `to_umount`, `auto_mount` |
| Server | `get_server_status`, `server_admin`, `get_overview`, `get_nfsstat`, `get_nfsiostat` |
| Verbindungen | `get_connections`, `get_disk_mounts`, `get_nfs_ports`, `fix_mountd_port` |
| Protokoll | `get_log`, `clear_log` |

---

## 12. Mitwirken

Dieses Projekt ist **Open Source** und lebt von der Community. Ihre Beiträge sind willkommen!

### So können Sie mitwirken

1. **Forken** Sie das Repository
2. Erstellen Sie Ihren Feature-Branch:
   ```bash
   git checkout -b feature/neue-funktionalitaet
   ```
3. Nehmen Sie Ihre Änderungen vor und überprüfen Sie die Funktion des Plugins in aaPanel
4. Committen Sie Ihre Änderungen:
   ```bash
   git commit -m 'Add: klare Beschreibung der Änderung'
   ```
5. Pushen Sie zu Ihrem Branch:
   ```bash
   git push origin feature/neue-funktionalitaet
   ```
6. Öffnen Sie einen **Pull Request**

### Beitragsrichtlinien

- Befolgen Sie den [PEP-8](https://pep8.org/) Styleguide für Python-Code
- Dokumentieren Sie alle öffentlichen Methoden mit Docstrings
- Fügen Sie Tests für neue Funktionen hinzu
- Aktualisieren Sie die relevante Dokumentation
- Bewahren Sie die Kompatibilität mit der aaPanel-Plugin-Schnittstelle

### Bereiche, die Hilfe benötigen

- 📝 Dokumentationsverbesserungen
- 🧪 Unit- und Integrationstests
- 🎨 Verbesserungen der Panel-Benutzeroberfläche
- 🔧 Neue NFS-Funktionen (Kerberos-Unterstützung, zusätzliche Metriken)
- 🌍 Dokumentationsübersetzungen
- 🐛 Fehlerberichte

---

## 13. Support und Community

### Benötigen Sie Hilfe?

- 🐛 **Fehler melden:** Öffnen Sie ein [Issue auf GitHub](https://github.com/jalexiscv/nfs_free/issues)
- 💡 **Funktionen anfragen:** Nutzen Sie [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- 📧 **Direktkontakt:** jalexiscv@gmail.com

### Community

- Nehmen Sie an Gesprächen in den [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions) teil
- Prüfen Sie [Issues mit dem Label "good first issue"](https://github.com/jalexiscv/nfs_free/labels/good%20first%20issue)

---

## 14. Lizenz

Vertrieben unter der **MIT**-Lizenz.

> Die MIT-Lizenz erlaubt die Nutzung, Kopie, Änderung, Zusammenführung, Veröffentlichung, Verteilung, Unterlizenzierung und den Verkauf von Kopien der Software ohne Einschränkungen, sofern der ursprüngliche Copyright-Hinweis enthalten ist.

---

## 15. Autor

**Jose Alexis Correa Valencia**
*Full Stack Developer & Software Architect*

Über 25 Jahre Erfahrung in der Entwicklung von Unternehmenssoftware, spezialisiert auf skalierbare Architekturen und Linux-Infrastruktur.

- **GitHub:** [@jalexiscv](https://github.com/jalexiscv)
- **LinkedIn:** [Jose Alexis Correa Valencia](https://www.linkedin.com/in/jalexiscv/)
- **E-Mail:** jalexiscv@gmail.com
- **Standort:** Kolumbien 🇨🇴

---

## 16. Spenden

Wenn dieses Plugin Ihnen oder Ihrem Unternehmen geholfen hat, erwägen Sie bitte, seine laufende Entwicklung und Wartung zu unterstützen.

| Methode | Details |
|---------|---------|
| **PayPal** | [jalexiscv@gmail.com](https://www.paypal.com/paypalme/jalexiscv) |
| **Nequi (Kolumbien)** | `3117977281` |

Ihre Unterstützung hilft bei:
- Beschleunigung der Entwicklung neuer Funktionen
- Erstellung weiterer Dokumentation und Beispiele
- Verbesserung der Testabdeckung
- Aktiv-Haltung und Aktualisierung des Projekts

*Vielen Dank für Ihre Unterstützung!*

---

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — Veröffentlicht am 24. Juli 2023 — MIT License*
