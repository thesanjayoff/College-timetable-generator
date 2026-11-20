"""Converts an XHSTT (xhstt.org / Kingston high-school-timetabling archive) instance XML
file directly into this project's solver IR (app.solver.ir.SolverInput), bypassing the
database entirely -- the IR is deliberately ORM-independent, so a real public benchmark
instance can be run through the exact same CP-SAT model and verifier as everything else.

Schema verified against a real downloaded instance (Kottenpark2008, University of Twente
HSTT archive, https://www.utwente.nl/en/eemcs/dmmp/hstt/), not guessed from the spec alone.

Known, deliberate scope limits (documented rather than silently wrong):
  - Only the primary resource for each Role family is used for conflict-tracking:
    a co-teaching event's "Teacher2" (etc.) is not cross-checked against that teacher's
    other classes. The vast majority of events have exactly one teacher; this is a
    simplification for the minority that don't.
  - If an event needs more than one not-yet-assigned room role (rare: a handful of
    "combined subject" lessons need two specialist rooms at once), only the first role
    is modeled; the second is dropped from hard-constraint tracking.
  - Constraint types honored: AvoidClashesConstraint (automatic -- it's just this
    project's normal no-double-booking rule), AvoidUnavailableTimesConstraint (teacher
    unavailability), AssignResourceConstraint/PreferResourcesConstraint (used together to
    resolve each event's eligible room set for an unassigned room role), SplitEventsConstraint
    with min/max amount 1 (automatic -- this project always schedules one occurrence as one
    contiguous block). NOT honored: PreferTimesConstraint, SpreadEventsConstraint,
    LinkEventsConstraint, OrderEventsConstraint, LimitIdleTimesConstraint,
    ClusterBusyTimesConstraint -- these are real soft/structural constraints in the
    instance that this converter does not translate into this project's soft-objective
    terms. A run against a converted instance is therefore a genuine test of the hard
    no-clash/placement machinery, not a full apples-to-apples score against the
    instance's own official objective function.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from types import SimpleNamespace

from app.models.enums import PeriodKind, RoomType
from app.solver.grid import TimeGrid
from app.solver.ir import ReqPart, RequirementGroup, SolverInput


@dataclass
class ConversionReport:
    instance_name: str
    num_days: int
    num_periods_per_day: int
    num_teachers: int
    num_rooms: int
    num_classes: int
    num_events: int
    num_groups_built: int
    num_teacher_unavailable_slots: int
    events_with_unresolved_room: int
    events_with_no_teacher: int
    events_with_multi_teacher: int


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _fake_time_structure(num_days: int, periods_per_day: int):
    days = [SimpleNamespace(day_index=d, name=f"Day{d}", max_period_index=None) for d in range(num_days)]
    periods = [
        SimpleNamespace(period_index=p, kind=PeriodKind.TEACHING, teaching_order=p)
        for p in range(periods_per_day)
    ]
    return SimpleNamespace(id=1, days=days, periods=periods)


def convert_xhstt_instance(xml_path: str) -> tuple[SolverInput, ConversionReport]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    instance = root.find(".//Instance")
    if instance is None:
        raise ValueError("No <Instance> element found -- not a valid XHSTT archive file")

    meta = instance.find("MetaData")
    instance_name = meta.findtext("Name", default="XHSTT instance") if meta is not None else "XHSTT instance"

    # ---- Times: map each Time Id -> (day_index, period_index) ----
    times_el = instance.find("Times")
    day_order: dict[str, int] = {}
    time_slot: dict[str, tuple[int, int]] = {}
    day_period_counts: dict[int, int] = {}
    for time_el in times_el.iterfind("Time"):
        time_id = time_el.get("Id")
        day_ref_el = time_el.find("Day")
        day_ref = day_ref_el.get("Reference") if day_ref_el is not None else None
        if day_ref is None:
            continue
        if day_ref not in day_order:
            day_order[day_ref] = len(day_order)
        day_index = day_order[day_ref]
        suffix = time_id.rsplit("_", 1)[-1]
        period_index = int(suffix) - 1 if suffix.isdigit() else day_period_counts.get(day_index, 0)
        time_slot[time_id] = (day_index, period_index)
        day_period_counts[day_index] = max(day_period_counts.get(day_index, 0), period_index + 1)

    num_days = len(day_order)
    periods_per_day = max(day_period_counts.values()) if day_period_counts else 0

    # ---- Resources: map each Resource Id -> a synthetic int, grouped by ResourceType ----
    resources_el = instance.find("Resources")
    teacher_ids: dict[str, int] = {}
    room_ids: dict[str, int] = {}
    class_ids: dict[str, int] = {}
    resource_group_members: dict[str, set[str]] = {}
    next_int = 1
    for res_el in resources_el.iterfind("Resource"):
        rid = res_el.get("Id")
        rtype_el = res_el.find("ResourceType")
        rtype = rtype_el.get("Reference") if rtype_el is not None else None
        if rtype == "Teacher":
            teacher_ids.setdefault(rid, next_int)
            next_int += 1
        elif rtype == "Room":
            room_ids.setdefault(rid, next_int)
            next_int += 1
        elif rtype == "Class":
            class_ids.setdefault(rid, next_int)
            next_int += 1
        for rg_el in res_el.iterfind("ResourceGroups/ResourceGroup"):
            gref = rg_el.get("Reference")
            resource_group_members.setdefault(gref, set()).add(rid)

    # ---- Events: map each Event Id -> set of its EventGroup memberships ----
    events_el = instance.find("Events")
    event_group_members: dict[str, set[str]] = {}
    event_elements: dict[str, ET.Element] = {}
    for event_el in events_el.iterfind("Event"):
        eid = event_el.get("Id")
        event_elements[eid] = event_el
        for eg_el in event_el.iterfind("EventGroups/EventGroup"):
            gref = eg_el.get("Reference")
            event_group_members.setdefault(gref, set()).add(eid)

    # ---- Constraints: resolve (event, room-role) -> eligible room ids, from
    # PreferResourcesConstraint (the thing that actually names candidate rooms) ----
    constraints_el = instance.find("Constraints")
    event_role_rooms: dict[tuple[str, str], set[int]] = {}
    teacher_unavailable: set[tuple[int, int, int]] = set()
    if constraints_el is not None:
        for c_el in constraints_el:
            tag = _local(c_el.tag)
            if tag == "PreferResourcesConstraint":
                role = c_el.findtext("Role")
                if not role:
                    continue
                applies_events: set[str] = set()
                for eg_ref_el in c_el.iterfind("AppliesTo/EventGroups/EventGroup"):
                    applies_events |= event_group_members.get(eg_ref_el.get("Reference"), set())
                for ev_ref_el in c_el.iterfind("AppliesTo/Events/Event"):
                    applies_events.add(ev_ref_el.get("Reference"))
                room_options: set[int] = set()
                for rg_ref_el in c_el.iterfind("ResourceGroups/ResourceGroup"):
                    for member_id in resource_group_members.get(rg_ref_el.get("Reference"), set()):
                        if member_id in room_ids:
                            room_options.add(room_ids[member_id])
                for res_ref_el in c_el.iterfind("Resources/Resource"):
                    rid = res_ref_el.get("Reference")
                    if rid in room_ids:
                        room_options.add(room_ids[rid])
                for eid in applies_events:
                    event_role_rooms.setdefault((eid, role), set()).update(room_options)
            elif tag == "AvoidUnavailableTimesConstraint":
                teacher_res_ids = [r.get("Reference") for r in c_el.iterfind("AppliesTo/Resources/Resource")]
                teacher_res_ids = [r for r in teacher_res_ids if r in teacher_ids]
                if not teacher_res_ids:
                    continue
                time_refs = [t.get("Reference") for t in c_el.iterfind("Times/Time")]
                for res_id in teacher_res_ids:
                    tid = teacher_ids[res_id]
                    for tref in time_refs:
                        slot = time_slot.get(tref)
                        if slot:
                            teacher_unavailable.add((tid, slot[0], slot[1]))

    all_room_option_ints = tuple(room_ids.values())

    # ---- Events -> RequirementGroup (one event = one weekly occurrence) ----
    groups: list[RequirementGroup] = []
    subject_id_by_course: dict[str, int] = {}
    next_subject_id = 1
    events_with_unresolved_room = 0
    events_with_no_teacher = 0
    events_with_multi_teacher = 0

    for eid, event_el in event_elements.items():
        name = event_el.findtext("Name", default=eid)
        duration = int(event_el.findtext("Duration", default="1"))
        course_el = event_el.find("Course")
        course_ref = course_el.get("Reference") if course_el is not None else eid
        if course_ref not in subject_id_by_course:
            subject_id_by_course[course_ref] = next_subject_id
            next_subject_id += 1
        subject_id = subject_id_by_course[course_ref]

        section_ids: list[int] = []
        teacher_option: int | None = None
        teacher_role_count = 0
        room_role: str | None = None
        room_ref: str | None = None

        for res_el in event_el.iterfind("Resources/Resource"):
            role = res_el.findtext("Role", default="")
            ref = res_el.get("Reference")
            rtype_el = res_el.find("ResourceType")
            rtype = rtype_el.get("Reference") if rtype_el is not None else None
            if rtype == "Class" and ref in class_ids:
                section_ids.append(class_ids[ref])
            elif rtype == "Teacher" or role.startswith("Teacher"):
                teacher_role_count += 1
                if ref in teacher_ids and teacher_option is None:
                    teacher_option = teacher_ids[ref]
            elif role.startswith("Room") and room_role is None:
                room_role = role
                room_ref = ref

        if teacher_option is None:
            events_with_no_teacher += 1
        if teacher_role_count > 1:
            events_with_multi_teacher += 1

        if room_ref is not None and room_ref in room_ids:
            room_options: tuple[int, ...] = (room_ids[room_ref],)
            is_fixed_room = True
        elif room_role is not None:
            candidates = event_role_rooms.get((eid, room_role), set())
            if not candidates:
                candidates = set(all_room_option_ints)
                events_with_unresolved_room += 1
            room_options = tuple(sorted(candidates))
            is_fixed_room = len(room_options) <= 1
        else:
            room_options = ()
            is_fixed_room = True

        part = ReqPart(
            key="main",
            subject_id=subject_id,
            teacher_options=(teacher_option,) if teacher_option is not None else (),
            is_fixed_teacher=True,
            room_type_required=RoomType.CLASSROOM,
            capacity_required=0,
            room_options=room_options,
            is_fixed_room=is_fixed_room,
        )
        groups.append(RequirementGroup(
            id=f"xhstt-{eid}", kind="regular", label=name, subject_id=subject_id,
            occupied_section_ids=tuple(section_ids), parts=(part,), sessions_per_week=1,
            block_size=max(1, duration), spread_across_days=False, max_per_day=99,
            time_structure_id=1, source_ref={"xhstt_event_id": eid},
        ))

    fake_structure = _fake_time_structure(num_days, periods_per_day)
    solver_input = SolverInput(
        groups=groups,
        time_structures={1: TimeGrid(fake_structure)},
        teacher_unavailable=teacher_unavailable,
    )
    report = ConversionReport(
        instance_name=instance_name, num_days=num_days, num_periods_per_day=periods_per_day,
        num_teachers=len(teacher_ids), num_rooms=len(room_ids), num_classes=len(class_ids),
        num_events=len(event_elements), num_groups_built=len(groups),
        num_teacher_unavailable_slots=len(teacher_unavailable),
        events_with_unresolved_room=events_with_unresolved_room,
        events_with_no_teacher=events_with_no_teacher, events_with_multi_teacher=events_with_multi_teacher,
    )
    return solver_input, report
