# Graph Report - pag_propensionesabogados  (2026-09-29)

## Corpus Check
- 298 files · ~100,554 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .mo 11, .po 11, .css 5)

## Summary
- 2542 nodes · 4871 edges · 197 communities (123 shown, 74 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 458 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `96877833`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- django_db
- CaseForm
- AttlasInsolvencyFormModel
- PQRSModel
- django_urls
- OtpModeTests
- auth_platform/api/urls.py
- Index Page
- uuid
- NoteFromGestorTests
- TimeStampedModel
- CaseModel
- AttlasInsolvencyCreditorsModel
- django_test
- insolvency_form/api/serializers.py
- ClientModel
- portal_otp.py
- Public case query portal (consultar_proceso.html)
- django_apps
- Command
- otp_login.py
- GestorRequiredMixin
- ClientViewSet
- PortfolioChartTests
- LadderRulesTests
- test_db_backend.py
- can_use_case_manager
- ImportPropDemoTests
- EmailShapeTests
- test_classification.py
- case_manager/views.py
- gestor.py
- make_user
- Mandate
- pedir_codigo
- InsolvencyFormWizardView
- FailuresAreSharedTests
- FinancialEducationModel
- faq/api/views.py
- AuthenticatedPortalTests
- reports.py
- PropensionesLoginView
- Account README
- account/forms.py
- Command
- LadderThroughThePortalTests
- django_contrib
- get_client_ip
- CaseFinanceModel
- OfficeFallbackTests
- WordReportTests
- settings.py
- ContactModel
- PazYSalvoAccessTests
- ThemeWiringTests
- test_honeypot.py
- ClientLookupTests
- WWWRedirectTests
- RateLimit
- NavbarAccountLinksTests
- core/admin.py
- core/views.py
- login_view.py
- Command
- AttlasInsolvencyAuthModel
- CaseFormMixin
- dynamic_flow.cjs
- AdminPagesRenderTests
- TablasTests
- PublicQueryTests
- AttemptLimitTests
- logging
- CaseListView
- PublicCardFieldsTests
- ClientDetailTests
- HasServerKey
- auth_platform/api/views.py
- verify_honeypot_value
- CheckHoneypotTests
- CaseFinanceQuerySet
- ClientToCasesTests
- account/views.py
- UserModelAdmin
- OwnershipTests
- django_utils_translation
- TidyTests
- CaseNoteModel
- DetailRowsTests
- VariosAsuntosTests
- AttlasLoginTests
- utils/admin.py
- vista
- RenderFieldTests
- SecondFactorIsNotSkippedTests
- ClientForm
- ClientCrudTests
- ConfirmacionPazYSalvoTests
- SessionFixationTests
- CodeLifetimeTests
- core/api/views.py
- CaseCrudTests
- GestorDashboardTests
- MaskedEmailTests
- AdminAccessTests
- CaseFinanceInline
- ForwardedHeaderTests
- FormResource
- GestorAccessTests
- templatetags/honeypot.py
- faq/migrations/0001_initial.py
- case_manager_extras.py
- SignatureCreateSerializer
- test_api_open_routes.py
- auth_platform/admin.py
- financial_education/api/views.py
- DynamicFlowTests
- .test_el_decorador_conserva_el_nombre_de_la_vista
- security.txt
- case_manager/api/urls.py
- AccessCodeEmailTests
- test_attempts.py
- Utils README
- Users README
- pag-propensiones
- TeamMemberModel
- CaseFinanceForm
- verify
- issue
- SendThrottleTests
- FinancialEducationModelSerializer
- CaseToggleSettlementView
- FinancialEducationListAPIView
- UserRegisterView
- manage.py
- faq/admin.py
- currency_format.py
- CaseNoteQuerySet
- CaseQuerySet
- .test_vaciar_la_sesion_no_reinicia_la_escalera
- rest_framework_decorators

## God Nodes (most connected - your core abstractions)
1. `CaseModel` - 82 edges
2. `ClientModel` - 77 edges
3. `AttlasInsolvencyFormModel` - 56 edges
4. `CaseFinanceModel` - 54 edges
5. `make_user()` - 44 edges
6. `TimeStampedModel` - 40 edges
7. `Service` - 36 edges
8. `ClientLookupTests` - 35 edges
9. `CaseForm` - 33 edges
10. `Stage` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Signature widget template` --conceptually_related_to--> `Gestor form field partial`  [AMBIGUOUS]
  apps/project/api/platform/insolvency_form/templates/signature/signature_widget.html → apps/project/api/platform/case_manager/templates/case_manager/gestor/partials/field.html
- `Two-factor login wizard (auth/otp/token/backup)` --references--> `django-two-factor-auth`  [EXTRACTED]
  apps/project/common/account/README.md → requirements.txt
- `ConctactModelSerializer` --uses--> `ContactModel`  [INFERRED]
  apps/common/core/api/serializers.py → apps/common/core/models.py
- `ContactCreateAPIView` --uses--> `ContactModel`  [INFERRED]
  apps/common/core/api/views.py → apps/common/core/models.py
- `ContactForm` --uses--> `ContactModel`  [INFERRED]
  apps/common/core/forms.py → apps/common/core/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Account login template inheritance chain** — apps_project_common_account_templates_two_factor_core_login, apps_project_common_account_templates_two_factor_base, apps_project_common_account_templates_account_layout_account, apps_project_common_account_templates_two_factor_wizard_actions, apps_project_common_account_templates_two_factor_wizard_forms [EXTRACTED 1.00]
- **Public case portal composition** — apps_project_api_platform_case_manager_templates_case_manager_consultar_proceso, apps_project_api_platform_case_manager_templates_case_manager_partials_contact_card, apps_project_api_platform_case_manager_templates_case_manager_partials_inactive_notice, apps_project_api_platform_case_manager_templates_case_manager_partials_legal_notice, apps_project_api_platform_case_manager_templates_case_manager_partials_client_notes, apps_project_api_platform_case_manager_templates_case_manager_partials_field [EXTRACTED 1.00]
- **Team member display** — apps_common_core_templates_pages_sections_13_team_section, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_sections_13_team_section_team_member_context [EXTRACTED 1.00]
- **Template inheritance chain** — apps_common_core_templates_raw, apps_common_core_templates_base, apps_common_core_templates_pages_index, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_documents, apps_common_core_templates_pages_privacy_policy, apps_common_core_templates_pages_terms_and_conditions [EXTRACTED 1.00]
- **Case note authoring, portal display and email notification** — apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_notes, apps_project_api_platform_case_manager_templates_case_manager_partials_client_notes, apps_project_api_platform_case_manager_templates_case_manager_email_case_note [INFERRED 0.85]
- **Visitor contact flow** — apps_common_core_templates_pages_sections_12_contact_section, apps_common_core_templates_pages_sections_12_contact_section_contact_form, apps_common_core_templates_email_contact_email_template, apps_common_core_templates_partials_toasts [INFERRED 0.85]
- **Gestor financial totals reporting** — apps_project_api_platform_case_manager_templates_case_manager_gestor_dashboard, apps_project_api_platform_case_manager_templates_case_manager_gestor_client_detail, apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_stat, apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_portfolio [INFERRED 0.85]
- **Login brute-force defense (axes + OTP + shared counter)** — apps_project_common_account_readme_email_otp_login, apps_project_common_account_readme_shared_attempt_counter, requirements_django_axes [INFERRED 0.85]

## Communities (197 total, 74 thin omitted)

### Community 0 - "django_db"
Cohesion: 0.03
Nodes (34): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+26 more)

### Community 1 - "CaseForm"
Cohesion: 0.17
Nodes (4): CaseForm, Alta y edicion de un asunto. Sigue servicio -> área/subnivel -> proceso. Los…, El arbol que el navegador necesita para repintar los desplegables. Va entero y…, ClassificationTests

### Community 2 - "AttlasInsolvencyFormModel"
Cohesion: 0.07
Nodes (43): action, decode_base64_image(), AttlasInsolvencyFormAdmin, ImportExportActionModelAdmin, register, _age(), _barcode_bytes(), _build_assets() (+35 more)

### Community 3 - "PQRSModel"
Cohesion: 0.18
Nodes (9): Meta, PQRSModelSerializer, ModelSerializer, IDTypeChoices, Meta, PQRSModel, RequestTypeChoicesEN, RequestTypeChoicesES (+1 more)

### Community 4 - "django_urls"
Cohesion: 0.09
Nodes (34): Court, instances_for(), PoliceInstance, Procedure, El vocabulario del gestor: servicios, tramites, areas, subtipos y etapas. Todo…, Instancia de la querella policiva., El avance publico del caso: la barra de progreso de la pantalla aprobada. Es…, Servicio contratado. El ``<select id="as">`` de la pantalla aprobada. (+26 more)

### Community 5 - "OtpModeTests"
Cohesion: 0.07
Nodes (18): LoginPageTests, make_user(), OfferAfterFailuresTests, OtpModeTests, TestCase, La segunda puerta: el codigo de seis cifras al correo., Quien pulsa «entrar con un codigo» puede no haber escrito su usuario todavia,…, Las imagenes remotas las bloquean casi todos los clientes de correo: un… (+10 more)

### Community 6 - "auth_platform/api/urls.py"
Cohesion: 0.18
Nodes (12): APIView, AttlasInsolvencyAuthSerializer, ClientLookupVerifySerializer, ClientResponseSerializer, Forma la respuesta de búsqueda leyendo los campos cifrados del modelo y…, AttlasInsolvencyAuthConsultantsRegisterAPIView, AttlasInsolvencyAuthLoginAPIView, AttlasInsolvencyAuthRegisterAPIView (+4 more)

### Community 7 - "Index Page"
Cohesion: 0.08
Nodes (41): Base Template, Contact Email Template, Documents Page, Required documents (power of attorney, service contract), Index Page, Privacy Policy Page, Corporate Social Responsibility Section, Stats Section (+33 more)

### Community 8 - "uuid"
Cohesion: 0.06
Nodes (25): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+17 more)

### Community 9 - "NoteFromGestorTests"
Cohesion: 0.12
Nodes (7): NoteFromGestorTests, Anadir una nota desde la ficha del asunto., El expediente tiene que decir quien dijo que., Las dos mitades hablan del mismo dato: lo que el despacho escribe aqui es lo…, Un correo diciendo que el asunto avanzo cuando no ha avanzado gasta la…, El despacho decide cuando avisar: hay correcciones de etapa que no son…, Lo que no se puede perder es la novedad; el correo es el aviso.

### Community 10 - "TimeStampedModel"
Cohesion: 0.09
Nodes (31): Abstract model providing timestamp fields (created and updated) and additional…, TimeStampedModel, AssetInline, CreditorsInline, GeneralInline, IncomeInline, IncomeOtherInline, JudicialProcessInline (+23 more)

### Community 11 - "CaseModel"
Cohesion: 0.06
Nodes (16): _as_int(), Command, BaseCommand, Trae a la base los expedientes que estaban en `localStorage.propDemo`. Por que…, Un importe del JSON como entero no negativo. El navegador guardaba lo que…, CaseModel, Un asunto del despacho: el expediente que ve el cliente. Los tres bloques de…, Las filas del bloque de detalle: lo que hay, no lo que tocaria. Es… (+8 more)

### Community 12 - "AttlasInsolvencyCreditorsModel"
Cohesion: 0.09
Nodes (23): InsolvencyFormConfig, AppConfig, ChatGPTAPI, creditor_nit_contact_prompt(), enrich_creditor(), _find_in_local_db(), _find_via_chatgpt(), _normalize() (+15 more)

### Community 13 - "django_test"
Cohesion: 0.08
Nodes (12): El tema claro/oscuro, que vive en un solo atributo del `<html>`. Lo que se…, Deja los catalogos de traduccion como tienen que quedar tras `makemessages`.…, El acceso: las dos puertas, y que ninguna abra lo que la otra cierra. Lo que se…, Que la puerta del codigo **no** es una puerta trasera al segundo factor. Es la…, datetime, django_core_management_base, django_otp_plugins_otp_totp_models, django_test (+4 more)

### Community 14 - "insolvency_form/api/serializers.py"
Cohesion: 0.14
Nodes (24): AssetSerializer, CreditorSerializer, IncomeOtherSerializer, IncomeSerializer, JudicialProcessSerializer, Meta, atomic, ResourceItemSerializer (+16 more)

### Community 15 - "ClientModel"
Cohesion: 0.13
Nodes (10): GestorDashboardView, TemplateView, El panel economico y el gerencial. Es lo que en la pantalla anterior calculaba…, Command, atomic, BaseCommand, Crea el grupo del gestor con los permisos que necesita. Se ejecuta una vez por…, ClientModel (+2 more)

### Community 16 - "portal_otp.py"
Cohesion: 0.10
Nodes (25): can_send(), clear(), _cycle_expired(), issue(), next_send_allowed_at(), office_recipients(), pending_client_pk(), El codigo de seis cifras que acredita al titular del proceso. Por que se cambio… (+17 more)

### Community 17 - "Public case query portal (consultar_proceso.html)"
Cohesion: 0.11
Nodes (30): Public case query portal (consultar_proceso.html), Email access code verification flow, case_manager_extras templatetags (grouped_identification), Access code email template, Case note email template, Gestor base layout, Gestor case form, Gestor case list (+22 more)

### Community 18 - "django_apps"
Cohesion: 0.06
Nodes (21): CoreConfig, AppConfig, AppConfig, UtilsConfig, FaqConfig, AppConfig, FinancialEducationConfig, AppConfig (+13 more)

### Community 19 - "Command"
Cohesion: 0.11
Nodes (6): Command, Path, Convert snake_case app name to PascalCase config class name., Generates a Django app with a full REST API scaffold. Usage: python manage.py…, django_core_management_commands_startapp, StartAppCommand

### Community 20 - "otp_login.py"
Cohesion: 0.15
Nodes (12): Un cubo de intentos por ventana de tiempo, para formularios publicos. Que…, contact_email(), entered_identifier(), has_live_code(), El codigo de seis cifras que llega al correo, y lo que lo sostiene. Para que…, A quien escribir si llega un codigo que no se pidio., Se queda con lo que se tecleo, sin emitir codigo. Hace falta para el boton…, Lo ultimo que se tecleo en la pantalla del codigo. (+4 more)

### Community 21 - "GestorRequiredMixin"
Cohesion: 0.09
Nodes (22): GestorRequiredMixin, LoginRequiredMixin, UserPassesTestMixin, Exige sesion iniciada y pertenencia al grupo del gestor. **Responde 404 y no…, CaseCreateView, CaseNoteCreateView, CaseReportView, CaseUpdateView (+14 more)

### Community 22 - "ClientViewSet"
Cohesion: 0.11
Nodes (14): BearerTokenAuthentication, LookupOrPlatformTokenAuthentication, ClientCreateSerializer, ClientDataSerializer, ClientUpdateSerializer, Meta, ClientViewSet, extend_schema (+6 more)

### Community 23 - "PortfolioChartTests"
Cohesion: 0.06
Nodes (19): DashboardTotalsTests, DebtorsAndExpectationsTests, ManagerExposeLasPreguntasTests, PortfolioChartTests, TestCase, `CaseFinanceQuerySet.totals()`: las cifras de cabecera. El escenario es el…, `show_in_dashboard` es del despacho, y se respeta en los totales., Los totales miran casos vivos, igual que el portal. (+11 more)

### Community 24 - "LadderRulesTests"
Cohesion: 0.14
Nodes (7): LadderRulesTests, No se queda bloqueado para siempre, y tampoco reanuda donde lo dejo: empieza de…, Acertar demuestra que el buzon registrado es suyo y que lo esta leyendo, que es…, Gastarla con una cedula no puede cerrarle el portal a otra persona., Esta en la base, no en la sesion ni en la cache. Si estuviera en la sesion,…, La escalera, mirada directamente y sin pasar por la pantalla., Apunta `veces` envios, el ultimo `hace` tiempo.

### Community 25 - "test_db_backend.py"
Cohesion: 0.10
Nodes (19): engine_for(), Qué motor de base de datos se instala de verdad, según el que se declara. El…, El motor a instalar para el que se declaró en el `.env`. Cualquier otro…, DatabaseFeatures, DatabaseWrapper, El backend de MySQL de siempre, con los UUID guardados como estaban. El…, Como antes de Django 5.0: los UUID van en ``char(32)``, en hex., EngineForTests (+11 more)

### Community 26 - "can_use_case_manager"
Cohesion: 0.12
Nodes (12): can_use_case_manager(), Si `user` puede usar el gestor. Es una funcion y no solo un mixin porque la…, CaseManagerAdminMixin, La misma puerta que `GestorRequiredMixin`, para el admin. El admin pregunta por…, `obj` lleva valor por defecto porque este mixin lo comparten un `ModelAdmin` y…, gestor_access(), Lo que la cabecera del sitio necesita saber del gestor. Por que un procesador…, Si quien mira puede entrar al gestor. (+4 more)

### Community 27 - "ImportPropDemoTests"
Cohesion: 0.11
Nodes (8): ImportPropDemoTests, TestCase, Inventar una etapa mas avanzada le diria al cliente que su asunto va por donde…, El campo del navegador no validaba nada: guardaba cadenas., El grupo del gestor y sus permisos., No hay papelera --esta fuera del alcance-- y borrar un cliente se lleva por…, SetupGroupTests, write()

### Community 28 - "EmailShapeTests"
Cohesion: 0.11
Nodes (12): EmailShapeTests, override_settings, Como sale el correo por dentro. Es lo que nadie mira hasta que falla, y cuando…, Del `DEFAULT_FROM_EMAIL`, que es el que de verdad esta autorizado a enviar por…, Quien firma el envio no es quien atiende la respuesta., Un correo solo-HTML puntua peor en los filtros de spam, y hay quien lee el…, Enlazadas se bloquean: casi todos los clientes de correo no cargan imagenes…, Sin los `<>` hay clientes que no resuelven el `cid:` y ensenan el cuadro roto… (+4 more)

### Community 29 - "test_classification.py"
Cohesion: 0.08
Nodes (22): alphabetical(), Area, is_other(), Los valores en orden alfabetico, con los «Otro…» al final. Un desplegable largo…, Los subtipos que cuelgan del servicio, y nada mas. `area` ya no decide nada…, El tercer nivel, si esa rama tiene uno. Devuelve vacio cuando no lo tiene --un…, Area o tipo de caso. El ``<select id="aa">``., second_subtypes_for() (+14 more)

### Community 30 - "case_manager/views.py"
Cohesion: 0.15
Nodes (15): PublicAccessCodeForm, PublicCaseQueryForm, El primer paso: solo la identificacion. Antes pedia tambien una «clave de…, Se queda solo con los digitos. Quien escribe su cedula con puntos esta…, El cliente de esa identificacion, exista o no. **Tambien devuelve a los que no…, El segundo paso: las seis cifras que llegaron al correo., authorized_client_pk(), PazYSalvoView (+7 more)

### Community 31 - "gestor.py"
Cohesion: 0.09
Nodes (28): La trampa para robots del formulario de contacto. Que hace -------- Se pinta un…, attach_inline_images(), Path, Lo comun a los correos que manda el sitio: que las imagenes se vean. Casi todos…, El fichero en disco de un estatico, mirando donde de verdad esta. Primero en…, Mete las imagenes en el mensaje y las marca como `inline`. `Content-ID` es lo…, static_source(), Verification emails for the public calculator. (+20 more)

### Community 32 - "make_user"
Cohesion: 0.14
Nodes (5): login_as(), make_user(), Deja la sesion abierta como esa cuenta, sin pasar por `authenticate()`.…, 404 y no 403. Un 403 confirma que en esa direccion hay algo; un 404 no dice…, Un informe con todo el dinero del despacho servido a quien pase seria peor que…

### Community 33 - "Mandate"
Cohesion: 0.22
Nodes (8): Mandate, Modalidad del contrato. Es el campo del que cuelga todo el dinero. Cual de los…, BalanceTests, make_case(), Los calculos financieros del gestor. Son la actividad que la cotizacion llama…, Un abono mayor que lo pactado es un error de captura o un anticipo. En ninguno…, Valor fijo cerrado: esta pactado y no se ha cobrado nada., `CaseFinanceModel.balance`: lo que falta por cobrar.

### Community 34 - "pedir_codigo"
Cohesion: 0.11
Nodes (8): El primer paso no identifica a nadie: solo manda un correo. Si abriera sesion,…, pedir_codigo(), Tapado por el centro: el cliente tiene que poder reconocer su buzon --si no, no…, La sesion recuerda **de quien** es el codigo. Sin eso, pedirlo para la cedula…, No se queda fuera. Antes se le cerraba el portal sin que hubiera nada que…, Prometer un codigo que no va a llegar deja a alguien mirando un campo vacio sin…, El primer paso: la cedula. Devuelve la respuesta., El primer paso no ensena expediente: manda un codigo y espera. Es el cambio…

### Community 35 - "InsolvencyFormWizardView"
Cohesion: 0.11
Nodes (13): InsolvencyFormWizardView, atomic, CreateAPIView, extend_schema, Si estamos en el paso 4 y llegó debtor_cessation_report, lo enviamos a…, Si la URL trae <id>, usamos el comportamiento normal (retrieve/update sobre ese…, GET /api/v1/insolvency-form/signature/<id>/ PATCH /api/v1/insolvency-…, POST /api/platform/signature/ { "signature": "<base64string>" } (+5 more)

### Community 36 - "FailuresAreSharedTests"
Cohesion: 0.29
Nodes (5): FailuresAreSharedTests, override_settings, El freno se aplica **antes** de mirar el codigo. Al reves se apuntarian los…, El control de la prueba anterior. Sin el, aquella pasaria igual si el codigo…, Un codigo equivocado cuenta igual que una contrasena equivocada.

### Community 37 - "FinancialEducationModel"
Cohesion: 0.28
Nodes (4): FinancialEducationModelAdmin, register, FinancialEducationModel, Meta

### Community 38 - "faq/api/views.py"
Cohesion: 0.22
Nodes (11): MainFAQModelSerializer, Meta, OtherFAQModelSerializer, ModelSerializer, MainFAQListAPIView, OtherFAQListAPIView, extend_schema, ListAPIView (+3 more)

### Community 40 - "reports.py"
Cohesion: 0.16
Nodes (21): client_report(), crm_report(), _descarga(), _dinero(), _documento(), _fila_de_asunto(), _pares(), _pie() (+13 more)

### Community 41 - "PropensionesLoginView"
Cohesion: 0.07
Nodes (23): handler400(), handler403(), handler404(), handler500(), HttpRequestAttakView, View, set_language(), PropensionesLoginView (+15 more)

### Community 42 - "Account README"
Cohesion: 0.13
Nodes (13): Account README, /admin/login/ redirected to account login, Email one-time code login, No account enumeration, Shared failed-attempt counter (django-axes), Two-factor login wizard (auth/otp/token/backup), Username-or-email auth backend, login_otp.html (OTP email) (+5 more)

### Community 43 - "account/forms.py"
Cohesion: 0.21
Nodes (13): ContactForm, Meta, Meta, UserRegisterForm, UserUpdateProfile, UnicodeLastNameValidator, UnicodeNameValidator, UnicodeUsernameValidator (+5 more)

### Community 44 - "Command"
Cohesion: 0.13
Nodes (12): Command, BaseCommand, Delete migration files. Args: deleted_files (list): List of deleted files.…, Get list of apps to skip migration deletion. Args: app_name (str, optional):…, Delete all migration files and folders except __init__.py, and custom apps., Print deletion results. Args: deleted_folders (List[tuple]): List of deleted…, Print deleted items. Args: items (List[tuple]): List of items to print. action…, Print exceptions. Args: exceptions (List[str]): List of exceptions to print. (+4 more)

### Community 45 - "LadderThroughThePortalTests"
Cohesion: 0.16
Nodes (7): LadderThroughThePortalTests, La misma escalera, pero pulsando «reenviar» en la pantalla., Mueve hacia atras el ultimo envio, que es lo mismo que esperar., La hora y no los segundos: el cliente puede dejar esta pantalla abierta un…, El ciclo completo, tal y como se pidio., Bloquear el **envio** no es invalidar lo enviado: quien recibio el quinto…, Volver al primer paso y teclear la cedula otra vez es el camino obvio para…

### Community 46 - "django_contrib"
Cohesion: 0.11
Nodes (12): AbstractUser, Meta, UserLoginAttemptModel, Meta, UserAdminForm, Meta, UserModel, django_contrib (+4 more)

### Community 47 - "get_client_ip"
Cohesion: 0.06
Nodes (33): Comprueba la clave del proxy en Django y DRF sin propagar errores., server_key_is_valid(), get_client_ip(), La IP del cliente, vacia si no se puede saber. Nunca lanza: esto se llama desde…, ClientIPProxyLoginTests, ClientIPProxyTests, APITestCase, override_settings (+25 more)

### Community 48 - "CaseFinanceModel"
Cohesion: 0.09
Nodes (14): El formulario del portal publico de consulta. Lo que aqui se valida lo validaba…, CaseFinanceModel, Que cada modalidad solo traiga las cifras que le corresponden., El dinero de un caso: que se pacto, que entro y que falta. Va aparte de…, Si esta fila es una **expectativa** y no una deuda. La regla que mas facil se…, Lo cerrado con el cliente. Una expectativa no esta cerrada., Abonos de modalidades de pago y cuotas litis de valor fijo., Lo que falta por cobrar. **No se guarda**: se calcula. Nunca es negativo: un… (+6 more)

### Community 49 - "OfficeFallbackTests"
Cohesion: 0.15
Nodes (9): OfficeFallbackTests, override_settings, El cliente sin correo registrado: su codigo va al despacho. Es el caso normal,…, A la oficina le llegarian seis cifras sueltas y no sabria a quien darselas. El…, Sin el recordatorio, este mismo correo vuelve a llegar la proxima vez que el…, El aviso de «nadie de Propensiones te pedira este codigo» es para el titular.…, Lo que cambia es a donde va, no lo que hace: quien lo teclea entra., Si no, hostigar una cedula sin correo llenaria el buzon de la propia oficina,… (+1 more)

### Community 50 - "WordReportTests"
Cohesion: 0.16
Nodes (7): Los dos informes descargables., La pantalla anterior bajaba un `.doc` que por dentro era HTML: Word avisa de…, Un informe que el despacho manda a un cliente no puede decir «$8000000»: se lee…, «No incluir en panel economico» tiene que valer tambien en el informe; si no,…, Todo el texto de un `.docx`, para poder buscar dentro. Un `.docx` es un zip con…, texto_del_docx(), WordReportTests

### Community 51 - "settings.py"
Cohesion: 0.13
Nodes (10): Any, ASGI config for app_core project. It exposes the ASGI callable as a module-…, WSGI config for app_core project. It exposes the WSGI callable as a module-…, custom_processors(), django_core_asgi, django_core_wsgi, dotenv, import_export_formats_base_formats (+2 more)

### Community 52 - "ContactModel"
Cohesion: 0.22
Nodes (6): ContactModel, PageChoices, StatesChoices, IndexTemplateView, FormView, method_decorator

### Community 53 - "PazYSalvoAccessTests"
Cohesion: 0.18
Nodes (6): PazYSalvoAccessTests, Se guarda sin puntos porque asi se busca; se imprime con ellos., Regla que venia escrita en el JavaScript original: el paz y salvo **no** lleva…, Saber la direccion no basta. Es lo que antes si bastaba: el documento lo armaba…, El paz y salvo dice que no se debe nada: no lo decide el cliente., Identificarse con la clave propia no abre el expediente ajeno, ni aunque ese…

### Community 54 - "ThemeWiringTests"
Cohesion: 0.12
Nodes (9): TestCase, `text-bg-light` ademas fija `color: #000`. Cambiarle solo el fondo lo deja…, Que el tema llega a las paginas del sitio, no solo a una., El trozo que lo aplica va en linea en el `<head>`. Si se moviera a `theme.js`…, Las dos declaran las mismas variables y ganan por orden. Al reves, la paleta…, En navegacion privada o con las cookies de terceros desactivadas,…, Las clases de Bootstrap que **no** cambian solas con el modo oscuro. Bootstrap…, ThemeWiringTests (+1 more)

### Community 55 - "test_honeypot.py"
Cohesion: 0.20
Nodes (6): honeypot_exempt(), Marca una vista para que no se le compruebe la trampa., ExemptTests, SimpleTestCase, La trampa para robots. Protege el unico formulario publico que escribe en la…, django_template

### Community 56 - "ClientLookupTests"
Cohesion: 0.11
Nodes (4): verify_token(), ClientLookupTests, APITestCase, override_settings

### Community 57 - "WWWRedirectTests"
Cohesion: 0.14
Nodes (10): HostNoPermitidoTests, OrdenDelMiddlewareTests, override_settings, SimpleTestCase, TestCase, Los nombres con los que se puede pedir el sitio. Hay un CNAME de `www` en la…, Un enlace compartido al `www` tiene que llevar a donde apunta, no a la portada:…, `mail.`, `webmail.`, `cpanel.`… apuntan a la misma IP pero no son de esta… (+2 more)

### Community 58 - "RateLimit"
Cohesion: 0.23
Nodes (6): RateLimit, Cuantos intentos caben, y de quien. Args: name: identifica al formulario. Dos…, RateLimitTests, El cubo de intentos, por separado., Una llave de cache es un sitio donde nadie espera encontrar datos personales:…, Falla **cerrado**. Aqui el limite no evita una molestia pasajera: es lo unico…

### Community 59 - "NavbarAccountLinksTests"
Cohesion: 0.06
Nodes (21): make_user(), NavbarAccountLinksTests, TestCase, Los enlaces de cuenta en la cabecera. Van dentro del menu «Plataformas»,…, El registro del sitio es publico, asi que cualquiera puede llegar aqui con una…, La cabecera es un `include`, asi que esto deberia darse solo. Se comprueba…, EmailOrUsernameModelBackend, Entrar con el nombre de usuario **o** con el correo. La pantalla de acceso… (+13 more)

### Community 60 - "core/admin.py"
Cohesion: 0.36
Nodes (5): ContactModelAdmin, ModalBannerModelAdmin, display, register, TeamMemberModelAdmin

### Community 61 - "core/views.py"
Cohesion: 0.21
Nodes (12): CalendarView, DocumentsView, PrivacyPolicyView, DetailView, TemplateView, security_txt_view(), TeamMemberDetailView, TermsAndConditionsView (+4 more)

### Community 62 - "login_view.py"
Cohesion: 0.09
Nodes (18): _credentials(), is_locked_out(), note_failure(), Un solo contador de intentos fallidos de acceso, para las dos puertas. El…, Las credenciales como las espera `axes`, normalizadas. Solo el nombre: la…, Apunta un intento fallido que no paso por `authenticate()`. Nunca lanza: esto…, Si esta conexion ya gasto sus intentos. Se le pregunta a `axes` en vez de…, forget_resolved_steps() (+10 more)

### Community 63 - "Command"
Cohesion: 0.23
Nodes (5): Command, BaseCommand, Devuelve el catalogo arreglado y cuantos arreglos hizo., Deja vacia la traduccion de las entradas marcadas como dudosas. Es lo que evita…, Entradas con `msgstr` vacio de verdad, sin contar la cabecera. El «de verdad»…

### Community 64 - "AttlasInsolvencyAuthModel"
Cohesion: 0.11
Nodes (12): hash_value(), AttlasInsolvencyAuthConsultantsRegisterSerializer, AttlasInsolvencyAuthRegisterSerializer, Meta, RegisterSerializer, AttlasInsolvencyAuthConsultantsModel, AttlasInsolvencyAuthModel, Meta (+4 more)

### Community 65 - "CaseFormMixin"
Cohesion: 0.22
Nodes (6): CaseNoteForm, Una novedad del expediente, y si se le avisa al cliente. La casilla de aviso…, CaseFormMixin, El asunto y su dinero se guardan juntos o no se guarda ninguno. Son dos…, Los errores que no son de un campo, como aviso flotante. Un error de campo se…, Avisa al cliente de que su asunto avanzo, si procede. Tres condiciones, y las…

### Community 66 - "dynamic_flow.cjs"
Cohesion: 0.13
Nodes (12): assert, edit, fresh, fs, { JSDOM }, path, reference, apps_project_api_platform_case_manager_tests_fixtures_reference_flow (+4 more)

### Community 67 - "AdminPagesRenderTests"
Cohesion: 0.22
Nodes (3): AdminPagesRenderTests, Que las paginas del gestor en el admin **abran de verdad**. Las pruebas de…, Es la pagina que llevaba el inline del dinero y reventaba.

### Community 68 - "TablasTests"
Cohesion: 0.14
Nodes (6): Los listados largos, ahora que los pagina el navegador. Antes esto probaba la…, Sin esto, DataTables ordenaria veinticinco filas y diria que eso es el orden de…, Son botones. Ordenar por una columna de botones no significa nada, y el `<th>`…, `annotate` agrupa, y una consulta agrupada deja de estar ordenada aunque el…, Un enlace guardado con `?q=` no se rompe por quitar el buscador., TablasTests

### Community 69 - "PublicQueryTests"
Cohesion: 0.11
Nodes (11): Las dos mitades hablan del mismo dato: lo que el despacho enciende aqui es lo…, identificarse(), PublicQueryTests, Se quema al usarlo: quien vea el correo por encima del hombro --o lo recupere…, Con el codigo al correo, decir «no hay nada con ese numero» ya no entrega una…, Si se le dijera «no encontramos nada» se pondria a probar cedulas creyendo que…, Decirle que llame no es abrirle el expediente: sigue sin vigencia., Un `GET` no puede traer datos de nadie. Esta es la prueba que sostiene el… (+3 more)

### Community 70 - "AttemptLimitTests"
Cohesion: 0.18
Nodes (6): AttemptLimitTests, El limite de intentos por IP. Es lo que frena a quien recorre cedulas para…, Cedulas que no son de nadie, que es el tanteo que esto frena., Un bloqueo sin `blocked_until` no bloquea a nadie: el middleware filtra por…, Si no, tantear seis cifras saldria gratis mientras que equivocarse de cedula…, Dos despistes y un acierto no dejan a nadie a un fallo del cierre.

### Community 71 - "logging"
Cohesion: 0.18
Nodes (12): client_ip(), is_lockout_exempt(), Enganches de `django-axes`, para que el freno al tanteo no sea un autobloqueo.…, IP para `AXES_CLIENT_IP_CALLABLE`., Si esta peticion de acceso nunca debe quedar bloqueada. Solo mira la lista…, is_whitelisted(), De que direccion viene una peticion, contestado en un solo sitio. Por que esto…, Si esa direccion esta en la lista blanca del proyecto. `WhiteListedIPModel` es… (+4 more)

### Community 72 - "CaseListView"
Cohesion: 0.17
Nodes (7): CaseListView, _client_or_none(), ClientListView, Los clientes del despacho, con busqueda por nombre o cedula. La busqueda es un…, Los asuntos del despacho, todos o los de un cliente. `?cliente=<uuid>` acota la…, El cliente de un `?cliente=<uuid>` de la URL, o `None`. Lo que llega en la URL…, ListView

### Community 73 - "PublicCardFieldsTests"
Cohesion: 0.19
Nodes (7): PublicCardFieldsTests, Los datos de la tarjeta, que son los del diseno aprobado. La etapa y el…, El asunto judicial la guarda en `instance` y la querella policiva en…, «Cuota litis» a secas no le dice a nadie cuanto va a pagar., El bloque se rellena despues de dar de alta el asunto, y entre una cosa y otra…, La modalidad si sale --esta en el diseno aprobado-- pero las cifras no: ni lo…, Subirla arriba sin quitarla de abajo la habria dejado dos veces en la misma…

### Community 74 - "ClientDetailTests"
Cohesion: 0.18
Nodes (6): BaseReportes, ClientDetailTests, TestCase, En la pantalla anterior un cliente **era** un asunto. Traducirla literalmente…, `totals()` sobre sus asuntos. Otro cliente con deuda no puede sumar aqui, que…, La ficha individual, en pantalla.

### Community 75 - "HasServerKey"
Cohesion: 0.12
Nodes (11): HasServerKey, Restringe la API de Attlas al servidor proxy mediante una clave compartida., check_attlas_server_key(), register, HasServerKeyTests, APITestCase, override_settings, TestCase (+3 more)

### Community 76 - "auth_platform/api/views.py"
Cohesion: 0.16
Nodes (17): codes_match(), generate_code(), hash_code(), Códigos de un solo uso compartidos por los portales., Seis cifras, del generador criptografico y no de `random`., El codigo tal y como se guarda: HMAC-SHA256 con la clave del proyecto. Con HMAC…, Compara el HMAC del código en tiempo constante., ClientSearchSerializer (+9 more)

### Community 77 - "verify_honeypot_value"
Cohesion: 0.17
Nodes (11): decorate(), inner(), honeypot_equals(), honeypot_error(), El comprobador por defecto: el campo tiene que llegar **vacio**.…, La respuesta por defecto cuando la trampa se dispara., Comprueba la trampa en un `POST`. Devuelve la respuesta de error, o `None`.…, verify_honeypot_value() (+3 more)

### Community 78 - "CheckHoneypotTests"
Cohesion: 0.15
Nodes (7): CheckHoneypotTests, El decorador, que es lo que protege la vista de contacto., Una persona no rellena un campo que no ve., Un robot rellena todo lo que encuentra., Quitar el campo antes de enviar tampoco vale. Es mas facil que rellenarlo, asi…, La trampa es del envio; pedir la pagina no manda ningun campo., A quien la dispara no se le cuenta como no dispararla.

### Community 79 - "CaseFinanceQuerySet"
Cohesion: 0.21
Nodes (7): CaseFinanceQuerySet, Las preguntas del panel economico y del panel gerencial. Cada una vive aqui y…, Los casos que el despacho decidio incluir en el panel economico., Quien debe dinero, hoy. Son dos cosas sumadas, y es la parte que mas se…, Lo que se espera ganar si los pleitos salen: `Cuota litis` sobre 0 %. No es…, Las cifras de cabecera del panel gerencial, en una sola consulta. Reproduce…, Lo mismo, repartido por area, de mas a menos. Es la «Distribucion por area /…

### Community 80 - "ClientToCasesTests"
Cohesion: 0.17
Nodes (4): ClientToCasesTests, Ir de un cliente a sus asuntos. Sin esto hay que salir al otro listado y…, Un enlace viejo o mal copiado ensena la lista entera, no un 500., El filtro sobrevive a la busqueda. Sin esto, buscar dentro de los asuntos de…

### Community 81 - "account/views.py"
Cohesion: 0.17
Nodes (5): Las rutas de la cuenta. Las rutas del segundo factor no estan aqui sino en…, View, UserLogoutView, django_shortcuts, django_views_generic_edit

### Community 82 - "UserModelAdmin"
Cohesion: 0.23
Nodes (4): ImportExportActionModelAdmin, register, UserModelAdmin, UserAdmin

### Community 83 - "OwnershipTests"
Cohesion: 0.19
Nodes (3): OwnershipTests, APITestCase, override_settings

### Community 84 - "django_utils_translation"
Cohesion: 0.10
Nodes (15): EncryptedPermissionsMixin, LoginGroupRequiredMixin, LoginRequiredMixin, UserPassesTestMixin, KeyForm, DetectSuspiciousRequestMiddleware, RedirectWWWMiddleware, IPBlockedModel (+7 more)

### Community 85 - "TidyTests"
Cohesion: 0.24
Nodes (4): ConteoTests, TestCase, El recuento del final, que es la unica senal de cuanto queda. Una traduccion…, TidyTests

### Community 86 - "CaseNoteModel"
Cohesion: 0.07
Nodes (20): NoteKind, De que va una nota del expediente. No es decoracion: decide el color y el icono…, CaseNoteModel, Meta, Una novedad del asunto, escrita para el cliente o para el despacho. Es lo que…, El color y el icono con que se pinta, segun el tipo., Si la nota le pide algo al cliente. Solo `DOCUMENT`. Sirve para que el portal…, EmailNotSentTests (+12 more)

### Community 87 - "DetailRowsTests"
Cohesion: 0.27
Nodes (4): DetailRowsTests, El bloque de detalle de la ficha publica. Colgaba del tipo de tramite, y los…, Los tres bloques se recorren enteros, pero un asunto no llena mas de uno: lo…, La prueba de arriba mira el modelo; esta mira lo que el cliente lee.

### Community 88 - "VariosAsuntosTests"
Cohesion: 0.24
Nodes (4): Un cliente con mas de un asunto los ve **todos**. Antes la vista hacia…, Lo que hace util verlos juntos: van por sitios distintos., El permiso es **por asunto**, no por cliente: se puede estar a paz y salvo de…, VariosAsuntosTests

### Community 89 - "AttlasLoginTests"
Cohesion: 0.17
Nodes (4): generate_token(), AttlasLoginTests, APITestCase, override_settings

### Community 90 - "utils/admin.py"
Cohesion: 0.24
Nodes (7): GeneralAdminModel, IPBlockedModelAdmin, ImportExportActionModelAdmin, register, WhiteListedIPModelAdmin, django_utils_safestring, import_export_admin

### Community 91 - "vista"
Cohesion: 0.33
Nodes (5): check_honeypot(), Decora una vista para que compruebe la trampa antes de atender el `POST`. Se…, vista(), DecoratorFormsTests, Las tres formas de escribir el decorador. Se prueban porque la vista de…

### Community 92 - "RenderFieldTests"
Cohesion: 0.27
Nodes (5): La etiqueta de plantilla, que es lo que pinta el campo en el formulario. Se…, Si saliera relleno, cada envio legitimo dispararia la trampa., Un robot que mire los estilos descartaria un campo con `display:none` o…, Las dos mitades tienen que hablar del mismo campo. Es la prueba que sostiene el…, RenderFieldTests

### Community 93 - "SecondFactorIsNotSkippedTests"
Cohesion: 0.18
Nodes (5): TestCase, `two_factor` parchea el admin para que su `/admin/login/` redirija aqui. Asi no…, El rodeo por el correo termina en la misma pantalla., El segundo factor es **opcional**: quien no lo ha dado de alta entra con su…, SecondFactorIsNotSkippedTests

### Community 94 - "ClientForm"
Cohesion: 0.20
Nodes (6): BootstrapFormMixin, ClientForm, Meta, Pone las clases de Bootstrap en los campos, una sola vez. Django pinta…, Alta y edicion de un cliente., Solo digitos, igual que en el portal. El modelo tambien lo normaliza al…

### Community 96 - "ConfirmacionPazYSalvoTests"
Cohesion: 0.27
Nodes (4): ConfirmacionPazYSalvoTests, El boton del listado: se pregunta antes, y no revienta con lo viejo. Dos cosas…, El boton no envia: abre la confirmacion, y la confirmacion lleva el formulario.…, `Consultoría` no tiene «Primera instancia» entre sus etapas, y hay expedientes…

### Community 97 - "SessionFixationTests"
Cohesion: 0.20
Nodes (6): PazYSalvoNoSigueElTemaTests, TestCase, Identificarse tiene que cambiar el identificador de sesion. Sin eso, una sesion…, El paz y salvo se imprime, y el papel es blanco. La plantilla extiende…, `theme.css` se carga en `raw.html` **despues** de `custom_css`. Si el paz y…, SessionFixationTests

### Community 99 - "CodeLifetimeTests"
Cohesion: 0.25
Nodes (4): CodeLifetimeTests, Cuanto vive un codigo y cuantas veces se puede fallar., Tantear cuesta pedir otro, y pedir otro tiene su escalera. Nadie necesita seis…, En la sesion va su HMAC. La sesion va firmada, no cifrada: con el motor de…

### Community 100 - "core/api/views.py"
Cohesion: 0.36
Nodes (5): ConctactModelSerializer, Meta, ModelSerializer, ContactCreateAPIView, CreateAPIView

### Community 101 - "CaseCrudTests"
Cohesion: 0.19
Nodes (5): CaseCrudTests, El asunto y su dinero, que se guardan juntos o no se guardan., Ningun campo del pago es obligatorio. Un abono se registra muchas veces antes…, La regla del modelo: una cuota litis no lleva honorario pactado. Si el asunto…, Una etapa que no es de ese servicio la rechaza `CaseModel.clean()`.

### Community 102 - "GestorDashboardTests"
Cohesion: 0.29
Nodes (3): GestorDashboardTests, El panel economico, con las cifras que ya prueba `test_finance`., Es la confusion que mas caro sale: una expectativa no se puede cobrar.

### Community 103 - "MaskedEmailTests"
Cohesion: 0.39
Nodes (3): MaskedEmailTests, El correo tapado, que es lo unico que la pantalla dice del buzon., Uno por letra diria de cuantas letras es el buzon, y eso tampoco hace falta…

### Community 104 - "AdminAccessTests"
Cohesion: 0.16
Nodes (9): CaseAdmin, ClientAdmin, register, AdminAccessTests, PasswordStorageTests, TestCase, La puerta, tal como la ve el navegador., No hay papelera, y un cliente borrado se lleva sus casos y su dinero. Para dar… (+1 more)

### Community 105 - "CaseFinanceInline"
Cohesion: 0.33
Nodes (4): CaseFinanceInline, display, Por donde va la escalera de reenvios de ese cliente. Se ensena porque es lo…, El dinero, pegado a su caso. Va como `inline` y no como una entrada suelta del…

### Community 106 - "ForwardedHeaderTests"
Cohesion: 0.38
Nodes (4): ForwardedHeaderTests, override_settings, TestCase, De donde se saca la IP. Si se confiara en `X-Forwarded-For` sin un proxy…

### Community 108 - "GestorAccessTests"
Cohesion: 0.14
Nodes (8): GestorAccessTests, TestCase, Lo que sostiene todo lo demas: el panel no se sirve a nadie mas., Quien puede abrir cada pantalla. Se recorren **todas** las rutas del gestor en…, El interruptor del paz y salvo, desde el listado., Cambia un dato, asi que es `POST`. Un `GET` que cambia datos lo dispara…, Sin sesion, al formulario de entrada: ahi se arregla entrando., SettlementToggleTests

### Community 109 - "templatetags/honeypot.py"
Cohesion: 0.40
Nodes (4): La etiqueta que pinta el campo trampa. Se llama `honeypot` para que `{% load…, Pinta el campo trampa, con `HONEYPOT_FIELD_NAME` si no se da nombre., render_honeypot_field(), inclusion_tag

### Community 110 - "faq/migrations/0001_initial.py"
Cohesion: 0.40
Nodes (3): Migration, Migration, django_ckeditor_5_fields

### Community 111 - "case_manager_extras.py"
Cohesion: 0.40
Nodes (4): grouped_identification(), filter, Filtros del gestor. Solo formato de presentacion. Ninguna decision, ninguna…, La cedula con puntos de millar: `16484186` -> `16.484.186`. Es…

### Community 114 - "test_api_open_routes.py"
Cohesion: 0.21
Nodes (9): api_routes(), APIOpenRoutesTests, APITestCase, override_settings, Toda apertura de la API debe ser una decisión explícita y revisable., Materializa cada patrón; falla si un tipo nuevo necesita otro ejemplo., sample_segment(), django_utils_regex_helper (+1 more)

### Community 115 - "auth_platform/admin.py"
Cohesion: 0.20
Nodes (7): AttlasInsolvencyAuthAdminModel, AttlasInsolvencyAuthConsultantsAdminModel, ClientLookupChallengeAdmin, register, Permite escribir la cédula o la fecha (AAAA-MM-DD) “en claro” y buscar contra…, ClientLookupChallenge, django_utils_dateparse

### Community 116 - "financial_education/api/views.py"
Cohesion: 0.24
Nodes (6): PQRSModelCreateAPIView, CreateAPIView, extend_schema, drf_spectacular_utils, rest_framework_generics, rest_framework_permissions

### Community 122 - "AccessCodeEmailTests"
Cohesion: 0.18
Nodes (6): AccessCodeEmailTests, TestCase, El correo que lleva el codigo., Las imagenes remotas las bloquean casi todos los clientes de correo: un…, No hay nada firmado que enviar. Son unos 40 KB por mensaje, y una firma…, Hay quien lee el correo en texto plano, y un correo solo-HTML puntua peor en…

### Community 123 - "test_attempts.py"
Cohesion: 0.20
Nodes (5): Quien esta intentando entrar, para `AXES_USERNAME_CALLABLE`. Se normaliza a…, username(), AxesKnowsWhoFailedTests, Que las dos puertas cuentan en el mismo sitio, y que pedir codigos tiene tope.…, `axes` busca un campo `username` en el POST y el asistente lo llama `auth-…

### Community 178 - "TeamMemberModel"
Cohesion: 0.25
Nodes (4): Meta, ModalBannerModel, Mini-blog por empleado: perfil, resumen, foto y LinkedIn. Estable a largo…, TeamMemberModel

### Community 179 - "CaseFinanceForm"
Cohesion: 0.31
Nodes (3): CaseFinanceForm, El dinero de un asunto. Cada modalidad muestra sus columnas; el modelo valida…, FreeModalityFormTests

### Community 180 - "verify"
Cohesion: 0.25
Nodes (8): backend_path(), clear(), hash_code(), Que backend anotar al entrar con codigo. Django lo exige cuando hay mas de uno…, Comprueba el codigo. Devuelve la cuenta, o `None`. Gasta un intento en cada…, Borra el codigo de la sesion. Seguro de llamar de mas., El codigo tal y como se guarda: HMAC-SHA256 con la clave del proyecto. Con HMAC…, verify()

### Community 181 - "issue"
Cohesion: 0.25
Nodes (8): find_user(), generate_code(), issue(), La cuenta a la que mandarle el codigo, o `None`. Se busca por nombre de usuario…, Emite un codigo y lo manda. Devuelve si **se acepto la peticion**. Devolver…, Cuanto dura un codigo, leido **en cada llamada**. Es una funcion y no una…, Seis cifras, del generador criptografico y no de `random`., ttl_minutes()

### Community 182 - "SendThrottleTests"
Cohesion: 0.32
Nodes (4): TestCase, Pedir codigos tiene tope, y el tope es del buzon., Pedir el codigo una vez por el usuario y otra por el correo son dos formas de…, SendThrottleTests

### Community 183 - "FinancialEducationModelSerializer"
Cohesion: 0.29
Nodes (5): FinancialEducationModelSerializer, Meta, ModelSerializer, Devuelve el campo `category` como una lista. Si está vacío o es None, se…, Devuelve el campo `category_en` como una lista. Si está vacío o es None, se…

### Community 184 - "CaseToggleSettlementView"
Cohesion: 0.29
Nodes (5): CaseToggleSettlementView, CrmReportView, View, El consolidado del portafolio, descargado como `.docx`., Autorizar o retirar el paz y salvo de un asunto, desde el listado. Es un `POST`…

### Community 185 - "FinancialEducationListAPIView"
Cohesion: 0.33
Nodes (3): FinancialEducationListAPIView, extend_schema, ListAPIView

### Community 187 - "manage.py"
Cohesion: 0.40
Nodes (4): main(), Django's command-line utility for administrative tasks., Run administrative tasks., sys

### Community 188 - "faq/admin.py"
Cohesion: 0.67
Nodes (3): MainFAQModelAdmin, OtherFAQModelAdmin, register

## Ambiguous Edges - Review These
- `Gestor form field partial` → `Signature widget template`  [AMBIGUOUS]
  apps/project/api/platform/insolvency_form/templates/signature/signature_widget.html · relation: conceptually_related_to

## Knowledge Gaps
- **108 isolated node(s):** `Meta`, `Meta`, `Migration`, `Migration`, `Migration` (+103 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1072 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **74 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Gestor form field partial` and `Signature widget template`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `CaseModel` connect `CaseModel` to `CaseForm`, `django_urls`, `TimeStampedModel`, `ClientModel`, `GestorRequiredMixin`, `PortfolioChartTests`, `ImportPropDemoTests`, `test_classification.py`, `case_manager/views.py`, `gestor.py`, `Mandate`, `AuthenticatedPortalTests`, `reports.py`, `LadderThroughThePortalTests`, `CaseFinanceModel`, `OfficeFallbackTests`, `WordReportTests`, `PazYSalvoAccessTests`, `CaseToggleSettlementView`, `CaseFormMixin`, `AdminPagesRenderTests`, `PublicQueryTests`, `CaseListView`, `PublicCardFieldsTests`, `ClientDetailTests`, `ClientToCasesTests`, `django_utils_translation`, `CaseNoteModel`, `DetailRowsTests`, `VariosAsuntosTests`, `ConfirmacionPazYSalvoTests`, `CodeLifetimeTests`, `CaseCrudTests`, `GestorDashboardTests`, `GestorAccessTests`, `DynamicFlowTests`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `ClientModel` connect `ClientModel` to `CaseForm`, `django_urls`, `TimeStampedModel`, `CaseModel`, `GestorRequiredMixin`, `PortfolioChartTests`, `LadderRulesTests`, `ImportPropDemoTests`, `test_classification.py`, `case_manager/views.py`, `gestor.py`, `Mandate`, `AuthenticatedPortalTests`, `reports.py`, `LadderThroughThePortalTests`, `CaseFinanceModel`, `OfficeFallbackTests`, `WordReportTests`, `PazYSalvoAccessTests`, `AdminPagesRenderTests`, `TablasTests`, `PublicQueryTests`, `AttemptLimitTests`, `CaseListView`, `PublicCardFieldsTests`, `ClientDetailTests`, `ClientToCasesTests`, `django_utils_translation`, `CaseNoteModel`, `DetailRowsTests`, `VariosAsuntosTests`, `ClientForm`, `ClientCrudTests`, `ConfirmacionPazYSalvoTests`, `SessionFixationTests`, `CodeLifetimeTests`, `CaseCrudTests`, `GestorDashboardTests`, `MaskedEmailTests`, `AdminAccessTests`, `GestorAccessTests`, `DynamicFlowTests`, `AccessCodeEmailTests`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `TimeStampedModel` connect `TimeStampedModel` to `AttlasInsolvencyAuthModel`, `AttlasInsolvencyFormModel`, `PQRSModel`, `django_urls`, `FinancialEducationModel`, `faq/api/views.py`, `logging`, `CaseModel`, `AttlasInsolvencyCreditorsModel`, `insolvency_form/api/serializers.py`, `ClientModel`, `CaseFinanceModel`, `django_contrib`, `TeamMemberModel`, `auth_platform/admin.py`, `django_utils_translation`, `ContactModel`, `CaseNoteModel`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `CaseModel` (e.g. with `CaseForm` and `CaseFormMixin`) actually correct?**
  _`CaseModel` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `ClientModel` (e.g. with `ClientForm` and `PublicCaseQueryForm`) actually correct?**
  _`ClientModel` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `AttlasInsolvencyFormModel` (e.g. with `AttlasInsolvencyAuthRegisterSerializer` and `ClientResponseSerializer`) actually correct?**
  _`AttlasInsolvencyFormModel` has 37 INFERRED edges - model-reasoned connections that need verification._