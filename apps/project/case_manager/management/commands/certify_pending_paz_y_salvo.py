"""
Reintenta la certificacion de los paz y salvo que no llegaron a gea.

Recorre los documentos PENDING o FAILED (con menos intentos que el maximo,
`PAZ_Y_SALVO_MAX_ATTEMPTS`) y los certifica. Reintentar no duplica: cada
documento manda siempre la misma `idempotency_key`, y gea devuelve el ya
emitido. Tambien termina las revocaciones que no se pudieron pedir a gea.

    manage.py certify_pending_paz_y_salvo [--case <uuid>] [--force]

Respaldo (cron cada pocos minutos): la certificacion normal corre en linea al
autorizar o reintentar; esto recoge lo que haya quedado PENDING o FAILED.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.project.case_manager import gea_client, paz_y_salvo
from apps.project.case_manager.models import \
    PazYSalvoDocumentModel

Status = PazYSalvoDocumentModel.Status


class Command(BaseCommand):
    help = 'Reintenta los paz y salvo PENDING/FAILED contra gea.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--case', help='Solo los documentos de este asunto (UUID).')
        parser.add_argument(
            '--force', action='store_true',
            help='Ignora el maximo de intentos.')

    def handle(self, *args, **options):
        if not gea_client.is_configured():
            self.stderr.write(
                'gea no esta configurado (GEA_CERT_API_BASE y '
                'SERVER_KEY): nada que hacer.')
            return

        documents = PazYSalvoDocumentModel.objects.all()
        if options['case']:
            documents = documents.filter(case_id=options['case'])

        pending = documents.filter(
            status__in=(Status.PENDING, Status.FAILED),
            case__deleted_at__isnull=True, case__client__deleted_at__isnull=True,
        )
        if not options['force']:
            pending = pending.filter(
                attempts__lt=settings.PAZ_Y_SALVO_MAX_ATTEMPTS)

        done = failed = 0
        for pk in list(pending.order_by('authorized_at')
                       .values_list('pk', flat=True)):
            document = paz_y_salvo.certify(pk, force=options['force'])
            if document.status == Status.CERTIFIED:
                done += 1
            else:
                failed += 1
                self.stderr.write(
                    f'{document.short_case_id} {document.pk}: '
                    f'{document.last_error}')

        revoked = 0
        stale = documents.filter(
            status=Status.REVOKED, gea_revoked=False,
        ).exclude(gea_document_id='')
        for pk in list(stale.values_list('pk', flat=True)):
            if paz_y_salvo.revoke_in_gea(pk).gea_revoked:
                revoked += 1

        self.stdout.write(
            f'Certificados: {done}. Fallidos: {failed}. '
            f'Revocaciones enviadas: {revoked}.')
