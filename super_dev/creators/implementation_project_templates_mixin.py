"""Backend, migration and local-development project templates."""

from __future__ import annotations

import json


class ImplementationProjectTemplatesMixin:
    def generate_fastapi_project(self, module_requirements: dict[str, list[str]]) -> list[str]:
        """生成完整的 FastAPI 项目结构（含配置、中间件、异常处理）"""
        backend_dir = self.project_dir / "backend"
        src_dir = backend_dir / "src"
        files: list[str] = []

        # Project structure
        for sub in (
            "config",
            "middleware",
            "models",
            "schemas",
            "routes",
            "services",
            "repositories",
        ):
            pkg_dir = src_dir / sub
            pkg_dir.mkdir(parents=True, exist_ok=True)
            init_file = pkg_dir / "__init__.py"
            init_file.write_text("", encoding="utf-8")
            files.append(str(init_file))

        # Config
        config_file = src_dir / "config" / "settings.py"
        config_file.write_text(
            (
                "from __future__ import annotations\n\n"
                "from functools import lru_cache\n\n"
                "from pydantic_settings import BaseSettings\n\n\n"
                "class Settings(BaseSettings):\n"
                "    app_name: str = 'Super Dev API'\n"
                "    debug: bool = False\n"
                "    database_url: str = 'postgresql+asyncpg://user:pass@localhost:5432/app'\n"
                "    redis_url: str = 'redis://localhost:6379/0'\n"
                "    secret_key: str = 'change-me-in-production'\n"
                "    cors_origins: list[str] = ['http://localhost:3000']\n"
                "    log_level: str = 'INFO'\n\n"
                "    class Config:\n"
                "        env_file = '.env'\n"
                "        env_file_encoding = 'utf-8'\n\n\n"
                "@lru_cache()\n"
                "def get_settings() -> Settings:\n"
                "    return Settings()\n"
            ),
            encoding="utf-8",
        )
        files.append(str(config_file))

        # Middleware
        middleware_file = src_dir / "middleware" / "error_handler.py"
        middleware_file.write_text(
            (
                "from __future__ import annotations\n\n"
                "import logging\n"
                "import time\n\n"
                "from fastapi import Request, Response\n"
                "from starlette.middleware.base import BaseHTTPMiddleware\n\n"
                "logger = logging.getLogger(__name__)\n\n\n"
                "class RequestTimingMiddleware(BaseHTTPMiddleware):\n"
                "    async def dispatch(self, request: Request, call_next) -> Response:\n"
                "        start = time.perf_counter()\n"
                "        response = await call_next(request)\n"
                "        elapsed = time.perf_counter() - start\n"
                "        response.headers['X-Process-Time'] = f'{elapsed:.4f}'\n"
                "        logger.info(\n"
                "            '%s %s %s %.4fs',\n"
                "            request.method, request.url.path,\n"
                "            response.status_code, elapsed,\n"
                "        )\n"
                "        return response\n"
            ),
            encoding="utf-8",
        )
        files.append(str(middleware_file))

        # Main app
        app_file = src_dir / "main.py"
        route_imports = []
        route_includes = []
        for module_name in module_requirements:
            seg = self._safe_route_segment(module_name)
            ident = self._safe_identifier(module_name)
            route_imports.append(f"from .routes.{seg}_route import router as {ident}_router")
            route_includes.append(f"app.include_router({ident}_router)")

        app_file.write_text(
            (
                "from __future__ import annotations\n\n"
                "from fastapi import FastAPI\n"
                "from fastapi.middleware.cors import CORSMiddleware\n\n"
                "from .config.settings import get_settings\n"
                "from .middleware.error_handler import RequestTimingMiddleware\n"
                + ("\n".join(route_imports) + "\n" if route_imports else "")
                + "\n"
                "settings = get_settings()\n\n"
                "app = FastAPI(\n"
                "    title=settings.app_name,\n"
                "    debug=settings.debug,\n"
                "    docs_url='/api/docs',\n"
                "    redoc_url='/api/redoc',\n"
                ")\n\n"
                "app.add_middleware(\n"
                "    CORSMiddleware,\n"
                "    allow_origins=settings.cors_origins,\n"
                "    allow_credentials=True,\n"
                "    allow_methods=['*'],\n"
                "    allow_headers=['*'],\n"
                ")\n"
                "app.add_middleware(RequestTimingMiddleware)\n\n\n"
                "@app.get('/health')\n"
                "async def health() -> dict:\n"
                "    return {'status': 'ok', 'service': settings.app_name}\n\n\n"
                + "\n".join(route_includes)
                + "\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))

        # pyproject.toml
        pyproject = backend_dir / "pyproject.toml"
        pyproject.write_text(
            (
                "[project]\n"
                f'name = "{self.package_name}-backend"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.11"\n'
                "dependencies = [\n"
                '    "fastapi>=0.110.0",\n'
                '    "uvicorn[standard]>=0.27.0",\n'
                '    "pydantic>=2.0.2",\n'
                '    "pydantic-settings>=2.0.0",\n'
                '    "sqlalchemy[asyncio]>=2.0.0",\n'
                '    "asyncpg>=0.29.0",\n'
                '    "alembic>=1.13.0",\n'
                '    "redis>=5.0.0",\n'
                '    "python-dotenv>=1.0.0",\n'
                "]\n\n"
                "[project.optional-dependencies]\n"
                "dev = [\n"
                '    "pytest>=8.0.0",\n'
                '    "pytest-asyncio>=0.23.0",\n'
                '    "httpx>=0.27.0",\n'
                '    "ruff>=0.3.0",\n'
                '    "mypy>=1.8.0",\n'
                "]\n"
            ),
            encoding="utf-8",
        )
        files.append(str(pyproject))

        return files

    def generate_django_project(self, module_requirements: dict[str, list[str]]) -> list[str]:
        """生成 Django 项目结构骨架"""
        backend_dir = self.project_dir / "backend"
        project_dir = backend_dir / "config"
        project_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        # manage.py
        manage_file = backend_dir / "manage.py"
        manage_file.write_text(
            (
                "#!/usr/bin/env python\n"
                "import os\n"
                "import sys\n\n"
                "def main():\n"
                "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n"
                "    from django.core.management import execute_from_command_line\n"
                "    execute_from_command_line(sys.argv)\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n"
            ),
            encoding="utf-8",
        )
        files.append(str(manage_file))

        # settings.py
        settings_file = project_dir / "settings.py"
        installed_apps = ", ".join(f"'{self._safe_identifier(m)}'" for m in module_requirements)
        settings_file.write_text(
            (
                "from pathlib import Path\n"
                "import os\n\n"
                "BASE_DIR = Path(__file__).resolve().parent.parent\n"
                "SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')\n"
                "DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'\n"
                "ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')\n\n"
                "INSTALLED_APPS = [\n"
                "    'django.contrib.admin',\n"
                "    'django.contrib.auth',\n"
                "    'django.contrib.contenttypes',\n"
                "    'django.contrib.sessions',\n"
                "    'rest_framework',\n"
                f"    {installed_apps},\n"
                "]\n\n"
                "MIDDLEWARE = [\n"
                "    'django.middleware.security.SecurityMiddleware',\n"
                "    'django.contrib.sessions.middleware.SessionMiddleware',\n"
                "    'corsheaders.middleware.CorsMiddleware',\n"
                "    'django.middleware.common.CommonMiddleware',\n"
                "]\n\n"
                "ROOT_URLCONF = 'config.urls'\n"
                "DATABASES = {\n"
                "    'default': {\n"
                "        'ENGINE': 'django.db.backends.postgresql',\n"
                "        'NAME': os.getenv('DB_NAME', 'app'),\n"
                "        'USER': os.getenv('DB_USER', 'postgres'),\n"
                "        'PASSWORD': os.getenv('DB_PASSWORD', ''),\n"
                "        'HOST': os.getenv('DB_HOST', 'localhost'),\n"
                "        'PORT': os.getenv('DB_PORT', '5432'),\n"
                "    }\n"
                "}\n"
                "REST_FRAMEWORK = {\n"
                "    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',\n"
                "    'PAGE_SIZE': 20,\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(settings_file))

        # urls.py
        url_includes = [
            f"    path('api/{self._safe_route_segment(m)}/', include('{self._safe_identifier(m)}.urls')),"
            for m in module_requirements
        ]
        urls_file = project_dir / "urls.py"
        urls_file.write_text(
            (
                "from django.urls import include, path\n\n"
                "urlpatterns = [\n"
                "    path('health/', lambda r: __import__('django.http', fromlist=['JsonResponse']).JsonResponse({'status': 'ok'})),\n"
                + "\n".join(url_includes)
                + "\n]\n"
            ),
            encoding="utf-8",
        )
        files.append(str(urls_file))

        # App modules
        for module_name in module_requirements:
            ident = self._safe_identifier(module_name)
            app_dir = backend_dir / ident
            app_dir.mkdir(parents=True, exist_ok=True)

            (app_dir / "__init__.py").write_text("", encoding="utf-8")
            files.append(str(app_dir / "__init__.py"))

            (app_dir / "models.py").write_text(
                (
                    "from django.db import models\n\n\n"
                    f"class {self._to_component(module_name)}(models.Model):\n"
                    "    name = models.CharField(max_length=255)\n"
                    "    created_at = models.DateTimeField(auto_now_add=True)\n"
                    "    updated_at = models.DateTimeField(auto_now=True)\n\n"
                    "    class Meta:\n"
                    f"        db_table = '{ident}_items'\n"
                ),
                encoding="utf-8",
            )
            files.append(str(app_dir / "models.py"))

            (app_dir / "views.py").write_text(
                (
                    "from rest_framework import viewsets, serializers\n"
                    f"from .models import {self._to_component(module_name)}\n\n\n"
                    f"class {self._to_component(module_name)}Serializer(serializers.ModelSerializer):\n"
                    "    class Meta:\n"
                    f"        model = {self._to_component(module_name)}\n"
                    "        fields = '__all__'\n\n\n"
                    f"class {self._to_component(module_name)}ViewSet(viewsets.ModelViewSet):\n"
                    f"    queryset = {self._to_component(module_name)}.objects.all()\n"
                    f"    serializer_class = {self._to_component(module_name)}Serializer\n"
                ),
                encoding="utf-8",
            )
            files.append(str(app_dir / "views.py"))

            (app_dir / "urls.py").write_text(
                (
                    "from rest_framework.routers import DefaultRouter\n"
                    f"from .views import {self._to_component(module_name)}ViewSet\n\n"
                    "router = DefaultRouter()\n"
                    f"router.register(r'', {self._to_component(module_name)}ViewSet)\n"
                    "urlpatterns = router.urls\n"
                ),
                encoding="utf-8",
            )
            files.append(str(app_dir / "urls.py"))

        return files

    def generate_nestjs_project(self, module_requirements: dict[str, list[str]]) -> list[str]:
        """生成 NestJS 项目结构骨架"""
        backend_dir = self.project_dir / "backend"
        src_dir = backend_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        # package.json
        package_json = {
            "name": f"{self.package_name}-backend",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "start": "nest start",
                "start:dev": "nest start --watch",
                "start:prod": "node dist/main",
                "build": "nest build",
                "test": "jest",
                "test:e2e": "jest --config ./test/jest-e2e.json",
            },
            "dependencies": {
                "@nestjs/common": "^10.0.0",
                "@nestjs/core": "^10.0.0",
                "@nestjs/platform-express": "^10.0.0",
                "@nestjs/typeorm": "^10.0.0",
                "typeorm": "^0.3.20",
                "pg": "^8.11.0",
                "class-validator": "^0.14.0",
                "class-transformer": "^0.5.1",
            },
            "devDependencies": {
                "@nestjs/cli": "^10.0.0",
                "@nestjs/testing": "^10.0.0",
                "typescript": "^5.0.0",
                "jest": "^29.0.0",
                "ts-jest": "^29.0.0",
            },
        }
        package_file = backend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        # main.ts
        main_file = src_dir / "main.ts"
        main_file.write_text(
            (
                "import { NestFactory } from '@nestjs/core';\n"
                "import { ValidationPipe } from '@nestjs/common';\n"
                "import { AppModule } from './app.module';\n\n"
                "async function bootstrap() {\n"
                "  const app = await NestFactory.create(AppModule);\n"
                "  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));\n"
                "  app.enableCors();\n"
                "  await app.listen(3001);\n"
                "}\n"
                "bootstrap();\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))

        # app.module.ts
        module_imports = []
        module_import_stmts = []
        for module_name in module_requirements:
            comp = self._to_component(module_name)
            seg = self._safe_route_segment(module_name)
            module_imports.append(f"{comp}Module")
            module_import_stmts.append(f"import {{ {comp}Module }} from './{seg}/{seg}.module';")

        app_module = src_dir / "app.module.ts"
        app_module.write_text(
            (
                "import { Module } from '@nestjs/common';\n"
                + "\n".join(module_import_stmts)
                + "\n\n"
                "@Module({\n"
                f"  imports: [{', '.join(module_imports)}],\n"
                "})\n"
                "export class AppModule {}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_module))

        # Module files
        for module_name in module_requirements:
            comp = self._to_component(module_name)
            seg = self._safe_route_segment(module_name)
            mod_dir = src_dir / seg
            mod_dir.mkdir(parents=True, exist_ok=True)

            # entity
            (mod_dir / f"{seg}.entity.ts").write_text(
                (
                    "import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from 'typeorm';\n\n"
                    f"@Entity('{seg}_items')\n"
                    f"export class {comp}Entity {{\n"
                    "  @PrimaryGeneratedColumn()\n"
                    "  id: number;\n\n"
                    "  @Column()\n"
                    "  name: string;\n\n"
                    "  @CreateDateColumn()\n"
                    "  createdAt: Date;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            files.append(str(mod_dir / f"{seg}.entity.ts"))

            # service
            (mod_dir / f"{seg}.service.ts").write_text(
                (
                    "import { Injectable } from '@nestjs/common';\n"
                    "import { InjectRepository } from '@nestjs/typeorm';\n"
                    "import { Repository } from 'typeorm';\n"
                    f"import {{ {comp}Entity }} from './{seg}.entity';\n\n"
                    "@Injectable()\n"
                    f"export class {comp}Service {{\n"
                    f"  constructor(@InjectRepository({comp}Entity) private repo: Repository<{comp}Entity>) {{}}\n\n"
                    f"  findAll() {{ return this.repo.find(); }}\n"
                    f"  create(data: Partial<{comp}Entity>) {{ return this.repo.save(data); }}\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            files.append(str(mod_dir / f"{seg}.service.ts"))

            # controller
            (mod_dir / f"{seg}.controller.ts").write_text(
                (
                    "import { Controller, Get, Post, Body } from '@nestjs/common';\n"
                    f"import {{ {comp}Service }} from './{seg}.service';\n\n"
                    f"@Controller('api/{seg}')\n"
                    f"export class {comp}Controller {{\n"
                    f"  constructor(private readonly service: {comp}Service) {{}}\n\n"
                    "  @Get()\n"
                    "  findAll() { return this.service.findAll(); }\n\n"
                    "  @Post()\n"
                    "  create(@Body() body: any) { return this.service.create(body); }\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            files.append(str(mod_dir / f"{seg}.controller.ts"))

            # module
            (mod_dir / f"{seg}.module.ts").write_text(
                (
                    "import { Module } from '@nestjs/common';\n"
                    "import { TypeOrmModule } from '@nestjs/typeorm';\n"
                    f"import {{ {comp}Entity }} from './{seg}.entity';\n"
                    f"import {{ {comp}Service }} from './{seg}.service';\n"
                    f"import {{ {comp}Controller }} from './{seg}.controller';\n\n"
                    "@Module({\n"
                    f"  imports: [TypeOrmModule.forFeature([{comp}Entity])],\n"
                    f"  controllers: [{comp}Controller],\n"
                    f"  providers: [{comp}Service],\n"
                    "})\n"
                    f"export class {comp}Module {{}}\n"
                ),
                encoding="utf-8",
            )
            files.append(str(mod_dir / f"{seg}.module.ts"))

        return files

    def generate_alembic_migration(self, modules: list[str]) -> list[str]:
        """生成 Alembic 迁移配置和初始迁移脚本"""
        backend_dir = self.project_dir / "backend"
        alembic_dir = backend_dir / "alembic"
        versions_dir = alembic_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        # alembic.ini
        ini_file = backend_dir / "alembic.ini"
        ini_file.write_text(
            (
                "[alembic]\n"
                "script_location = alembic\n"
                "sqlalchemy.url = postgresql://user:pass@localhost:5432/app\n\n"
                "[loggers]\n"
                "keys = root,sqlalchemy,alembic\n\n"
                "[handlers]\n"
                "keys = console\n\n"
                "[formatters]\n"
                "keys = generic\n\n"
                "[logger_root]\n"
                "level = WARN\n"
                "handlers = console\n\n"
                "[logger_sqlalchemy]\n"
                "level = WARN\n"
                "handlers =\n"
                "qualname = sqlalchemy.engine\n\n"
                "[logger_alembic]\n"
                "level = INFO\n"
                "handlers =\n"
                "qualname = alembic\n\n"
                "[handler_console]\n"
                "class = StreamHandler\n"
                "args = (sys.stderr,)\n"
                "level = NOTSET\n"
                "formatter = generic\n\n"
                "[formatter_generic]\n"
                "format = %(levelname)-5.5s [%(name)s] %(message)s\n"
            ),
            encoding="utf-8",
        )
        files.append(str(ini_file))

        # env.py
        env_file = alembic_dir / "env.py"
        env_file.write_text(
            (
                "from alembic import context\n"
                "from sqlalchemy import engine_from_config, pool\n"
                "from logging.config import fileConfig\n\n"
                "config = context.config\n"
                "if config.config_file_name is not None:\n"
                "    fileConfig(config.config_file_name)\n\n"
                "target_metadata = None\n\n"
                "def run_migrations_online() -> None:\n"
                "    connectable = engine_from_config(\n"
                "        config.get_section(config.config_ini_section, {}),\n"
                "        prefix='sqlalchemy.',\n"
                "        poolclass=pool.NullPool,\n"
                "    )\n"
                "    with connectable.connect() as connection:\n"
                "        context.configure(connection=connection, target_metadata=target_metadata)\n"
                "        with context.begin_transaction():\n"
                "            context.run_migrations()\n\n"
                "run_migrations_online()\n"
            ),
            encoding="utf-8",
        )
        files.append(str(env_file))

        # Initial migration
        table_blocks = []
        for module_name in modules:
            seg = self._safe_route_segment(module_name)
            table_blocks.append(
                f"    op.create_table(\n"
                f"        '{seg}_items',\n"
                f"        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),\n"
                f"        sa.Column('name', sa.String(255), nullable=False),\n"
                f"        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),\n"
                f"        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),\n"
                f"    )"
            )

        drop_blocks = [
            f"    op.drop_table('{self._safe_route_segment(m)}_items')" for m in reversed(modules)
        ]

        migration_file = versions_dir / "001_initial_tables.py"
        migration_file.write_text(
            (
                '"""Initial tables"""\n\n'
                "revision = '001'\n"
                "down_revision = None\n\n"
                "import sqlalchemy as sa\n"
                "from alembic import op\n\n\n"
                "def upgrade() -> None:\n" + "\n".join(table_blocks) + "\n\n\n"
                "def downgrade() -> None:\n" + "\n".join(drop_blocks) + "\n"
            ),
            encoding="utf-8",
        )
        files.append(str(migration_file))

        return files

    def generate_prisma_schema(self, modules: list[str]) -> list[str]:
        """生成 Prisma schema 和迁移配置"""
        backend_dir = self.project_dir / "backend"
        prisma_dir = backend_dir / "prisma"
        prisma_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        model_blocks = []
        for module_name in modules:
            comp = self._to_component(module_name)
            model_blocks.append(
                f"model {comp} {{\n"
                f"  id        Int      @id @default(autoincrement())\n"
                f"  name      String   @db.VarChar(255)\n"
                f'  createdAt DateTime @default(now()) @map("created_at")\n'
                f'  updatedAt DateTime @updatedAt @map("updated_at")\n\n'
                f'  @@map("{self._safe_route_segment(module_name)}_items")\n'
                f"}}"
            )

        schema_file = prisma_dir / "schema.prisma"
        schema_file.write_text(
            (
                "generator client {\n"
                '  provider = "prisma-client-js"\n'
                "}\n\n"
                "datasource db {\n"
                '  provider = "postgresql"\n'
                '  url      = env("DATABASE_URL")\n'
                "}\n\n" + "\n\n".join(model_blocks) + "\n"
            ),
            encoding="utf-8",
        )
        files.append(str(schema_file))

        return files

    def generate_typeorm_migration(self, modules: list[str]) -> list[str]:
        """生成 TypeORM 迁移配置和初始迁移"""
        backend_dir = self.project_dir / "backend"
        migrations_dir = backend_dir / "src" / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        # ormconfig
        ormconfig = backend_dir / "ormconfig.json"
        ormconfig.write_text(
            json.dumps(
                {
                    "type": "postgres",
                    "host": "localhost",
                    "port": 5432,
                    "username": "postgres",
                    "password": "",
                    "database": "app",
                    "entities": ["src/**/*.entity.ts"],
                    "migrations": ["src/migrations/*.ts"],
                    "cli": {"migrationsDir": "src/migrations"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        files.append(str(ormconfig))

        # Initial migration
        up_stmts = []
        down_stmts = []
        for module_name in modules:
            seg = self._safe_route_segment(module_name)
            up_stmts.append(
                f"        await queryRunner.query(`\n"
                f'            CREATE TABLE IF NOT EXISTS "{seg}_items" (\n'
                f'                "id" SERIAL PRIMARY KEY,\n'
                f'                "name" VARCHAR(255) NOT NULL,\n'
                f'                "createdAt" TIMESTAMP DEFAULT now(),\n'
                f'                "updatedAt" TIMESTAMP DEFAULT now()\n'
                f"            )\n"
                f"        `);"
            )
            down_stmts.append(
                f'        await queryRunner.query(`DROP TABLE IF EXISTS "{seg}_items"`);'
            )

        migration_file = migrations_dir / "1_InitialTables.ts"
        migration_file.write_text(
            (
                "import { MigrationInterface, QueryRunner } from 'typeorm';\n\n"
                "export class InitialTables1 implements MigrationInterface {\n"
                "    async up(queryRunner: QueryRunner): Promise<void> {\n"
                + "\n".join(up_stmts)
                + "\n    }\n\n"
                "    async down(queryRunner: QueryRunner): Promise<void> {\n"
                + "\n".join(down_stmts)
                + "\n    }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(migration_file))

        return files

    def generate_docker_dev_config(self) -> list[str]:
        """生成 Docker 开发环境配置（docker-compose + Dockerfiles）"""
        files: list[str] = []

        # docker-compose.yml
        compose_file = self.project_dir / "docker-compose.yml"
        backend_kind = self.backend.lower()
        backend_cmd = {
            "python": "uvicorn src.main:app --host 0.0.0.0 --port 3001 --reload",
            "node": "node src/app.js",
            "go": "go run src/main.go",
        }.get(backend_kind, "node src/app.js")

        compose_file.write_text(
            (
                "version: '3.8'\n\n"
                "services:\n"
                "  frontend:\n"
                "    build:\n"
                "      context: ./frontend\n"
                "      dockerfile: Dockerfile.dev\n"
                "    ports:\n"
                "      - '3000:3000'\n"
                "    volumes:\n"
                "      - ./frontend/src:/app/src\n"
                "    environment:\n"
                "      - VITE_API_URL=http://localhost:3001\n\n"
                "  api:\n"
                "    build:\n"
                "      context: ./backend\n"
                "      dockerfile: Dockerfile.dev\n"
                "    ports:\n"
                "      - '3001:3001'\n"
                "    volumes:\n"
                "      - ./backend/src:/app/src\n"
                "    environment:\n"
                "      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/app\n"
                "      - REDIS_URL=redis://redis:6379/0\n"
                f"    command: {backend_cmd}\n"
                "    depends_on:\n"
                "      postgres:\n"
                "        condition: service_healthy\n"
                "      redis:\n"
                "        condition: service_healthy\n\n"
                "  postgres:\n"
                "    image: postgres:16-alpine\n"
                "    ports:\n"
                "      - '5432:5432'\n"
                "    environment:\n"
                "      POSTGRES_USER: postgres\n"
                "      POSTGRES_PASSWORD: postgres\n"
                "      POSTGRES_DB: app\n"
                "    volumes:\n"
                "      - pgdata:/var/lib/postgresql/data\n"
                "    healthcheck:\n"
                "      test: ['CMD-SHELL', 'pg_isready -U postgres']\n"
                "      interval: 5s\n"
                "      timeout: 5s\n"
                "      retries: 5\n\n"
                "  redis:\n"
                "    image: redis:7-alpine\n"
                "    ports:\n"
                "      - '6379:6379'\n"
                "    healthcheck:\n"
                "      test: ['CMD', 'redis-cli', 'ping']\n"
                "      interval: 5s\n"
                "      timeout: 5s\n"
                "      retries: 5\n\n"
                "volumes:\n"
                "  pgdata:\n"
            ),
            encoding="utf-8",
        )
        files.append(str(compose_file))

        # Frontend Dockerfile.dev
        frontend_dir = self.project_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        frontend_dockerfile = frontend_dir / "Dockerfile.dev"
        frontend_dockerfile.write_text(
            (
                "FROM node:20-alpine\n"
                "WORKDIR /app\n"
                "COPY package*.json ./\n"
                "RUN npm ci\n"
                "COPY . .\n"
                "EXPOSE 3000\n"
                'CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]\n'
            ),
            encoding="utf-8",
        )
        files.append(str(frontend_dockerfile))

        # Backend Dockerfile.dev
        backend_dir = self.project_dir / "backend"
        backend_dir.mkdir(parents=True, exist_ok=True)
        backend_dockerfile = backend_dir / "Dockerfile.dev"
        if backend_kind == "python":
            backend_dockerfile.write_text(
                (
                    "FROM python:3.12-slim\n"
                    "WORKDIR /app\n"
                    "COPY requirements.txt pyproject.toml* ./\n"
                    "RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || pip install --no-cache-dir -e '.[dev]'\n"
                    "COPY . .\n"
                    "EXPOSE 3001\n"
                    'CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3001", "--reload"]\n'
                ),
                encoding="utf-8",
            )
        else:
            backend_dockerfile.write_text(
                (
                    "FROM node:20-alpine\n"
                    "WORKDIR /app\n"
                    "COPY package*.json ./\n"
                    "RUN npm ci\n"
                    "COPY . .\n"
                    "EXPOSE 3001\n"
                    'CMD ["node", "src/app.js"]\n'
                ),
                encoding="utf-8",
            )
        files.append(str(backend_dockerfile))

        # .dockerignore
        dockerignore = self.project_dir / ".dockerignore"
        dockerignore.write_text(
            "node_modules\n"
            ".git\n"
            ".env\n"
            "__pycache__\n"
            "*.pyc\n"
            ".mypy_cache\n"
            ".pytest_cache\n"
            "dist\n"
            "build\n"
            ".next\n"
            "coverage\n",
            encoding="utf-8",
        )
        files.append(str(dockerignore))

        return files

    def generate_env_config(self) -> list[str]:
        """生成环境变量管理文件（.env.example + 验证脚本）"""
        files: list[str] = []

        # .env.example
        env_example = self.project_dir / ".env.example"
        env_example.write_text(
            (
                "# ============================================\n"
                f"# {self.name} Environment Variables\n"
                "# ============================================\n"
                "# Copy this file to .env and fill in the values\n\n"
                "# --- Application ---\n"
                "NODE_ENV=development\n"
                "APP_PORT=3001\n"
                "APP_URL=http://localhost:3001\n"
                "FRONTEND_URL=http://localhost:3000\n\n"
                "# --- Database ---\n"
                "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app\n"
                "DB_HOST=localhost\n"
                "DB_PORT=5432\n"
                "DB_NAME=app\n"
                "DB_USER=postgres\n"
                "DB_PASSWORD=postgres\n\n"
                "# --- Redis ---\n"
                "REDIS_URL=redis://localhost:6379/0\n\n"
                "# --- Auth ---\n"
                "SECRET_KEY=change-me-in-production\n"
                "JWT_SECRET=change-me-in-production\n"
                "JWT_EXPIRES_IN=7d\n\n"
                "# --- External Services ---\n"
                "# SMTP_HOST=smtp.example.com\n"
                "# SMTP_PORT=587\n"
                "# SMTP_USER=\n"
                "# SMTP_PASS=\n"
                "# S3_BUCKET=\n"
                "# S3_REGION=\n"
                "# S3_ACCESS_KEY=\n"
                "# S3_SECRET_KEY=\n\n"
                "# --- Monitoring ---\n"
                "LOG_LEVEL=info\n"
                "# SENTRY_DSN=\n"
            ),
            encoding="utf-8",
        )
        files.append(str(env_example))

        # env validation script (Python)
        scripts_dir = self.project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        validate_env = scripts_dir / "validate_env.py"
        validate_env.write_text(
            (
                '"""Validate environment variables against .env.example."""\n\n'
                "from __future__ import annotations\n\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n\n\n"
                "def load_env_example(path: Path) -> dict[str, str]:\n"
                "    variables: dict[str, str] = {}\n"
                "    if not path.exists():\n"
                "        return variables\n"
                "    for line in path.read_text().splitlines():\n"
                "        line = line.strip()\n"
                "        if not line or line.startswith('#'):\n"
                "            continue\n"
                "        key, _, default = line.partition('=')\n"
                "        variables[key.strip()] = default.strip()\n"
                "    return variables\n\n\n"
                "def validate() -> bool:\n"
                "    project_root = Path(__file__).resolve().parents[1]\n"
                "    example = load_env_example(project_root / '.env.example')\n"
                "    if not example:\n"
                "        print('No .env.example found, skipping validation.')\n"
                "        return True\n\n"
                "    required = [k for k, v in example.items() if not k.startswith('#') and not v.startswith('change-me')]\n"
                "    missing = [k for k in required if not os.getenv(k)]\n"
                "    secrets_with_defaults = [\n"
                "        k for k, v in example.items()\n"
                "        if 'change-me' in v and os.getenv(k, '') in ('', v)\n"
                "    ]\n\n"
                "    ok = True\n"
                "    if missing:\n"
                "        print(f'Missing required env vars: {\", \".join(missing)}')\n"
                "        ok = False\n"
                "    if secrets_with_defaults:\n"
                "        print(f'Secrets still using default values: {\", \".join(secrets_with_defaults)}')\n"
                "        if os.getenv('NODE_ENV') == 'production':\n"
                "            ok = False\n"
                "    if ok:\n"
                "        print('Environment validation passed.')\n"
                "    return ok\n\n\n"
                "if __name__ == '__main__':\n"
                "    sys.exit(0 if validate() else 1)\n"
            ),
            encoding="utf-8",
        )
        files.append(str(validate_env))

        # .gitignore additions
        gitignore_file = self.project_dir / ".gitignore"
        gitignore_additions = "\n# Environment\n.env\n.env.local\n.env.*.local\n"
        if gitignore_file.exists():
            existing = gitignore_file.read_text(encoding="utf-8")
            if ".env" not in existing:
                gitignore_file.write_text(existing + gitignore_additions, encoding="utf-8")
                files.append(str(gitignore_file))
        else:
            gitignore_file.write_text(
                "node_modules/\n__pycache__/\n*.pyc\ndist/\nbuild/\n.next/\ncoverage/\n"
                + gitignore_additions,
                encoding="utf-8",
            )
            files.append(str(gitignore_file))

        return files
