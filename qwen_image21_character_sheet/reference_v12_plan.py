"""Per-output reference selection, shared by prompt authoring and encoding."""
import json

from .common.state import StateValidationError, decode_json
from .multi_reference_compiler import (
    BODY_IDS, CLOTHING_IDS, MULTI_VIEW_IDS, PORTRAIT_IDS, role_views,
    validate_reference_presence,
)
from .reference_plan import EXTRA_INPUTS, REFERENCE_ROLES

SOURCES = ('layout_image', 'character_image', *EXTRA_INPUTS)


def build_reference_plan(state, presence, *, use_layout_image=False):
    presence = validate_reference_presence(presence)
    winners = {}
    for source in EXTRA_INPUTS:
        role = state['reference_roles'][source]
        if presence[source] and role != 'same_character':
            winners[role] = source
    selected = set()
    missing = []
    need_character = False
    subject = False
    for view in state['views']:
        is_subject = view in (*PORTRAIT_IDS, *BODY_IDS) or (
            view in CLOTHING_IDS and state['clothing_mode'] == 'worn')
        subject |= is_subject
        applicable = {role: source for role, source in winners.items()
                      if view in role_views(state, role)}
        if view in CLOTHING_IDS and state['clothing_mode'] == 'garment':
            applicable = {r: s for r, s in applicable.items()
                          if r in ('clothing', 'clothing_front', 'clothing_back')}
        selected.update(applicable.values())
        needs_base = is_subject or not applicable
        need_character |= needs_base
        if needs_base and not presence['character_image']:
            missing.append(view)
    if subject:
        selected.update(source for source in EXTRA_INPUTS if presence[source]
                        and state['reference_roles'][source] == 'same_character')
    entries = []
    if use_layout_image:
        entries.append({'source': 'layout_image', 'role': 'layout'})
    if need_character and presence['character_image']:
        entries.append({'source': 'character_image', 'role': 'character'})
    entries.extend({'source': source, 'role': state['reference_roles'][source]}
                   for source in EXTRA_INPUTS if source in selected)
    plan = {'schema_version': 1, 'view_ids': list(state['views']), 'sources': entries}
    return plan, missing


def numbered_references(plan):
    return [{**source, 'image_number': number, 'tag': f'<image{number}>'}
            for number, source in enumerate(plan['sources'], 1)]


def parse_reference_plan(raw):
    plan = decode_json(raw)
    if type(plan) is not dict or set(plan) != {'schema_version', 'view_ids', 'sources'}:
        raise StateValidationError('Invalid reference plan fields.', 'invalid_reference_plan')
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise StateValidationError('Unsupported reference plan version.', 'invalid_reference_plan')
    views = plan['view_ids']
    if type(views) is not list or not views or any(type(v) is not str or v not in MULTI_VIEW_IDS for v in views) or len(set(views)) != len(views):
        raise StateValidationError('Invalid reference plan views.', 'invalid_reference_plan')
    entries = plan['sources']
    if type(entries) is not list or not entries or len(entries) > len(SOURCES):
        raise StateValidationError('Invalid reference sources.', 'invalid_reference_plan')
    ranks = []
    for entry in entries:
        if type(entry) is not dict or set(entry) != {'source', 'role'} or entry['source'] not in SOURCES:
            raise StateValidationError('Unknown reference source.', 'invalid_reference_plan')
        source, role = entry['source'], entry['role']
        allowed = ('layout',) if source == 'layout_image' else ('character',) if source == 'character_image' else REFERENCE_ROLES
        if role not in allowed:
            raise StateValidationError('Invalid source role.', 'invalid_reference_plan')
        ranks.append(SOURCES.index(source))
    if ranks != sorted(set(ranks)) or not any(e['source'] != 'layout_image' for e in entries):
        raise StateValidationError('References must be unique and ordered, with a subject reference.', 'invalid_reference_plan')
    return plan


def serialize_reference_plan(plan):
    return json.dumps(plan, ensure_ascii=False, separators=(',', ':'))
