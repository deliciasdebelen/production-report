# Informe de Soporte Técnico: Problemas en la Creación de Tickets y Correos

## Resumen del Problema
De acuerdo con los reportes de los usuarios:
1. **Errores o bloqueos al crear tickets**: En ocasiones la aplicación "se queda colgada" al intentar generar el ticket.
2. **Correos no enviados**: Los usuarios no recibían las notificaciones correspondientes a las diferentes etapas del proceso de soporte.

## Diagnóstico Realizado

1. **Revisión del EndPoint (`/ticket`)**:
   - En FastAPI, el endpoint `@router.post("/ticket")` estaba declarado como `async def create_ticket`. Adicionalmente, este endpoint realizaba múltiples operaciones de bases de datos altamente *bloqueantes* y *síncronas* haciendo uso de SQLAlchemy clásico, tales como el guardado de archivos iterando bloques y varios `db.query()`, `db.add()` y `db.commit()`.
   - Resulta que en FastAPI, cuando se usa `async def`, el código se ejecuta directamente en el *Event Loop* (Hilo Principal) de Starlette. Esto significa que todo el servidor y el proceso de la aplicación entera quedaba totalmente **bloqueado y congelado** esperando que la base de datos terminara sus procesos o que la copia del archivo adjunto se culminara. Ésta era la principal razón detrás de que se quedara colgada la iteración en producción.

2. **Revisión de `email_utils.py` y SMTP**:
   - Analizando el script de background task `email_utils.send_email`, observamos que utilizaba siempre la clase `smtplib.SMTP(smtp_server, smtp_port)` en conjunto con `starttls()`.
   - Se verificaron los ajustes usados por el servidor consumiendo la ruta `GET http://192.168.1.79:8000/api/support/config`. Los registros mostraban el puerto `465` (perteneciente a `server42.web-hosting.com`).
   - El puerto 465 requiere una conexión SSL estricta **implícita** desde el incio usando la clase `smtplib.SMTP_SSL`. Como el código intentaba conectarse por texto plano para luego invocar STARTTLS, la conexión *se quedaba colgando* y fallaba al pasar el límite del `timeout`, y por ende, no llegaba a completar el envío del correo electrónico cayendo en excepción silenciosa.

## Solución Aplicada

Se tomaron permisos inmediatos para corregir ambos problemas desde el código, generando un respaldo primero y luego publicando los cambios de nuevo en `192.168.1.79:8000`.

- **Se modificó el router `create_ticket`:** Se eliminó la etiqueta `async` de la función `async def create_ticket` a `def create_ticket` en el archivo `app/routers/support.py`. Este pequeño y vital ajuste instruye a FastAPI a despachar este endpoint en el `ThreadPool` asíncrono, permitiendo que múltiples usuarios guarden sus tickets **simultáneamente** sin bloquear por completo el *Event Loop*.

- **Se ajustó la capa de correos SSL:** En el script `app/email_utils.py` se incluyó lógica direccional que evalúa si el puerto SMTP administrado es el `465`. En caso afirmativo, automáticamente cambia la clase a iniciar por `smtplib.SMTP_SSL()`, lo cual solucionó de inmediato la caída del proceso y la salida de correos sin tener que depender de un STARTTLS de texto plano obsoleto.

- **Respaldo y Despliegue**: Antes de accionar fue realizado un respaldo local previo y con copia de toda la estructura de la aplicación a `c:\Users\ovargas\Projects\production-report_backup`. Mediante tu script `deploy_to_79.ps1` se compilaron y enviaron estos cambios al Servidor de Producción 192.168.1.79 y se reinició el contenedor correspondiente de manera exitosa usando SSH asíncrono.

## Conclusión

El servicio `Support` ha sido restaurado y ahora ambos problemas deberían estar completamente erradicados en la instancia `http://192.168.1.79:8000`. Se recomienda mantener una revisión las próximas 24 horas para constatar su efectividad.
