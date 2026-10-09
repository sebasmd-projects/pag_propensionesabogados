"""Purga supervisada. Nunca amplía el conjunto que el operador confirmó."""
import logging
from datetime import date, datetime, time, timedelta
from functools import partial

from auditlog.context import disable_auditlog
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ...models import CaseModel, ClientModel, PazYSalvoDocumentModel

logger = logging.getLogger('case_manager.purge')


def short_id(value):
    return str(value)[:8] if value is not None else '—'


def timestamp(value):
    return (timezone.localtime(value) if timezone.is_aware(value) else value).isoformat()


def blocked_document(document):
    certified = (document.status == 'CERTIFIED' or document.certified_at is not None
                 or bool(document.gea_document_id) or bool(document.gea_code))
    return certified and not document.gea_revoked


def documents(case, lock=False):
    queryset = PazYSalvoDocumentModel.objects.filter(case_id=case.pk)
    return list(queryset.select_for_update() if lock else queryset)


def case_reason(case, cutoff, docs):
    if case.deleted_at is None or case.deleted_at >= cutoff:
        return 'asunto activo o no vencido para el límite elegido'
    if any(blocked_document(doc) for doc in docs):
        return 'paz y salvo certificado sin revocar en gea'
    return ''


def record_purge(kind, pk, actor, deleted_at):
    logger.info('fecha=%s tipo=%s id=%s deleted_at=%s deleted_by=%s',
                timezone.now().isoformat(), kind, short_id(pk),
                timestamp(deleted_at), short_id(actor))


def finish_case(pk, actor, deleted_at, files):
    # El disco no participa en la transacción SQL: jamás quitar un PDF si
    # la BD hizo rollback. Un fallo de disco se informa sin rutas ni PII.
    record_purge('asunto', pk, actor, deleted_at)
    failed = False
    for storage, name in files:
        try:
            storage.delete(name)
        except OSError:
            failed = True
    if failed:
        logger.error('fecha=%s id=%s limpieza_ficheros=fallida',
                     timezone.now().isoformat(), short_id(pk))
        raise CommandError(f'Asunto {short_id(pk)} purgado; revisar limpieza de ficheros privados.')


class Command(BaseCommand):
    help = 'Simula la purga de eliminados vencidos; --apply exige confirmación.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--yes', action='store_true')
        parser.add_argument('--before', metavar='YYYY-MM-DD')

    def handle(self, *args, **options):
        if options['yes'] and not options['apply']:
            raise CommandError('--yes solo se permite junto con --apply.')
        days = settings.SOFT_DELETE_RETENTION_DAYS
        if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
            raise CommandError('SOFT_DELETE_RETENTION_DAYS debe ser un entero positivo.')
        limit = timezone.localdate() - timedelta(days=days)
        before = limit
        if options['before']:
            try:
                before = date.fromisoformat(options['before'])
                if before.isoformat() != options['before']:
                    raise ValueError
            except ValueError:
                raise CommandError('--before debe tener formato YYYY-MM-DD.') from None
            if before >= limit:
                raise CommandError('--before debe ser anterior al límite de retención.')
        cutoff = datetime.combine(before, time.min)
        if settings.USE_TZ:
            cutoff = timezone.make_aware(cutoff, timezone.get_current_timezone())
        self.stdout.write(f'Límite exclusivo: {before}; retención: {days} días.')
        cases = []
        for case in CaseModel.all_objects.filter(deleted_at__lt=cutoff).select_related('client').order_by('pk'):
            reason = case_reason(case, cutoff, documents(case))
            self.show('Asunto', case, reason)
            if not reason:
                cases.append(case)
        case_ids = {case.pk for case in cases}
        clients = []
        for client in ClientModel.all_objects.filter(deleted_at__lt=cutoff).order_by('pk'):
            blocked = list(CaseModel.all_objects.filter(client_id=client.pk).exclude(pk__in=case_ids))
            reason = ''
            if blocked:
                reason = '; '.join(f'{short_id(case.pk)}: {case_reason(case, cutoff, documents(case))}'
                                   for case in blocked)
            self.show('Cliente', client, reason)
            if not reason:
                clients.append(client)
        total = len(cases) + len(clients)
        self.stdout.write(f'Total: asuntos={len(cases)}, clientes={len(clients)}, registros={total}.')
        if not options['apply']:
            self.stdout.write('SIMULACIÓN: no se ha borrado nada.')
            return
        if not total:
            return
        if not options['yes']:
            try:
                answer = input(f'Escriba {total} para borrar definitivamente {total} registros: ')
            except (EOFError, KeyboardInterrupt):
                answer = ''
            if answer != str(total):
                raise CommandError('Confirmación incorrecta. No se ha borrado nada.')
        purged_cases = sum(self.purge_case(case, cutoff) for case in cases)
        purged_clients = sum(self.purge_client(client, cutoff) for client in clients)
        self.stdout.write(f'Purgados: asuntos={purged_cases}, clientes={purged_clients}.')

    def show(self, kind, obj, reason):
        is_case = isinstance(obj, CaseModel)
        client = obj.client if is_case else obj
        service = obj.service_display if is_case else '—'
        reference = obj.public_reference if is_case else '—'
        self.stdout.write(
            f'{kind} {short_id(obj.pk)} | cliente={client.full_name} | servicio={service} | '
            f'radicado={reference} | deleted_at={timestamp(obj.deleted_at)} | '
            f'deleted_by={short_id(obj.deleted_by_id)} | '
            f'{"BLOQUEADO: " + reason if reason else "PURGABLE"}')

    def unchanged(self, obj, snapshot, cutoff):
        return (obj is not None and obj.deleted_at is not None and obj.deleted_at < cutoff
                and obj.deleted_at == snapshot.deleted_at
                and obj.deleted_by_id == snapshot.deleted_by_id)

    def purge_case(self, snapshot, cutoff):
        with transaction.atomic():
            # Mismo orden que el borrado/restauración del cliente. Sin joins
            # en FOR UPDATE: portable a MySQL/MariaDB y PostgreSQL.
            ClientModel.all_objects.select_for_update().filter(pk=snapshot.client_id).first()
            case = CaseModel.all_objects.select_for_update().filter(pk=snapshot.pk).first()
            if not self.unchanged(case, snapshot, cutoff):
                self.stdout.write(f'Omitido asunto {short_id(snapshot.pk)}: cambió desde la revisión.')
                return 0
            docs = documents(case, lock=True)
            reason = case_reason(case, cutoff, docs)
            if reason:
                self.stdout.write(f'Omitido asunto {short_id(case.pk)}: {reason}.')
                return 0
            files = [(field.storage, field.name) for doc in docs
                     for field in (doc.source_file, doc.public_copy_file) if field.name]
            callback = partial(finish_case, case.pk, case.deleted_by_id, case.deleted_at, files)
            # La auditoría normal serializa nombres y documentos al borrar.
            # Esta operación conserva exclusivamente el registro mínimo de purga.
            with disable_auditlog():
                case.delete()
            transaction.on_commit(callback)
        return 1

    def purge_client(self, snapshot, cutoff):
        with transaction.atomic():
            client = ClientModel.all_objects.select_for_update().filter(pk=snapshot.pk).first()
            if (not self.unchanged(client, snapshot, cutoff)
                    or CaseModel.all_objects.filter(client_id=snapshot.pk).exists()):
                self.stdout.write(f'Omitido cliente {short_id(snapshot.pk)}: cambió o conserva asuntos.')
                return 0
            callback = partial(record_purge, 'cliente', client.pk, client.deleted_by_id, client.deleted_at)
            with disable_auditlog():
                client.delete()
            transaction.on_commit(callback)
        return 1
