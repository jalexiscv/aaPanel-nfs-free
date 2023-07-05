# 🇪🇸 Network File System (NFS) — Free Edition

> [🇧🇷 Português](README_PT.md) · [🇬🇧 English](README_EN.md) · [🇯🇵 日本語](README_JA.md) · [🇩🇪 Deutsch](README_DE.md) · [🇷🇺 Русский](README_RU.md)

Plugin gratuito y de código abierto para aaPanel que proporciona gestión completa de NFS mediante interfaz gráfica: crear exportaciones, montar directorios remotos, monitorear el servidor NFS y diagnosticar fallos automáticamente.

```
Autor:   Jose Alexis Correa Valencia (jalexiscv)
Versión: 1.0
Licencia: MIT — Software Libre
```

---

## Índice

1. [Acerca del protocolo NFS](#1-acerca-del-protocolo-nfs)
2. [Características del plugin](#2-características-del-plugin)
3. [Requisitos del sistema](#3-requisitos-del-sistema)
4. [Instalación](#4-instalación)
5. [Estructura de archivos](#5-estructura-de-archivos)
6. [Puertos y firewall](#6-puertos-y-firewall)
7. [Archivos de configuración](#7-archivos-de-configuración)
8. [Auto-mount al arranque](#8-auto-mount-al-arranque)
9. [Diagnóstico de fallos](#9-diagnóstico-de-fallos)
10. [Scripts de mantenimiento](#10-scripts-de-mantenimiento)
11. [API del backend](#11-api-del-backend)
12. [Contribución](#12-contribución)
13. [Soporte y comunidad](#13-soporte-y-comunidad)
14. [Licencia](#14-licencia)
15. [Autor](#15-autor)
16. [Donaciones](#16-donaciones)

---

## 1. Acerca del protocolo NFS

**Network File System (NFS)** es un protocolo de sistema de archivos distribuido desarrollado originalmente por Sun Microsystems en 1984. Permite que un sistema operativo acceda a archivos ubicados en otro equipo de la red de la misma forma en que accedería a archivos locales, haciendo la ubicación física del almacenamiento transparente para las aplicaciones.

NFS opera sobre el modelo cliente/servidor: el servidor **exporta** un directorio y lo pone a disposición de la red; el cliente lo **monta** localmente como si fuera un volumen propio. La comunicación se realiza mediante llamadas a procedimiento remoto (RPC) sobre TCP o UDP.

### Versiones del protocolo

| Versión | Año  | Características principales |
|---------|------|-----------------------------|
| NFSv2   | 1989 | Primera versión ampliamente desplegada; solo UDP; archivos máx. 2 GB |
| NFSv3   | 1995 | Soporte TCP; archivos de gran tamaño (64-bit); escritura asíncrona |
| NFSv4   | 2003 | Protocolo con estado (_stateful_); autenticación fuerte (Kerberos); un solo puerto (2049); soporte ACL |
| NFSv4.1 | 2010 | pNFS (acceso paralelo); sesiones resilientes; mejor soporte para clústeres |

### Casos de uso comunes

- Almacenamiento compartido entre servidores de aplicaciones
- Directorios home centralizados en entornos Linux/Unix
- Infraestructura de backups distribuidos
- Almacenamiento compartido en clústeres HPC y Kubernetes
- Compartición de assets estáticos (imágenes, vídeos) entre servidores web

> **Seguridad:** NFS no cifra el tráfico de datos en tránsito (salvo con Kerberos + RPCSEC_GSS). Restringe siempre el acceso a subredes de confianza y nunca expongas los puertos NFS a Internet.

---

## 2. Características del plugin

- **Shares (exportaciones NFS):** define qué directorios locales son accesibles por clientes remotos, con control de IPs autorizadas (CIDR), modo lectura/escritura, sincronización y política de squash de permisos.
- **Mounts (montajes remotos):** conecta recursos compartidos de otros servidores NFS con opciones completas de protocolo: versión (NFSv3/NFSv4), tamaño de bloque (rsize/wsize), timeouts, TCP/UDP, hard/soft mount.
- **Monitoreo del servidor:** estado de `nfs-server` y `rpcbind`, servicios RPC registrados, estadísticas de protocolo desde `/proc/net/rpc`, métricas de I/O por mount via `nfsiostat`.
- **Auto-mount al arranque:** monta automáticamente los recursos configurados con `auto_mount=1` mediante un servicio init del sistema.
- **Detección de conexiones:** monitorea montajes activos y clientes entrantes en tiempo real; detecta cambios de estado que ocurren fuera del plugin.
- **Diagnóstico inteligente de fallos:** 7 pasos de verificación (ping, IP, puertos, showmount, CIDR-matching) con causa exacta y sugerencias accionables.
- **Registro de actividad:** bitácora thread-safe de todas las operaciones con filtros por tipo de evento, resultado e IP.

---

## 3. Requisitos del sistema

| Componente | Requerimiento |
|---|---|
| Panel | aaPanel (BT Panel) instalado |
| Sistema operativo | Ubuntu/Debian 16.04+ · CentOS/RHEL/Rocky/Alma 7+ |
| Python | 3.6+ (incluido en el entorno del panel) |
| Paquetes del SO | `nfs-kernel-server` + `nfs-common` (Debian/Ubuntu) · `nfs-utils` (RHEL/CentOS) |

---

## 4. Instalación

```bash
# 1. Copiar el plugin al directorio del panel
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. Ejecutar el instalador
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

El instalador realiza automáticamente:

- Instalación de paquetes NFS del sistema operativo
- Configuración de mountd en puerto fijo 20048
- Apertura de puertos en ufw (si está activo)
- Registro del servicio init `/etc/init.d/nfs_free`
- Activación de `nfs-server` y `rpcbind` via systemd
- Recarga del panel aaPanel

**Desinstalación:**

```bash
sudo bash /www/server/panel/plugin/nfs_free/install.sh uninstall
```

> Los paquetes NFS del sistema y `/etc/exports` **no se modifican** al desinstalar.

**Instalación manual de dependencias (si el instalador automático falla):**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server nfs-common rpcbind

# RHEL/CentOS/Rocky/Alma
sudo yum install -y nfs-utils rpcbind
```

---

## 5. Estructura de archivos

```
nfs_free/
├── info.json              # Metadatos del plugin (nombre, versión, autor)
├── icon.png               # Ícono 48×48 RGBA
├── index.html             # Frontend: CSS + HTML + JavaScript
├── nfs_free_main.py       # Backend: clase nfs_free_main (32 métodos)
├── nfs_free_service       # Wrapper Python para auto_mount() al boot
├── install.sh             # Instalación y desinstalación
├── init.sh                # Script /etc/init.d para auto-mount
├── upgrade.sh             # Actualiza paquetes NFS y reinicia servicios
├── repair.sh              # Reconfigura puerto mountd y reinicia
└── config/
    ├── share.json             # Exportaciones NFS configuradas
    ├── mount.json             # Montajes remotos configurados
    ├── connection_state.json  # Estado actual de conexiones
    └── activity.log.json      # Bitácora (últimas 1000 entradas)
```

---

## 6. Puertos y firewall

NFS requiere los siguientes puertos abiertos en el **servidor**:

| Puerto | Servicio | Protocolo | Descripción |
|--------|----------|-----------|-------------|
| 111    | rpcbind  | TCP/UDP   | Port mapper — descubre servicios RPC |
| 2049   | nfs      | TCP       | Protocolo principal NFS |
| 20048  | mountd   | TCP/UDP   | Solicitudes de montaje (puerto fijo) |
| 32874  | lockd    | TCP/UDP   | Bloqueo de archivos |
| 32876  | statd    | TCP/UDP   | Recuperación de estado |

Por defecto, mountd usa un puerto aleatorio asignado por rpcbind. El plugin configura `/etc/nfs.conf` para fijarlo al puerto **20048**, permitiendo reglas de firewall predecibles entre servidores.

```bash
# Abrir puertos para una subred específica con ufw
sudo ufw allow from 192.168.1.0/24 to any port 111
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 20048
```

---

## 7. Archivos de configuración

### share.json — Exportaciones NFS

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
    "ps": "Backups diarios"
  }
]
```

### mount.json — Montajes remotos

```json
[
  {
    "mount_name": "produccion",
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

## 8. Auto-mount al arranque

El servicio `/etc/init.d/nfs_free` monta automáticamente todos los recursos con `auto_mount=1` al iniciar el sistema.

```
Sistema arranca
  → /etc/init.d/nfs_free start
    → nfs_free_service (Python)
      → nfs_free_main.auto_mount()
        → para cada mount con auto_mount=1:
            verifica si ya está montado (mountpoint -q)
            si no: ejecuta mount -t nfs -o ...
```

```bash
/etc/init.d/nfs_free start    # Iniciar
/etc/init.d/nfs_free stop     # Detener
/etc/init.d/nfs_free restart  # Reiniciar
/etc/init.d/nfs_free status   # Ver estado
```

---

## 9. Diagnóstico de fallos

Cuando un montaje falla, el sistema ejecuta automáticamente una secuencia de 7 verificaciones:

| Paso | Verificación | Herramienta |
|------|-------------|-------------|
| 1    | Accesibilidad del servidor | `ping -c 1 -W 2` |
| 2    | IP de salida del cliente | `ip route get` |
| 3    | Puertos 111, 2049, 20048 | `/dev/tcp` |
| 4    | Lista de exports del servidor | `showmount -e` |
| 5    | Ruta presente en exports | parseo de showmount |
| 6    | IP cliente en reglas de acceso | `ipaddress.ip_network()` CIDR |
| 7    | Pistas del error del kernel | análisis de keywords |

**Ejemplo de respuesta:**

```
Mount failed: mount.nfs: access denied by server while mounting 192.168.1.10:/data

Diagnostic:
  • Server 192.168.1.10 rejected IP 10.0.0.5:
    export '/data' only allows [192.168.1.0/24]

Suggestions:
  → On the server, add '10.0.0.5' to 'Allowed IPs' for share '/data', then click 'Save'
```

---

## 10. Scripts de mantenimiento

```bash
# Reparar puerto mountd y reiniciar servicios
sudo bash /www/server/panel/plugin/nfs_free/repair.sh

# Actualizar paquetes NFS del sistema
sudo bash /www/server/panel/plugin/nfs_free/upgrade.sh
```

---

## 11. API del backend

La clase `nfs_free_main` expone 32 métodos en 5 categorías:

| Categoría | Métodos principales |
|---|---|
| Shares | `get_share_list`, `create_share`, `modify_share`, `remove_share`, `show_ip_share_list` |
| Mounts | `get_mount_list`, `create_mount`, `modify_mount`, `remove_mount`, `to_mount`, `to_umount`, `auto_mount` |
| Servidor | `get_server_status`, `server_admin`, `get_overview`, `get_nfsstat`, `get_nfsiostat` |
| Conexiones | `get_connections`, `get_disk_mounts`, `get_nfs_ports`, `fix_mountd_port` |
| Log | `get_log`, `clear_log` |

---

## 12. Contribución

Este proyecto es **Open Source** y vive gracias a la comunidad. ¡Tus contribuciones son bienvenidas!

### Cómo contribuir

1. Haz un **fork** del repositorio
2. Crea tu rama de característica:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```
3. Realiza tus cambios y verifica que el plugin funcione en aaPanel
4. Haz commit de tus cambios:
   ```bash
   git commit -m 'Add: descripción clara del cambio'
   ```
5. Haz push a tu rama:
   ```bash
   git push origin feature/nueva-funcionalidad
   ```
6. Abre un **Pull Request**

### Directrices de contribución

- Sigue la guía de estilo [PEP-8](https://pep8.org/) para código Python
- Documenta todos los métodos públicos con docstrings
- Agrega pruebas para nuevas funcionalidades
- Actualiza la documentación relevante
- Mantén la compatibilidad con la interfaz de plugins de aaPanel

### Áreas que necesitan ayuda

- 📝 Mejoras en documentación
- 🧪 Pruebas unitarias e integración
- 🎨 Mejoras en la interfaz del panel
- 🔧 Nuevas funcionalidades NFS (soporte Kerberos, métricas adicionales)
- 🌍 Traducciones de documentación
- 🐛 Reporte de bugs

---

## 13. Soporte y comunidad

### ¿Necesitas ayuda?

- 🐛 **Reportar bugs:** Abre un [issue en GitHub](https://github.com/jalexiscv/nfs_free/issues)
- 💡 **Solicitar funcionalidades:** Usa [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- 📧 **Contacto directo:** jalexiscv@gmail.com

### Comunidad

- Únete a las conversaciones en [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- Revisa los [issues etiquetados como "good first issue"](https://github.com/jalexiscv/nfs_free/labels/good%20first%20issue)

---

## 14. Licencia

Distribuido bajo la Licencia **MIT**.

> La licencia MIT te permite usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del software sin restricciones, siempre que se incluya el aviso de copyright original.

---

## 15. Autor

**Jose Alexis Correa Valencia**
*Full Stack Developer & Software Architect*

Con más de 25 años de experiencia en desarrollo de software empresarial, especializado en arquitecturas escalables e infraestructura Linux.

- **GitHub:** [@jalexiscv](https://github.com/jalexiscv)
- **LinkedIn:** [Jose Alexis Correa Valencia](https://www.linkedin.com/in/jalexiscv/)
- **Email:** jalexiscv@gmail.com
- **Ubicación:** Colombia 🇨🇴

---

## 16. Donaciones

Si este plugin te ha sido útil, considera apoyar su desarrollo y mantenimiento continuo.

| Método | Detalles |
|--------|----------|
| **PayPal** | [jalexiscv@gmail.com](https://www.paypal.com/paypalme/jalexiscv) |
| **Nequi (Colombia)** | `3117977281` |

Tu aporte ayuda a:
- Acelerar el desarrollo de nuevas funcionalidades
- Crear más documentación y ejemplos
- Mejorar la cobertura de pruebas
- Mantener el proyecto activo y actualizado

*¡Gracias por tu apoyo!*

---

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — Publicado el 5 de julio de 2023 — MIT License*
