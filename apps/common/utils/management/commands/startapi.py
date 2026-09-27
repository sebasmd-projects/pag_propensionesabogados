# apps/common/core/management/commands/startapi.py

from pathlib import Path

from django.core.management.commands.startapp import Command as StartAppCommand


class Command(StartAppCommand):
    """
    Generates a Django app with a full REST API scaffold.

    Usage:
        python manage.py startapi <app_name> <directory>

    Examples:
        python manage.py startapi users apps/common/users_and_auth
        python manage.py startapi users apps.common.users_and_auth
        python manage.py startapi users apps/common/users_and_auth/
    """

    help = (
        "Creates a Django app with REST API structure (models/, api/v1/, tests/, tasks.py).\n"
        "Usage: python manage.py startapi <app_name> <directory>"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Argument definition
    # ─────────────────────────────────────────────────────────────────────────

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "name",
            help="Name of the application (e.g. users)",
        )
        parser.add_argument(
            "directory",
            help=(
                "Target directory. Accepts slash-path (apps/common/module) "
                "or dot-notation (apps.common.module). Trailing slash/dot is stripped."
            ),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────────────────────────

    def handle(self, **options) -> None:
        app_name: str = options["name"]
        raw_dir: str = options["directory"]

        # Normalize: replace dots with slashes, strip trailing separators
        directory: str = raw_dir.replace(".", "/").strip("/")

        app_path: Path = Path(directory) / app_name
        app_module: str = f"{directory.replace('/', '.')}.{app_name}"
        base_path: str = f"{directory}/{app_name}"

        self._create_app_structure(app_name, app_path, app_module, base_path)

        # ASCII-only output: Windows consoles often use cp1252, where non-ASCII
        # glyphs (e.g. a check mark) raise UnicodeEncodeError after the files
        # were already written, making the command exit non-zero spuriously.
        self.stdout.write(
            self.style.SUCCESS(
                f"\n[OK]  App '{app_name}' created at  {app_path}/\n"
                f"      Module path: {app_module}\n"
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Structure orchestrator
    # ─────────────────────────────────────────────────────────────────────────

    def _create_app_structure(self, app_name: str, app_path: Path, app_module: str, base_path: str) -> None:
        app_path.mkdir(parents=True, exist_ok=True)

        # ── Root files ────────────────────────────────────────────────────────
        self._write(
            "__init__.py",
            app_path / "__init__.py",
            self._root_init(base_path)
        )
        self._write(
            "apps.py",
            app_path / "apps.py",
            self._apps(app_name, app_module, base_path)
        )
        self._write(
            "admin.py",
            app_path / "admin.py",
            self._admin(base_path)
        )
        self._write(
            "tasks.py",
            app_path / "tasks.py",
            self._tasks(base_path)
        )
        self._write(
            "urls.py",
            app_path / "urls.py",
            self._urls_main(app_name, base_path)
        )
        self._write(
            "README.md",
            app_path / "README.md",
            self._readme(app_name, app_module, base_path)
        )

        # ── models/ ───────────────────────────────────────────────────────────
        models_dir: Path = app_path / "models"
        models_dir.mkdir(exist_ok=True)
        self._write(
            "models/__init__.py",
            models_dir / "__init__.py",
            self._models_init(base_path)
        )
        self._write(
            "models/managers.py",
            models_dir / "managers.py",
            self._models_managers(base_path)
        )
        self._write(
            "models/signals.py",
            models_dir / "signals.py",
            self._models_signals(base_path)
        )

        # ── api/v1/ ───────────────────────────────────────────────────────────
        api_dir: Path = app_path / "api"
        v1_dir: Path = api_dir / "v1"
        api_dir.mkdir(exist_ok=True)
        v1_dir.mkdir(exist_ok=True)
        self._write(
            "api/__init__.py",
            api_dir / "__init__.py",
            self._generic_init(f"{base_path}/api")
        )
        self._write(
            "api/v1/__init__.py",
            v1_dir / "__init__.py",
            self._generic_init(f"{base_path}/api/v1")
        )
        self._write(
            "api/v1/serializers.py",
            v1_dir / "serializers.py",
            self._v1_serializers(base_path)
        )
        self._write(
            "api/v1/filters.py",
            v1_dir / "filters.py",
            self._v1_filters(base_path)
        )
        self._write(
            "api/v1/views.py",
            v1_dir / "views.py",
            self._v1_views(base_path)
        )
        self._write(
            "api/v1/permissions.py",
            v1_dir / "permissions.py",
            self._v1_permissions(base_path)
        )
        self._write(
            "api/v1/urls.py",
            v1_dir / "urls.py",
            self._urls_api(base_path)
        )

        # ── tests/ ────────────────────────────────────────────────────────────
        tests_dir: Path = app_path / "tests"
        tests_dir.mkdir(exist_ok=True)
        self._write(
            "tests/__init__.py",
            tests_dir / "__init__.py",
            self._generic_init(f"{base_path}/tests")
        )
        self._write(
            "tests/factories.py",
            tests_dir / "factories.py",
            self._test_factories(base_path)
        )
        self._write(
            "tests/test_models.py",
            tests_dir / "test_models.py",
            self._test_models(base_path)
        )
        self._write(
            "tests/test_views.py",
            tests_dir / "test_views.py",
            self._test_views(base_path)
        )
        self._write(
            "tests/test_api.py",
            tests_dir / "test_api.py",
            self._test_api(base_path)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # File writer helper
    # ─────────────────────────────────────────────────────────────────────────

    def _write(self, label: str, path: Path, content: str) -> None:
        if path.exists():
            self.stdout.write(self.style.WARNING(
                f"  [skip]  {label}  (already exists)"))
            return
        path.write_text(content, encoding="utf-8")
        self.stdout.write(f"  [ok]    {label}")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_class_name(app_name: str) -> str:
        """Convert snake_case app name to PascalCase config class name."""
        return "".join(part.capitalize() for part in app_name.split("_"))

    # ─────────────────────────────────────────────────────────────────────────
    # Content generators ── root
    # ─────────────────────────────────────────────────────────────────────────

    def _root_init(self, base_path: str) -> str:
        return f"# {base_path}/__init__.py\n"

    def _generic_init(self, path_str: str) -> str:
        return f"# {path_str}/__init__.py\n"

    def _apps(self, app_name: str, app_module: str, base_path: str) -> str:
        cls = self._to_class_name(app_name)
        return (
            f"# {base_path}/apps.py\n\n"
            f"from django.apps import AppConfig\n\n\n"
            f"class {cls}Config(AppConfig):\n"
            f"    default_auto_field = 'django.db.models.BigAutoField'\n"
            f"    name = '{app_module}'\n"
            f"    verbose_name = '{cls}APP'\n"
        )

    def _admin(self, base_path: str) -> str:
        return (
            f"# {base_path}/admin.py\n\n"
            f"from django.contrib import admin\n"
        )

    def _tasks(self, base_path: str) -> str:
        return (
            f"# {base_path}/tasks.py\n\n"
            f"# from celery import shared_task\n\n\n"
            f"# @shared_task\n"
            f"# def example_task():\n"
            f"#     pass\n"
        )

    def _urls_main(self, app_name: str, base_path: str) -> str:
        return (
            f"# {base_path}/urls.py\n\n"
            f"from django.urls import include, path\n\n"
            f"from .api.v1 import urls as api_urls\n\n"
            f"app_name = '{app_name}'\n\n"
            f"urlpatterns = [\n"
            f"    path('api/v1/', include(api_urls)),\n"
            f"]\n"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Content generators ── models/
    # ─────────────────────────────────────────────────────────────────────────

    def _models_init(self, base_path: str) -> str:
        return (
            f"# {base_path}/models/__init__.py\n\n"
            f"from django.db import models\n"
            f"from django.utils.translation import gettext_lazy as _\n\n"
            f"from apps.common.core.models import TimeStampedModel\n\n\n"
        )

    def _models_managers(self, base_path: str) -> str:
        return (
            f"# {base_path}/models/managers.py\n\n"
            f"from django.db import models\n\n\n"
        )

    def _models_signals(self, base_path: str) -> str:
        return (
            f"# {base_path}/models/signals.py\n\n"
            f"from django.db.models.signals import post_save, pre_save\n"
            f"from django.dispatch import receiver\n"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Content generators ── api/v1/
    # ─────────────────────────────────────────────────────────────────────────

    def _v1_serializers(self, base_path: str) -> str:
        return (
            f"# {base_path}/api/v1/serializers.py\n\n"
            f"from rest_framework import serializers\n\n\n"
        )

    def _v1_filters(self, base_path: str) -> str:
        return (
            f"# {base_path}/api/v1/filters.py\n\n"
            f"import django_filters\n\n\n"
        )

    def _v1_views(self, base_path: str) -> str:
        return (
            f"# {base_path}/api/v1/views.py\n\n"
            f"from rest_framework import viewsets\n"
            f"from rest_framework import generics\n"
            f"from rest_framework import views\n\n\n"
        )

    def _v1_permissions(self, base_path: str) -> str:
        return (
            f"# {base_path}/api/v1/permissions.py\n\n"
            f"from rest_framework import permissions\n\n\n"
        )

    def _urls_api(self, base_path: str) -> str:
        return (
            f"# {base_path}/api/v1/urls.py\n\n"
            f"from django.urls import include, path\n\n"
            f"urlpatterns = []\n"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Content generators ── tests/
    # ─────────────────────────────────────────────────────────────────────────

    def _test_factories(self, base_path: str) -> str:
        return (
            f"# {base_path}/tests/factories.py\n\n"
            f"import factory\n\n\n"
        )

    def _test_models(self, base_path: str) -> str:
        return (
            f"# {base_path}/tests/test_models.py\n\n"
            f"import pytest\n\n\n"
        )

    def _test_views(self, base_path: str) -> str:
        return (
            f"# {base_path}/tests/test_views.py\n\n"
            f"import pytest\n\n\n"
        )

    def _test_api(self, base_path: str) -> str:
        return (
            f"# {base_path}/tests/test_api.py\n\n"
            f"import pytest\n\n\n"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Content generators ── README.md
    # ─────────────────────────────────────────────────────────────────────────

    def _readme(self, app_name: str, app_module: str, base_path: str) -> str:
        title = " ".join(part.capitalize() for part in app_name.split("_"))
        return (
            f"# {title}\n\n"
            f"## App Module\n\n"
            f"```\n"
            f"{app_module}\n"
            f"```\n\n"
            f"## Description\n\n"
            f"> TODO: Add a description for this app.\n\n"
            f"## Installation\n\n"
            f"Add to `INSTALLED_APPS` in your settings:\n\n"
            f"```python\n"
            f"INSTALLED_APPS = [\n"
            f"    ...\n"
            f"    '{app_module}',\n"
            f"]\n"
            f"```\n\n"
            f"Include the URLs in your project's `urls.py`:\n\n"
            f"```python\n"
            f"urlpatterns = [\n"
            f"    ...\n"
            f"    path('{app_name}/', include('{app_module}.urls')),\n"
            f"]\n"
            f"```\n\n"
            f"## Structure\n\n"
            f"```\n"
            f"{app_name}/\n"
            f"├── __init__.py\n"
            f"├── apps.py\n"
            f"├── admin.py\n"
            f"├── tasks.py\n"
            f"├── urls.py\n"
            f"├── README.md\n"
            f"├── models/\n"
            f"│   ├── __init__.py\n"
            f"│   ├── managers.py\n"
            f"│   └── signals.py\n"
            f"├── api/\n"
            f"│   └── v1/\n"
            f"│       ├── __init__.py\n"
            f"│       ├── serializers.py\n"
            f"│       ├── permissions.py\n"
            f"│       ├── filters.py\n"
            f"│       ├── views.py\n"
            f"│       └── urls.py\n"
            f"└── tests/\n"
            f"    ├── __init__.py\n"
            f"    ├── factories.py\n"
            f"    ├── test_models.py\n"
            f"    ├── test_views.py\n"
            f"    └── test_api.py\n"
            f"```\n\n"
            f"## API Endpoints (v1)\n\n"
            f"| Method | URL  | Description |\n"
            f"|--------|------|-------------|\n"
            f"|  TODO  | TODO |    TODO     |\n\n"
            f"## Models\n\n"
            f"> TODO: Document models.\n\n"
            f"## Tasks\n\n"
            f"> TODO: Document Celery tasks.\n"
        )
