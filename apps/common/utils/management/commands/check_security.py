# apps/common/utils/management/commands/check_security.py
"""
La auditoria de seguridad, reproducible antes de cada despliegue.

Un informe se lee una vez y se archiva; lo que hace falta es poder repetirlo.
Este comando comprueba lo que se reviso a mano, y lo hace **sobre el codigo
que hay ahora**, no sobre lo que decia el informe (``docs/SEGURIDAD.md``).

Las seis primeras son propias de este proyecto:

1. **Vistas publicas sin guardia**, contrastadas con una lista de las que lo
   son a proposito. Una vista nueva sin control aparece aqui la primera vez
   que se ejecuta, no cuando alguien la encuentra. Cubre las vistas de Django
   y las de la API (``permission_classes``): la API nacio publica por defecto
   y fue el hallazgo 2 de la auditoria.
2. **Formularios publicos sin limite de intentos.** El buscador de clientes
   fue el hallazgo grave: aceptaba una fecha de nacimiento sin ningun freno.
3. **Ejecucion por shell** (``os.system``, ``os.popen``, ``shell=True``).
4. **SQL construido con cadenas.**
5. **Carpetas de subidas que reparte el servidor web** por su cuenta, sin
   pasar por Django. Recorre los ``FileField`` de los modelos (fotos del
   equipo, avisos modales, PDF del paz y salvo en ``PRIVATE_MEDIA_ROOT``) y lo
   que sube CKEditor 5; ver ``utils/media_audit.py``.
6. **Ajustes de produccion** que dependen de que ``DEBUG`` este apagado, mas
   las claves (``SERVER_KEY``, ``FIELD_ENCRYPTION_KEY``) y CORS.

Y tres que no las sabe este proyecto, sino herramientas de fuera:

7. **bandit** sobre el codigo, con las excepciones razonadas en
   ``utils/scanners.py``.
8. **pip-audit** sobre las dependencias instaladas. Contesta "¿la version que
   tengo tiene un CVE?", que no se puede saber leyendo este repositorio. **Es
   la de produccion**, porque no lleva credencial: no hay clave que rotar ni
   que guardar en el servidor.
9. **safety**, la misma pregunta con una base mas rica, **solo en local**
   (Safety CLI 3 siempre se autentica: en un servidor eso es un cuelgue).
   Saltarsela alli no cuenta como hueco.

Las tres ultimas son **opcionales**: ninguna esta en ``requirements.txt``
--son herramientas de diagnostico y el servidor no las necesita para servir
paginas-- y si faltan, la seccion lo dice en voz alta y sigue. No haberlas
ejecutado no es una vulnerabilidad, pero callarselo convertiria un "sin
hallazgos" en una media verdad, asi que se cuenta aparte al final.

No sustituye a `manage.py check --deploy`, que mira los ajustes de Django.
Esto mira lo que es propio de este proyecto.

    manage.py check_security
    manage.py check_security --strict     # sale con codigo != 0 si hay algo
"""

import inspect
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from ...media_audit import (CKEDITOR_REASON, CKEDITOR_ROOT, MEDIA_HTACCESS,
                            PUBLICLY_SERVABLE_MEDIA, UNKNOWN_PREFIX,
                            is_inside, private_fields, upload_prefixes)
from ...scanners import run_bandit, run_pip_audit, run_safety

#: Mixins que cuentan como control de acceso.
GUARD_MIXINS = frozenset({
    'LoginRequiredMixin', 'GestorRequiredMixin', 'LoginGroupRequiredMixin',
    'PermissionRequiredMixin', 'UserPassesTestMixin', 'AccessMixin',
})

#: Vistas publicas **a proposito**, con la razon al lado.
#:
#: Es una lista de excepciones justificadas, no una lista de exclusion para
#: silenciar avisos: cada entrada dice por que esa vista puede ser publica, y
#: anadir una obliga a escribir esa razon. La clave es ``namespace:nombre`` (o
#: solo el nombre cuando la ruta no tiene espacio de nombres, como las de la
#: API).
#:
#: Las rutas de la API con ``permission_classes`` distinto de ``AllowAny``
#: (``HasServerKey``, ``IsAuthenticated``) cuentan como guardadas y no salen
#: aqui; las que declaran ``AllowAny`` **si** tienen que estar. La lista de las
#: publicas de la API la fija tambien ``app_core/tests/test_api_open_routes.py``,
#: y ``utils/tests/test_check_security.py`` comprueba que las dos coinciden.
INTENTIONALLY_PUBLIC = {
    'core:index': 'portada del sitio; lleva el formulario de contacto '
                  '(con honeypot)',
    'core:calendar': 'calendario publico del despacho',
    'core:terms_and_conditions': 'aviso legal, tiene que leerse antes de '
                                 'registrarse',
    'core:privacy_policy': 'politica de privacidad; publica por obligacion '
                           'legal',
    'core:documents': 'documentos publicos del despacho',
    'core:team_member_detail': 'ficha publica de cada miembro del equipo',
    'core:security_txt': '/.well-known/security.txt: publico por definicion '
                         '(RFC 9116)',
    'core:health_check': 'lo consulta el monitor y `check_health --http`; '
                         'solo dice si responden base de datos, cache y '
                         'correo, sin datos ni mensajes de error',
    'two_factor:login': 'la misma pantalla de acceso, registrada tambien '
                        'bajo el nombre que buscan django-otp y '
                        'django-two-factor-auth (ver two_factor_urls.py)',
    'account:login': 'la pantalla de acceso; sus frenos son axes para la '
                     'contrasena y otp_login.send_throttle para el codigo '
                     'por correo',
    'account:register': 'alta de cuenta (sin permisos hasta que alguien se '
                        'los conceda)',
    'account:logout': 'cerrar sesion; sin sesion no hace nada',
    'account:forgot_password': 'recuperacion; limitada por IP y destinatario',
    'account:change_password': 'exige sesion (lo comprueba dispatch) y la '
                               'contrasena actual',
    'case_manager:public_query': 'portal del cliente: cedula + codigo al '
                                 'correo; limitado por IP (attempts)',
    'case_manager:paz_y_salvo': 'exige el cliente identificado en la sesion '
                                'o personal del gestor',
    'case_manager:paz_y_salvo_download': 'igual: el mismo 404 para todo lo '
                                         'que no sea el cliente del caso o '
                                         'el gestor',
    'attack_path': 'la trampa anti-escaneo',
    'set_language': 'cambio de idioma',
    'csp_report': 'destino de los informes de CSP; publico porque lo '
                        'llama el navegador, con cupo por IP, cuerpo maximo y '
                        'sin guardar nada en la base de datos',
    # --- API con AllowAny explicito ---
    'api-contact-create': 'formulario de contacto para visitantes sin cuenta',
    'api-pqrs-create': 'recepcion publica de peticiones, quejas, reclamos y '
                       'sugerencias',
    'api-main-faq-list': 'preguntas frecuentes publicas del sitio',
    'api-other-faq-list': 'preguntas frecuentes adicionales publicas',
    'api-financial-education-list': 'contenido publico de educacion '
                                    'financiera',
}

#: Rutas publicas sin nombre en el URLconf, identificadas por su ruta.
#:
#: `reverse()` no las alcanza y no tienen etiqueta, asi que se listan por lo
#: unico que las identifica.
INTENTIONALLY_PUBLIC_PATHS = {
    'robots.txt': 'lo pide cualquier buscador, por definicion publico',
}

#: Formularios publicos que aceptan POST y **tienen que** llevar limite.
#:
#: El contacto (`core:index`, `api-contact-create`), el PQRS y el registro
#: figuran aqui aunque hoy no lo lleven: son justo el tipo de formulario que
#: un bot llena a golpes, y salen como hallazgo hasta que se les ponga freno.
#: Ver `docs/SEGURIDAD.md`.
THROTTLED_FORMS = {
    'account:login',
    'account:register',
    'account:forgot_password',
    'case_manager:public_query',
    'core:index',
    'api-contact-create',
    'api-pqrs-create',
}

#: Cualquiera de estas marcas en el codigo de la vista cuenta como freno.
THROTTLE_MARKERS = (
    'RateLimit', 'throttle', '.consume(', 'spend_', 'attempts.',
    'is_locked_out', 'note_failure', 'axes',
)

SHELL_CALLS = re.compile(r'os\.system\(|os\.popen\(|shell\s*=\s*True')
STRING_SQL = re.compile(
    r'cursor\.execute\(\s*[f\'"].*%s*[\'"]\s*%|\.raw\(\s*f')


class Command(BaseCommand):
    help = 'Comprueba la superficie de seguridad propia de este proyecto.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Sale con codigo distinto de cero si hay algun hallazgo.',
        )

    def handle(self, *args, **options):
        self.findings = []

        self.not_checked = []

        self._check_unguarded_views()
        self._check_throttles()
        self._check_shell_calls()
        self._check_string_sql()
        self._check_uploads_are_not_served()
        self._check_settings()
        self._check_bandit()
        self._check_dependencies()
        self._check_dependencies_deeply()

        self.stdout.write('')

        # Lo que no se pudo mirar se dice siempre, haya hallazgos o no. Un
        # informe que acaba en "sin hallazgos" habiendose saltado dos
        # secciones enteras dice algo que no es verdad.
        if self.not_checked:
            self.stdout.write(self.style.WARNING(
                f'{len(self.not_checked)} comprobacion(es) no se han hecho:'
            ))

            for reason in self.not_checked:
                self.stdout.write(self.style.WARNING(f'   · {reason}'))

            self.stdout.write('')

        if not self.findings:
            self.stdout.write(self.style.SUCCESS(
                'Sin hallazgos. Recuerda que esto no sustituye a '
                '"manage.py check --deploy".'
            ))
            return

        self.stdout.write(self.style.ERROR(
            f'{len(self.findings)} hallazgo(s).'
        ))

        if options['strict']:
            raise SystemExit(1)

    # ------------------------------------------------------------------
    def _section(self, title):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(title))

    def _ok(self, message):
        self.stdout.write(self.style.SUCCESS(f'   OK    {message}'))

    def _finding(self, message):
        self.findings.append(message)
        self.stdout.write(self.style.ERROR(f'   AVISO {message}'))

    def _not_checked(self, reason):
        """
        Lo que no se ha podido mirar.

        No es un hallazgo --no haber ejecutado un escaner no es una
        vulnerabilidad-- pero tampoco pasa en silencio: un informe de
        seguridad que parece completo sin serlo es peor que uno que falta.
        """
        self.not_checked.append(reason)
        self.stdout.write(self.style.WARNING(f'   SIN MIRAR {reason}'))

    # ------------------------------------------------------------------
    def _report_scan(self, result):
        """Lo comun a las tres secciones de escaner."""
        if result.skipped:
            # Un salto previsto --safety fuera de local-- se cuenta, pero no
            # como un hueco: sacarlo en la lista de "sin mirar" en cada
            # despliegue por algo que esta bien acabaria con que nadie lee esa
            # lista, ni cuando trae uno de verdad.
            if result.by_design:
                self.stdout.write(f'   (omitida: {result.skipped})')
            else:
                self._not_checked(result.skipped)

            return False

        if result.error:
            self._not_checked(result.error)
            return False

        return True

    def _check_bandit(self):
        self._section('7. Analisis estatico del codigo (bandit)')

        result = run_bandit()

        if not self._report_scan(result):
            return

        if result.accepted:
            self.stdout.write(
                f'   ({result.accepted} aviso(s) dados por buenos, con su '
                f'razon escrita en utils/scanners.py)'
            )

        if not result.findings:
            self._ok('Ningun aviso nuevo.')
            return

        for finding in result.findings:
            self._finding(finding)

        self.stdout.write(
            '   Si alguno es un falso positivo, va a BANDIT_ACCEPTED con su '
            'motivo; no se silencia sin escribir por que.'
        )

    def _check_dependencies(self):
        self._section('8. Vulnerabilidades en las dependencias (pip-audit)')

        self.stdout.write(
            '   (mira lo que hay INSTALADO en este entorno, no '
            'requirements.txt: la version que se ejecuta es la que puede '
            'tener el fallo, asi que para que valga hay que lanzarlo donde '
            'corre la aplicacion)'
        )

        result = run_pip_audit()

        if not self._report_scan(result):
            return

        if not result.findings:
            self._ok('Ninguna dependencia con vulnerabilidad conocida.')
            return

        for finding in result.findings:
            self._finding(finding)

    def _check_dependencies_deeply(self):
        self._section('9. Segunda opinion sobre las dependencias (safety)')

        result = run_safety()

        if not self._report_scan(result):
            return

        if not result.findings:
            self._ok('Ninguna dependencia con vulnerabilidad conocida.')
            return

        for finding in result.findings:
            self._finding(finding)

    # ------------------------------------------------------------------
    def _upload_prefixes(self):
        """
        La primera carpeta de cada campo de fichero **bajo ``MEDIA_ROOT``**.

        Sigue existiendo aqui, y no solo en ``media_audit``, porque las
        pruebas y quien lea este comando lo buscan donde se usa. La lectura
        del ``upload_to`` (cadena, o funcion leida con AST) esta en
        ``utils/media_audit.py``.
        """
        return upload_prefixes()

    def _check_uploads_are_not_served(self):
        """
        Que ninguna carpeta de subidas la reparta el servidor web por su cuenta.

        El control de acceso de Django no pinta nada sobre un fichero que
        Apache sirve antes de que Django lo vea. Bajo ``MEDIA_ROOT`` solo debe
        haber lo que se declara servible en ``PUBLICLY_SERVABLE_MEDIA`` (con su
        razon) o lo que ``deploy/media.htaccess`` bloquea; lo sensible --los
        PDF del paz y salvo-- vive **fuera** de ``MEDIA_ROOT``, en
        ``PRIVATE_MEDIA_ROOT``, y aqui se comprueba que asi sea.
        """
        self._section('5. Carpetas de subidas que serviria el servidor web')

        media_root = Path(str(settings.MEDIA_ROOT))
        blocked_file = Path(settings.BASE_DIR) / MEDIA_HTACCESS
        rules = (blocked_file.read_text(encoding='utf-8')
                 if blocked_file.exists() else '')

        # -- lo privado: fuera de MEDIA_ROOT, sin URL y sin publicar ------
        for row in private_fields():
            private_root = row['root']

            if is_inside(media_root, private_root):
                self._finding(
                    f'{row["label"]} escribe en {private_root}, que contiene '
                    'MEDIA_ROOT: lo servido directo alcanzaria lo privado.'
                )
            elif 'public_html' in Path(private_root).parts:
                self._finding(
                    f'{row["label"]} escribe en {private_root}, dentro de '
                    'public_html: el servidor web puede repartirlo sin pasar '
                    'por Django. PRIVATE_MEDIA_ROOT debe quedar fuera.'
                )
            elif is_inside(private_root, getattr(settings, 'STATIC_ROOT', '')
                           or '/nonexistent'):
                self._finding(
                    f'{row["label"]} escribe dentro de STATIC_ROOT, que se '
                    'publica.'
                )
            else:
                self._ok(
                    f'{row["label"]} va a {private_root}, fuera de '
                    'MEDIA_ROOT y sin URL.'
                )

        # -- lo que cuelga de MEDIA_ROOT ---------------------------------
        for prefix, fields in sorted(self._upload_prefixes().items()):
            if prefix == UNKNOWN_PREFIX:
                self._finding(
                    f'No se pudo leer a que carpeta escriben: '
                    f'{", ".join(fields)}. Miralo a mano y, si hace falta, '
                    'ensena a `prefix_from_function` la forma nueva.'
                )
                continue

            if prefix in PUBLICLY_SERVABLE_MEDIA:
                self._ok(
                    f'{prefix}/ ({", ".join(fields)}) se sirve directo, '
                    'declarado: ' + PUBLICLY_SERVABLE_MEDIA[prefix]
                )
                continue

            if prefix and re.search(rf'\b{re.escape(prefix)}\b', rules):
                self._ok(f'{prefix}/ esta bloqueado en {MEDIA_HTACCESS}.')
                continue

            self._finding(
                f'{prefix or "(raiz)"}/ ({", ".join(fields)}) no esta '
                f'bloqueado en {MEDIA_HTACCESS} ni declarado como publico. '
                'Cualquiera con la URL se lo descarga sin pasar por Django. '
                'Si de verdad puede servirse directo, ponlo en '
                'PUBLICLY_SERVABLE_MEDIA (utils/media_audit.py) con su razon; '
                'si no, muevelo a PRIVATE_MEDIA_ROOT.'
            )

        # -- CKEditor 5: cae en la raiz de MEDIA_ROOT, sin campo de modelo ---
        if 'django_ckeditor_5' in settings.INSTALLED_APPS:
            if getattr(settings, 'CKEDITOR_5_ALLOW_ALL_FILE_TYPES', False):
                self._finding(
                    'CKEDITOR_5_ALLOW_ALL_FILE_TYPES esta activo: el editor '
                    'aceptaria cualquier tipo de fichero y lo dejaria en la '
                    'raiz de MEDIA_ROOT, servido directo.'
                )
            else:
                self._ok(f'{CKEDITOR_ROOT}: {CKEDITOR_REASON}.')

    # ------------------------------------------------------------------
    def _own_views(self):
        """Las rutas de este proyecto, con su guardia."""
        rows = []
        admin_url = str(getattr(settings, 'ADMIN_URL', '') or '\0')

        def walk(patterns, prefix='', namespaces=()):
            for entry in patterns:
                route = str(getattr(entry.pattern, '_route', '') or
                            entry.pattern)

                if isinstance(entry, URLResolver):
                    inner = namespaces + (
                        (entry.namespace,) if entry.namespace else ())
                    walk(entry.url_patterns, prefix + route, inner)
                    continue

                if not isinstance(entry, URLPattern):
                    continue

                callback = entry.callback
                module = getattr(callback, '__module__', '')

                if not module.startswith('apps.'):
                    continue

                # El admin no se audita ruta por ruta: tiene una sola puerta
                # (`admin_view`) y sus vistas van envueltas, asi que desde
                # fuera no se les ve ningun mixin y saldrian todas como
                # desprotegidas -- avisos falsos que tapan los de verdad.
                if (prefix + route).startswith(admin_url):
                    continue

                view_class = (getattr(callback, 'view_class', None)
                              or getattr(callback, 'cls', None))
                mro = ([base.__name__ for base in view_class.__mro__]
                       if view_class else [])

                permissions = None

                if view_class is not None and hasattr(
                        view_class, 'permission_classes'):
                    permissions = [
                        getattr(item, '__name__', str(item))
                        for item in view_class.permission_classes
                    ]

                # Una vista de DRF esta guardada si declara algun permiso que
                # no sea `AllowAny`; una de Django, si lleva un mixin de acceso.
                guarded = bool(GUARD_MIXINS & set(mro)) or bool(
                    permissions and 'AllowAny' not in permissions)

                rows.append({
                    'path': prefix + route,
                    'name': getattr(entry, 'name', '') or '',
                    'namespace': namespaces[-1] if namespaces else '',
                    'guarded': guarded,
                    'is_class': view_class is not None,
                    'callback': callback,
                    'view_class': view_class,
                })

        walk(get_resolver().url_patterns)

        return rows

    def _label(self, row) -> str:
        """``namespace:name`` (o solo ``name``), como en las listas de arriba."""
        if row['namespace']:
            return f'{row["namespace"]}:{row["name"]}'

        return row['name']

    def _check_unguarded_views(self):
        self._section('1. Vistas propias sin control de acceso')

        unexpected = []

        for row in self._own_views():
            if row['guarded']:
                continue

            label = self._label(row)

            # Una vista de funcion puede llevar decoradores que no se ven
            # desde aqui; se comprueba su codigo por separado.
            if not row['is_class'] and self._function_has_guard(
                    row['callback']):
                continue

            if label in INTENTIONALLY_PUBLIC:
                continue

            if row['path'] in INTENTIONALLY_PUBLIC_PATHS:
                continue

            unexpected.append((label or '(sin nombre)', row['path']))

        if not unexpected:
            total = len(INTENTIONALLY_PUBLIC) + len(INTENTIONALLY_PUBLIC_PATHS)
            self._ok(
                f'{total} vistas publicas, todas justificadas en la lista del '
                'comando.'
            )
            return

        for label, path in unexpected:
            self._finding(
                f'{label} (/{path}) no tiene control de acceso y no esta en '
                'la lista de publicas a proposito.'
            )

    def _function_has_guard(self, callback) -> bool:
        """Si una vista de funcion comprueba algo antes de responder."""
        try:
            source = inspect.getsource(callback)
        except (OSError, TypeError):
            return True  # ante la duda, no se avisa

        return any(token in source for token in (
            'login_required', 'is_staff', 'is_superuser', 'has_perm',
            'permission_required',
        ))

    # ------------------------------------------------------------------
    def _check_throttles(self):
        self._section('2. Formularios publicos con limite de intentos')

        rows = {self._label(row): row for row in self._own_views()}

        for label in sorted(THROTTLED_FORMS):
            row = rows.get(label)

            if row is None:
                self._finding(f'{label} ya no existe: revisa la lista.')
                continue

            source = self._source_of(row)

            # Los limites son todos de la misma familia (`RateLimit`,
            # `attempts`, axes): basta con buscar la clase o una llamada a
            # `.consume()`. Se mira el modulo de la vista y no solo la clase
            # porque el limite suele declararse a nivel de modulo.
            if any(marker in source for marker in THROTTLE_MARKERS):
                self._ok(f'{label} limita los intentos.')
            else:
                self._finding(
                    f'{label} es publico, acepta POST y **no limita los '
                    'intentos**. Es lo que convierte un formulario en un '
                    'oraculo enumerable o en un buzon que se llena a '
                    'golpes.'
                )

    def _source_of(self, row) -> str:
        """
        El codigo de la vista, mas los nombres de limite que use.

        Solo el de la vista y **no** el del modulo entero: en un modulo con
        varias vistas (`account/views.py`) el `RateLimit` de una habria dado
        por limitadas a todas. Un limite declarado a nivel de modulo
        (`reset_by_ip = RateLimit(...)`) se reconoce porque la vista lo nombra:
        aqui se le anade el nombre del objeto a lo que se busca.
        """
        from ...throttling import RateLimit

        callback = row['callback']
        parts = []

        for target in (row['view_class'], callback):
            if target is None:
                continue

            try:
                parts.append(inspect.getsource(target))
            except (OSError, TypeError):
                continue

        source = '\n'.join(parts)

        module = inspect.getmodule(callback)
        names = [
            name for name, value in vars(module).items()
            if isinstance(value, RateLimit)
        ] if module is not None else []

        # Los limites que se declaran dentro de la clase (`reset_by_ip =
        # RateLimit(...)`) ya llevan la palabra `RateLimit` en su codigo; los
        # de modulo se cuentan si la vista los nombra.
        if any(re.search(rf'\b{re.escape(name)}\b', source) for name in names):
            source += '\nRateLimit'

        return source

    # ------------------------------------------------------------------
    def _sources(self):
        root = Path(settings.BASE_DIR) / 'apps'

        for path in root.rglob('*.py'):
            # Este mismo fichero contiene los patrones que busca, en su
            # docstring y en sus mensajes. Auditarse a si mismo da dos avisos
            # garantizados que no significan nada.
            if 'test' in path.name or '/migrations/' in str(path).replace(
                    '\\', '/'):
                continue

            if path.name == 'check_security.py':
                continue

            try:
                yield path, path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue

    def _check_shell_calls(self):
        self._section('3. Ejecucion por shell')

        found = [
            (path, line)
            for path, body in self._sources()
            for line in body.splitlines()
            if SHELL_CALLS.search(line) and not line.strip().startswith('#')
        ]

        if not found:
            self._ok('Ningun os.system, os.popen ni shell=True.')
            return

        for path, line in found:
            self._finding(
                f'{path.relative_to(settings.BASE_DIR)}: {line.strip()[:70]}'
            )

    def _check_string_sql(self):
        self._section('4. SQL construido con cadenas')

        found = [
            (path, line)
            for path, body in self._sources()
            for line in body.splitlines()
            if STRING_SQL.search(line)
        ]

        if not found:
            self._ok('Ninguna consulta construida por interpolacion.')
            return

        for path, line in found:
            self._finding(
                f'{path.relative_to(settings.BASE_DIR)}: {line.strip()[:70]}'
            )

    # ------------------------------------------------------------------
    def _check_settings(self):
        self._section('6. Ajustes del entorno')

        self.stdout.write(
            '   (esta seccion depende de donde se ejecute: para que valga, '
            'lanzalo con los ajustes de produccion)'
        )

        if settings.DEBUG:
            self._finding(
                'DEBUG esta activado. En produccion expone la traza completa '
                'de cada error, con ajustes y consultas dentro.'
            )
        else:
            self._ok('DEBUG apagado.')

        expected = {
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'CSRF_COOKIE_SAMESITE': 'Lax',
        }

        # Con DEBUG encendido las cookies seguras se relajan a proposito
        # (desarrollo en http); el aviso de DEBUG ya lo cubre.
        if not settings.DEBUG:
            expected.update({
                'SESSION_COOKIE_SECURE': True,
                'CSRF_COOKIE_SECURE': True,
                'SECURE_SSL_REDIRECT': True,
            })

        for name, value in expected.items():
            if getattr(settings, name, None) == value:
                self._ok(f'{name} = {value!r}')
            else:
                self._finding(
                    f'{name} deberia ser {value!r} y es '
                    f'{getattr(settings, name, None)!r}.'
                )

        # --- claves ---
        server_key = getattr(settings, 'SERVER_KEY', '') or ''

        if len(server_key) < 32:
            self._finding(
                'SERVER_KEY tiene menos de 32 caracteres (o esta vacia): es '
                'la clave servidor a servidor de la API de Attlas y ante gea, '
                'y decide si se cree X-Client-IP.'
            )
        else:
            self._ok('SERVER_KEY de 32 caracteres o mas.')

        if not getattr(settings, 'FIELD_ENCRYPTION_KEY', None):
            self._finding(
                'FIELD_ENCRYPTION_KEY sin configurar: los campos cifrados '
                '(cedula y fecha de nacimiento de los clientes de la '
                'plataforma) no se podrian leer ni escribir.'
            )
        else:
            self._ok('FIELD_ENCRYPTION_KEY configurada.')

        admin_url = str(getattr(settings, 'ADMIN_URL', '') or '')

        if not settings.DEBUG and admin_url.strip('/') == 'admin':
            self._finding(
                'DJANGO_ADMIN_URL es la de por defecto (admin/): es la '
                'primera ruta que prueba cualquier escaner.'
            )
        else:
            self._ok('El admin no esta en la ruta por defecto.')

        # --- CORS: origenes enumerados, sin comodin ---
        cors_bad = []

        if getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False):
            cors_bad.append('CORS_ALLOW_ALL_ORIGINS activo')

        if getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', None):
            cors_bad.append('CORS_ALLOWED_ORIGIN_REGEXES con expresiones')

        if any('*' in str(origin)
               for origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', [])):
            cors_bad.append('un comodin en CORS_ALLOWED_ORIGINS')

        if cors_bad:
            self._finding(
                'CORS deja de estar enumerado: ' + ', '.join(cors_bad) + '.'
            )
        else:
            self._ok('CORS con origenes enumerados, sin comodines.')

        if '*' in getattr(settings, 'ALLOWED_HOSTS', []):
            self._finding('ALLOWED_HOSTS contiene "*".')
        else:
            self._ok('ALLOWED_HOSTS sin comodin.')

        # --- cache compartida ---
        backend = str(getattr(settings, 'CACHES', {}).get(
            'default', {}).get('BACKEND', 'locmem'))

        if 'locmem' in backend.lower() or 'dummy' in backend.lower():
            self._finding(
                'La cache no es compartida (LocMemCache): los limites de '
                'intentos son **por worker**, asi que el limite real es el '
                'configurado multiplicado por el numero de procesos. '
                '`manage.py check_cache` lo confirma.'
            )
        else:
            self._ok('Cache compartida: los limites cuentan de verdad.')
