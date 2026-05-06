from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from lmjm.model import (
    Diagnostic,
    Insemination,
    ProcedureAction,
    ProcedureActionType,
    Weight,
)

if TYPE_CHECKING:
    from lmjm.model import Animal
    from lmjm.repo import AnimalRepo, DiagnosticRepo, InseminationRepo, WeightRepo


class ProcedureConfirmService:
    def __init__(
        self,
        animal_repo: AnimalRepo,
        insemination_repo: InseminationRepo,
        diagnostic_repo: DiagnosticRepo,
        weight_repo: WeightRepo,
    ) -> None:
        self.animal_repo = animal_repo
        self.insemination_repo = insemination_repo
        self.diagnostic_repo = diagnostic_repo
        self.weight_repo = weight_repo

    def apply_actions(self, actions: list[ProcedureAction]) -> tuple[int, int, list[dict[str, str]]]:
        applied_count = 0
        failed_count = 0
        failures: list[dict[str, str]] = []

        for action in actions:
            try:
                self._apply_single_action(action)
                applied_count += 1
            except Exception as exc:
                failed_count += 1
                failures.append(
                    {
                        "ear_tag": action.ear_tag,
                        "action_type": str(action.action_type),
                        "reason": str(exc),
                    }
                )

        return applied_count, failed_count, failures

    def _apply_single_action(self, action: ProcedureAction) -> None:
        if action.action_type == ProcedureActionType.inspected:
            return

        animal = self.animal_repo.get_by_ear_tag(action.ear_tag)
        if not animal:
            raise ValueError(f"Animal not found: {action.ear_tag}")

        if action.action_type == ProcedureActionType.weight:
            self._apply_weight(action, animal)
        elif action.action_type == ProcedureActionType.insemination:
            self._apply_insemination(action, animal)
        elif action.action_type == ProcedureActionType.diagnostic:
            self._apply_diagnostic(action, animal)
        elif action.action_type == ProcedureActionType.observation:
            self._apply_observation(action, animal)
        elif action.action_type == ProcedureActionType.implant:
            self._apply_implant(action, animal)

    def _apply_weight(self, action: ProcedureAction, animal: Animal) -> None:
        date_str = action.weighing_date or ""
        parsed_date = datetime.strptime(date_str, "%Y%m%d")
        formatted = parsed_date.strftime("%Y%m%d")
        weight = Weight(
            pk=animal.pk,
            sk=f"Peso|{formatted}",
            weight_kg=action.weight_kg or 0,
            weighing_date=parsed_date.strftime("%Y-%m-%d"),
        )
        self.weight_repo.put(weight)

    def _apply_insemination(self, action: ProcedureAction, animal: Animal) -> None:
        date_str = action.insemination_date or ""
        parsed = datetime.strptime(date_str, "%Y%m%d")
        insemination = Insemination(
            pk=animal.pk,
            sk=f"Insemination|{parsed.strftime('%Y%m%d')}",
            insemination_date=parsed.strftime("%Y-%m-%d"),
            semen=action.semen or "",
        )
        self.insemination_repo.put(insemination)

        animal.inseminated = True
        animal.implanted = False
        animal.pregnant = False
        animal.transferred = False

        default_note = f"{parsed.strftime('%d-%m-%Y')}: Inseminated {action.semen or ''}"
        if not animal.notes:
            animal.notes = []
        animal.notes.append(default_note)
        if action.note:
            animal.notes.append(action.note)

        self.animal_repo.update(animal)

    def _apply_diagnostic(self, action: ProcedureAction, animal: Animal) -> None:
        date_str = action.diagnostic_date or ""
        diagnostic_date = datetime.strptime(date_str, "%Y%m%d")

        insemination = self.insemination_repo.get_latest(animal.pk)
        if not insemination:
            raise ValueError(f"No insemination found for {action.ear_tag}")

        expected_delivery_date = (
            datetime.strptime(insemination.insemination_date, "%Y-%m-%d") + timedelta(days=292)
        ).strftime("%Y-%m-%d")

        pregnant = action.pregnant if action.pregnant is not None else False

        diagnostic = Diagnostic(
            pk=animal.pk,
            sk=f"Diagnostic|{diagnostic_date.strftime('%Y%m%d')}",
            diagnostic_date=diagnostic_date.strftime("%Y-%m-%d"),
            breeding_date=insemination.insemination_date,
            pregnant=pregnant,
            expected_delivery_date=expected_delivery_date,
            semen=insemination.semen,
        )
        self.diagnostic_repo.put(diagnostic)

        if pregnant:
            animal.pregnant = True
            animal.implanted = False
            animal.inseminated = False
            animal.transferred = False

            edd_formatted = datetime.strptime(expected_delivery_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            default_note = (
                f"{diagnostic_date.strftime('%d-%m-%Y')}: Pregnancy Confirmed. "
                f"{insemination.semen}. EDD: {edd_formatted}"
            )
        else:
            default_note = f"{diagnostic_date.strftime('%d-%m-%Y')}: IATF Failed"

        if not animal.notes:
            animal.notes = []
        animal.notes.append(default_note)
        if action.note:
            animal.notes.append(action.note)
        if action.tags:
            if not animal.tags:
                animal.tags = []
            animal.tags.append(action.tags)

        self.animal_repo.update(animal)

    def _apply_observation(self, action: ProcedureAction, animal: Animal) -> None:
        if not animal.notes:
            animal.notes = []
        animal.notes.append(action.note or "")
        self.animal_repo.update(animal)

    def _apply_implant(self, action: ProcedureAction, animal: Animal) -> None:
        animal.implanted = True
        animal.inseminated = False
        animal.pregnant = False
        animal.transferred = False

        if not animal.notes:
            animal.notes = []
        animal.notes.append("Implante realizado")

        self.animal_repo.update(animal)
