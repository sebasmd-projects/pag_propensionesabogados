# ACCOUNT

Las cuentas del sitio: entrar, salir y registrarse.

## Cómo se entra

`/accounts/login/` es un **asistente** de `django-two-factor-auth` con cuatro
pantallas, de las que cada persona ve las que le tocan:

| paso     | qué pide                     | cuándo sale                          |
|----------|------------------------------|--------------------------------------|
| `auth`   | usuario o correo y contraseña| siempre                              |
| `otp`    | usuario/correo **y** código  | solo en modo código                  |
| `token`  | el código de la aplicación   | si la cuenta tiene segundo factor    |
| `backup` | un código de respaldo        | como alternativa al anterior         |

El registro sigue siendo **público** y el segundo factor es **opcional**: se
da de alta desde `/accounts/two_factor/`, y quien no lo hace entra con su
contraseña sin más.

### La segunda puerta: el código al correo

Quien no se acuerda de su contraseña puede pedir un código de seis cifras.
Aparece de dos formas: pulsando «entrar con un código», y solo, al **tercer**
fallo seguido de contraseña —así quien está a punto de quedarse bloqueado
tiene por dónde salir—.

Tres cosas que no son evidentes y sostienen lo demás:

- **No salta el segundo factor.** El paso del código deja el usuario
  identificado exactamente igual que el de contraseña; lo que venga después es
  el flujo de siempre. Una vista aparte que llamara a `login()` habría sido
  mucho más corta y habría convertido el correo en una puerta trasera al TOTP
  de otra persona.
- **No dice nunca si una cuenta existe.** La pantalla contesta lo mismo se
  pida el código para un correo real o inventado.
- **Los fallos de las dos puertas cuentan en el mismo sitio.** Un código
  equivocado suma en `django-axes` igual que una contraseña equivocada. Si no,
  el tope de cinco intentos por código se esquivaría pidiendo otro código.

## Los ficheros

| fichero             | qué hay dentro                                        |
|---------------------|-------------------------------------------------------|
| `login_view.py`     | el asistente: los pasos, los modos y el recuento       |
| `otp_login.py`      | emitir, comprobar y caducar el código; los tres frenos |
| `emails.py`         | el correo institucional con el código                  |
| `forms.py`          | `LoginOTPForm` y el formulario de registro             |
| `two_factor_urls.py`| las rutas `two_factor:…`, con el acceso apuntando aquí |

Y fuera de la aplicación, porque los usa algo más:

| fichero                              | qué hay dentro                     |
|--------------------------------------|------------------------------------|
| `apps/common/utils/login_attempts.py`| el contador común de las dos puertas |
| `apps/common/utils/axes_hooks.py`    | que `axes` sepa quién falla y desde dónde |
| `apps/common/utils/throttling.py`    | el cupo de codigos por buzón y por conexión |
| `apps/common/utils/client_ip.py`     | de dónde viene una petición, en un solo sitio |
| `apps/common/utils/wizards.py`       | avisar a `formtools` cuando cambian los pasos |
| `apps/common/utils/backend/`         | entrar con el usuario **o** con el correo |

## Al desplegar

1. `pip install -r requirements.txt` (entran `django-two-factor-auth`,
   `django-otp`, `django-axes`, `django-formtools` y `django-phonenumber-field`).
2. `python manage.py migrate` (tablas de `axes`, `otp_static`, `otp_totp` y
   `two_factor`).
3. Revisa las variables de la sección **Acceso** de `docs/env.example`.

`/admin/login/` queda redirigido a esta pantalla: así no hay una segunda
puerta —la de Django— sin código al correo, sin el freno de `axes` y sin
segundo factor.

## Pruebas

`python manage.py test apps.project.common.account` — 42 pruebas repartidas
en cuatro ficheros: la pantalla y los dos modos (`test_login.py`), que el
código no salta el segundo factor (`test_second_factor.py`), que los fallos se
cuentan juntos y que pedir códigos tiene tope (`test_attempts.py`), y el
backend de usuario-o-correo (`test_backend.py`).
