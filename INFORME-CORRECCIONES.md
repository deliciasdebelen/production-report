# PASOS REALIZADOS PARA CORREGIR DESPLIEGUE

## 1. Instalación de Docker y Compose
El servidor no tenía Docker. Se instaló:
- Docker Engine
- Docker Compose (Standalone v2.24.0)

## 2. Corrección de Error de Base de Datos
La aplicación fallaba al conectar a SQLite (`unable to open database file`).
Causa: Problema de persistencia y permisos al intentar escribir en la raíz del contenedor con volúmenes montados.

**Solución aplicada:**
1. Se modificó `app/database.py` para usar una variable de entorno `DATABASE_URL`.
2. Se modificó `docker-compose.yml` para apuntar la base de datos a `/app/data/production.db`, una ruta segura dentro del volumen persistente.
3. Se creó el script `fix-db.sh` y se ejecutó en el servidor para:
   - Crear el directorio `~/apps/production-report/data`.
   - Asignar permisos 777 a ese directorio (para asegurar escritura desde el contenedor).
   - Reconstruir e iniciar los contenedores.

## 3. Estado Final
- **URL**: http://192.168.1.79:8000
- **Log**: La aplicación arranca correctamente y responde 200 OK.
- **Base de Datos**: Archivo `production.db` creado exitosamente en el volumen.
- **Login**: Verificado exitosamente con usuario `admin`.

## 4. Notas Importantes
- Los cambios de configuración (`docker-compose.yml`, `database.py`) están en tu máquina local y en el servidor.
- Hubo un conflicto al intentar hacer `git push`. **Recomendación**: Revisar el estado de Git local y forzar el push o resolver conflictos para mantener el repositorio de GitHub sincronizado con el servidor.
