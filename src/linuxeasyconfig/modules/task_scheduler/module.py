from __future__ import annotations

from linuxeasyconfig.core.module_api import (
    FeatureDefinition,
    LECModule,
    ViewDefinition,
)

from .repository import TaskSchedulerRepository
from .views import TaskSchedulerView


class TaskSchedulerModule(LECModule):
    def __init__(self) -> None:
        self._repository = TaskSchedulerRepository()

    def feature_definitions(self) -> list[FeatureDefinition]:
        return [
            FeatureDefinition(
                id="task_scheduler.main",
                title="Task Scheduler",
                target_type="view",
                target_id="task_scheduler.main",
                description=(
                    "Create LEC scheduled tasks and inspect existing "
                    "systemd timers and cron schedules."
                ),
                category="System",
                icon="view-calendar-tasks",
                keywords=(
                    "schedule",
                    "task",
                    "timer",
                    "cron",
                    "systemd",
                    "automation",
                ),
            )
        ]

    def view_definitions(self) -> list[ViewDefinition]:
        return [
            ViewDefinition(
                id="task_scheduler.main",
                title="Task Scheduler",
                view_type="custom",
                data={
                    "factory": lambda: TaskSchedulerView(
                        self._repository
                    )
                },
            )
        ]
