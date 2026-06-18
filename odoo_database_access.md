# Documentación de Acceso: Odoo y PostgreSQL

Este documento resume las credenciales y ubicaciones de los servicios clave para el ecosistema Odoo-Manufactura, según la última auditoría de infraestructuras en el entorno de producción.

## 1. Contenedores y Rutas (Host Odoo)

Todos los servicios principales de Odoo y PostgreSQL se ejecutan en entorno Dockerizados (vía `docker-compose`) localizados en el servidor **192.168.1.193**.

* **IP del Servidor:** `192.168.1.193`
* **Acceso por Consola SSH:**
  * Usuario: `administrador`
  * Clave: `GRW7czL3*`
* **Servicio Docker Principal:** `odoo_manufactura`
  * Contenedor de Odoo Web: `odoo_manufactura-web-1` (Expuesto en `0.0.0.0:8069`)
  * Contenedor Postgres: `odoo_manufactura-db-1` (Expuesto internamente en Bridge al Web)

Para verificar qué servicios están corriendo, puedes usar:
```bash
docker ps --filter "name=odoo_manufactura"
```

## 2. Acceso a Odoo (Interfaz Web y API XML-RPC)

El acceso estándar para los usuarios operativos, e integración del Bridge API, se realiza a través de HTTP.

* **Dirección URL (Localhost para Integraciones):** `http://192.168.1.193:8070`
  * *Nota:* Aunque Docker reporta que el mapeo interno va al `8069`, las redes del orquestador y los proxies inversos lo enrutan por el puerto `8070` para las integraciones XML-RPC.
* **Base de Datos:** `carmal_odoo`

### Credenciales Administrativas Confirmadas
Odoo mapea los usuarios por correo asociado al "Login".
* **Usuario (Login):** `cvasquezdbelen@gmail.com`
* **Contraseña:** `carmal2024`

*(No existe un usuario estándar "admin" suelto en esta instancia; los privilegios administrativos recaen sobre el usuario de este correo).*

## 3. Acceso Directo a la Base de Datos PostgreSQL

PostgreSQL es el gestor de la base de datos `carmal_odoo` y está aislado dentro de la red Docker (`odoo_manufactura-db-1`). 

### Comando Rápido (vía Línea de Comandos)
Dado que el puerto nativo (5432) puede estar bloqueado o no mapeado para hosts externos, la manera más segura de ejecutar consultas (`psql`) es interactuando directamente a través de `docker exec`:

```bash
docker exec -it odoo_manufactura-db-1 psql -U odoo -d carmal_odoo
```

Una vez dentro, puedes ejecutar cualquier consulta. Por ejemplo, listar los usuarios disponibles en la tabla de Odoo:
```sql
SELECT id, login, active FROM res_users;
```

### Extracción / Respaldo Físico (Dump)
Para crear un archivo de volcado/respaldo de toda la base de datos de Odoo mediante la consola:
```bash
docker exec odoo_manufactura-db-1 pg_dump -U odoo -d carmal_odoo -F c > /home/administrador/odoo_backup.dump
```

## 4. Configuración para pgAdmin 4

Debido a que el puerto de PostgreSQL (`5432/tcp`) **no está expuesto públicamente al host** en la configuración actual de Docker para maximizar la seguridad, no puedes conectarte directamente con la IP `192.168.1.193`. En su lugar, la herramienta pgAdmin 4 permite conectarse a través de un **Túnel SSH**.

### Requisito Previo (Modificación Menor de Docker)
Dado que el contenedor de base de datos (`odoo_manufactura-db-1`) tiene una IP interna (ej. `172.18.x.x`) que cambia en cada reinicio, la forma más estable y estándar de exponer la base de datos a un túnel SSH es publicarla *solo para el acceso local* (127.0.0.1) dentro de `docker-compose.yml` de Odoo en 192.168.1.193:

```yaml
  db:
    image: postgres:15-alpine
    ports:
      - "127.0.0.1:5432:5432" # Agrega esta línea para exponer Postgres internamente
```
*(Si agregas esa línea, requiere correr `docker-compose up -d` en la carpeta de odoo para aplicar).*

### Pasos en pgAdmin 4:

1. Crea un nuevo servidor: Click derecho en **Servers > Register > Server...**
2. **Pestaña General**:
   * Name: `Produccion Odoo (carmal_odoo)`
3. **Pestaña Connection**:
   * Host name/address: `localhost` *(¡Importante: Debe ser localhost porque usaremos el Túnel!)*
   * Port: `5432`
   * Maintenance database: `carmal_odoo`
   * Username: `odoo`
   * Password: `odoo` *(o la clave si fue cambiada, por defecto odoo/odoo)*
4. **Pestaña SSH Tunnel** (¡Paso Crucial!):
   * Use SSH tunneling: Activar (`Yes/True`)
   * Tunnel host: `192.168.1.193`
   * Tunnel port: `22`
   * Username: `administrador`
   * Password: `GRW7czL3*`

Al guardar, pgAdmin establecerá una conexión segura encriptada con el servidor `192.168.1.193` y desde allí se conectará al puerto `5432` local sin exponer la base de datos a internet.
