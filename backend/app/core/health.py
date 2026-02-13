import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import text
from backend.app.core.db import async_session_factory
from backend.app.core.celery_app import celery_app
from backend.app.core.logging import get_logger

logger = get_logger()


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    DOWN = "down"


class HealthCheck:
    def __init__(self):
        self._services: Dict[str, ServiceStatus] = {}
        self._check_functions: Dict[str, Callable[[], Awaitable[bool]]] = {}
        self._last_check: Dict[
            str, datetime
        ] = {}  # Timestamp of the last health check per service
        self._timeout: Dict[str, float] = {}
        self._retry_delays: Dict[str, float] = {}
        self._max_retries: Dict[str, int] = {}
        self._dependencies: Dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

        self._cache_duration: timedelta = timedelta(seconds=30)
        self._cached_status: Optional[Dict[str, Any]] = None
        self._last_check_time: Optional[datetime] = (
            None  # Timestamp of the last health check was run
        )

    async def validate_dependencies(
        self, service_name: str, depends_on: list[str]
    ) -> None:
        if not depends_on:
            return

        for dependency in depends_on:
            if dependency not in self._services:
                raise ValueError(
                    f"Service '{service_name}' depends on unknown service '{dependency}'"
                )

    async def add_service(
        self,
        name: str,
        check_function: Callable[[], Awaitable[bool]],
        depends_on: Optional[list[str]] = None,
        timeout: float = 5.0,
        retry_delay: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        async with self._lock:
            if name in self._services:
                raise ValueError(f"Service '{name}' is already registered")

            if depends_on is None:
                depends_on = []

            self._services[name] = ServiceStatus.STARTING
            self._check_functions[name] = check_function
            self._last_check[name] = (
                datetime.now(timezone.utc) - self._cache_duration
            )  # Force an immediate check on first status request
            self._timeout[name] = timeout
            self._retry_delays[name] = retry_delay
            self._max_retries[name] = max_retries

            if depends_on:
                await self.validate_dependencies(name, depends_on)
                self._dependencies[name] = set(depends_on)
                logger.info(
                    f"Service '{name}' registered with dependencies: {depends_on}"
                )

    async def check_database(self) -> bool:
        try:
            # TODO: load models
            # TODO: add logger info
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                await session.commit()

                self._last_check["database"] = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def check_redis(self) -> bool:
        try:
            redis_client = celery_app.backend.client
            redis_client.ping()

            self._last_check["redis"] = datetime.now(timezone.utc)
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # Check if the health of celery or rabbitmq is healthy
    async def check_celery(self) -> bool:
        try:
            inspect = celery_app.control.inspect()
            workers = inspect.ping()

            if not workers:
                conn = celery_app.connection()
                try:
                    conn.ensure_connection(max_retries=3)
                    logger.warning(
                        "No celery workers found, but connection to RabbitMQ is healthy"
                    )
                    self._last_check["celery"] = datetime.now(timezone.utc)
                    return True
                finally:
                    conn.close()

            self._last_check["celery"] = datetime.now(timezone.utc)
            return True
        except Exception as e:
            logger.error(f"Celery connection check failed: {e}")
            return False

    async def check_service_health(self, service_name: str) -> ServiceStatus:
        # Check the health of dependencies first
        if service_name in self._dependencies:
            for dependency in self._dependencies[service_name]:
                dep_status = await self.check_service_health(dependency)
                if dep_status != ServiceStatus.HEALTHY:
                    logger.error(
                        f"Dependency '{dependency}' for service '{service_name}' is not healthy: {dep_status}"
                    )
                    return ServiceStatus.DEGRADED

        if service_name not in self._check_functions:
            raise ValueError(f"Service '{service_name}' is not registered")

        check_function: Callable[[], Awaitable[bool]] = self._check_functions[
            service_name
        ]
        timeout: float = self._timeout.get(service_name, 5.0)
        retry_delay: float = self._retry_delays[service_name]
        max_retries: int = self._max_retries[service_name]

        metrics = {"attempts": 0, "total_delay": 0.0, "last_error": None}

        for attempt in range(max_retries):
            metrics["attempts"] += 1
            try:
                async with asyncio.timeout(timeout):
                    is_healthy = await check_function()
                if is_healthy:
                    async with self._lock:
                        self._services[service_name] = ServiceStatus.HEALTHY
                        self._last_check[service_name] = datetime.now(timezone.utc)

                        if attempt > 0:
                            logger.info(
                                f"Service '{service_name}' recovered after {metrics['attempts']} attempts"
                            )
                    return ServiceStatus.HEALTHY
                async with self._lock:
                    self._services[service_name] = ServiceStatus.DEGRADED
            except asyncio.TimeoutError:
                metrics["last_error"] = (
                    f"Health check for service '{service_name}' timed out after {attempt + 1} attempts"
                )
                if attempt == max_retries - 1:
                    logger.warning(metrics["last_error"])
            except Exception as e:
                metrics["last_error"] = (
                    f"Health check for service '{service_name}' failed on attempt {attempt + 1}: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(metrics["last_error"])
            metrics["total_delay"] += retry_delay
            await asyncio.sleep(retry_delay)

        async with self._lock:
            self._services[service_name] = ServiceStatus.UNHEALTHY
            logger.error(
                f"Service '{service_name}' is unhealthy after {metrics['attempts']} attempts: {metrics['last_error']}"
            )

        return ServiceStatus.UNHEALTHY

    async def check_all_services(self) -> Dict[str, Any]:
        current_time = datetime.now(timezone.utc)
        if (
            self._cached_status is not None
            and self._last_check_time is not None
            and current_time - self._last_check_time < self._cache_duration
        ):
            return self._cached_status

        async with self._lock:
            services = list(self._services.keys())
        tasks = [self.check_service_health(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status = {
            "status": ServiceStatus.HEALTHY,
            "time_stamp": current_time.isoformat(),
            "services": {},
        }

        for service, result in zip(services, results):
            if isinstance(result, Exception):
                health_status["services"][service] = {
                    "status": ServiceStatus.UNHEALTHY,
                    "error": str(result),
                    "last_check": self._last_check[service].isoformat(),
                }
                health_status["status"] = ServiceStatus.DEGRADED
            else:
                health_status["services"][service] = {
                    "status": result,
                    "last_check": self._last_check[service].isoformat(),
                }
                if result != ServiceStatus.HEALTHY:
                    health_status["status"] = ServiceStatus.DEGRADED

        self._cached_status = health_status
        self._last_check_time = current_time

        return health_status

    async def wait_for_services(self, timeout: float = 30.0) -> bool:
        try:
            start_time = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - start_time) < timedelta(
                seconds=timeout
            ):
                status = await self.check_all_services()
                if status["status"] == ServiceStatus.HEALTHY:
                    return True
                await asyncio.sleep(1)
            return False
        except Exception as e:
            logger.error(f"Error while waiting for services to become healthy: {e}")
            return False

    async def cleanup(self) -> None:
        async with self._lock:
            self._services.clear()
            self._check_functions.clear()
            self._last_check.clear()
            self._timeout.clear()
            self._retry_delays.clear()
            self._max_retries.clear()
            self._dependencies.clear()


health_checker = HealthCheck()
