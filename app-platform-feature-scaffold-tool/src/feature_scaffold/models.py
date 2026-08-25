from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


AuthMode = Literal["entra", "mock", "none"]
RegistryMode = Literal["rest", "file", "none"]
BackendTokenStrategy = Literal["forwarded-bearer", "shell-session", "none", "bearer"]
FrontendFramework = Literal["react-vite"]
BackendFramework = Literal["fastapi"]
DeploymentTarget = Literal["azure-container-apps", "app-service", "none"]
TriggerKind = Literal["queue", "topic-subscription"]
FilePolicy = Literal["replace", "create_if_missing", "manual"]


@dataclass(slots=True)
class RetryPolicy:
    max_retries: int = 3
    backoff: str = "exponential"


@dataclass(slots=True)
class FrontendConfig:
    enabled: bool = True
    framework: FrontendFramework = "react-vite"
    shell_integration: bool = True


@dataclass(slots=True)
class BackendConfig:
    enabled: bool = True
    framework: BackendFramework = "fastapi"
    api_base_path: str = "/api"


@dataclass
class AuthConfig:
    mode: str = "mock"
    shell_auth_required: bool = True
    token_forwarding: bool = False
    allowed_dev_modes: list[str] = field(default_factory=lambda: ["mock"])
    roles: list[str] = field(default_factory=list)
    backend_token_strategy: str = "none"

@dataclass(slots=True)
class RegistryConfig:
    enabled: bool = True
    mode: RegistryMode = "rest"
    manifest_publish: bool = True


@dataclass(slots=True)
class ScheduledJobConfig:
    name: str
    description: str = ""
    schedule: str = ""
    entrypoint: str = ""
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass(slots=True)
class EventTriggerConfig:
    kind: TriggerKind = "topic-subscription"
    topic: str = ""
    subscription: str = ""
    queue: str = ""


@dataclass(slots=True)
class EventDrivenJobConfig:
    name: str
    description: str = ""
    trigger: EventTriggerConfig = field(default_factory=EventTriggerConfig)
    payload_schema: str = ""
    dead_letter: bool = True
    max_concurrency: int = 1
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass(slots=True)
class EventListenerConfig:
    name: str
    description: str = ""
    event_name: str = ""
    payload_schema: str = ""


@dataclass(slots=True)
class EventContract:
    name: str
    schema: str


@dataclass(slots=True)
class EventsConfig:
    publishes: list[EventContract] = field(default_factory=list)
    consumes: list[EventContract] = field(default_factory=list)

@dataclass(slots=True)
class ApiDeploymentConfig:
    enabled: bool = True
    runtime: str = "container-app"
    container_app_name: str = ""
    image_repository: str = ""
    port: int = 8000


@dataclass(slots=True)
class JobDeploymentTargetConfig:
    name: str
    enabled: bool = True
    runtime: str = "container-app-job"
    container_app_name: str = ""
    image_repository: str = ""
    trigger_type: str = "schedule"


@dataclass(slots=True)
class ListenerDeploymentTargetConfig:
    name: str
    enabled: bool = True
    runtime: str = "container-app"
    container_app_name: str = ""
    image_repository: str = ""


# @dataclass(slots=True)
# class DeploymentConfig:
#     backend_target: DeploymentTarget = "azure-container-apps"
#     worker_target: DeploymentTarget = "azure-container-apps"
#     include_terraform: bool = True
#     include_github_actions: bool = True


@dataclass(slots=True)
class DeploymentConfig:
    api: ApiDeploymentConfig = field(default_factory=ApiDeploymentConfig)
    jobs: list[JobDeploymentTargetConfig] = field(default_factory=list)
    listeners: list[ListenerDeploymentTargetConfig] = field(default_factory=list)
    @property
    def backend_target(self) -> ApiDeploymentConfig:
        """
        Backward compatibility for existing templates/tests.
        """
        return self.api
    
    @property
    def worker_target(self) -> JobDeploymentTargetConfig:
        """
        Backward compatibility for existing templates/tests that expect a single worker target.
        Returns the first configured job deployment target, or a default placeholder.
        """
        if self.jobs:
            return self.jobs[0]
        return JobDeploymentTargetConfig(name="")

    @property
    def listener_target(self) -> ListenerDeploymentTargetConfig:
        """
        Backward compatibility for existing templates/tests that expect a single listener target.
        Returns the first configured listener deployment target, or a default placeholder.
        """
        if self.listeners:
            return self.listeners[0]
        return ListenerDeploymentTargetConfig(name="")

    @property
    def include_terraform(self) -> bool:
        """
        Backward compatibility: assume infra is enabled unless explicitly disabled.
        """
        return True

    @property
    def include_github_actions(self) -> bool:
        """
        Backward compatibility: assume CI/CD is enabled.
        """
        return True

@dataclass(slots=True)
class DeveloperExperienceConfig:
    include_docs: bool = True
    include_tests: bool = True
    include_scripts: bool = True


@dataclass
class PostgresCapabilityConfig:
    enabled: bool = False
    orm: bool = True
    migrations: bool = True


@dataclass
class SnowflakeCapabilityConfig:
    enabled: bool = False


@dataclass
class DatabaseProvidersConfig:
    postgresql: PostgresCapabilityConfig = field(default_factory=PostgresCapabilityConfig)
    snowflake: SnowflakeCapabilityConfig = field(default_factory=SnowflakeCapabilityConfig)


@dataclass
class DatabaseCapabilityConfig:
    enabled: bool = False
    targets: list[str] = field(default_factory=list)
    providers: DatabaseProvidersConfig = field(default_factory=DatabaseProvidersConfig)


@dataclass
class BlobStorageCapabilityConfig:
    enabled: bool = False
    provider: str = "azure_blob"
    targets: list[str] = field(default_factory=list)


@dataclass
class MemoryCacheCapabilityConfig:
    enabled: bool = True


@dataclass
class RedisCacheCapabilityConfig:
    enabled: bool = False


@dataclass
class CacheProvidersConfig:
    memory: MemoryCacheCapabilityConfig = field(default_factory=MemoryCacheCapabilityConfig)
    redis: RedisCacheCapabilityConfig = field(default_factory=RedisCacheCapabilityConfig)


@dataclass
class CacheCapabilityConfig:
    enabled: bool = False
    targets: list[str] = field(default_factory=list)
    providers: CacheProvidersConfig = field(default_factory=CacheProvidersConfig)


@dataclass
class CapabilitiesConfig:
    database: DatabaseCapabilityConfig = field(default_factory=DatabaseCapabilityConfig)
    blob_storage: BlobStorageCapabilityConfig = field(default_factory=BlobStorageCapabilityConfig)
    cache: CacheCapabilityConfig = field(default_factory=CacheCapabilityConfig)


@dataclass(slots=True)
class ScaffoldConfig:
    feature_name: str
    display_name: str
    base_path: str

    description: str = ""
    version: str = "0.1.0"

    frontend: FrontendConfig = field(default_factory=FrontendConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)

    scheduled_jobs: list[ScheduledJobConfig] = field(default_factory=list)
    event_driven_jobs: list[EventDrivenJobConfig] = field(default_factory=list)
    event_listeners: list[EventListenerConfig] = field(default_factory=list)
    events: EventsConfig = field(default_factory=EventsConfig)

    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    developer_experience: DeveloperExperienceConfig = field(default_factory=DeveloperExperienceConfig)

    capabilities: CapabilitiesConfig = field(default_factory=CapabilitiesConfig)


@dataclass(slots=True)
class NormalizedNames:
    feature_key: str
    repo_name: str
    display_name: str
    title_case_name: str
    description: str
    base_path: str
    api_base_path: str
    python_package_name: str
    frontend_package_name: str
    backend_module_name: str
    feature_var_prefix: str


@dataclass(slots=True)
class NormalizedScaffoldConfig:
    names: NormalizedNames

    manifest_version: str

    frontend_enabled: bool
    backend_enabled: bool

    shell_integration: bool
    registry_enabled: bool
    registry_mode: RegistryMode

    auth_mode: str
    auth_context_source: str
    auth_shell_auth_required: bool
    auth_token_forwarding: bool
    auth_allowed_dev_modes: list[str]
    auth_roles: list[str]
    backend_token_strategy: str

    scheduled_jobs: list[ScheduledJobConfig]
    event_driven_jobs: list[EventDrivenJobConfig]
    event_listeners: list[EventListenerConfig]

    published_events: list[EventContract]
    consumed_events: list[EventContract]

    backend_target: ApiDeploymentConfig
    worker_target: JobDeploymentTargetConfig

    include_terraform: bool
    include_github_actions: bool
    include_docs: bool
    include_tests: bool
    include_scripts: bool

    database_enabled: bool
    database_targets: list[str]
    postgres_enabled: bool
    postgres_orm_enabled: bool
    postgres_migrations_enabled: bool
    snowflake_enabled: bool
    blob_storage_enabled: bool
    blob_storage_provider: str
    blob_storage_targets: list[str]

    # --- cache capability ---
    cache_enabled: bool = False
    cache_targets: list[str] = field(default_factory=list)
    memory_cache_enabled: bool = True
    redis_enabled: bool = False

@dataclass(slots=True)
class PlannedFile:
    target_path: str
    template_path: str | None = None
    literal_content: str | None = None
    template_context: dict | None = None
    policy: FilePolicy = "replace"