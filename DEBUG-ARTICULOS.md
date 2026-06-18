# Reporte de Depuración: Carga de Artículos

## Diagnóstico
Se investigó el error "Error cargando artículos" en la interfaz.

**Hallazgos:**
1. **Falta de Drivers**: El contenedor Docker original no tenía los drivers ODBC de Microsoft necesarios para conectar a SQL Server (Profit Plus).
2. **Error de Conexión**: Incluso con los drivers instalados, la conexión al servidor de Profit Plus (192.168.1.205) falló.

## Acciones Realizadas
1. **Actualización de Infraestructura**: 
   - Se actualizó el `Dockerfile` para instalar los drivers oficiales de Microsoft (`msodbcsql17`) compatibles con Debian 12.
   - Se reconstruyó la imagen en el servidor.

2. **Implementación de Fallback (Modo Seguro)**:
   - Se modificó la API (`external.py`) para que, en caso de fallo de conexión a Profit, no devuelva un error 500 (que rompe la interfaz).
   - Ahora devuelve una lista de artículos de "Modo Offline" o Mock.

## Estado Actual
- La aplicación **YA NO** muestra "Error cargando artículos".
- Ahora muestra una lista básica que incluye: `ERROR CONEXION PROFIT - MODO OFFLINE`.
- Esto permite usar la interfaz para pruebas, aunque sin datos reales de Profit.

## Pasos para Conectar a Profit Real
Para que la conexión a Profit (192.168.1.205) funcione, verifica:
1. Que el servidor 192.168.1.79 tenga acceso a 192.168.1.205 en el puerto 1433 (SQL Server).
2. Que el usuario `PROFIT` y contraseña `profit` sean correctos.
3. Que el Firewall de Windows en 192.168.1.205 permita conexiones entrantes.
