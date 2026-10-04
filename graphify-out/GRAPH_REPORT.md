# Graph Report - pag_propensionesabogados  (2026-10-04)

## Corpus Check
- 392 files · ~189,135 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .mo 11, .po 11, .css 5)

## Summary
- 4807 nodes · 9503 edges · 283 communities (104 shown, 179 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 629 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `87fd2baa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- django_db
- test_logs.py
- AttlasInsolvencyFormModel
- PQRSModel
- test_reports.py
- OtpModeTests
- auth_platform/api/views.py
- Index Page
- django_utils_timezone
- make_user
- TimeStampedModel
- .toggle
- AttlasInsolvencyCreditorsModel
- django_test
- insolvency_form/api/serializers.py
- .ask
- attack_patterns.py
- Signature widget template
- django_apps
- Command
- portal_otp.py
- CaseNoteCreateView
- ClientViewSet
- CaseNoteModel
- Mandate
- settings.py
- NoteVisibilityToggleTests
- ClientToCasesTests
- CaseFinanceModel
- media_audit.py
- test_blocking_details.py
- django_conf
- .check
- test_sri.py
- LoginPathsBase
- InsolvencyFormWizardView
- FailuresAreSharedTests
- FinancialEducationModel
- faq/api/views.py
- ConsultantRegistrationTests
- gestor.py
- PropensionesLoginView
- Account README
- django
- Command
- dashboard_boxes.py
- UserModel
- get_client_ip
- CaseModel
- utils/views.py
- send
- os
- test_scanning.py
- PublicQueryTests
- ThemeWiringTests
- test_honeypot.py
- ClientLookupTests
- WWWRedirectTests
- RateLimit
- EmailOrUsernameBackendTests
- require_http_url
- core/views.py
- account/views.py
- Command
- AttlasInsolvencyAuthModel
- CspHeaderTests
- dynamic_flow.cjs
- GestorDashboardTests
- .run_backup
- ClientModel
- backup_crypto.py
- otp_login.py
- CaseListView
- Command
- .report
- HasServerKey
- paz_y_salvo.py
- verify_honeypot_value
- CheckHoneypotTests
- gea_client.py
- IPBlockedModel
- paz_y_salvo_pdf.py
- UserModelAdmin
- OwnershipTests
- mixins.py
- TidyTests
- ImportPropDemoTests
- EmailShapeTests
- custom_filters.py
- AttlasLoginTests
- IPBlockedModelAdmin
- vista
- RenderFieldTests
- SecondFactorIsNotSkippedTests
- Command
- CaseFinanceQuerySet
- PazYSalvoDocumentModel
- LockoutBase
- GestorRequiredMixin
- ArbolAprobadoTests
- test_openapi_schema.py
- can_use_case_manager
- upload_prefixes
- seed_gestor_demo.py
- CaseForm
- LadderThroughThePortalTests
- insolvency_form/admin.py
- Command
- templatetags/honeypot.py
- faq/migrations/0001_initial.py
- JSONReportRunner
- SignatureCreateSerializer
- test_api_open_routes.py
- hash_value
- BlockedRequestTests
- attempts.py
- security.txt
- PublicCaseQueryView
- CaseCrudTests
- InlineBase
- test_env.py
- OfficeFallbackTests
- test_check_security.py
- Utils README
- csp_report.py
- scanners.py
- financial_chart.py
- ClientForm
- PazYSalvoAccessTests
- LadderRulesTests
- test_login_otp.py
- CaseFormMixin
- Users README
- pag-propensiones
- WhyThereIsNoUserTests
- identification.py
- ClientCleanTests
- ConfirmacionPazYSalvoTests
- .ask_for_code
- AttemptLimitTests
- case_manager/views.py
- Command
- upload_fields
- dead_cache
- CspReportTests
- test_scanners.py
- PublicCardFieldsTests
- LoginWithoutUserInStorageTests
- NavbarAccountLinksTests
- Command
- netintel.py
- _safety_findings
- test_reporting.py
- VariosAsuntosTests
- ThreeWrongPasswordsOfferTheCodeTests
- utils/admin.py
- db_backup.py
- describe_duration
- Command
- middleware/__init__.py
- RecordingResult
- TheSettingsSectionTests
- TheCoverageIsSplitByAppTests
- WhichScannerRunsWhereTests
- send_case_note
- CaseFinanceForm
- ClassificationTests
- DetailRowsTests
- AccessCodeEmailTests
- PasswordResetRateLimitTests
- TheHealthCommandTests
- ServerKeyAPITests
- nit_check_digit
- HealthCheckView
- BlockBadBotsMiddleware
- TheCheckCatchesANewFieldTests
- ScannerAndBrowserTests
- PazYSalvoDocumentAdmin
- PortalNitTests
- TheOutcomesAreCountedApartTests
- SafetyNeverWaitsForAnAnswerTests
- ReadingPipAuditsAnswerTests
- PasswordResetDoesNotLeakAccountsTests
- test_db_portability.py
- PrivateMediaStorage
- ThePassphraseNameTests
- TheWarmupCronTests
- TheReportsDirectoryTests
- CaseFinanceInline
- CodeLifetimeTests
- MaskedEmailTests
- test_backup.py
- ThePublicListsAgreeTests
- TheHealthCheckViewTests
- sample_case
- Command
- AttlasInsolvencyFormAdmin
- TheCoverageTests
- ForwardedHeaderTests
- TestCase
- _first_json_object
- test_admin_date_hierarchy.py
- BanditOverThisProjectTests
- axis_ticks
- GestorDashboardView
- SimpleTestCase
- ExportsTests
- _labels
- .form_invalid
- Command
- MiddlewareOrderTests
- MigrationTests
- InlineThread
- _NoRedirect
- ._own_views
- CaseNoteQuerySet
- CaseQuerySet

## God Nodes (most connected - your core abstractions)
1. `ClientModel` - 119 edges
2. `CaseModel` - 114 edges
3. `CaseFinanceModel` - 68 edges
4. `make_user()` - 66 edges
5. `AttlasInsolvencyFormModel` - 58 edges
6. `login_as()` - 53 edges
7. `Service` - 49 edges
8. `IPBlockedModel` - 47 edges
9. `Stage` - 46 edges
10. `PazYSalvoDocumentModel` - 43 edges

## Surprising Connections (you probably didn't know these)
- `SchemaGenerationTests` --uses--> `LookupOrPlatformTokenAuthentication`  [INFERRED]
  app_core/tests/test_openapi_schema.py → apps/project/api/platform/auth_platform/authentication.py
- `SchemaGenerationTests` --uses--> `ClientViewSet`  [INFERRED]
  app_core/tests/test_openapi_schema.py → apps/project/api/platform/calculator/api/views.py
- `DocsPagesTests` --uses--> `UserModel`  [INFERRED]
  app_core/tests/test_openapi_schema.py → apps/project/common/users/models.py
- `CspHeaderTests` --uses--> `Service`  [INFERRED]
  app_core/tests/test_security_headers.py → apps/project/case_manager/choices.py
- `CspHeaderTests` --uses--> `Stage`  [INFERRED]
  app_core/tests/test_security_headers.py → apps/project/case_manager/choices.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Account login template inheritance chain** — apps_project_common_account_templates_two_factor_core_login, apps_project_common_account_templates_two_factor_base, apps_project_common_account_templates_account_layout_account, apps_project_common_account_templates_two_factor_wizard_actions, apps_project_common_account_templates_two_factor_wizard_forms [EXTRACTED 1.00]
- **Team member display** — apps_common_core_templates_pages_sections_13_team_section, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_sections_13_team_section_team_member_context [EXTRACTED 1.00]
- **Template inheritance chain** — apps_common_core_templates_raw, apps_common_core_templates_base, apps_common_core_templates_pages_index, apps_common_core_templates_pages_team_detail, apps_common_core_templates_pages_documents, apps_common_core_templates_pages_privacy_policy, apps_common_core_templates_pages_terms_and_conditions [EXTRACTED 1.00]
- **Visitor contact flow** — apps_common_core_templates_pages_sections_12_contact_section, apps_common_core_templates_pages_sections_12_contact_section_contact_form, apps_common_core_templates_email_contact_email_template, apps_common_core_templates_partials_toasts [INFERRED 0.85]
- **Login brute-force defense (axes + OTP + shared counter)** — apps_project_common_account_readme_email_otp_login, apps_project_common_account_readme_shared_attempt_counter, requirements_django_axes [INFERRED 0.85]

## Communities (283 total, 179 thin omitted)

### Community 0 - "django_db"
Cohesion: 0.03
Nodes (35): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+27 more)

### Community 1 - "test_logs.py"
Cohesion: 0.05
Nodes (19): human_size(), log_file(), next_number(), prune(), rotate(), rotated_files(), rotated_name(), should_rotate() (+11 more)

### Community 2 - "AttlasInsolvencyFormModel"
Cohesion: 0.09
Nodes (17): Step11Serializer, _age(), _barcode_bytes(), _build_assets(), build_context(), _build_creditors(), _build_creditors_unique(), _build_debtor_partner() (+9 more)

### Community 3 - "PQRSModel"
Cohesion: 0.13
Nodes (8): Meta, PQRSModelSerializer, PQRSModelCreateAPIView, IDTypeChoices, Meta, PQRSModel, RequestTypeChoicesEN, RequestTypeChoicesES

### Community 4 - "test_reports.py"
Cohesion: 0.07
Nodes (4): GestorScreensTests, BaseReportes, texto_del_docx(), WordReportTests

### Community 5 - "OtpModeTests"
Cohesion: 0.05
Nodes (5): GettingInTests, LoginPageTests, make_user(), OfferAfterFailuresTests, OtpModeTests

### Community 6 - "auth_platform/api/views.py"
Cohesion: 0.09
Nodes (20): codes_match(), generate_code(), hash_code(), AttlasInsolvencyAuthConsultantsRegisterSerializer, AttlasInsolvencyAuthSerializer, ClientLookupVerifySerializer, ClientResponseSerializer, ClientSearchSerializer (+12 more)

### Community 7 - "Index Page"
Cohesion: 0.08
Nodes (40): Base Template, Contact Email Template, Documents Page, Required documents (power of attorney, service contract), Index Page, Privacy Policy Page, Corporate Social Responsibility Section, Stats Section (+32 more)

### Community 8 - "django_utils_timezone"
Cohesion: 0.05
Nodes (21): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+13 more)

### Community 9 - "make_user"
Cohesion: 0.03
Nodes (11): ClientAdmin, AdminAccessTests, AdminPagesRenderTests, login_as(), make_user(), PasswordStorageTests, AuditActorTests, AuthenticatedPortalTests (+3 more)

### Community 10 - "TimeStampedModel"
Cohesion: 0.08
Nodes (14): decode_base64_image(), TimeStampedModel, ASSET_TYPE_OPTIONS, AttlasInsolvencyAssetModel, AttlasInsolvencyIncomeModel, AttlasInsolvencyIncomeOtherModel, AttlasInsolvencyJudicialProcessModel, AttlasInsolvencyResourceItemModel (+6 more)

### Community 11 - ".toggle"
Cohesion: 0.05
Nodes (8): AuthorizeAndCertifyTests, CertifiedBase, DownloadTests, FailureAndRetryTests, FakeGea, FakeResponse, GestorTests, PublicViewTests

### Community 12 - "AttlasInsolvencyCreditorsModel"
Cohesion: 0.10
Nodes (12): InsolvencyFormConfig, ChatGPTAPI, creditor_nit_contact_prompt(), enrich_creditor(), _find_in_local_db(), _find_via_chatgpt(), _normalize(), AttlasInsolvencyCreditorsModel (+4 more)

### Community 13 - "django_test"
Cohesion: 0.04
Nodes (11): Court, IdentificationType, LegalRepIdentificationType, PoliceInstance, Procedure, restore_classification(), Sector, Service (+3 more)

### Community 14 - "insolvency_form/api/serializers.py"
Cohesion: 0.21
Nodes (21): AssetSerializer, CreditorSerializer, IncomeOtherSerializer, IncomeSerializer, JudicialProcessSerializer, Meta, ResourceItemSerializer, ResourceSerializer (+13 more)

### Community 15 - ".ask"
Cohesion: 0.06
Nodes (8): ChangePasswordTests, ForgotPasswordBase, link_in(), make_user(), TheEmailTests, TheLinkTests, TheNewPasswordIsCheckedTests, TheSessionIsKeptTests

### Community 16 - "attack_patterns.py"
Cohesion: 0.06
Nodes (13): build_pattern(), find_conflicts(), walk(), matched_term(), normalize_terms(), _term_pattern(), Command, NormalizationTests (+5 more)

### Community 18 - "django_apps"
Cohesion: 0.05
Nodes (11): CoreConfig, FaqConfig, FinancialEducationConfig, AuthConfig, BearerTokenAuthenticationScheme, LookupOrPlatformTokenAuthenticationScheme, CalculatorConfig, PqrsConfig (+3 more)

### Community 20 - "portal_otp.py"
Cohesion: 0.09
Nodes (12): can_send(), clear(), _cycle_expired(), issue(), next_send_allowed_at(), office_recipients(), pending_client_pk(), register_send() (+4 more)

### Community 22 - "ClientViewSet"
Cohesion: 0.13
Nodes (6): LookupOrPlatformTokenAuthentication, ClientCreateSerializer, ClientDataSerializer, ClientUpdateSerializer, Meta, ClientViewSet

### Community 23 - "CaseNoteModel"
Cohesion: 0.05
Nodes (8): NoteKind, CaseNoteModel, Meta, NoteFromGestorTests, NoteModelTests, StageChangeEmailTests, seed(), SeedGestorDemoTests

### Community 24 - "Mandate"
Cohesion: 0.05
Nodes (7): Mandate, BalanceTests, DashboardTotalsTests, DebtorsAndExpectationsTests, make_case(), ManagerExposeLasPreguntasTests, PortfolioChartTests

### Community 25 - "settings.py"
Cohesion: 0.06
Nodes (11): engine_for(), DatabaseFeatures, DatabaseWrapper, check_environment(), env_int(), env_list(), expected_variables(), format_missing() (+3 more)

### Community 26 - "NoteVisibilityToggleTests"
Cohesion: 0.05
Nodes (5): FeeArrangementLabelTests, add_notes(), AllNotesAreShownTests, NoteVisibilityToggleTests, make_case()

### Community 27 - "ClientToCasesTests"
Cohesion: 0.04
Nodes (5): ClientCrudTests, ClientToCasesTests, ListadosAlturaTests, TablasTests, TablasVaciasTests

### Community 28 - "CaseFinanceModel"
Cohesion: 0.05
Nodes (6): Command, CaseFinanceModel, DashboardBoxPageTests, galeria(), DashboardCoverageTests, make_case()

### Community 29 - "media_audit.py"
Cohesion: 0.22
Nodes (3): is_inside(), prefix_from_function(), _prefix_of()

### Community 30 - "test_blocking_details.py"
Cohesion: 0.08
Nodes (9): apply_to_entry(), block_duration(), block_until(), capped_until(), note_attempt(), _token_regex(), DetectSuspiciousRequestMiddleware, a_request() (+1 more)

### Community 31 - "django_conf"
Cohesion: 0.05
Nodes (11): custom_processors(), attach_inline_images(), static_source(), Command, contact_email(), _logo_png(), send_otp_email(), send_lookup_code() (+3 more)

### Community 32 - ".check"
Cohesion: 0.08
Nodes (7): safe_next(), SafeNextTests, TestOverHttps, TestTheFallback, TestWhatItLetsThrough, TestWhatItRefuses, TestWhereItReadsFrom

### Community 33 - "test_sri.py"
Cohesion: 0.08
Nodes (10): CssImportsTests, EveryThirdPartyAssetIsPinnedTests, host_of(), is_dynamic(), is_external(), NothingIsLoadedFromAnUnpinnedVersionTests, offending_tags(), tags_in() (+2 more)

### Community 34 - "LoginPathsBase"
Cohesion: 0.11
Nodes (4): EveryScreenOffersItsButtonTests, LoginPathsBase, WithASecondFactorTests, WithoutASecondFactorTests

### Community 35 - "InsolvencyFormWizardView"
Cohesion: 0.09
Nodes (5): BearerTokenAuthentication, InsolvencyFormMeView, InsolvencyFormWizardView, SignatureCreateAPIView, SignatureUpdateView

### Community 36 - "FailuresAreSharedTests"
Cohesion: 0.11
Nodes (3): AxesKnowsWhoFailedTests, FailuresAreSharedTests, SendThrottleTests

### Community 37 - "FinancialEducationModel"
Cohesion: 0.10
Nodes (6): FinancialEducationModelAdmin, FinancialEducationModelSerializer, Meta, FinancialEducationListAPIView, FinancialEducationModel, Meta

### Community 38 - "faq/api/views.py"
Cohesion: 0.18
Nodes (10): MainFAQModelAdmin, OtherFAQModelAdmin, MainFAQModelSerializer, Meta, OtherFAQModelSerializer, MainFAQListAPIView, OtherFAQListAPIView, MainFAQModel (+2 more)

### Community 40 - "gestor.py"
Cohesion: 0.06
Nodes (16): CaseReportView, CaseUpdateView, ClientDetailView, ClientReportView, ClientUpdateView, client_report(), crm_report(), _descarga() (+8 more)

### Community 42 - "Account README"
Cohesion: 0.14
Nodes (7): Account README, Username-or-email auth backend, account/login.html (legacy), Project README (uv setup), Django 5.2.17, django-axes, django-two-factor-auth

### Community 43 - "django"
Cohesion: 0.08
Nodes (11): ContactForm, Meta, currency(), ChangePasswordForm, ForgotPasswordStep1Form, Meta, UserRegisterForm, UserUpdateProfile (+3 more)

### Community 45 - "dashboard_boxes.py"
Cohesion: 0.09
Nodes (14): _authorized(), Box, build_boxes(), _client_cell(), _date(), _fee_arrangement(), _finances(), _money() (+6 more)

### Community 46 - "UserModel"
Cohesion: 0.11
Nodes (7): EmailOrUsernameModelBackend, Meta, UserLoginAttemptModel, Meta, UserAdminForm, Meta, UserModel

### Community 47 - "get_client_ip"
Cohesion: 0.09
Nodes (11): server_key_is_valid(), get_client_ip(), forget(), _key(), looks_like_enumeration(), note_not_found(), _setting(), threshold() (+3 more)

### Community 48 - "CaseModel"
Cohesion: 0.05
Nodes (3): _as_int(), Command, CaseModel

### Community 49 - "utils/views.py"
Cohesion: 0.09
Nodes (9): handler400(), handler403(), handler404(), handler500(), HttpRequestAttakView, is_safe_path(), _normalize_request_path(), ForgotPasswordStep2Form (+1 more)

### Community 50 - "send"
Cohesion: 0.09
Nodes (7): send(), Sent, TheGreetingTests, TheLogosTravelInsideTests, TheMessageSaysWhatItHasToTests, ThePlainTextHalfIsReadableTests, TheReplyToTests

### Community 52 - "test_scanning.py"
Cohesion: 0.09
Nodes (4): a_request(), ScannerSignatureTests, ScanningWindowTests, WithoutCacheNothingIsBlockedTests

### Community 55 - "test_honeypot.py"
Cohesion: 0.17
Nodes (3): honeypot_equals(), honeypot_error(), honeypot_exempt()

### Community 57 - "WWWRedirectTests"
Cohesion: 0.14
Nodes (3): HostNoPermitidoTests, OrdenDelMiddlewareTests, WWWRedirectTests

### Community 60 - "require_http_url"
Cohesion: 0.10
Nodes (5): InsecureUrlScheme, is_http_url(), require_http_url(), WhatGetsRejectedTests, WhatGetsThroughTests

### Community 61 - "core/views.py"
Cohesion: 0.06
Nodes (19): ContactModelAdmin, ModalBannerModelAdmin, TeamMemberModelAdmin, ConctactModelSerializer, Meta, ContactCreateAPIView, ContactModel, Meta (+11 more)

### Community 62 - "account/views.py"
Cohesion: 0.09
Nodes (6): _credentials(), is_locked_out(), note_failure(), ChangePasswordFormView, UserLogoutView, UserRegisterView

### Community 64 - "AttlasInsolvencyAuthModel"
Cohesion: 0.10
Nodes (9): sha256_hex(), verify_token(), make_pii(), Migration, AttlasInsolvencyAuthConsultantsModel, AttlasInsolvencyAuthModel, ClientLookupChallenge, ConsultantRegistrationChallenge (+1 more)

### Community 65 - "CspHeaderTests"
Cohesion: 0.08
Nodes (4): CookiesAndUploadsTests, CorsTests, CspHeaderTests, directives()

### Community 66 - "dynamic_flow.cjs"
Cohesion: 0.09
Nodes (13): assert, edit, fresh, fs, { JSDOM }, path, reference, assert (+5 more)

### Community 68 - ".run_backup"
Cohesion: 0.14
Nodes (3): BackupTestCase, TheBackupCommandTests, TheGeneralDumpTests

### Community 69 - "ClientModel"
Cohesion: 0.08
Nodes (7): ClientModel, client_identification(), client_identification_search(), client_number(), grouped_identification(), FormatTests, SessionFixationTests

### Community 70 - "backup_crypto.py"
Cohesion: 0.11
Nodes (6): BackupCryptoError, decrypt(), derive_key(), encrypt(), Command, TheEnvelopeTests

### Community 71 - "otp_login.py"
Cohesion: 0.04
Nodes (19): client_ip(), is_lockout_exempt(), username(), is_whitelisted(), Meta, WhiteListedIPModel, forget_resolved_steps(), LoginOTPForm (+11 more)

### Community 72 - "CaseListView"
Cohesion: 0.14
Nodes (4): CaseCreateView, CaseListView, _client_or_none(), ClientListView

### Community 74 - ".report"
Cohesion: 0.15
Nodes (5): FakeProjectMixin, installed(), TheDeclaredListsAreComparedTests, TheInstalledEnvironmentIsComparedTests, TheRealFilesTests

### Community 75 - "HasServerKey"
Cohesion: 0.13
Nodes (5): HasServerKey, UtilsConfig, check_server_key(), HasServerKeyTests, ServerKeyCheckTests

### Community 76 - "paz_y_salvo.py"
Cohesion: 0.15
Nodes (12): authorize(), barcode_text(), certify_now(), _dispatch(), _mark_revoked(), revoke(), _run(), _spawn() (+4 more)

### Community 77 - "verify_honeypot_value"
Cohesion: 0.25
Nodes (4): decorate(), inner(), verify_honeypot_value(), SettingsTests

### Community 79 - "gea_client.py"
Cohesion: 0.14
Nodes (16): check_gea_certification(), download_public_copy(), _error_from(), GeaError, GeaNotConfigured, _headers(), is_configured(), issue() (+8 more)

### Community 80 - "IPBlockedModel"
Cohesion: 0.09
Nodes (4): IPBlockedModel, ReasonsChoices, TheBlockStateIsCalculatedNotStoredTests, TheOriginIsResolvedOfflineTests

### Community 81 - "paz_y_salvo_pdf.py"
Cohesion: 0.11
Nodes (12): barcode_box(), build_pdf(), _fecha(), _header_cursor(), _image_height(), _logo_box(), _para(), placement() (+4 more)

### Community 84 - "mixins.py"
Cohesion: 0.14
Nodes (3): EncryptedPermissionsMixin, LoginGroupRequiredMixin, KeyForm

### Community 86 - "ImportPropDemoTests"
Cohesion: 0.11
Nodes (3): ImportPropDemoTests, SetupGroupTests, write()

### Community 88 - "custom_filters.py"
Cohesion: 0.13
Nodes (13): active_class(), add_attrs(), add_class(), aria_expanded(), collapse_open_class(), currency(), _current_url_name(), is_active() (+5 more)

### Community 90 - "IPBlockedModelAdmin"
Cohesion: 0.14
Nodes (3): GeneralAdminModel, IPBlockedModelAdmin, WhiteListedIPModelAdmin

### Community 91 - "vista"
Cohesion: 0.33
Nodes (3): check_honeypot(), vista(), DecoratorFormsTests

### Community 96 - "PazYSalvoDocumentModel"
Cohesion: 0.11
Nodes (11): PazYSalvoDocumentModel, Status, certify(), _clean(), _fail(), qr_url(), _reload(), revoke_in_gea() (+3 more)

### Community 97 - "LockoutBase"
Cohesion: 0.15
Nodes (4): AWrongCodeCountsTests, AWrongSecondFactorCountsTests, code_in(), LockoutBase

### Community 99 - "GestorRequiredMixin"
Cohesion: 0.11
Nodes (5): GestorRequiredMixin, CaseNoteVisibilityView, CaseRetryCertificationView, CaseToggleSettlementView, CrmReportView

### Community 100 - "ArbolAprobadoTests"
Cohesion: 0.09
Nodes (7): alphabetical(), Area, is_other(), second_subtypes_for(), subtypes_for(), ArbolAprobadoTests, TiempoTranscurridoTests

### Community 101 - "test_openapi_schema.py"
Cohesion: 0.11
Nodes (4): DocsPagesTests, QuietSchema, SchemaGenerationTests, login_with_otp()

### Community 102 - "can_use_case_manager"
Cohesion: 0.12
Nodes (4): can_use_case_manager(), CaseManagerAdminMixin, gestor_access(), CanUseCaseManagerTests

### Community 103 - "upload_prefixes"
Cohesion: 0.11
Nodes (5): private_fields(), upload_prefixes(), CheckMediaTests, ThePrivateFilesStayPrivateTests, WhatSitsUnderMediaRootIsDeclaredTests

### Community 104 - "seed_gestor_demo.py"
Cohesion: 0.19
Nodes (13): instances_for(), A(), add_months(), C(), d(), document_clients(), E(), generated_clients() (+5 more)

### Community 107 - "insolvency_form/admin.py"
Cohesion: 0.10
Nodes (15): AssetInline, CreditorsInline, FormResource, GeneralInline, IncomeInline, IncomeOtherInline, JudicialProcessInline, Meta (+7 more)

### Community 111 - "JSONReportRunner"
Cohesion: 0.16
Nodes (3): JSONReportRunner, run_sample(), TheReportIsOnlyWrittenWhenAskedTests

### Community 114 - "test_api_open_routes.py"
Cohesion: 0.12
Nodes (5): api_routes(), APIOpenRoutesTests, sample_segment(), Command, normalize()

### Community 115 - "hash_value"
Cohesion: 0.09
Nodes (7): hash_value(), AttlasInsolvencyAuthAdminModel, AttlasInsolvencyAuthConsultantsAdminModel, ClientLookupChallengeAdmin, AttlasInsolvencyAuthRegisterSerializer, Meta, RegisterSerializer

### Community 116 - "BlockedRequestTests"
Cohesion: 0.14
Nodes (3): BlockedRequestTests, NotFoundBurstTests, RedirectAuthenticatedUserTests

### Community 117 - "attempts.py"
Cohesion: 0.14
Nodes (9): attempt_window(), attempts_for(), block(), client_ip(), is_blocked(), _key(), max_attempts(), register_failure() (+1 more)

### Community 121 - "PublicCaseQueryView"
Cohesion: 0.28
Nodes (3): PublicAccessCodeForm, PublicCaseQueryForm, PublicCaseQueryView

### Community 123 - "InlineBase"
Cohesion: 0.22
Nodes (4): InlineBase, RetryInlineTests, textos(), ToggleInlineTests

### Community 124 - "test_env.py"
Cohesion: 0.07
Nodes (9): complete_environment(), declared(), EnvExampleTests, ErrorMessageTests, GeaDefaultTests, MissingVariablesTests, read_settings(), SettingsCoverageTests (+1 more)

### Community 135 - "test_check_security.py"
Cohesion: 0.13
Nodes (5): run_check_security(), section(), TheReportTests, TheThrottleSectionTests, TheViewsSectionTests

### Community 151 - "csp_report.py"
Cohesion: 0.14
Nodes (6): _clean(), csp_report(), _reports(), scrub_uri(), summarize(), set_language()

### Community 152 - "scanners.py"
Cohesion: 0.20
Nodes (7): _module_available(), _pip_audit_findings(), _python(), run_bandit(), run_pip_audit(), run_safety(), ScanResult

### Community 153 - "financial_chart.py"
Cohesion: 0.18
Nodes (10): _as_date(), _bucket_start(), build_financial_chart(), _created_date(), _events(), _granularity(), _month_end(), _next_bucket() (+2 more)

### Community 157 - "test_login_otp.py"
Cohesion: 0.20
Nodes (4): codes_in(), LoginOTPMixin, TheCodeIsNotASecondKeyTests, TheCodeIsSpentAndExpiresTests

### Community 158 - "CaseFormMixin"
Cohesion: 0.17
Nodes (3): BootstrapFormMixin, CaseNoteForm, CaseFormMixin

### Community 179 - "identification.py"
Cohesion: 0.16
Nodes (5): format_identification(), _group_thousands(), normalize_number(), only_digits(), split_lookup()

### Community 184 - "case_manager/views.py"
Cohesion: 0.17
Nodes (3): authorized_client_pk(), PazYSalvoDownloadView, PazYSalvoView

### Community 186 - "upload_fields"
Cohesion: 0.18
Nodes (3): upload_fields(), TheCheckReadsTheRealPathsTests, upload_path()

### Community 187 - "dead_cache"
Cohesion: 0.15
Nodes (3): dead_cache(), PasswordResetLinkTests, PasswordResetWithoutCacheTests

### Community 197 - "netintel.py"
Cohesion: 0.21
Nodes (5): _compiled_networks(), country_code(), describe(), _geoip(), network_owner()

### Community 198 - "_safety_findings"
Cohesion: 0.21
Nodes (4): _lines_for(), _listed(), _safety_findings(), ReadingSafetysAnswerTests

### Community 199 - "test_reporting.py"
Cohesion: 0.24
Nodes (3): app_of(), _fake(), TheAppOfATestTests

### Community 212 - "CaseFinanceForm"
Cohesion: 0.21
Nodes (3): CaseFinanceForm, Meta, FreeModalityFormTests

### Community 219 - "nit_check_digit"
Cohesion: 0.24
Nodes (3): nit_check_digit(), CheckDigitTests, SeedTests

### Community 230 - "test_db_portability.py"
Cohesion: 0.32
Nodes (3): DbPortabilityTests, _is_excluded(), _offences()

## Knowledge Gaps
- **113 isolated node(s):** `Meta`, `Meta`, `Migration`, `Migration`, `Migration` (+108 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1960 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **179 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ClientModel` connect `ClientModel` to `test_reports.py`, `OfficeFallbackTests`, `make_user`, `TimeStampedModel`, `.toggle`, `django_test`, `CaseNoteCreateView`, `CaseNoteModel`, `Mandate`, `ClientForm`, `ClientToCasesTests`, `CaseFinanceModel`, `NoteVisibilityToggleTests`, `PazYSalvoAccessTests`, `LadderRulesTests`, `gestor.py`, `CaseModel`, `ClientCleanTests`, `ConfirmacionPazYSalvoTests`, `PublicQueryTests`, `AttemptLimitTests`, `case_manager/views.py`, `PublicCardFieldsTests`, `AttlasInsolvencyAuthModel`, `CspHeaderTests`, `GestorDashboardTests`, `CaseListView`, `VariosAsuntosTests`, `ClassificationTests`, `DetailRowsTests`, `ImportPropDemoTests`, `AccessCodeEmailTests`, `nit_check_digit`, `PortalNitTests`, `GestorRequiredMixin`, `ArbolAprobadoTests`, `upload_prefixes`, `seed_gestor_demo.py`, `CaseForm`, `LadderThroughThePortalTests`, `InlineBase`, `CodeLifetimeTests`, `MaskedEmailTests`, `test_backup.py`, `Command`, `PublicCaseQueryView`, `CaseCrudTests`, `GestorDashboardView`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `TimeStampedModel` connect `TimeStampedModel` to `django_db`, `AttlasInsolvencyFormModel`, `PQRSModel`, `AttlasInsolvencyCreditorsModel`, `django_test`, `insolvency_form/api/serializers.py`, `CaseNoteModel`, `CaseFinanceModel`, `FinancialEducationModel`, `faq/api/views.py`, `UserModel`, `CaseModel`, `core/views.py`, `AttlasInsolvencyAuthModel`, `ClientModel`, `otp_login.py`, `IPBlockedModel`, `PazYSalvoDocumentModel`, `insolvency_form/admin.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `CaseModel` connect `CaseModel` to `test_reports.py`, `OfficeFallbackTests`, `make_user`, `TimeStampedModel`, `.toggle`, `django_test`, `CaseNoteCreateView`, `CaseNoteModel`, `Mandate`, `NoteVisibilityToggleTests`, `ClientToCasesTests`, `CaseFinanceModel`, `PazYSalvoAccessTests`, `CaseFormMixin`, `gestor.py`, `dashboard_boxes.py`, `ConfirmacionPazYSalvoTests`, `PublicQueryTests`, `case_manager/views.py`, `PublicCardFieldsTests`, `AttlasInsolvencyAuthModel`, `CspHeaderTests`, `GestorDashboardTests`, `CaseListView`, `VariosAsuntosTests`, `paz_y_salvo.py`, `ClassificationTests`, `DetailRowsTests`, `ImportPropDemoTests`, `PazYSalvoDocumentAdmin`, `PortalNitTests`, `GestorRequiredMixin`, `ArbolAprobadoTests`, `upload_prefixes`, `seed_gestor_demo.py`, `CaseForm`, `LadderThroughThePortalTests`, `InlineBase`, `CodeLifetimeTests`, `test_backup.py`, `Command`, `PublicCaseQueryView`, `CaseCrudTests`, `GestorDashboardView`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `ClientModel` (e.g. with `CspHeaderTests` and `make_pii()`) actually correct?**
  _`ClientModel` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 61 inferred relationships involving `CaseModel` (e.g. with `CspHeaderTests` and `make_pii()`) actually correct?**
  _`CaseModel` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `CaseFinanceModel` (e.g. with `CaseFinanceInline` and `build_boxes()`) actually correct?**
  _`CaseFinanceModel` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Meta`, `Meta`, `Migration` to the rest of the system?**
  _113 weakly-connected nodes found - possible documentation gaps or missing edges._