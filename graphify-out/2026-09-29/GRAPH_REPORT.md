# Graph Report - pag_propensionesabogados  (2026-09-29)

## Corpus Check
- 349 files · ~96,265 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .mo 11, .po 11, .css 5)

## Summary
- 2373 nodes · 4422 edges · 178 communities (110 shown, 68 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 428 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Migraciones (case_manager/insolvency)
- Formularios de caso y finanzas
- Firma y decodificación base64
- FAQ y educación financiera
- Catálogo de choices del caso
- Tests de la pantalla de login
- API de tokens (auth_platform)
- Plantillas del sitio público
- Migraciones (core/utils)
- Tests de notas del gestor
- Admin del formulario de insolvencia
- Comando import_propdemo
- Config insolvencia y ChatGPT
- Tests de tema y apps varias
- Serializers de insolvencia
- Vistas del gestor
- OTP del portal de consulta
- Plantillas del gestor de casos
- AppConfigs de Django
- Comando startapi
- Login OTP y throttling
- Mixins de acceso al gestor
- API de la calculadora
- Tests de deudores y expectativas
- Tests del correo de código
- Motor de base de datos
- Admin del gestor de casos
- Tests de import_propdemo
- Tests de forma del correo
- Orden de choices
- Formularios del portal público
- Correo con imágenes inline
- Tests de acceso al gestor
- Tests de balance y mandato
- Tests de consulta pública
- API wizard de insolvencia
- Tests de fallos en axes
- Modelos base (TimeStampedModel)
- API de FAQ
- Tests de acceso al admin
- Informes descargables
- Vista de login de Propensiones
- README de cuenta (login OTP)
- Formularios y formato moneda
- Comando delete_migrations
- Tests de la escalera de acceso
- Usuarios y backend email/usuario
- Bloqueo por intentos del portal
- Modelo CaseFinance
- Tests de respaldo a la oficina
- Tests de informes
- Settings y firma de software
- Modelos del sitio (core)
- Tests de acceso a paz y salvo
- Tests de tema claro/oscuro
- Honeypot
- Wizards y vistas FAQ
- Tests de hosts permitidos
- Rate limiting
- Bearer token y backend de email
- Admin del sitio (core)
- Vistas y URLs del sitio
- Contador de intentos de login
- Comando tidy_messages
- Admin de auth_platform
- Formulario de notas del caso
- Tests JS de flujo dinámico
- Tests de render del admin
- Tests de listados DataTables
- Tests de identificación del cliente
- Tests de límite de intentos
- Hooks de django-axes
- Vistas de lista/alta de casos
- Tests de ficha pública
- Tests de detalle de cliente
- Tests de enlaces del navbar
- Detección de ataques e IPs bloqueadas
- Verificación del honeypot
- Tests de check_honeypot
- QuerySet de CaseFinance
- Tests cliente → casos
- Vistas y URLs de cuenta
- Admin de usuarios
- Grupo del gestor y navbar
- Mixins de permisos
- Tests de tidy_messages
- Envío de notas por correo
- Tests de filas de detalle
- Tests de varios asuntos
- Handlers de error
- Admin general e IPs
- Tests del decorador honeypot
- Tests del campo honeypot
- Tests del segundo factor
- BootstrapFormMixin
- Tests CRUD de clientes
- Tests de confirmación paz y salvo
- Tests de impresión paz y salvo
- Tests de vida del código
- API del sitio (core)
- Vistas de alta de notas/clientes
- Tests del dashboard
- Tests de correo enmascarado
- Admin de reenvío de correos
- Inline de CaseFinance
- Tests de cabecera forwarded
- Export de insolvencia
- Pasos del wizard de login
- Templatetag honeypot
- Migraciones FAQ/educación
- Filtros del gestor
- Serializer de firma
- __init__
- test_honeypot
- urls
- middleware
- test_honeypot 2
- security
- urls 2
- forms
- forms 2
- README
- README 2
- pyproject

## God Nodes (most connected - your core abstractions)
1. `CaseModel` - 82 edges
2. `ClientModel` - 77 edges
3. `CaseFinanceModel` - 54 edges
4. `AttlasInsolvencyFormModel` - 52 edges
5. `make_user()` - 44 edges
6. `TimeStampedModel` - 39 edges
7. `Service` - 36 edges
8. `CaseForm` - 33 edges
9. `Stage` - 32 edges
10. `login_as()` - 29 edges

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
- **Visitor contact flow** — apps_common_core_templates_pages_sections_12_contact_section, apps_common_core_templates_pages_sections_12_contact_section_contact_form, apps_common_core_templates_email_contact_email_template, apps_common_core_templates_partials_toasts [INFERRED 0.85]
- **Team member display** — apps_common_core_templates_pages_sections_13_team_section, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_sections_13_team_section_team_member_context [EXTRACTED 1.00]
- **Template inheritance chain** — apps_common_core_templates_raw, apps_common_core_templates_base, apps_common_core_templates_pages_index, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_documents, apps_common_core_templates_pages_privacy_policy, apps_common_core_templates_pages_terms_and_conditions [EXTRACTED 1.00]
- **Public case portal composition** — apps_project_api_platform_case_manager_templates_case_manager_consultar_proceso, apps_project_api_platform_case_manager_templates_case_manager_partials_contact_card, apps_project_api_platform_case_manager_templates_case_manager_partials_inactive_notice, apps_project_api_platform_case_manager_templates_case_manager_partials_legal_notice, apps_project_api_platform_case_manager_templates_case_manager_partials_client_notes, apps_project_api_platform_case_manager_templates_case_manager_partials_field [EXTRACTED 1.00]
- **Gestor financial totals reporting** — apps_project_api_platform_case_manager_templates_case_manager_gestor_dashboard, apps_project_api_platform_case_manager_templates_case_manager_gestor_client_detail, apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_stat, apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_portfolio [INFERRED 0.85]
- **Case note authoring, portal display and email notification** — apps_project_api_platform_case_manager_templates_case_manager_gestor_partials_notes, apps_project_api_platform_case_manager_templates_case_manager_partials_client_notes, apps_project_api_platform_case_manager_templates_case_manager_email_case_note [INFERRED 0.85]
- **Login brute-force defense (axes + OTP + shared counter)** — apps_project_common_account_readme_email_otp_login, apps_project_common_account_readme_shared_attempt_counter, requirements_django_axes [INFERRED 0.85]
- **Account login template inheritance chain** — apps_project_common_account_templates_two_factor_core_login, apps_project_common_account_templates_two_factor_base, apps_project_common_account_templates_account_layout_account, apps_project_common_account_templates_two_factor_wizard_actions, apps_project_common_account_templates_two_factor_wizard_forms [EXTRACTED 1.00]

## Communities (178 total, 68 thin omitted)

### Community 0 - "Migraciones (case_manager/insolvency)"
Cohesion: 0.03
Nodes (34): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+26 more)

### Community 1 - "Formularios de caso y finanzas"
Cohesion: 0.05
Nodes (15): CaseFinanceForm, CaseForm, Alta y edicion de un asunto. Sigue servicio -> área/subnivel -> proceso. Los…, El arbol que el navegador necesita para repintar los desplegables. Va entero y…, El dinero de un asunto. Cada modalidad muestra sus columnas; el modelo valida…, La nota no vale: se vuelve a la ficha con el formulario y sus errores, que es…, ClassificationTests, DynamicFlowTests (+7 more)

### Community 2 - "Firma y decodificación base64"
Cohesion: 0.07
Nodes (38): decode_base64_image(), Step11Serializer, _age(), _barcode_bytes(), _build_assets(), build_context(), _build_creditors(), _build_creditors_unique() (+30 more)

### Community 3 - "FAQ y educación financiera"
Cohesion: 0.06
Nodes (26): FinancialEducationModelAdmin, register, FinancialEducationModelSerializer, Meta, ModelSerializer, Devuelve el campo `category` como una lista. Si está vacío o es None, se…, Devuelve el campo `category_en` como una lista. Si está vacío o es None, se…, FinancialEducationListAPIView (+18 more)

### Community 4 - "Catálogo de choices del caso"
Cohesion: 0.09
Nodes (35): Area, Court, instances_for(), NoteKind, PoliceInstance, Procedure, El vocabulario del gestor: servicios, tramites, areas, subtipos y etapas. Todo…, Instancia de la querella policiva. (+27 more)

### Community 5 - "Tests de la pantalla de login"
Cohesion: 0.07
Nodes (18): LoginPageTests, make_user(), OfferAfterFailuresTests, OtpModeTests, TestCase, La segunda puerta: el codigo de seis cifras al correo., Quien pulsa «entrar con un codigo» puede no haber escrito su usuario todavia,…, Las imagenes remotas las bloquean casi todos los clientes de correo: un… (+10 more)

### Community 6 - "API de tokens (auth_platform)"
Cohesion: 0.10
Nodes (24): APIView, generate_token(), verify_token(), AttlasInsolvencyAuthConsultantsRegisterSerializer, AttlasInsolvencyAuthRegisterSerializer, AttlasInsolvencyAuthSerializer, ClientResponseSerializer, ClientSearchSerializer (+16 more)

### Community 7 - "Plantillas del sitio público"
Cohesion: 0.08
Nodes (41): Base Template, Contact Email Template, Documents Page, Required documents (power of attorney, service contract), Index Page, Privacy Policy Page, Corporate Social Responsibility Section, Stats Section (+33 more)

### Community 8 - "Migraciones (core/utils)"
Cohesion: 0.06
Nodes (22): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+14 more)

### Community 9 - "Tests de notas del gestor"
Cohesion: 0.07
Nodes (15): NoteFromGestorTests, NoteModelTests, TestCase, Anadir una nota desde la ficha del asunto., El expediente tiene que decir quien dijo que., Las dos mitades hablan del mismo dato: lo que el despacho escribe aqui es lo…, El aviso automatico cuando el asunto avanza., Un correo diciendo que el asunto avanzo cuando no ha avanzado gasta la… (+7 more)

### Community 10 - "Admin del formulario de insolvencia"
Cohesion: 0.09
Nodes (27): AssetInline, CreditorsInline, GeneralInline, IncomeInline, IncomeOtherInline, JudicialProcessInline, Meta, ResourceInline (+19 more)

### Community 11 - "Comando import_propdemo"
Cohesion: 0.06
Nodes (16): _as_int(), Command, BaseCommand, Trae a la base los expedientes que estaban en `localStorage.propDemo`. Por que…, Un importe del JSON como entero no negativo. El navegador guardaba lo que…, CaseModel, Un asunto del despacho: el expediente que ve el cliente. Los tres bloques de…, Las filas del bloque de detalle: lo que hay, no lo que tocaria. Es… (+8 more)

### Community 12 - "Config insolvencia y ChatGPT"
Cohesion: 0.09
Nodes (22): InsolvencyFormConfig, AppConfig, ChatGPTAPI, creditor_nit_contact_prompt(), enrich_creditor(), _find_in_local_db(), _find_via_chatgpt(), _normalize() (+14 more)

### Community 13 - "Tests de tema y apps varias"
Cohesion: 0.11
Nodes (15): El tema claro/oscuro, que vive en un solo atributo del `<html>`. Lo que se…, El codigo de acceso del portal y su escalera de reenvios. La escalera pedida, y…, La puerta del portal publico de consulta. Lo que se prueba aqui es,…, Que las dos puertas cuentan en el mismo sitio, y que pedir codigos tiene tope.…, El backend que deja entrar con el usuario o con el correo. Las tres pruebas que…, El acceso: las dos puertas, y que ninguna abra lo que la otra cierra. Lo que se…, Que la puerta del codigo **no** es una puerta trasera al segundo factor. Es la…, axes_models (+7 more)

### Community 14 - "Serializers de insolvencia"
Cohesion: 0.14
Nodes (25): AssetSerializer, CreditorSerializer, IncomeOtherSerializer, IncomeSerializer, JudicialProcessSerializer, Meta, atomic, ResourceItemSerializer (+17 more)

### Community 15 - "Vistas del gestor"
Cohesion: 0.08
Nodes (21): El formulario del portal publico de consulta. Lo que aqui se valida lo validaba…, ClientDetailView, El gestor de procesos y clientes, como pantallas del sitio. Por que no solo el…, La ficha de un cliente: quien es, que le debe al despacho y por que. Es la…, CaseNoteModel, CaseNoteQuerySet, CaseQuerySet, ClientModel (+13 more)

### Community 16 - "OTP del portal de consulta"
Cohesion: 0.08
Nodes (31): can_send(), clear(), _cycle_expired(), generate_code(), hash_code(), issue(), next_send_allowed_at(), office_recipients() (+23 more)

### Community 17 - "Plantillas del gestor de casos"
Cohesion: 0.11
Nodes (30): Public case query portal (consultar_proceso.html), Email access code verification flow, case_manager_extras templatetags (grouped_identification), Access code email template, Case note email template, Gestor base layout, Gestor case form, Gestor case list (+22 more)

### Community 18 - "AppConfigs de Django"
Cohesion: 0.06
Nodes (21): CoreConfig, AppConfig, AppConfig, UtilsConfig, FaqConfig, AppConfig, FinancialEducationConfig, AppConfig (+13 more)

### Community 19 - "Comando startapi"
Cohesion: 0.11
Nodes (6): Command, Path, Convert snake_case app name to PascalCase config class name., Generates a Django app with a full REST API scaffold. Usage: python manage.py…, django_core_management_commands_startapp, StartAppCommand

### Community 20 - "Login OTP y throttling"
Cohesion: 0.09
Nodes (28): Un cubo de intentos por ventana de tiempo, para formularios publicos. Que…, backend_path(), clear(), contact_email(), entered_identifier(), find_user(), generate_code(), has_live_code() (+20 more)

### Community 21 - "Mixins de acceso al gestor"
Cohesion: 0.09
Nodes (21): GestorRequiredMixin, LoginRequiredMixin, UserPassesTestMixin, Exige sesion iniciada y pertenencia al grupo del gestor. **Responde 404 y no…, CaseReportView, CaseToggleSettlementView, CaseUpdateView, ClientReportView (+13 more)

### Community 22 - "API de la calculadora"
Cohesion: 0.10
Nodes (15): hash_value(), RegisterSerializer, ClientCreateSerializer, ClientDataSerializer, ClientSearchSerializer, ClientUpdateSerializer, Meta, ClientViewSet (+7 more)

### Community 23 - "Tests de deudores y expectativas"
Cohesion: 0.08
Nodes (14): DebtorsAndExpectationsTests, ManagerExposeLasPreguntasTests, PortfolioChartTests, TestCase, Las dos listas del panel gerencial. Que sean dos consultas y no dos tablas es…, La confusion que mas caro sale: no se le puede cobrar., Ninguna fila puede estar en las dos. Si se solaparan, el pendiente potencial…, Las dos cifras que solo existen para que se dibuje el panel. Se prueban porque… (+6 more)

### Community 24 - "Tests del correo de código"
Cohesion: 0.09
Nodes (12): AccessCodeEmailTests, LadderRulesTests, No se queda bloqueado para siempre, y tampoco reanuda donde lo dejo: empieza de…, Acertar demuestra que el buzon registrado es suyo y que lo esta leyendo, que es…, Gastarla con una cedula no puede cerrarle el portal a otra persona., Esta en la base, no en la sesion ni en la cache. Si estuviera en la sesion,…, El correo que lleva el codigo., La escalera, mirada directamente y sin pasar por la pantalla. (+4 more)

### Community 25 - "Motor de base de datos"
Cohesion: 0.10
Nodes (19): engine_for(), Qué motor de base de datos se instala de verdad, según el que se declara. El…, El motor a instalar para el que se declaró en el `.env`. Cualquier otro…, DatabaseFeatures, DatabaseWrapper, El backend de MySQL de siempre, con los UUID guardados como estaban. El…, Como antes de Django 5.0: los UUID van en ``char(32)``, en hex., EngineForTests (+11 more)

### Community 26 - "Admin del gestor de casos"
Cohesion: 0.10
Nodes (15): can_use_case_manager(), Si `user` puede usar el gestor. Es una funcion y no solo un mixin porque la…, CaseAdmin, CaseManagerAdminMixin, register, El gestor dentro del admin de Django. Por que el admin y no una pantalla propia…, La misma puerta que `GestorRequiredMixin`, para el admin. El admin pregunta por…, `obj` lleva valor por defecto porque este mixin lo comparten un `ModelAdmin` y… (+7 more)

### Community 27 - "Tests de import_propdemo"
Cohesion: 0.11
Nodes (8): ImportPropDemoTests, TestCase, Inventar una etapa mas avanzada le diria al cliente que su asunto va por donde…, El campo del navegador no validaba nada: guardaba cadenas., El grupo del gestor y sus permisos., No hay papelera --esta fuera del alcance-- y borrar un cliente se lleva por…, SetupGroupTests, write()

### Community 28 - "Tests de forma del correo"
Cohesion: 0.11
Nodes (12): EmailShapeTests, override_settings, Como sale el correo por dentro. Es lo que nadie mira hasta que falla, y cuando…, Del `DEFAULT_FROM_EMAIL`, que es el que de verdad esta autorizado a enviar por…, Quien firma el envio no es quien atiende la respuesta., Un correo solo-HTML puntua peor en los filtros de spam, y hay quien lee el…, Enlazadas se bloquean: casi todos los clientes de correo no cargan imagenes…, Sin los `<>` hay clientes que no resuelven el `cid:` y ensenan el cuadro roto… (+4 more)

### Community 29 - "Orden de choices"
Cohesion: 0.09
Nodes (15): alphabetical(), is_other(), Los valores en orden alfabetico, con los «Otro…» al final. Un desplegable largo…, Los subtipos que cuelgan del servicio, y nada mas. `area` ya no decide nada…, El tercer nivel, si esa rama tiene uno. Devuelve vacio cuando no lo tiene --un…, second_subtypes_for(), subtypes_for(), ArbolAprobadoTests (+7 more)

### Community 30 - "Formularios del portal público"
Cohesion: 0.19
Nodes (13): PublicAccessCodeForm, PublicCaseQueryForm, El primer paso: solo la identificacion. Antes pedia tambien una «clave de…, El segundo paso: las seis cifras que llegaron al correo., authorized_client_pk(), PazYSalvoView, PublicCaseQueryView, TemplateView (+5 more)

### Community 31 - "Correo con imágenes inline"
Cohesion: 0.14
Nodes (20): attach_inline_images(), Path, Lo comun a los correos que manda el sitio: que las imagenes se vean. Casi todos…, El fichero en disco de un estatico, mirando donde de verdad esta. Primero en…, Mete las imagenes en el mensaje y las marca como `inline`. `Content-ID` es lo…, static_source(), Los correos que el despacho le manda al cliente. Que se manda ------------ Tres…, Le manda al cliente el codigo con el que entra a ver su proceso. Cuando el… (+12 more)

### Community 32 - "Tests de acceso al gestor"
Cohesion: 0.09
Nodes (10): login_as(), Deja la sesion abierta como esa cuenta, sin pasar por `authenticate()`.…, GestorAccessTests, Lo que sostiene todo lo demas: el panel no se sirve a nadie mas., Quien puede abrir cada pantalla. Se recorren **todas** las rutas del gestor en…, El interruptor del paz y salvo, desde el listado., Cambia un dato, asi que es `POST`. Un `GET` que cambia datos lo dispara…, Sin sesion, al formulario de entrada: ahi se arregla entrando. (+2 more)

### Community 33 - "Tests de balance y mandato"
Cohesion: 0.12
Nodes (13): Mandate, Modalidad del contrato. Es el campo del que cuelga todo el dinero. Cual de los…, BalanceTests, DashboardTotalsTests, make_case(), Los calculos financieros del gestor. Son la actividad que la cotizacion llama…, Un abono mayor que lo pactado es un error de captura o un anticipo. En ninguno…, Valor fijo cerrado: esta pactado y no se ha cobrado nada. (+5 more)

### Community 34 - "Tests de consulta pública"
Cohesion: 0.11
Nodes (11): pedir_codigo(), PublicQueryTests, Tapado por el centro: el cliente tiene que poder reconocer su buzon --si no, no…, La sesion recuerda **de quien** es el codigo. Sin eso, pedirlo para la cedula…, No se queda fuera. Antes se le cerraba el portal sin que hubiera nada que…, Prometer un codigo que no va a llegar deja a alguien mirando un campo vacio sin…, Con el codigo al correo, decir «no hay nada con ese numero» ya no entrega una…, Un `GET` no puede traer datos de nadie. Esta es la prueba que sostiene el… (+3 more)

### Community 35 - "API wizard de insolvencia"
Cohesion: 0.12
Nodes (13): InsolvencyFormWizardView, atomic, CreateAPIView, extend_schema, Si estamos en el paso 4 y llegó debtor_cessation_report, lo enviamos a…, Si la URL trae <id>, usamos el comportamiento normal (retrieve/update sobre ese…, GET /api/v1/insolvency-form/signature/<id>/ PATCH /api/v1/insolvency-…, POST /api/platform/signature/ { "cedula": "0000000000", "signature":… (+5 more)

### Community 36 - "Tests de fallos en axes"
Cohesion: 0.11
Nodes (11): AxesKnowsWhoFailedTests, FailuresAreSharedTests, override_settings, TestCase, El freno se aplica **antes** de mirar el codigo. Al reves se apuntarian los…, El control de la prueba anterior. Sin el, aquella pasaria igual si el codigo…, Pedir codigos tiene tope, y el tope es del buzon., Pedir el codigo una vez por el usuario y otra por el correo son dos formas de… (+3 more)

### Community 37 - "Modelos base (TimeStampedModel)"
Cohesion: 0.19
Nodes (12): Abstract model providing timestamp fields (created and updated) and additional…, TimeStampedModel, Migration, AttlasInsolvencySummaryModel, auditlog_models, auditlog_registry, django_contrib_auth_hashers, django_core_files_base (+4 more)

### Community 38 - "API de FAQ"
Cohesion: 0.18
Nodes (14): MainFAQModelAdmin, OtherFAQModelAdmin, register, MainFAQModelSerializer, Meta, OtherFAQModelSerializer, ModelSerializer, MainFAQListAPIView (+6 more)

### Community 39 - "Tests de acceso al admin"
Cohesion: 0.13
Nodes (7): ClientAdmin, AdminAccessTests, make_user(), La puerta, tal como la ve el navegador., No hay papelera, y un cliente borrado se lleva sus casos y su dinero. Para dar…, AuthenticatedPortalTests, TestCase

### Community 40 - "Informes descargables"
Cohesion: 0.16
Nodes (21): client_report(), crm_report(), _descarga(), _dinero(), _documento(), _fila_de_asunto(), _pares(), _pie() (+13 more)

### Community 41 - "Vista de login de Propensiones"
Cohesion: 0.13
Nodes (9): PropensionesLoginView, El prefijo del asistente se queda como `login_view`. `formtools` lo saca del…, Tira la lista de pasos que `formtools` guarda en cache. La condicion del paso…, Deja el asistente en la pantalla del codigo. `send` sale en `False` cuando solo…, Que pasos exigen que el usuario ya este identificado. El del codigo **no**: es…, Que formularios se revalidan al terminar. Ni el de contrasena ni el del codigo:…, Vacia el asistente y devuelve a la primera pantalla, con aviso. `get_user()`…, El asistente de siempre, mas la entrada por codigo. (+1 more)

### Community 42 - "README de cuenta (login OTP)"
Cohesion: 0.13
Nodes (13): Account README, /admin/login/ redirected to account login, Email one-time code login, No account enumeration, Shared failed-attempt counter (django-axes), Two-factor login wizard (auth/otp/token/backup), Username-or-email auth backend, login_otp.html (OTP email) (+5 more)

### Community 43 - "Formularios y formato moneda"
Cohesion: 0.17
Nodes (15): ContactForm, Meta, currency(), filter, Meta, UserRegisterForm, UserUpdateProfile, UnicodeLastNameValidator (+7 more)

### Community 44 - "Comando delete_migrations"
Cohesion: 0.13
Nodes (12): Command, BaseCommand, Delete migration files. Args: deleted_files (list): List of deleted files.…, Get list of apps to skip migration deletion. Args: app_name (str, optional):…, Delete all migration files and folders except __init__.py, and custom apps., Print deletion results. Args: deleted_folders (List[tuple]): List of deleted…, Print deleted items. Args: items (List[tuple]): List of items to print. action…, Print exceptions. Args: exceptions (List[str]): List of exceptions to print. (+4 more)

### Community 45 - "Tests de la escalera de acceso"
Cohesion: 0.14
Nodes (8): LadderThroughThePortalTests, La misma escalera, pero pulsando «reenviar» en la pantalla., Mueve hacia atras el ultimo envio, que es lo mismo que esperar., La hora y no los segundos: el cliente puede dejar esta pantalla abierta un…, El ciclo completo, tal y como se pidio., Bloquear el **envio** no es invalidar lo enviado: quien recibio el quinto…, Volver al primer paso y teclear la cedula otra vez es el camino obvio para…, Si la cuenta viviera en la sesion, tirar la galleta seria el bypass.

### Community 46 - "Usuarios y backend email/usuario"
Cohesion: 0.11
Nodes (13): AbstractUser, EmailOrUsernameModelBackend, Entrar con el nombre de usuario **o** con el correo. La pantalla de acceso…, Meta, UserAdminForm, Meta, UserModel, django_contrib_auth_admin (+5 more)

### Community 47 - "Bloqueo por intentos del portal"
Cohesion: 0.14
Nodes (18): attempt_window(), attempts_for(), block(), client_ip(), is_blocked(), _key(), max_attempts(), Cuantas veces se puede fallar la clave del portal antes de que la IP descanse.… (+10 more)

### Community 48 - "Modelo CaseFinance"
Cohesion: 0.11
Nodes (10): CaseFinanceModel, Que cada modalidad solo traiga las cifras que le corresponden., El dinero de un caso: que se pacto, que entro y que falta. Va aparte de…, Si esta fila es una **expectativa** y no una deuda. La regla que mas facil se…, Lo cerrado con el cliente. Una expectativa no esta cerrada., Abonos de modalidades de pago y cuotas litis de valor fijo., Lo que falta por cobrar. **No se guarda**: se calcula. Nunca es negativo: un…, Lo que se espera ganar si el pleito sale. No es deuda. (+2 more)

### Community 49 - "Tests de respaldo a la oficina"
Cohesion: 0.15
Nodes (9): OfficeFallbackTests, override_settings, El cliente sin correo registrado: su codigo va al despacho. Es el caso normal,…, A la oficina le llegarian seis cifras sueltas y no sabria a quien darselas. El…, Sin el recordatorio, este mismo correo vuelve a llegar la proxima vez que el…, El aviso de «nadie de Propensiones te pedira este codigo» es para el titular.…, Lo que cambia es a donde va, no lo que hace: quien lo teclea entra., Si no, hostigar una cedula sin correo llenaria el buzon de la propia oficina,… (+1 more)

### Community 50 - "Tests de informes"
Cohesion: 0.14
Nodes (8): Los dos informes descargables., Un informe con todo el dinero del despacho servido a quien pase seria peor que…, La pantalla anterior bajaba un `.doc` que por dentro era HTML: Word avisa de…, Un informe que el despacho manda a un cliente no puede decir «$8000000»: se lee…, «No incluir en panel economico» tiene que valer tambien en el informe; si no,…, Todo el texto de un `.docx`, para poder buscar dentro. Un `.docx` es un zip con…, texto_del_docx(), WordReportTests

### Community 51 - "Settings y firma de software"
Cohesion: 0.11
Nodes (12): ASGI config for app_core project. It exposes the ASGI callable as a module-…, WSGI config for app_core project. It exposes the WSGI callable as a module-…, datetime, django_core_asgi, django_core_wsgi, dotenv, import_export_formats_base_formats, main() (+4 more)

### Community 52 - "Modelos del sitio (core)"
Cohesion: 0.13
Nodes (10): ContactModel, Meta, ModalBannerModel, PageChoices, Mini-blog por empleado: perfil, resumen, foto y LinkedIn. Estable a largo…, StatesChoices, TeamMemberModel, IndexTemplateView (+2 more)

### Community 53 - "Tests de acceso a paz y salvo"
Cohesion: 0.16
Nodes (7): PazYSalvoAccessTests, El primer paso no identifica a nadie: solo manda un correo. Si abriera sesion,…, Se guarda sin puntos porque asi se busca; se imprime con ellos., Regla que venia escrita en el JavaScript original: el paz y salvo **no** lleva…, Saber la direccion no basta. Es lo que antes si bastaba: el documento lo armaba…, El paz y salvo dice que no se debe nada: no lo decide el cliente., Identificarse con la clave propia no abre el expediente ajeno, ni aunque ese…

### Community 54 - "Tests de tema claro/oscuro"
Cohesion: 0.12
Nodes (9): TestCase, `text-bg-light` ademas fija `color: #000`. Cambiarle solo el fondo lo deja…, Que el tema llega a las paginas del sitio, no solo a una., El trozo que lo aplica va en linea en el `<head>`. Si se moviera a `theme.js`…, Las dos declaran las mismas variables y ganan por orden. Al reves, la paleta…, En navegacion privada o con las cookies de terceros desactivadas,…, Las clases de Bootstrap que **no** cambian solas con el modo oscuro. Bootstrap…, ThemeWiringTests (+1 more)

### Community 55 - "Honeypot"
Cohesion: 0.13
Nodes (12): honeypot_error(), honeypot_exempt(), La trampa para robots del formulario de contacto. Que hace -------- Se pinta un…, Marca una vista para que no se le compruebe la trampa., La respuesta por defecto cuando la trampa se dispara., La trampa para robots. Protege el unico formulario publico que escribe en la…, View, UserLogoutView (+4 more)

### Community 56 - "Wizards y vistas FAQ"
Cohesion: 0.13
Nodes (9): forget_resolved_steps(), Lo que hay que decirle a `formtools` cuando los pasos cambian a mitad de vuelo.…, Olvida los pasos que el asistente tenga cacheados. Llamalo **justo despues** de…, El asistente de acceso, con una segunda puerta: el codigo por correo. Por que…, Las rutas de `django-two-factor-auth`, con el acceso apuntando a esta casa. Por…, django_shortcuts, time, two_factor_forms (+1 more)

### Community 57 - "Tests de hosts permitidos"
Cohesion: 0.14
Nodes (10): HostNoPermitidoTests, OrdenDelMiddlewareTests, override_settings, SimpleTestCase, TestCase, Los nombres con los que se puede pedir el sitio. Hay un CNAME de `www` en la…, Un enlace compartido al `www` tiene que llevar a donde apunta, no a la portada:…, `mail.`, `webmail.`, `cpanel.`… apuntan a la misma IP pero no son de esta… (+2 more)

### Community 58 - "Rate limiting"
Cohesion: 0.17
Nodes (8): RateLimit, Cuantos intentos caben, y de quien. Args: name: identifica al formulario. Dos…, Por IP salvo que se diga otra cosa. Sin `scope`, el cubo es de la direccion y…, Apunta un intento y dice si puede seguir. Se apunta **antes** de saber si…, RateLimitTests, El cubo de intentos, por separado., Una llave de cache es un sitio donde nadie espera encontrar datos personales:…, Falla **cerrado**. Aqui el limite no evita una molestia pasajera: es lo unico…

### Community 59 - "Bearer token y backend de email"
Cohesion: 0.17
Nodes (7): BearerTokenAuthentication, EmailOrUsernameBackendTests, TestCase, Desactivar a quien se va del despacho tiene que bastar. La version anterior…, Django llama a **todos** los backends con los mismos argumentos, asi que una…, El modelo solo exige que sea unica la pareja (usuario, correo), asi que el…, SOLO_MODELO

### Community 60 - "Admin del sitio (core)"
Cohesion: 0.16
Nodes (8): ContactModelAdmin, ModalBannerModelAdmin, display, register, TeamMemberModelAdmin, Meta, UserLoginAttemptModel, django_contrib

### Community 61 - "Vistas y URLs del sitio"
Cohesion: 0.21
Nodes (12): CalendarView, DocumentsView, PrivacyPolicyView, DetailView, TemplateView, security_txt_view(), TeamMemberDetailView, TermsAndConditionsView (+4 more)

### Community 62 - "Contador de intentos de login"
Cohesion: 0.16
Nodes (10): _credentials(), is_locked_out(), note_failure(), Un solo contador de intentos fallidos de acceso, para las dos puertas. El…, Las credenciales como las espera `axes`, normalizadas. Solo el nombre: la…, Apunta un intento fallido que no paso por `authenticate()`. Nunca lanza: esto…, Si esta conexion ya gasto sus intentos. Se le pregunta a `axes` en vez de…, LoginOTPForm (+2 more)

### Community 63 - "Comando tidy_messages"
Cohesion: 0.17
Nodes (7): Command, BaseCommand, Deja los catalogos de traduccion como tienen que quedar tras `makemessages`.…, Devuelve el catalogo arreglado y cuantos arreglos hizo., Deja vacia la traduccion de las entradas marcadas como dudosas. Es lo que evita…, Entradas con `msgstr` vacio de verdad, sin contar la cabecera. El «de verdad»…, re

### Community 64 - "Admin de auth_platform"
Cohesion: 0.14
Nodes (8): AttlasInsolvencyAuthAdminModel, AttlasInsolvencyAuthConsultantsAdminModel, register, Permite escribir la cédula o la fecha (AAAA-MM-DD) “en claro” y buscar contra…, AttlasInsolvencyAuthConsultantsModel, Meta, Versión concisa de la función de iniciales, django_utils_dateparse

### Community 65 - "Formulario de notas del caso"
Cohesion: 0.20
Nodes (6): CaseNoteForm, Una novedad del expediente, y si se le avisa al cliente. La casilla de aviso…, CaseFormMixin, El asunto y su dinero se guardan juntos o no se guarda ninguno. Son dos…, Los errores que no son de un campo, como aviso flotante. Un error de campo se…, Avisa al cliente de que su asunto avanzo, si procede. Tres condiciones, y las…

### Community 66 - "Tests JS de flujo dinámico"
Cohesion: 0.13
Nodes (12): assert, edit, fresh, fs, { JSDOM }, path, reference, apps_project_api_platform_case_manager_tests_fixtures_reference_flow (+4 more)

### Community 67 - "Tests de render del admin"
Cohesion: 0.13
Nodes (6): AdminPagesRenderTests, PasswordStorageTests, TestCase, La contrasena no se guarda, se resume. Es lo minimo, y es exactamente lo que no…, Que las paginas del gestor en el admin **abran de verdad**. Las pruebas de…, Es la pagina que llevaba el inline del dinero y reventaba.

### Community 68 - "Tests de listados DataTables"
Cohesion: 0.13
Nodes (7): TestCase, Los listados largos, ahora que los pagina el navegador. Antes esto probaba la…, Sin esto, DataTables ordenaria veinticinco filas y diria que eso es el orden de…, Son botones. Ordenar por una columna de botones no significa nada, y el `<th>`…, `annotate` agrupa, y una consulta agrupada deja de estar ordenada aunque el…, Un enlace guardado con `?q=` no se rompe por quitar el buscador., TablasTests

### Community 69 - "Tests de identificación del cliente"
Cohesion: 0.13
Nodes (7): Las dos mitades hablan del mismo dato: lo que el despacho enciende aqui es lo…, identificarse(), Se quema al usarlo: quien vea el correo por encima del hombro --o lo recupere…, Si se le dijera «no encontramos nada» se pondria a probar cedulas creyendo que…, Decirle que llame no es abrirle el expediente: sigue sin vigencia., El expediente es del cliente; lo que se le cobra es de puertas adentro. Van en…, Los dos pasos del portal en una linea: la cedula y el codigo del correo. El…

### Community 70 - "Tests de límite de intentos"
Cohesion: 0.18
Nodes (6): AttemptLimitTests, El limite de intentos por IP. Es lo que frena a quien recorre cedulas para…, Cedulas que no son de nadie, que es el tanteo que esto frena., Un bloqueo sin `blocked_until` no bloquea a nadie: el middleware filtra por…, Si no, tantear seis cifras saldria gratis mientras que equivocarse de cedula…, Dos despistes y un acierto no dejan a nadie a un fallo del cierre.

### Community 71 - "Hooks de django-axes"
Cohesion: 0.20
Nodes (12): client_ip(), is_lockout_exempt(), Enganches de `django-axes`, para que el freno al tanteo no sea un autobloqueo.…, IP para `AXES_CLIENT_IP_CALLABLE`., Si esta peticion de acceso nunca debe quedar bloqueada. Solo mira la lista…, Quien esta intentando entrar, para `AXES_USERNAME_CALLABLE`. Se normaliza a…, username(), get_client_ip() (+4 more)

### Community 72 - "Vistas de lista/alta de casos"
Cohesion: 0.14
Nodes (9): CaseCreateView, CaseListView, _client_or_none(), ClientListView, Los clientes del despacho, con busqueda por nombre o cedula. La busqueda es un…, Los asuntos del despacho, todos o los de un cliente. `?cliente=<uuid>` acota la…, Alta de un asunto, con el cliente ya puesto si se vino desde su ficha.…, El cliente de un `?cliente=<uuid>` de la URL, o `None`. Lo que llega en la URL… (+1 more)

### Community 73 - "Tests de ficha pública"
Cohesion: 0.19
Nodes (7): PublicCardFieldsTests, Los datos de la tarjeta, que son los del diseno aprobado. La etapa y el…, El asunto judicial la guarda en `instance` y la querella policiva en…, «Cuota litis» a secas no le dice a nadie cuanto va a pagar., El bloque se rellena despues de dar de alta el asunto, y entre una cosa y otra…, La modalidad si sale --esta en el diseno aprobado-- pero las cifras no: ni lo…, Subirla arriba sin quitarla de abajo la habria dejado dos veces en la misma…

### Community 74 - "Tests de detalle de cliente"
Cohesion: 0.15
Nodes (8): BaseReportes, ClientDetailTests, TestCase, La ficha individual y los informes en Word. Lo que se prueba aqui, por orden de…, En la pantalla anterior un cliente **era** un asunto. Traducirla literalmente…, `totals()` sobre sus asuntos. Otro cliente con deuda no puede sumar aqui, que…, La ficha individual, en pantalla., zipfile

### Community 75 - "Tests de enlaces del navbar"
Cohesion: 0.27
Nodes (5): make_user(), NavbarAccountLinksTests, TestCase, El registro del sitio es publico, asi que cualquiera puede llegar aqui con una…, La cabecera es un `include`, asi que esto deberia darse solo. Se comprueba…

### Community 76 - "Detección de ataques e IPs bloqueadas"
Cohesion: 0.17
Nodes (7): DetectSuspiciousRequestMiddleware, IPBlockedModel, Meta, ReasonsChoices, WhiteListedIPModel, HttpRequestAttakView, View

### Community 77 - "Verificación del honeypot"
Cohesion: 0.21
Nodes (9): decorate(), inner(), honeypot_equals(), El comprobador por defecto: el campo tiene que llegar **vacio**.…, Comprueba la trampa en un `POST`. Devuelve la respuesta de error, o `None`.…, verify_honeypot_value(), override_settings, Los ajustes que el paquete permitia y que se conservan. (+1 more)

### Community 78 - "Tests de check_honeypot"
Cohesion: 0.15
Nodes (7): CheckHoneypotTests, El decorador, que es lo que protege la vista de contacto., Una persona no rellena un campo que no ve., Un robot rellena todo lo que encuentra., Quitar el campo antes de enviar tampoco vale. Es mas facil que rellenarlo, asi…, La trampa es del envio; pedir la pagina no manda ningun campo., A quien la dispara no se le cuenta como no dispararla.

### Community 79 - "QuerySet de CaseFinance"
Cohesion: 0.21
Nodes (7): CaseFinanceQuerySet, Las preguntas del panel economico y del panel gerencial. Cada una vive aqui y…, Los casos que el despacho decidio incluir en el panel economico., Quien debe dinero, hoy. Son dos cosas sumadas, y es la parte que mas se…, Lo que se espera ganar si los pleitos salen: `Cuota litis` sobre 0 %. No es…, Las cifras de cabecera del panel gerencial, en una sola consulta. Reproduce…, Lo mismo, repartido por area, de mas a menos. Es la «Distribucion por area /…

### Community 80 - "Tests cliente → casos"
Cohesion: 0.15
Nodes (4): ClientToCasesTests, Ir de un cliente a sus asuntos. Sin esto hay que salir al otro listado y…, Un enlace viejo o mal copiado ensena la lista entera, no un 500., El filtro sobrevive a la busqueda. Sin esto, buscar dentro de los asuntos de…

### Community 81 - "Vistas y URLs de cuenta"
Cohesion: 0.18
Nodes (6): Las rutas de la cuenta. Las rutas del segundo factor no estan aqui sino en…, FormView, View, UserLogoutView, UserRegisterView, django_views_generic_edit

### Community 82 - "Admin de usuarios"
Cohesion: 0.23
Nodes (4): ImportExportActionModelAdmin, register, UserModelAdmin, UserAdmin

### Community 83 - "Grupo del gestor y navbar"
Cohesion: 0.18
Nodes (8): Los enlaces de cuenta en la cabecera. Van dentro del menu «Plataformas»,…, Quien puede ver y tocar el gestor. Esta en un modulo propio y no repartido por…, Command, atomic, BaseCommand, Crea el grupo del gestor con los permisos que necesita. Se ejecuta una vez por…, django_contrib_auth_models, django_core_management_base

### Community 84 - "Mixins de permisos"
Cohesion: 0.23
Nodes (6): EncryptedPermissionsMixin, LoginGroupRequiredMixin, LoginRequiredMixin, UserPassesTestMixin, KeyForm, django_contrib_auth_mixins

### Community 85 - "Tests de tidy_messages"
Cohesion: 0.24
Nodes (4): ConteoTests, TestCase, El recuento del final, que es la unica senal de cuanto queda. Una traduccion…, TidyTests

### Community 86 - "Envío de notas por correo"
Cohesion: 0.21
Nodes (7): Le manda al cliente el correo de una nota. Devuelve si salio. No se manda y…, send_case_note(), EmailNotSentTests, Cuando no se manda, que es tan importante como cuando si., Hay clientes de los que solo se tiene el telefono., Si se marcara antes, un fallo del servidor dejaria el expediente diciendo que…, Es una fecha y no un booleano: «le avisamos» y «le avisamos el 3 de marzo» no…

### Community 87 - "Tests de filas de detalle"
Cohesion: 0.27
Nodes (4): DetailRowsTests, El bloque de detalle de la ficha publica. Colgaba del tipo de tramite, y los…, Los tres bloques se recorren enteros, pero un asunto no llena mas de uno: lo…, La prueba de arriba mira el modelo; esta mira lo que el cliente lee.

### Community 88 - "Tests de varios asuntos"
Cohesion: 0.24
Nodes (4): Un cliente con mas de un asunto los ve **todos**. Antes la vista hacia…, Lo que hace util verlos juntos: van por sitios distintos., El permiso es **por asunto**, no por cliente: se puede estar a paz y salvo de…, VariosAsuntosTests

### Community 89 - "Handlers de error"
Cohesion: 0.31
Nodes (8): handler400(), handler403(), handler404(), handler500(), Cuenta los fallos y, al tercero de contrasena, ofrece el codigo. Se cuenta aqui…, django_conf_urls_static, drf_spectacular_views, importlib_util

### Community 90 - "Admin general e IPs"
Cohesion: 0.24
Nodes (7): GeneralAdminModel, IPBlockedModelAdmin, ImportExportActionModelAdmin, register, WhiteListedIPModelAdmin, django_utils_safestring, import_export_admin

### Community 91 - "Tests del decorador honeypot"
Cohesion: 0.33
Nodes (5): check_honeypot(), Decora una vista para que compruebe la trampa antes de atender el `POST`. Se…, vista(), DecoratorFormsTests, Las tres formas de escribir el decorador. Se prueban porque la vista de…

### Community 92 - "Tests del campo honeypot"
Cohesion: 0.27
Nodes (5): La etiqueta de plantilla, que es lo que pinta el campo en el formulario. Se…, Si saliera relleno, cada envio legitimo dispararia la trampa., Un robot que mire los estilos descartaria un campo con `display:none` o…, Las dos mitades tienen que hablar del mismo campo. Es la prueba que sostiene el…, RenderFieldTests

### Community 93 - "Tests del segundo factor"
Cohesion: 0.18
Nodes (5): TestCase, `two_factor` parchea el admin para que su `/admin/login/` redirija aqui. Asi no…, El rodeo por el correo termina en la misma pantalla., El segundo factor es **opcional**: quien no lo ha dado de alta entra con su…, SecondFactorIsNotSkippedTests

### Community 94 - "BootstrapFormMixin"
Cohesion: 0.20
Nodes (6): BootstrapFormMixin, ClientForm, Meta, Pone las clases de Bootstrap en los campos, una sola vez. Django pinta…, Alta y edicion de un cliente., Solo digitos, igual que en el portal. El modelo tambien lo normaliza al…

### Community 96 - "Tests de confirmación paz y salvo"
Cohesion: 0.27
Nodes (4): ConfirmacionPazYSalvoTests, El boton del listado: se pregunta antes, y no revienta con lo viejo. Dos cosas…, El boton no envia: abre la confirmacion, y la confirmacion lleva el formulario.…, `Consultoría` no tiene «Primera instancia» entre sus etapas, y hay expedientes…

### Community 97 - "Tests de impresión paz y salvo"
Cohesion: 0.20
Nodes (6): PazYSalvoNoSigueElTemaTests, TestCase, Identificarse tiene que cambiar el identificador de sesion. Sin eso, una sesion…, El paz y salvo se imprime, y el papel es blanco. La plantilla extiende…, `theme.css` se carga en `raw.html` **despues** de `custom_css`. Si el paz y…, SessionFixationTests

### Community 99 - "Tests de vida del código"
Cohesion: 0.22
Nodes (5): CodeLifetimeTests, TestCase, Cuanto vive un codigo y cuantas veces se puede fallar., Tantear cuesta pedir otro, y pedir otro tiene su escalera. Nadie necesita seis…, En la sesion va su HMAC. La sesion va firmada, no cifrada: con el motor de…

### Community 100 - "API del sitio (core)"
Cohesion: 0.36
Nodes (5): ConctactModelSerializer, Meta, ModelSerializer, ContactCreateAPIView, CreateAPIView

### Community 101 - "Vistas de alta de notas/clientes"
Cohesion: 0.32
Nodes (4): CaseNoteCreateView, ClientCreateView, Anade una novedad a un asunto, y la manda al cliente si se marco. Es lo que el…, CreateView

### Community 102 - "Tests del dashboard"
Cohesion: 0.25
Nodes (3): GestorDashboardTests, El panel economico, con las cifras que ya prueba `test_finance`., Es la confusion que mas caro sale: una expectativa no se puede cobrar.

### Community 103 - "Tests de correo enmascarado"
Cohesion: 0.39
Nodes (3): MaskedEmailTests, El correo tapado, que es lo unico que la pantalla dice del buzon., Uno por letra diria de cuantas letras es el buzon, y eso tampoco hace falta…

### Community 104 - "Admin de reenvío de correos"
Cohesion: 0.32
Nodes (6): AttlasInsolvencyFormAdmin, action, ImportExportActionModelAdmin, register, Genera el DOCX en memoria y lo devuelve como BytesIO., render_document()

### Community 105 - "Inline de CaseFinance"
Cohesion: 0.33
Nodes (4): CaseFinanceInline, display, Por donde va la escalera de reenvios de ese cliente. Se ensena porque es lo…, El dinero, pegado a su caso. Va como `inline` y no como una entrada suelta del…

### Community 106 - "Tests de cabecera forwarded"
Cohesion: 0.38
Nodes (4): ForwardedHeaderTests, override_settings, TestCase, De donde se saca la IP. Si se confiara en `X-Forwarded-For` sin un proxy…

### Community 108 - "Pasos del wizard de login"
Cohesion: 0.29
Nodes (3): Lo que pasa al superar cada paso. El paso del codigo hace lo mismo que el de…, Quien intentaba entrar, mire el paso que mire., Titulo y frase de cada pantalla, en un solo sitio.

### Community 109 - "Templatetag honeypot"
Cohesion: 0.40
Nodes (4): La etiqueta que pinta el campo trampa. Se llama `honeypot` para que `{% load…, Pinta el campo trampa, con `HONEYPOT_FIELD_NAME` si no se da nombre., render_honeypot_field(), inclusion_tag

### Community 110 - "Migraciones FAQ/educación"
Cohesion: 0.40
Nodes (3): Migration, Migration, django_ckeditor_5_fields

### Community 111 - "Filtros del gestor"
Cohesion: 0.40
Nodes (4): grouped_identification(), filter, Filtros del gestor. Solo formato de presentacion. Ninguna decision, ninguna…, La cedula con puntos de millar: `16484186` -> `16.484.186`. Es…

### Community 114 - "__init__"
Cohesion: 0.50
Nodes (3): Any, custom_processors(), typing

## Ambiguous Edges - Review These
- `Gestor form field partial` → `Signature widget template`  [AMBIGUOUS]
  apps/project/api/platform/insolvency_form/templates/signature/signature_widget.html · relation: conceptually_related_to

## Knowledge Gaps
- **107 isolated node(s):** `Meta`, `Meta`, `Migration`, `Migration`, `Migration` (+102 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1032 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **68 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Gestor form field partial` and `Signature widget template`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `CaseModel` connect `Comando import_propdemo` to `Formularios de caso y finanzas`, `Catálogo de choices del caso`, `Tests de tema y apps varias`, `Vistas del gestor`, `Mixins de acceso al gestor`, `Tests de deudores y expectativas`, `Admin del gestor de casos`, `Tests de import_propdemo`, `Orden de choices`, `Formularios del portal público`, `Tests de acceso al gestor`, `Tests de balance y mandato`, `Tests de consulta pública`, `Modelos base (TimeStampedModel)`, `Tests de acceso al admin`, `Informes descargables`, `Tests de la escalera de acceso`, `Tests de respaldo a la oficina`, `Tests de informes`, `Tests de acceso a paz y salvo`, `Formulario de notas del caso`, `Tests de render del admin`, `Vistas de lista/alta de casos`, `Tests de ficha pública`, `Tests de detalle de cliente`, `Tests cliente → casos`, `Grupo del gestor y navbar`, `Tests de filas de detalle`, `Tests de varios asuntos`, `Tests de confirmación paz y salvo`, `Tests de vida del código`, `Vistas de alta de notas/clientes`, `Tests del dashboard`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `TimeStampedModel` connect `Modelos base (TimeStampedModel)` to `Admin de auth_platform`, `Firma y decodificación base64`, `FAQ y educación financiera`, `API de FAQ`, `API de tokens (auth_platform)`, `Admin del formulario de insolvencia`, `Comando import_propdemo`, `Detección de ataques e IPs bloqueadas`, `Config insolvencia y ChatGPT`, `Serializers de insolvencia`, `Vistas del gestor`, `Modelo CaseFinance`, `Usuarios y backend email/usuario`, `Modelos del sitio (core)`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `ClientModel` connect `Vistas del gestor` to `Formularios de caso y finanzas`, `Catálogo de choices del caso`, `Tests de notas del gestor`, `Comando import_propdemo`, `Tests de tema y apps varias`, `Mixins de acceso al gestor`, `Tests de deudores y expectativas`, `Tests del correo de código`, `Admin del gestor de casos`, `Tests de import_propdemo`, `Orden de choices`, `Formularios del portal público`, `Tests de acceso al gestor`, `Tests de balance y mandato`, `Tests de consulta pública`, `Modelos base (TimeStampedModel)`, `Tests de acceso al admin`, `Informes descargables`, `Tests de la escalera de acceso`, `Tests de respaldo a la oficina`, `Tests de informes`, `Tests de acceso a paz y salvo`, `Tests de render del admin`, `Tests de listados DataTables`, `Tests de límite de intentos`, `Vistas de lista/alta de casos`, `Tests de ficha pública`, `Tests de detalle de cliente`, `Tests cliente → casos`, `Grupo del gestor y navbar`, `Tests de filas de detalle`, `Tests de varios asuntos`, `BootstrapFormMixin`, `Tests CRUD de clientes`, `Tests de confirmación paz y salvo`, `Tests de impresión paz y salvo`, `Tests de vida del código`, `Vistas de alta de notas/clientes`, `Tests del dashboard`, `Tests de correo enmascarado`, `forms 2`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `CaseModel` (e.g. with `CaseForm` and `CaseFormMixin`) actually correct?**
  _`CaseModel` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `ClientModel` (e.g. with `ClientForm` and `PublicCaseQueryForm`) actually correct?**
  _`ClientModel` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `CaseFinanceModel` (e.g. with `CaseFinanceInline` and `CaseFinanceForm`) actually correct?**
  _`CaseFinanceModel` has 26 INFERRED edges - model-reasoned connections that need verification._