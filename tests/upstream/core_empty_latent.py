"""Isolated function excerpt from ComfyUI comfy/sample.py.
Source commit: f1072eb0350638a3390ddb6afbcaa8c6b237c6fd
Original file Git blob: 4ebad9666c6bd12a8b54c4ea2775d74a7712b19c
Tests supply torch/comfy globals and a format stub. This is not a Core install.
"""

def fix_empty_latent_channels(model, latent_image, downscale_ratio_spacial=None, downscale_ratio_temporal=None):
    if latent_image.is_nested:
        return latent_image
    latent_format = model.get_model_object("latent_format")
    is_empty = torch.count_nonzero(latent_image) == 0
    if is_empty:
        if latent_format.latent_channels != latent_image.shape[1]:
            latent_image = comfy.utils.repeat_to_batch_size(latent_image, latent_format.latent_channels, dim=1)
        if downscale_ratio_spacial is not None:
            if downscale_ratio_spacial != latent_format.spacial_downscale_ratio:
                ratio = downscale_ratio_spacial / latent_format.spacial_downscale_ratio
                latent_image = comfy.utils.common_upscale(latent_image, round(latent_image.shape[-1] * ratio), round(latent_image.shape[-2] * ratio), "nearest-exact", crop="disabled")

    if latent_format.latent_dimensions == 3 and latent_image.ndim == 4:
        latent_image = latent_image.unsqueeze(2)

    if is_empty and downscale_ratio_temporal is not None:
        if downscale_ratio_temporal != latent_format.temporal_downscale_ratio:
            ratio = downscale_ratio_temporal / latent_format.temporal_downscale_ratio
            new_t = max(1, round(latent_image.shape[2] * ratio))
            latent_image = comfy.utils.repeat_to_batch_size(latent_image, new_t, dim=2)

    if is_empty:
        latent_image = latent_format.fix_empty_latent(latent_image)

    return latent_image
