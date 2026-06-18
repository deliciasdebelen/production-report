# Guía: Cómo Subir el Código a GitHub

## Problema: GitHub ya no acepta contraseñas

GitHub eliminó el soporte para autenticación con contraseña en agosto de 2021. Ahora debes usar un **Personal Access Token (PAT)**.

## Solución: Crear un Personal Access Token

### Paso 1: Generar el Token

1. Inicia sesión en GitHub: https://github.com/login
   - Usuario: `github@deliciasdebelen.com`
   - Contraseña: `C4rm4l2025`

2. Ve a Settings → Developer settings → Personal access tokens:
   - URL directa: https://github.com/settings/tokens

3. Click en **"Generate new token"** → **"Generate new token (classic)"**

4. Configura el token:
   - **Note**: `production-report-deployment` (o cualquier nombre descriptivo)
   - **Expiration**: 90 days (o "No expiration" si prefieres)
   - **Select scopes**: Marca **`repo`** (esto da acceso completo a repositorios privados y públicos)

5. Click en **"Generate token"** al final de la página

6. **IMPORTANTE**: Copia el token inmediatamente (se muestra solo una vez)
   - Formato: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Guárdalo en un lugar seguro

### Paso 2: Usar el Token para Push

Una vez que tengas el token, ejecuta:

```bash
cd c:\Users\ovargas\Projects\production-report

# Configurar remote (si no está configurado)
git remote add origin https://github.com/deliciasdebelen/production-report.git

# Renombrar rama
git branch -M main

# Push
git push -u origin main
```

Cuando Git pida credenciales:
- **Username**: `github@deliciasdebelen.com`
- **Password**: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (tu token, NO la contraseña)

### Paso 3: Guardar Credenciales (Opcional)

Para no tener que ingresar el token cada vez:

```bash
# Configurar credential helper
git config --global credential.helper wincred
```

La próxima vez que hagas push, Git recordará tus credenciales.

## Alternativa: GitHub CLI

Si prefieres una forma más simple:

### 1. Instalar GitHub CLI

```bash
winget install GitHub.cli
```

O descarga desde: https://cli.github.com/

### 2. Autenticarse

```bash
gh auth login
```

Sigue las instrucciones:
- Selecciona: GitHub.com
- Protocolo: HTTPS
- Autenticación: Login with a web browser
- Copia el código y pégalo en el navegador

### 3. Push

Una vez autenticado con `gh`, Git usará automáticamente esas credenciales:

```bash
git push -u origin main
```

## Verificación

Después del push exitoso, verifica en:
https://github.com/deliciasdebelen/production-report

Deberías ver todos tus archivos ahí.

## Próximo Paso

Una vez que el código esté en GitHub, puedes proceder con el despliegue en el servidor ejecutando:

```bash
.\deploy-to-server.bat
```

## Troubleshooting

### Error 403: Permission denied

- Estás usando la contraseña en lugar del token
- Genera un Personal Access Token y úsalo como contraseña

### Error 404: Repository not found

- El repositorio no existe o el nombre es incorrecto
- Verifica en https://github.com/deliciasdebelen/production-report

### Error: Remote already exists

```bash
git remote remove origin
git remote add origin https://github.com/deliciasdebelen/production-report.git
```

### Error: Updates were rejected

El repositorio remoto tiene contenido que no tienes localmente:

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```
