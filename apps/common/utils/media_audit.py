# apps/common/utils/media_audit.py
"""
Que carpetas de subidas hay, a donde escribe cada campo y que se puede servir.

Lo comparten ``manage.py check_security`` (seccion de subidas) y
``manage.py check_media``, y sus pruebas. Vive aparte para que las dos
comprobaciones lean **lo mismo**: dos lecturas de la misma cosa acaban
discrepando, y entonces no se sabe cual creer.

Que sube quien, en pag
----------------------
* **Campos de fichero** (``FileField`` / ``ImageField``) de los modelos del
  proyecto:

  - ``core.TeamMemberModel.photo`` -> ``team/`` y
    ``core.ModalBannerModel.image_file[_en]`` -> ``modal_banners/``: contenido
    del sitio que sube el personal desde el admin y que se pinta en paginas
    publicas. Se sirven directo a proposito.
  - ``case_manager.PazYSalvoDocumentModel.source_file`` / ``public_copy_file``
    -> ``paz_y_salvo/``: **datos personales**. Viven en un almacen propio
    (``PrivateMediaStorage``) bajo ``PRIVATE_MEDIA_ROOT``, **fuera de
    ``MEDIA_ROOT``**, sin URL, y solo salen por las vistas del gestor con
    permiso.

* **CKEditor 5** (``django_ckeditor_5``): la vista ``image_upload/`` guarda lo
  que sube el personal desde el editor **en la raiz de ``MEDIA_ROOT``**, sin
  carpeta, con ``CKEDITOR_5_FILE_STORAGE``. No es un campo de modelo, asi que
  ninguna lectura de modelos lo veria; se declara aparte. Solo admite imagenes
  (verifica con Pillow) mientras ``CKEDITOR_5_ALLOW_ALL_FILE_TYPES`` no se
  active, y solo a personal (``is_staff``).

* **``insolvency_form``**: no escribe ficheros. La firma es un ``TextField``
  con la imagen en base64 dentro de la base de datos, y el DOCX del formulario
  se genera en memoria (``BytesIO``) y se entrega en la respuesta. Nada de eso
  toca disco, y por eso no aparece aqui: su proteccion es la de la base de
  datos (y el respaldo cifrado, ver ``db_backup``).
"""

import ast
import inspect
import textwrap
from pathlib import Path

from django.conf import settings

#: Carpetas de ``MEDIA_ROOT`` que **si** puede repartir el servidor web.
#:
#: Es una lista de excepciones justificadas, no de exclusion: la pregunta
#: «¿esto puede servirse directo?» hay que contestarla al crear el campo, no
#: cuando alguien encuentra el fichero. Lo que no este aqui tiene que estar
#: bloqueado (``deploy/media.htaccess``) o vivir fuera de ``MEDIA_ROOT``.
PUBLICLY_SERVABLE_MEDIA = {
    'team': 'fotos del equipo; se pintan en la pagina publica de cada miembro',
    'modal_banners': (
        'imagen de los avisos modales del sitio (ModalBannerModel); es '
        'publicidad del despacho y se pinta a cualquier visitante'
    ),
}

#: El destino de las subidas de CKEditor 5, que no lleva carpeta: cae en la
#: raiz de ``MEDIA_ROOT``. Va con su razon, igual que las carpetas.
CKEDITOR_ROOT = '(raiz de MEDIA_ROOT, CKEditor 5)'
CKEDITOR_REASON = (
    'imagenes que el personal inserta en el contenido publico desde el '
    'editor; solo is_staff las sube y solo se admiten imagenes'
)

#: Donde se declara el bloqueo, para leerlo y contrastarlo.
MEDIA_HTACCESS = 'deploy/media.htaccess'

#: Marcador para un campo cuyo destino no se pudo leer. Se avisa, no se salta.
UNKNOWN_PREFIX = '?'


def _prefix_of(value):
    """El primer segmento de una expresion que construye una ruta."""
    # return 'carpeta/lo-que-sea'
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value.strip('/').split('/')[0] or None

    # return f'paz_y_salvo/{case_id}/{pk}-source.pdf'
    if isinstance(value, ast.JoinedStr):
        for part in value.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                return part.value.strip('/').split('/')[0] or None
        return None

    # return os.path.join('offer', slug, ...)  |  Path('x') / y
    if isinstance(value, ast.Call) and value.args:
        return _prefix_of(value.args[0])

    return None


def prefix_from_function(upload_to):
    """
    La carpeta que devuelve una funcion de ``upload_to``.

    No se puede llamar --necesita una instancia--, asi que se lee su codigo
    **con AST**, y se mira **lo que se devuelve**, no la primera cadena que
    aparezca: un ``ast.walk`` recorre en anchura y no en orden de codigo, y la
    primera cadena puede ser el valor por defecto de un nombre. Con una
    expresion regular sobre el texto se leia ademas el docstring. La ruta esta
    en el ``return``, y ahi es donde hay que mirar.
    """
    try:
        source = inspect.getsource(upload_to)
    except (OSError, TypeError):
        return None

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None

    function = tree.body[0]

    # `path = os.path.join(...)` y luego `return path`: se resuelve el nombre a
    # lo ultimo que se le asigno. Sin esto el campo se quedaba **sin mirar**,
    # que en una comprobacion de seguridad es peor que un falso positivo.
    assigned = {}

    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = node.value

    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or node.value is None:
            continue

        value = node.value

        if isinstance(value, ast.Name):
            value = assigned.get(value.id)

        prefix = _prefix_of(value) if value is not None else None

        if prefix:
            return prefix

    return None


def storage_root(field):
    """
    La carpeta raiz donde guarda ese campo, o ``None`` si no se sabe.

    Un ``FileField`` sin almacen propio usa el de por defecto, que cuelga de
    ``MEDIA_ROOT``; ``PrivateMediaStorage`` cuelga de ``PRIVATE_MEDIA_ROOT``.
    """
    location = getattr(getattr(field, 'storage', None), 'location', None)

    return Path(location).resolve() if location else None


def is_inside(child, parent) -> bool:
    """Si ``child`` es ``parent`` o esta dentro. Sin tocar el disco."""
    if child is None or parent is None:
        return False

    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
    except ValueError:
        return False

    return True


def upload_fields():
    """
    Los campos de fichero de los modelos del proyecto.

    Devuelve dicts con ``label`` (``app.Modelo.campo``), ``field``, ``model``,
    ``prefix`` (primera carpeta de ``upload_to``, o ``UNKNOWN_PREFIX``),
    ``root`` (donde escribe) y ``private`` (si escribe fuera de
    ``MEDIA_ROOT``). Un campo cuyo destino no se sabe leer se **incluye** con
    ``UNKNOWN_PREFIX``: saltarlo lo dejaria fuera de la comprobacion sin que
    nadie lo supiera, que es la forma de fallo que esto existe para evitar.
    """
    from django.apps import apps as django_apps
    from django.db.models import FileField

    rows = []
    media_root = Path(str(settings.MEDIA_ROOT))

    for model in django_apps.get_models():
        if not model.__module__.startswith('apps.'):
            continue

        for field in model._meta.get_fields():
            # `ImageField` hereda de `FileField`.
            if not isinstance(field, FileField):
                continue

            upload_to = getattr(field, 'upload_to', None)

            if not upload_to:
                prefix = ''
            elif callable(upload_to):
                prefix = prefix_from_function(upload_to)
            else:
                prefix = str(upload_to).strip('/').split('/')[0]

            root = storage_root(field)

            rows.append({
                'label': f'{model._meta.label}.{field.name}',
                'model': model,
                'field': field,
                'prefix': UNKNOWN_PREFIX if prefix is None else prefix,
                'root': root,
                'private': root is not None
                and not is_inside(root, media_root),
            })

    return rows


def upload_prefixes():
    """``{carpeta: [campos]}`` de lo que escribe **bajo ``MEDIA_ROOT``**."""
    prefixes = {}

    for row in upload_fields():
        if row['private']:
            continue

        prefixes.setdefault(row['prefix'], []).append(row['label'])

    return prefixes


def private_fields():
    """Los campos que escriben fuera de ``MEDIA_ROOT``."""
    return [row for row in upload_fields() if row['private']]
