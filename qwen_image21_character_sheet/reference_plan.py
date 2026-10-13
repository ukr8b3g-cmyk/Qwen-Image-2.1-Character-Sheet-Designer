"""Qwen Core's numeric input order and compact image tags, without tensors."""
from dataclasses import dataclass

EXTRA_INPUTS = ('reference_image_1', 'reference_image_2', 'reference_image_3')
REFERENCE_ROLES = ('same_character', 'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'hands', 'footwear')


@dataclass(frozen=True)
class ReferencePlan:
    references: tuple


def build_reference_plan(character_image, reference_image_1=None, reference_image_2=None,
                         reference_image_3=None, *, use_layout_image=False, roles=None):
    """Presence means `is not None`, matching Core, including a ref-2-only case.

    Objects are never copied, read or retained. The layout occupies image_1;
    character/extra inputs always use image_2/image_3/image_4/image_5 respectively.
    """
    if character_image is None:
        return ReferencePlan(())
    roles = roles or dict.fromkeys(EXTRA_INPUTS, 'same_character')
    sources = []
    if use_layout_image:
        sources.append(('layout_image', 'layout', 1))
    sources.append(('character_image', 'character', 2))
    for index, image in enumerate((reference_image_1, reference_image_2, reference_image_3), start=1):
        if image is not None:
            name = f'reference_image_{index}'
            sources.append((name, roles[name], index + 2))
    return ReferencePlan(tuple(
        {'source': source, 'role': role, 'image_number': number,
         'tag': f'<image{number}>', 'core_input': f'images.image_{slot}'}
        for number, (source, role, slot) in enumerate(sources, start=1)))
